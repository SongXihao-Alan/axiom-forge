#!/usr/bin/env python3
"""
Axiom Forge — KB Node Extractor (literature → KB JSON)

Given a paper record (from literature_fetcher.py), extracts structured
KB nodes of types: literature, axiom, assumption, theorem, value_anchor.

Two modes:
  (1) Rule-based: NL heuristics from title + abstract → draft nodes
  (2) M3-powered: hand off to LLM for richer extraction (when MINIMAX_API_KEY set)

Output: drafts/*.json (for human review before commit to kb/nodes/)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

# ── Rule-based axiom / theorem extraction ──────────────────────────────
# These heuristics extract candidate axiom/theorem statements from paper
# abstracts. ML papers rarely use the word "axiom" — they say "framework",
# "method", "property", "principle" instead. The patterns below cover both
# the formal-math phrasing (Shapley 1953 style) and the modern-ML phrasing.
AXIOM_PATTERNS = [
    # Formal: "propose a/the X axiom/property/principle"
    re.compile(r"\b(?:we )?propose (?:an? |the )?([A-Z][A-Za-z0-9\- ]{2,60}) (axiom|property|principle|requirement|condition)\b", re.IGNORECASE),
    re.compile(r"\b(?:we )?introduce (?:an? |the )?([A-Z][A-Za-z0-9\- ]{2,60}) (axiom|property|principle|framework|method)\b", re.IGNORECASE),
    # "the X axiom/property" (just naming)
    re.compile(r"\b(?:the )?([A-Z][A-Za-z\-]+(?:\s+[A-Z][A-Za-z\-]+){0,5}) (axiom|property|principle)\b"),
    # ALL CAPS or "SHAP-like" abbreviations: "EFF axiom", "DUM property"
    re.compile(r"\b(?:the )?([A-Z][A-Z\-]{1,10}) (axiom|property|condition|criterion)\b"),
    # ML style: "we propose a framework / method for"
    re.compile(r"\b(?:we )?(?:propose|introduce|present|develop) (?:an? |the )?([A-Z][A-Za-z0-9\- ]{2,60}) (framework|method|approach|metric|measure|score)\b", re.IGNORECASE),
    # ML style: "we propose/introduce X, a/an Y" — restrict Y to axiom-like kinds
    # (algorithm/framework/measure/principle/...). Plain "novel X" or "training-free X"
    # is a paper-style intro, not an axiom-equivalent.
    re.compile(r"\b(?:we )?(?:propose|introduce|present|develop) ([A-Z][A-Za-z0-9\-\$]{1,30})(?:\s|,)+(?:an? |the )?(algorithm|framework|measure|principle|metric|method|approach|definition|criterion|property|score|index)\b", re.IGNORECASE),
    # "our X framework/property"
    re.compile(r"\bour ([A-Z][A-Za-z\-]+(?:\s+[A-Z][A-Za-z\-]+){0,3}) (framework|property|principle|method|approach)\b"),
]
THEOREM_PATTERNS = [
    # "we prove/show/demonstrate that X"
    re.compile(r"\b(?:we )?(?:prove|show|demonstrate|establish) (?:that )?([A-Z][A-Za-z0-9 ,\-:]{8,200}?)(?:\.|$)", re.IGNORECASE | re.MULTILINE),
    # "Theorem 1: ..." or "Theorem 1. ..."
    re.compile(r"\bTheorem\s+\d+(?:\.\d+)?[\.:]?\s*([A-Z][^\.]{10,200})"),
    # "Our main result: ..."
    re.compile(r"\b(?:Main|Our) (?:Result|Theorem|Proposition|Lemma|Corollary)[\.:]?\s*([A-Z][^\.]{10,200})"),
    # "X implies Y" / "X iff Y"  (theorem-like claims)
    re.compile(r"\b([A-Z][A-Za-z\-]+(?:\s+[a-z]+){2,8}) (?:implies|⇔|iff|is equivalent to) ([A-Z][A-Za-z\-]+(?:\s+[a-z]+){0,8})"),
    # "we prove (a bound)..."
    re.compile(r"\b(?:we )?prove (?:an? |the )?(bound|convergence rate|approximation|existence|uniqueness|hardness|complexity) ([^.]{5,100})", re.IGNORECASE),
]
ASSUMPTION_PATTERNS = [
    re.compile(r"\b(?:we )?assume (?:that )?([a-z][^\.]{10,150})", re.IGNORECASE),
    re.compile(r"\b(?:under (?:the )?assumption (?:that )?)([a-z][^\.]{10,150})", re.IGNORECASE),
    re.compile(r"\bcharacteristic function[^.]*?v\(S\)\s*[:=]\s*([^.]+)"),
]


def extract_literature_node(paper: dict) -> dict:
    """Always produce a 'literature' node from a paper record."""
    return {
        "id": _id_for_literature(paper),
        "type": "literature",
        "version": "1.0",
        "created": time.strftime("%Y-%m-%d"),
        "status": "seed",
        "title": paper.get("title", "").strip(),
        "authors": paper.get("authors", []),
        "year": int(paper.get("year") or paper.get("published", "2020")[:4]),
        "venue": paper.get("venue", ""),
        "domain": _guess_domain(paper),
        "arxiv_id": paper.get("arxiv_id") or (paper["id"] if paper.get("source") == "arxiv" else None),
        "s2_id": paper.get("id") if paper.get("source") == "s2" else None,
        "url": paper.get("url", ""),
        "abstract_nl": paper.get("abstract", "").strip(),
        "anchors": [
            {"type": "community", "supporters": [paper.get("venue") or paper.get("source", "unknown")]}
        ],
        "source": {
            "primary": f"ingest:literature_fetcher.py source={paper.get('source')}",
            "external_ids": {
                k: v for k, v in {
                    "arxiv": paper.get("arxiv_id") or (paper["id"] if paper.get("source") == "arxiv" else None),
                    "s2": paper.get("id") if paper.get("source") == "s2" else None,
                }.items() if v
            }
        },
        "process_meta": {
            "[AUTO-INGEST]": f"Generated by kb/ingest/extract_nodes.py on {time.strftime('%Y-%m-%d')}",
        }
    }


def _id_for_literature(paper: dict) -> str:
    """Generate LIT-<venue>-<year>-<n> id, fall back to LIT-<arxiv-id>."""
    arxiv_id = paper.get("arxiv_id") or (paper["id"] if paper.get("source") == "arxiv" else None)
    if arxiv_id:
        return f"LIT-ARXIV-{arxiv_id.replace('/', '-').replace('.', '-')[:24]}"
    s2_id = paper.get("id", "")
    return f"LIT-S2-{s2_id[:16]}"


def _guess_domain(paper: dict) -> str:
    text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()
    if "shap" in text or "shapley" in text or "attribution" in text:
        return "feature_attribution"
    if "mechanism design" in text or "strategy-proof" in text:
        return "mechanism_design"
    if "voting" in text or "arrow" in text:
        return "social_choice"
    if "fair division" in text or "envy-free" in text:
        return "fair_division"
    if "moral" in text or "ethical" in text:
        return "moral"
    if "philosophical" in text or "kantian" in text or "rawls" in text:
        return "philosophical"
    return "methodology"


def extract_axiom_drafts(paper: dict) -> list[dict]:
    """Rule-based axiom/theorem/assumption extraction from title + abstract."""
    text = (paper.get("title", "") + "\n" + paper.get("abstract", ""))
    drafts = []
    lit_id = _id_for_literature(paper)

    for i, pat in enumerate(AXIOM_PATTERNS):
        for j, m in enumerate(pat.finditer(text)):
            label = m.group(1).strip()
            kind = m.group(2).lower() if m.lastindex and m.lastindex >= 2 else "framework"
            if len(label) < 3 or len(label) > 80:
                continue
            drafts.append({
                "id": f"AX-DRAFT-{_id_for_literature(paper)[-8:]}-{i}-{j}",
                "type": "axiom",
                "status": "draft",
                "label": label,
                "kind_hint": kind,
                "linage_in": [lit_id],
                "anchors": [{"type": "empirical", "subtype": "literature_extracted"}],
                "source": {
                    "primary": lit_id,
                    "extracted_from": f"{lit_id} abstract",
                }
            })
    return drafts


def extract_theorem_drafts(paper: dict) -> list[dict]:
    text = paper.get("abstract", "")
    drafts = []
    lit_id = _id_for_literature(paper)

    for i, pat in enumerate(THEOREM_PATTERNS):
        for j, m in enumerate(pat.finditer(text)):
            # For the 5-tuple pattern (lastindex == 3), m.group(1) is the X part
            if m.lastindex and m.lastindex >= 3:
                stmt = f"{m.group(1).strip()} → {m.group(2).strip()}"
            else:
                stmt = (m.group(1) or "").strip()
            if len(stmt) < 10 or len(stmt) > 250:
                continue
            drafts.append({
                "id": f"TH-DRAFT-{_id_for_literature(paper)[-8:]}-{i}-{j}",
                "type": "theorem",
                "status": "draft",
                "nl": stmt,
                "linage_in": [lit_id],
                "anchors": [{"type": "empirical", "subtype": "literature_extracted"}],
                "source": {
                    "primary": lit_id,
                    "extracted_from": f"{lit_id} abstract",
                }
            })
    return drafts


# ── M3-powered deep extraction (optional) ──────────────────────────────
def m3_extract(paper: dict) -> dict:
    """Use MINIMAX to extract richer KB nodes from paper abstract."""
    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        return {}
    base_url = os.environ.get("MINIMAX_BASE_URL", "https://api.minimaxi.com/v1")
    model = os.environ.get("MINIMAX_MODEL", "MiniMax-M3")
    system = (
        "You are a knowledge-base extraction assistant for Axiom Forge. "
        "Given a paper's title + abstract, extract structured nodes: "
        "literature, axiom, assumption, theorem, value_anchor. "
        "Output ONLY a JSON object with keys: literature, axioms, theorems, "
        "assumptions, value_anchors. Each list/empty if not present."
    )
    user = json.dumps({
        "title": paper.get("title"),
        "abstract": paper.get("abstract"),
    }, ensure_ascii=False, indent=2)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "max_tokens": 4000,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode("utf-8"))
        raw = data["choices"][0]["message"]["content"]
        # Strip <think>...</think>
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        return json.loads(raw)
    except Exception as e:
        print(f"[m3] error: {e}", file=sys.stderr)
        return {}


# ── Main ────────────────────────────────────────────────────────────────
def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="input", required=True,
                   help="candidates.json from literature_fetcher.py")
    p.add_argument("--out", default=str(ROOT / "kb" / "ingest" / "drafts"),
                   help="Output directory for draft KB node JSONs")
    p.add_argument("--limit", type=int, default=50,
                   help="Max papers to process (default: 50)")
    p.add_argument("--use-m3", action="store_true",
                   help="Also call MINIMAX_API_KEY for richer extraction (optional)")
    args = p.parse_args()

    candidates = json.loads(Path(args.input).read_text(encoding="utf-8"))
    papers = candidates.get("papers", [])[:args.limit]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processing {len(papers)} papers...", file=sys.stderr)
    n_lit = n_ax = n_th = 0
    for i, paper in enumerate(papers):
        lit_id = _id_for_literature(paper)
        # Always emit literature node
        lit = extract_literature_node(paper)
        (out_dir / f"{lit_id}.json").write_text(
            json.dumps(lit, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        n_lit += 1

        # Rule-based axiom + theorem drafts
        for ax in extract_axiom_drafts(paper):
            (out_dir / f"{ax['id']}.json").write_text(
                json.dumps(ax, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            n_ax += 1
        for th in extract_theorem_drafts(paper):
            (out_dir / f"{th['id']}.json").write_text(
                json.dumps(th, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            n_th += 1

        # Optional: M3 deep extraction
        if args.use_m3:
            deep = m3_extract(paper)
            if deep:
                for j, ax in enumerate(deep.get("axioms", [])):
                    ax["id"] = ax.get("id") or f"AX-M3-{lit_id[-8:]}-{j}"
                    ax["type"] = "axiom"
                    ax["status"] = "draft"
                    ax["linage_in"] = [lit_id]
                    (out_dir / f"{ax['id']}.json").write_text(
                        json.dumps(ax, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                    n_ax += 1
            time.sleep(1.0)  # be polite to API

    print(f"Done: {n_lit} literature + {n_ax} axiom drafts + {n_th} theorem drafts",
          file=sys.stderr)
    print(f"Wrote drafts to {out_dir}/", file=sys.stderr)
    print("Review and rename before moving to kb/nodes/<type>/", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
