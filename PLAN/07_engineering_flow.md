
# Engineering Flow

CI, testing, deployment, version control + 3-layer verification + Lean CI
Song Xihao (Alan), University of Glasgow  •  2026-06-24


# 1. Repository Layout (updated)

axiom-forge/
├── kb/ingest/
│   ├── lane_b_evaluator.py     # 3-layer evaluation (LLM→Z3→self-critique)
│   ├── lane_b_prompts/         # v1.md, v2.md, v3.md (prompt versioning)
│   ├── z3_verify.py            # Z3 formal verification (Layer 2)
│   ├── extract_prompts/       # v1.md, v2.md (extraction versioning)
│   └── extract_nodes.py         # node extraction (updated for versioning)
├── paper/
│   ├── data/
│   │   ├── gold.json
│   │   └── gold_dual_annotator.json  # dual-annotator subset
│   └── results/
│       ├── lane_b_predictions.json  # full 3-layer output
│       ├── lane_c_stats.json
│       ├── lane_c_report.md
│       └── lane_c_feedback.json       # convergence diagnostic
├── agents/
│   ├── gap_finder.py
│   └── gap_finder_prompts/     # v1.md, v2.md
├── formal/examples/             # Z3+Lean examples
└── .github/workflows/ci.yml   # includes lean-build + lane-c-feedback


# 2. Branch Strategy

main: always green
feat/lane-B-v1:  baseline 3-layer evaluation (v1 prompt)
feat/lane-B-v2:  prompt refinement iteration 2
feat/lane-B-v3:  prompt refinement iteration 3 (last resort)
feat/lane-C-v2:  Lane C re-run after v2
feat/expert-panel:  domain expert validation
feat/discovery-path:  gap_finder → candidate generation
feat/lean-ci:  Lean 4 build in GitHub Actions


# 3. CI / GitHub Actions (updated)

Jobs:
  cli-check:     basic CLI smoke tests
  security-check:  .env not tracked; KB JSON validation
  lean-build:    cd formal && lake build [NEW]
  lane-b-scale:  evaluate-gold + evaluate-distractors [UPDATED for 3-layer]
  lane-c-feedback:  compute stats + check convergence [UPDATED]


# 4. 3-Layer Evaluation in CI

lane-b-scale job now runs:
  python kb/ingest/lane_b_evaluator.py evaluate-gold --prompt-version v3
  # Z3 runs automatically on every formal statement (Layer 2)
  # Self-critique runs automatically (Layer 3)
  python paper/data/lane_c_stats.py --prompt-version v3
  # lane_c_stats.py reads final_scores (Layer 3 corrected), not layer1
