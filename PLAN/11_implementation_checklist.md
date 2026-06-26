
# Implementation Checklist

Concrete tasks with file paths and status + 3-layer verification tasks
Song Xihao (Alan), University of Glasgow  •  2026-06-24


# 1. Setup (DONE)

Task    Files    Status
Repository initialized    github.com/SongXihao-Alan/axiom-forge    DONE
KB 85 nodes / 63 relations / 8 types    kb/nodes/    DONE
CLI 13 commands    kb/kb_query.py    DONE
Web API 9 endpoints    web_api.py    DONE
Lean 4.20.0 toolchain    /Users/alan/.elan/toolchains/    DONE
Lane B 5-layer evaluator (Layer 1a discover + 1b score + 1c backtranslate + Z3 + self-critique)    kb/ingest/lane_b_evaluator.py    DONE
Z3 formal verifier    kb/ingest/z3_verify.py    DONE
Lane C statistics + feedback    paper/data/lane_c_stats.py    DONE
Prompt versioning (v1/v2/v3)    kb/ingest/lane_b_prompts/    DONE


# 2. Immediate (No Blocker)

Task    Files    Effort    Status
Recruit second annotator (30-item subset)    gold.json    2-4 hrs    TODO
Compute inter-rater QWK    gold_dual_annotator.json    1 hr    TODO
Document limitation if second annotator unavailable    paper/main.tex    30 min    TODO


# 2b. 5-Layer Verification Testing

Task    Files    Effort    Status
Test Z3 on gold.json items with formal statements    z3_verify.py    1 hr    TODO
Measure z3_parse_rate and z3_override_impact on 104 items    lane_c_stats.py    1 hr    TODO
Verify self-critique (Layer 3) overrides Z3 correctly    lane_b_evaluator.py    1 hr    TODO
Run 5-layer eval on gold.json (104 items)    axiom-forge lane-b evaluate-gold    ~50 min    TODO


# 2ba. Back-translation Similarity

Task    Files    Effort    Status
Calibrate bt_similarity threshold from 30-item dual-annotator data    gold_dual_annotator.json    2 hrs    TODO
Verify string_similarity Jaccard is appropriate metric    lane_b_evaluator.py    1 hr    TODO
Check layer1c backtranslate output quality on 10 sample items    lane_b_evaluator.py    1 hr    TODO
Confirm backtranslation_similarity added to lane_c_feedback.json    lane_c_stats.py    30 min    DONE


# 2c. Post-3-Layer-Run

Task    Files    Effort    Status
Review lane_c_feedback.json for low-QWK dims    lane_c_*.json    1 hr    TODO
Refine Lane B prompt → v2 if needed    lane_b_prompts/v2.md    2 hrs    TODO
Run Lane C v2    axiom-forge lane-c    1 min    TODO
Check convergence: QWK ≥ 0.6 on all dims?    lane_c_feedback.json    30 min    TODO


# 2d. Expert Panel (After Convergence)

Task    Files    Effort    Status
Identify top-10 hardest axioms from Lane C    lane_c_stats.json    1 hr    TODO
Recruit: economist + philosopher + SC researcher    —    1 day    TODO
Collect + synthesize expert scores    paper/main.tex (App. A.3)    4 hrs    TODO


# 2e. Lean CI (Any Time — Independent)

Task    Files    Effort    Status
Add lean-build to GitHub Actions    ci.yml    30 min    TODO
Verify lake build passes on PR    CI    10 min    TODO


# 2f. Discovery Path (Post-Paper)

Task    Files    Effort    Status
Run gap_finder.py on KB (85 nodes)    gap_finder.py    2 hrs    TODO
Z3 verify top-3 candidate axioms    z3_verify.py    1 hr    TODO
Lean 4 formalize 1 verified axiom    formal/    1 week    TODO
Expert panel review of new candidates    —    1 day    TODO
New KB node PR: AX-NEW-*    kb/nodes/    2 hrs    TODO
