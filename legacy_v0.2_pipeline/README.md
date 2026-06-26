# legacy_v0.2_pipeline — 5-agent axiom deriver

> **This directory is preserved for historical reference. It is NOT used by the current v0.3-alpha CLI.**
>
> Active skill: see `./knowledge-base/kb_query.py` + `./knowledge-base/kb_llm.py` (13 commands, no pipeline dependency).

## What was here

The `axiom_v02/` module was a 5-agent pipeline that derived a new axiom from a seed paper:

1. **Literature Node Loader** — structured a paper PDF into {axiom, assumption, theorem, proposition}
2. **Perturbation Sampler** — picked one axiom and applied a perturbation
3. **Value Evaluator** — scored the perturbation on an 8-dim value checklist
4. **Axiom Deriver v2** — drafted the new axiom (collaborated with Notation Definer)
5. **Consequence Predictor** — predicted 4 types of downstream consequences

Plus post-processing: `completeness_auditor.py` (4-dim audit) and `completeness_rewriter.py` (auto-rewrite score<0.6 fields).

## Why it was retired

- Pipeline required M3 API for every run (5+ calls, 8-12 min/run, fragile on M3's `<think>` token consumption)
- The "mainline" result it produced — **Structural Consistency** + **Impossibility Theorem 5.1** — was *handcrafted* in `outputs/v0.2_shap/AX-STRUCTURAL-CONSISTENCY-001.md` after one failed pipeline run; the pipeline couldn't reliably reproduce it
- v0.3-alpha replaces this with a deterministic KB + optional M3 RAG bridge, much more reproducible

## What survived

- The KB nodes (`kb/nodes/axioms/AX-SC-001.json` etc.) are the canonical artifacts, not the pipeline
- `outputs/v0.2_shap/` keeps the perturbation records and the handcrafted main memo
- `training/seeds/` keeps the 4 seed JSONs used as pipeline inputs

## If you want to re-run the v0.2 pipeline

```bash
# Requires M3 API key in .env (see .env.example)
# 4 months of work went into this pipeline; results were unstable.
python legacy_v0.2_pipeline/pipeline.py training/seeds/lundberg_2017_shap.json
```

## Renamed from `axiom_v02/`

In June 2026 (v0.3-alpha public release prep), this directory was renamed to `legacy_v0.2_pipeline/` to make its non-current status obvious to readers. No code changes.