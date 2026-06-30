#!/usr/bin/env python3
"""
kb_to_chunks.py — Convert KB axiom/theorem/assumption nodes into
DiscoverInput JSONL chunks for Phase 2 pipeline ingestion.

Reads knowledge-base/nodes/{axioms,theorems,assumptions}/*.json and emits
one DiscoverInput per node, where the "text" field is the node's `nl`
(natural language description) and `domain` is taken from the node's
domain tag (defaulting to "general" if missing).

Usage:
    python scripts/kb_to_chunks.py \\
        --output /tmp/ax-test/kb_chunks.jsonl

Then run the Phase 2 pipeline:
    python3 knowledge-base/ingest/pipeline.py \\
        --input /tmp/ax-test/kb_chunks.jsonl \\
        --output /tmp/ax-test/kb_records.jsonl
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KB_NODES = ROOT / "knowledge-base" / "nodes"


def load_nodes(type_dir: str) -> list[dict]:
    """Load all JSON nodes from a KB subdirectory."""
    p = KB_NODES / type_dir
    if not p.exists():
        return []
    out = []
    for f in sorted(p.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            data["_source_file"] = f.name
            data["_type_dir"] = type_dir
            out.append(data)
        except Exception as e:
            print(f"  warn: failed to load {f}: {e}", file=sys.stderr)
    return out


def to_discover_input(node: dict) -> dict | None:
    """Convert a KB node into a DiscoverInput dict (matches DiscoverInput
    fields in knowledge-base/ingest/discover.py: chunk_id, text,
    source_paper, domain).

    Text source priority (longest first to maximise discover signal):
      1. node.nl_long (long-form natural language, on axioms/theorems)
      2. node.description (verbose prose)
      3. concatenated aliases + nl (fallback synthesis)
      4. synthetic prose from title + abstract + summary + content
         (for literature/value_anchor/scenario nodes that lack `nl`)
      5. node.nl alone (canonical formal statement)

    Filter: skip nodes where the longest available text is < 100 chars,
    because Phase 1's call_1_discover rejects chunks shorter than
    DISCOVER_MIN_TEXT_LENGTH.
    """
    # Tier 1+2+3: existing rich NL fields
    rich_candidates = [
        node.get("nl_long", "").strip(),
        node.get("description", "").strip(),
        ("; ".join(filter(None, (node.get("aliases") or []))) +
         " | " + node.get("nl", "").strip()).strip(" |"),
    ]
    # Tier 4: synthetic prose from whatever's available (literature,
    # value_anchors, scenarios tend to have title + abstract / summary / content)
    parts = []
    for key in ("abstract_nl", "abstract", "summary", "content", "body", "narrative"):
        v = (node.get(key) or "").strip()
        if v:
            parts.append(v)
    title = (node.get("title") or "").strip()
    if title:
        parts.insert(0, title)

    # value_anchor-specific: combine label + description + cross-cultural note
    label_en = (node.get("label_en") or "").strip()
    label_zh = (node.get("label_zh") or "").strip()
    desc = (node.get("description") or "").strip()
    cc = (node.get("cross_cultural_consistency") or "").strip()
    va_class = (node.get("value_class") or "").strip()
    va_sub = (node.get("value_subclass") or "").strip()
    if label_en or desc:
        va_text = f"Value anchor ({va_class}/{va_sub}): {label_en}"
        if label_zh:
            va_text += f" [{label_zh}]"
        va_text += f". {desc}"
        if cc:
            va_text += f" Cross-cultural consistency: {cc}."
        parts.append(va_text)

    if parts:
        rich_candidates.append("\n\n".join(parts))

    # Tier 5: formal statement alone (last resort)
    rich_candidates.append(node.get("nl", "").strip())

    text = max((c for c in rich_candidates if c), key=len, default="")
    if len(text) < 100:
        return None

    # domain: KB schema has either a single `domain` string or a list
    domain = node.get("domain")
    if isinstance(domain, list):
        domain = domain[0] if domain else "general"
    domain = (domain or "general").strip()

    # DiscoverInput has a fixed VALID_DOMAINS whitelist
    # (game_theory / mechanism_design / social_choice / welfare_economics /
    #  credit_systems / political_philosophy / ml_fairness / history /
    #  math / other). Map KB domains into the closest valid one.
    DOMAIN_MAP = {
        "feature_attribution": "ml_fairness",
        "shap": "ml_fairness",
        "ml_fairness": "ml_fairness",
        "moral": "political_philosophy",
        "value": "political_philosophy",
        "fairness": "political_philosophy",
        "scenarios": "other",
        "general": "other",
    }
    domain = DOMAIN_MAP.get(domain, "other")

    # For non-axiom nodes, infer domain from type_dir
    if domain == "other" and node.get("_type_dir") == "literature":
        domain = "ml_fairness"
    if domain == "other" and node.get("_type_dir") == "value_anchors":
        domain = "political_philosophy"

    # source_paper: prefer 'source' field, else id, else "unknown"
    source = (
        node.get("source")
        or node.get("source_paper")
        or node.get("citation")
        or node.get("authors")  # literature nodes often have this
        or f"KB/{node.get('_type_dir', 'unknown')}/{node.get('id', 'unknown')}"
    )

    return {
        "chunk_id": node.get("id") or node["_source_file"].replace(".json", ""),
        "text": text,
        "source_paper": source,
        "domain": domain,
        # Tags from KB node — used by pipeline to route to special tiers
        # (e.g. tag "impossibility" triggers Tier D Z3 verification)
        "tags": list(node.get("tags") or []),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True,
                    help="Output JSONL path (one DiscoverInput per line)")
    ap.add_argument("--types", nargs="+",
                    default=[
                        "axioms", "theorems", "assumptions",
                        "literature", "value_anchors", "scenarios",
                    ],
                    help="KB node subdirs to include")
    ap.add_argument("--limit", type=int, default=0,
                    help="Optional cap on number of chunks (0 = no cap)")
    args = ap.parse_args()

    inputs = []
    for t in args.types:
        nodes = load_nodes(t)
        n_skipped = 0
        for n in nodes:
            di = to_discover_input(n)
            if di is None:
                n_skipped += 1
                continue
            inputs.append(di)
        print(f"  {t}: {len(nodes)} nodes, {len(nodes) - n_skipped} kept, "
              f"{n_skipped} skipped (short text)", file=sys.stderr)

    if args.limit and len(inputs) > args.limit:
        inputs = inputs[: args.limit]
        print(f"  limit: kept first {args.limit}", file=sys.stderr)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for di in inputs:
            f.write(json.dumps(di, ensure_ascii=False) + "\n")
    print(f"Wrote {len(inputs)} chunks → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())