#!/usr/bin/env python3
"""
Axiom Forge — Literature Fetcher (arXiv + Semantic Scholar + Google Scholar)

Pulls SHAP / axiomatic attribution / feature importance / Thomson-style
mechanism design / social choice papers from three sources, deduplicates,
and emits a unified candidate list for the KB ingest agent.

Sources:
  arXiv  — official API, no key needed (https://info.arxiv.org/help/api/)
  S2     — Semantic Scholar Graph API, key optional
  GS     — Google Scholar via scholarly lib (manual/assisted, no official API)

Scope (Q4 spec, 2026-06-22):
  Within: microeconomic theory, political science, history, philosophy, math
  Adjacent: feature attribution, axiomatic method, mechanism design,
            social choice, fair division, voting theory, structural models

Usage:
  # Smoke test: 5 papers from arXiv
  python kb/ingest/literature_fetcher.py --source arxiv --max 5

  # Full search, all sources
  python kb/ingest/literature_fetcher.py --max 30 --out /tmp/forge_candidates.json

  # Single keyword, single source
  python kb/ingest/literature_fetcher.py --source s2 --query "anchored SHAP" --max 10

Env:
  S2_API_KEY  — Semantic Scholar API key (optional, raises rate limit)
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parent.parent.parent  # axiom-finder/ (3 levels up from kb/ingest/)
KB_NODES = ROOT / "kb" / "nodes"
DEFAULT_OUT = ROOT / "kb" / "ingest" / "candidates.json"

# ── arXiv query bank (Q4 spec scope) ────────────────────────────────────
ARXIV_CATEGORIES = ["cs.LG", "stat.ML", "cs.AI", "cs.GT", "econ.TH", "econ.EM"]

ARXIV_KEYWORDS = [
    # SHAP / feature attribution
    "SHAP axiomatic attribution",
    "SHAP feature importance",
    "Shapley value attribution",
    "Structural Importance Shapley",
    "anchored SHAP",
    "asymmetric SHAP",
    "SHAP interaction values",
    "SHAP fairness",
    "causal Shapley value",
    "axiomatic feature attribution",
    # mechanism design / social choice (Thomson 2023 scope)
    "axiomatic mechanism design",
    "strategy-proofness allocation",
    "population monotonicity",
    "no-envy fair allocation",
    "social choice axiomatic",
    "voting theory impossibility",
    "Arrow impossibility theorem",
    "fair division algorithm",
    # adjacent: theoretical econ + political philosophy
    "axiomatic welfare economics",
    "Rawls maximin formalization",
    "Harsanyi utilitarianism formal",
    "cooperative game theory axiom",
]

# ── Semantic Scholar query bank ─────────────────────────────────────────
S2_FIELDS = [
    "SHAP",
    "Shapley value",
    "axiomatic attribution",
    "feature importance axioms",
    "axiomatic mechanism design",
    "social choice axiomatic",
    "impossibility theorem",
    "voting theory",
    "fair division",
    "cooperative game theory",
]

# ── HTTP helpers ────────────────────────────────────────────────────────
def _http_get(url: str, headers: dict | None = None, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers=headers or {})
    # Use certifi's CA bundle if available; fall back to system default.
    # This is needed on macOS where Python's bundled OpenSSL doesn't trust
    # the system keychain CA that curl uses.
    ctx = None
    try:
        import ssl
        import certifi  # type: ignore
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass  # certifi not installed; let urllib fall back to default
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read()


def _http_get_json(url: str, headers: dict | None = None) -> dict | list:
    raw = _http_get(url, headers=headers)
    return json.loads(raw.decode("utf-8"))


# ── arXiv fetcher ───────────────────────────────────────────────────────
def arxiv_search(query: str, max_results: int = 10,
                 year_from: int = 2020) -> list[dict]:
    """arXiv API: http://export.arxiv.org/api/query?search_query=...&start=0&max_results=..."""
    cat_clause = " OR ".join(f"cat:{c}" for c in ARXIV_CATEGORIES)
    # Both query and cat_clause must be URL-quoted (spaces → %20, OR → OR)
    quoted_q = urllib.parse.quote(f"({query})", safe="()")
    quoted_cats = urllib.parse.quote(f"({cat_clause})", safe="():")
    search = f"{quoted_q}+AND+{quoted_cats}"  # arXiv API: spaces in search_query → + (form-encoded)
    url = (
        f"https://export.arxiv.org/api/query?search_query={search}"
        f"&start=0&max_results={max_results}"
        f"&sortBy=submittedDate&sortOrder=descending"
    )
    raw = _http_get(url, timeout=60).decode("utf-8")
    return _parse_arxiv_atom(raw)


_ARXIV_ENTRY = re.compile(
    r"<entry>(.*?)</entry>", re.DOTALL
)
_ARXIV_ID = re.compile(r"<id>(http://arxiv\.org/abs/[^<]+)</id>")
_ARXIV_TITLE = re.compile(r"<title>(.*?)</title>", re.DOTALL)
_ARXIV_SUMMARY = re.compile(r"<summary>(.*?)</summary>", re.DOTALL)
_ARXIV_AUTHOR = re.compile(r"<author>\s*<name>([^<]+)</name>", re.DOTALL)
_ARXIV_PUB = re.compile(r"<published>(\d{4}-\d{2}-\d{2})")


def _parse_arxiv_atom(xml: str) -> list[dict]:
    out = []
    for m in _ARXIV_ENTRY.finditer(xml):
        entry = m.group(1)
        arxiv_id_m = _ARXIV_ID.search(entry)
        title_m = _ARXIV_TITLE.search(entry)
        summary_m = _ARXIV_SUMMARY.search(entry)
        pub_m = _ARXIV_PUB.search(entry)
        if not (arxiv_id_m and title_m and summary_m and pub_m):
            continue
        arxiv_id = arxiv_id_m.group(1).split("/abs/")[-1]
        authors = _ARXIV_AUTHOR.findall(entry)
        out.append({
            "source": "arxiv",
            "id": arxiv_id,
            "url": arxiv_id_m.group(1),
            "title": re.sub(r"\s+", " ", title_m.group(1)).strip(),
            "abstract": re.sub(r"\s+", " ", summary_m.group(1)).strip(),
            "authors": authors,
            "published": pub_m.group(1),
        })
    return out


# ── Semantic Scholar fetcher ───────────────────────────────────────────
def s2_search(query: str, max_results: int = 10,
              year_from: int = 2020) -> list[dict]:
    """S2 Graph API: https://api.semanticscholar.org/graph/v1/paper/search"""
    headers = {}
    api_key = os.environ.get("S2_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key
    params = {
        "query": query,
        "limit": min(max_results, 100),
        "year": f"{year_from}-",
        "fields": "paperId,title,abstract,authors,year,citationCount,venue,externalIds",
    }
    url = "https://api.semanticscholar.org/graph/v1/paper/search?" + urllib.parse.urlencode(params)
    data = _http_get_json(url, headers=headers)
    if not isinstance(data, dict) or "data" not in data:
        return []
    out = []
    for p in data["data"]:
        arxiv_id = (p.get("externalIds") or {}).get("ArXiv")
        out.append({
            "source": "s2",
            "id": p.get("paperId", ""),
            "arxiv_id": arxiv_id,
            "url": f"https://www.semanticscholar.org/paper/{p.get('paperId', '')}",
            "title": (p.get("title") or "").strip(),
            "abstract": (p.get("abstract") or "").strip(),
            "authors": [a.get("name", "") for a in (p.get("authors") or [])],
            "year": p.get("year"),
            "citation_count": p.get("citationCount", 0),
            "venue": p.get("venue"),
        })
    return out


# ── Google Scholar fetcher (optional, requires `scholarly` lib) ────────
def gs_search(query: str, max_results: int = 10) -> list[dict]:
    """Google Scholar via scholarly (pip install scholarly).
    NOTE: Google aggressively rate-limits Scholar scraping; expect 429/403.
    Use sparingly; prefer arXiv + S2 for bulk fetches.
    """
    try:
        from scholarly import scholarly, ProxyGenerator  # type: ignore
    except ImportError:
        print("[gs] 'scholarly' not installed; skipping. `pip install scholarly` to enable.",
              file=sys.stderr)
        return []
    out = []
    try:
        pg = ProxyGenerator()
        if pg.FreeProxies():
            scholarly.use_proxy(pg)
    except Exception:
        pass
    search_query = scholarly.search_pubs(query)
    for _ in range(max_results):
        try:
            pub = next(search_query)
        except StopIteration:
            break
        except Exception as e:
            print(f"[gs] fetch error: {e}", file=sys.stderr)
            break
        bib = pub.get("bib", {})
        out.append({
            "source": "gs",
            "id": pub.get("url_scholarbib", ""),
            "url": pub.get("url", ""),
            "title": (bib.get("title") or "").strip(),
            "abstract": (bib.get("abstract") or "").strip(),
            "authors": bib.get("author", []),
            "year": bib.get("pub_year"),
        })
        time.sleep(2.0)  # be polite
    return out


# ── Dedup + unify ───────────────────────────────────────────────────────
def dedup(records: list[dict]) -> list[dict]:
    """Prefer arXiv ID match; fall back to title similarity."""
    seen_arxiv: dict[str, dict] = {}
    seen_title: dict[str, dict] = {}
    out: list[dict] = []
    for r in records:
        arxiv_id = r.get("arxiv_id") or (r["id"] if r.get("source") == "arxiv" else None)
        title_key = re.sub(r"\W+", " ", (r.get("title") or "").lower()).strip()[:80]
        if arxiv_id and arxiv_id in seen_arxiv:
            seen_arxiv[arxiv_id].setdefault("also_found_in", []).append(r["source"])
            continue
        if title_key and title_key in seen_title:
            seen_title[title_key].setdefault("also_found_in", []).append(r["source"])
            continue
        if arxiv_id:
            seen_arxiv[arxiv_id] = r
        if title_key:
            seen_title[title_key] = r
        out.append(r)
    return out


# ── CLI ─────────────────────────────────────────────────────────────────
def main() -> int:
    p = argparse.ArgumentParser(description="Axiom Forge literature fetcher")
    p.add_argument("--source", choices=["arxiv", "s2", "gs", "all"],
                   default="all", help="Source to query (default: all)")
    p.add_argument("--query", help="Single query (default: query bank per source)")
    p.add_argument("--max", type=int, default=10,
                   help="Max results per query (default: 10)")
    p.add_argument("--year-from", type=int, default=2020,
                   help="Earliest year (default: 2020)")
    p.add_argument("--out", default=str(DEFAULT_OUT),
                   help=f"Output JSON (default: {DEFAULT_OUT})")
    p.add_argument("--append", action="store_true",
                   help="Append to existing output file instead of overwriting")
    args = p.parse_args()

    sources = ["arxiv", "s2", "gs"] if args.source == "all" else [args.source]
    records: list[dict] = []

    for src in sources:
        if src == "arxiv":
            queries = [args.query] if args.query else ARXIV_KEYWORDS
            for q in queries:
                print(f"[arxiv] {q} ...", file=sys.stderr)
                try:
                    batch = arxiv_search(q, args.max, args.year_from)
                    for r in batch:
                        r["search_query"] = q
                    records.extend(batch)
                except Exception as e:
                    print(f"[arxiv] error: {e}", file=sys.stderr)
                time.sleep(3.0)  # arXiv rate limit: 1 req / 3s polite
        elif src == "s2":
            queries = [args.query] if args.query else S2_FIELDS
            for q in queries:
                print(f"[s2] {q} ...", file=sys.stderr)
                try:
                    batch = s2_search(q, args.max, args.year_from)
                    for r in batch:
                        r["search_query"] = q
                    records.extend(batch)
                except Exception as e:
                    print(f"[s2] error: {e}", file=sys.stderr)
                time.sleep(1.0)
        elif src == "gs":
            if args.query:
                queries = [args.query]
            else:
                print("[gs] --query required for Google Scholar (no query bank; too noisy)",
                      file=sys.stderr)
                continue
            for q in queries:
                print(f"[gs] {q} ...", file=sys.stderr)
                try:
                    batch = gs_search(q, args.max)
                    for r in batch:
                        r["search_query"] = q
                    records.extend(batch)
                except Exception as e:
                    print(f"[gs] error: {e}", file=sys.stderr)

    before = len(records)
    records = dedup(records)
    print(f"Dedup: {before} -> {len(records)}", file=sys.stderr)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.append and out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            existing_papers = existing.get("papers", [])
            if records:
                all_papers = existing_papers + records
                before_total = len(all_papers)
                all_papers = dedup(all_papers)
                print(f"Append-dedup: {before_total} -> {len(all_papers)}", file=sys.stderr)
                payload = {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "scope": "axiom-finder v0.3-alpha (Q4 spec: microecon/poli-sci/history/phil/math)",
                    "count": len(all_papers),
                    "papers": all_papers,
                }
            else:
                # No new records; keep existing
                print(f"No new records; keeping existing ({len(existing_papers)} papers)",
                      file=sys.stderr)
                payload = existing
        except Exception as e:
            print(f"Append failed ({e}); overwriting", file=sys.stderr)
            payload = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "scope": "axiom-finder v0.3-alpha (Q4 spec: microecon/poli-sci/history/phil/math)",
                "count": len(records),
                "papers": records,
            }
    else:
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scope": "axiom-finder v0.3-alpha (Q4 spec: microecon/poli-sci/history/phil/math)",
            "count": len(records),
            "papers": records,
        }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    print(f"Wrote {out_path} (count={payload['count']})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
