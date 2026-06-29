
# Axiom Forge — Project Plan

From KB to LLM-Evaluator Calibration: A 4-Lane Research Program
Song Xihao (Alan), University of Glasgow  •  2026-06-24

**v0.4 update (2026-06-26)**: Phase 2 D⇄F pipeline (D-F-BT-Z3) is now end-to-end
working with M3 (minimaxi) + SBERT. See `knowledge-base/SPEC_cn.md` for the
Chinese tech spec, and `scripts/kb_to_chunks.py` for the 51-chunk adapter.
The pipeline produces 20 axiom records from 51 KB nodes; 6/20 are
Z3-verified in consistency mode. Run in `--z3-mode refute` to look for
impossibility theorems (see `_derive_status` for the 7-tier status taxonomy).


# 1. Executive Summary

Axiom Forge is a research program that asks: can a Large Language Model (LLM) reliably assess the quality of an axiom? The project combines a hand-curated 85-node knowledge base (KB) of SHAP literature, value anchors, and theorems with a gold-standard evaluation dataset (104 items: 74 real axioms + 30 hand-built distractors) and a 5-dimension rubric (clarity, novelty, internal consistency, empirical grounding, actionability). We scale evaluation to 2000+ items and measure LLM-human agreement via quadratic-weighted Cohen's kappa.

■ 5-Layer Automated Verification (NEW — backtranslation gate)
Lane B now includes a FIVE-LAYER evaluation pipeline that combines the scalability of LLM evaluation with the rigor of automated formal verification and a formalization fidelity gate:
  Layer 1a: LLM discover → structured claim extraction (claim_nl + formal_claim)
  Layer 1b: LLM v3 prompt → raw scores (novelty, actionability, clarity)
  Layer 1c: LLM back-translate formal_claim → NL → similarity score (fidelity check)
  Layer 2: Z3 formal verification → internal_consistency check (ms-level)
  Layer 3: LLM self-critique → corrected final scores using Z3 results
This hybrid approach combines what LLMs do well (semantic judgment of NL) with what formal verification does well (exact logic checking). Layer 1c (back-translation) acts as a semantic fidelity gate — it catches silent disambiguation drift between the original NL claim and the formal capture. Back-translation similarity (tokenised Jaccard) is reported as a sixth metric alongside the 5-dimension rubric.

■ Iteration Loop: Calibrate → Diagnose → Refine → Re-calibrate
The 4-Lane pipeline is NOT a one-shot. After Lane C, calibration results feed back into Lane B prompt refinement.
  Lane B (prompt v1) → Lane C → Low-QWK dims identified + bt_similarity measured
      ↕ feedback
  Lane B (prompt v2, refined) → Lane C → ...
Converges when: QWK ≥ 0.6 on all 5 dimensions AND backtranslation_similarity ≥ 0.7 (provisional). Maximum 3 iterations (v1→v2→v3).

■ Expert Validation Panel (AI for Social Science)
After Lane D, a 3-person expert panel (economist + philosopher + social choice researcher) reviews top-10 candidate axioms for real-world validity.

■ The Discovery Path (post-calibration)
Once calibrated (QWK ≥ 0.6 on ≥3 dimensions):
  KB axioms → gap_finder.py → candidate axioms → Z3/LLM 3-layer eval → Lean 4 proof → Expert panel → KB PR
Deliverable: published discovery (e.g., 'AX-NEW-EFFICIENCY-FAIRNESS-001') alongside the calibration paper.


# 2. The 4-Lane Workflow

Lane    Goal    Primary deliverable    Tooling
A    Build gold standard    paper/data/gold.json + gold_dual_annotator.json    Hand annotation + KB inspection
B    3-layer evaluation    paper/results/lane_b_predictions.json    M3 API + lane_b_evaluator.py + Z3
C    Calibration statistics    paper/results/lane_c_report.md + lane_c_feedback.json    lane_c_stats.py + scipy
D    Paper    paper/main.pdf (8-12 pages)    LaTeX


# 3. Five-Layer Verification Detail



## 3.1 Layer 1a: LLM Structured Claim Discovery

M3 extracts a clean, structured claim (claim_nl + formal_claim) from the axiom NL + formal + anchors. This step forces the LLM to commit to a disambiguation before scoring, making the back-translation fidelity check meaningful.


## 3.2 Layer 1b: LLM v3 Prompt Scoring

M3 evaluates the discovered claim on the 5-dimension rubric. Output: raw scores + tier + failure_modes_detected.


## 3.3 Layer 1c: Back-Translation Fidelity Check

M3 independently re-interpret the formal_claim back to natural language (reconstructed_nl) without seeing the original claim_nl. Tokenised Jaccard similarity between claim_nl and reconstructed_nl is the formalization fidelity metric. A low similarity (below threshold 0.7) signals silent disambiguation drift — the formal captured something different from what NL intended.


## 3.4 Layer 2: Z3 Formal Verification (automatic)

If a formal statement is present, Z3 checks internal consistency in milliseconds:
  - Sat (counterexample found) → axiom is refuted; internal_consistency = 1
  - Unsat → axiom is consistent
  - Pattern detection: vacuous quantifiers, contradictions, tautologies
Z3 runs via kb/ingest/z3_verify.py; results are stored in layer2_z3 of each prediction.


## 3.5 Layer 3: LLM Self-Critique with Z3 Results

LLM reviews its own Layer 1b scores using Z3 findings:
  - Z3 found contradiction → force internal_consistency = 1
  - Z3 found tautology → force novelty = 1 (canonical restatement)
  - Z3 found vacuous → force internal_consistency = 2
Self-critique also checks citation quality and operationalizability independently.


# 4. The Discovery Path (Post-Lane-D)

Step 1 — Gap Finding: gap_finder.py scans KB for evidence gaps.
Step 2 — Candidate Generation: M3 generates axioms targeting each gap.
Step 3 — 5-Layer Evaluation: Layer 1a/c fidelity gate + Layer 1b scoring + Z3 consistency check + Layer 3 self-critique.
Step 4 — Lean 4 Formal Proof: 1-2 verified axioms get full proof.
Step 5 — Expert Panel Review: domain validation (economist + philosopher + SC researcher).
Step 6 — KB Publication: new AX-NEW-* node via PR.


# 5. Success Metrics

Calibration success: QWK ≥ 0.6 on all 5 dimensions AND backtranslation_similarity ≥ 0.7 after ≤ 3 iterations
Tier accuracy: ≥ 75% on gold standard
Z3 coverage: ≥ 80% of items with formal statements get Z3 verdict
Expert panel: ≥ 2/3 majority on top-10 axioms
Discovery: ≥ 1 new AX-NEW-* node merged to KB via PR
