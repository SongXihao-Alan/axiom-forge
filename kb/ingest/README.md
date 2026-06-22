# Axiom Forge — KB Ingest (literature → KB nodes)

> Auto-extract structured KB nodes from arXiv / Semantic Scholar / Google Scholar papers.

## Pipeline

```
[arXiv + S2 + GS]                  [kb/ingest/literature_fetcher.py]
        ↓                                       │
       papers                                   ↓
                                   [candidates.json]
                                              │
                                              ↓
                              [kb/ingest/extract_nodes.py]
                                              │
                                              ↓
                                   [kb/ingest/drafts/*.json]
                                              │
                                  (human review)
                                              ↓
                              [kb/nodes/<type>/<id>.json]
```

## Quickstart (smoke test)

```bash
# 1) Pull 3 papers from arXiv (free, no key)
python kb/ingest/literature_fetcher.py --source arxiv --query "SHAP" --max 3

# 2) Extract draft nodes (no LLM call, rule-based)
python kb/ingest/extract_nodes.py --in kb/ingest/candidates.json

# 3) Review drafts in kb/ingest/drafts/
ls kb/ingest/drafts/

# 4) Move validated drafts to kb/nodes/<type>/
mv kb/ingest/drafts/LIT-ARXIV-*.json kb/nodes/literature/
# (axiom/theorem drafts need human-curated id + depends_on; move manually)
```

## Full search (production)

```bash
# 1) Pull 30 papers per query, all 3 sources
#    (Semantic Scholar: optional S2_API_KEY in env raises rate limit)
python kb/ingest/literature_fetcher.py --source all --max 30 \
    --out kb/ingest/candidates_2026-06-22.json

# 2) Extract (rule-based only, fast)
python kb/ingest/extract_nodes.py --in kb/ingest/candidates_2026-06-22.json \
    --out kb/ingest/drafts_2026-06-22 --limit 200

# 3) Extract WITH M3 (richer, costs API tokens)
export MINIMAX_API_KEY=sk-cp-...
python kb/ingest/extract_nodes.py --in kb/ingest/candidates_2026-06-22.json \
    --out kb/ingest/drafts_2026-06-22_m3 --limit 200 --use-m3
```

## Scope (Q4 spec, 2026-06-22)

Q4 = **microeconomic theory + political science + history + philosophy + math**

Queries are biased toward:
- SHAP / Shapley / feature attribution
- Axiomatic mechanism design, social choice
- Voting theory, fair division, Arrow
- Cooperative game theory axioms
- Political philosophy (Rawls, Harsanyi, Kant)
- Adjacent: voting theory, institutional analysis

The query bank lives in `literature_fetcher.py`:
- `ARXIV_KEYWORDS` — arXiv query list
- `S2_FIELDS` — Semantic Scholar field list

## Periodic ingest (Q4 option b)

Run weekly (cron suggested in TODO below). Save snapshots:
```bash
DATED=$(date +%Y-%m-%d)
python kb/ingest/literature_fetcher.py --source all --max 50 \
    --out kb/ingest/snapshots/candidates_${DATED}.json
```

Then review + commit new literature nodes per snapshot.

## Limitations

- **Rule-based extraction is noisy** — axiom/theorem drafts need human review.
- **Google Scholar scraping is fragile** — prefer arXiv + S2 for bulk.
- **M3 extraction quality** — depends on abstract quality; full-text ingestion not yet supported.
- **No full-text** — only abstracts are processed. For deep extraction, add PDF ingestion (TBD).

## TODO (post-Phase C)

- [ ] Cron job: weekly ingest (Q4 option b)
- [ ] PDF ingestion: download + parse PDFs for full-text axiom extraction
- [ ] Dedup against existing KB (currently dedups only within a fetch)
- [ ] Automatic relation extraction (axiom-X depends_on axiom-Y, etc.)
- [ ] Confidence scoring: weight M3-extracted nodes lower than human-curated
