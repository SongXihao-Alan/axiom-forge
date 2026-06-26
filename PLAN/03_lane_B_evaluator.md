
# Lane B — LLM Evaluator Harness (3-Layer)

5-dimension rubric + 3-layer verification pipeline + prompt versioning
Song Xihao (Alan), University of Glasgow  •  2026-06-24


# 1. Purpose

Lane B runs the 3-layer evaluation pipeline on 2000+ items. It is NOT a one-shot LLM call — it combines LLM semantic judgment, Z3 formal verification, and LLM self-critique into a single automated pipeline. Prompt versioning ensures reproducibility across iterations.


# 2. Three-Layer Pipeline



## Layer 1: LLM v3 Scoring (semantic dimensions)

Role: Evaluate clarity, novelty, empirical_grounding, actionability using the v3 rubric.
Dimensions LLM handles well: clarity, novelty, empirical_grounding, actionability
Dimensions LLM struggles with: internal_consistency (needs formal logic)
Output: raw scores + tier + failure_modes_detected


## Layer 2: Z3 Formal Verification (automatic, ms-level)

Role: Verify internal_consistency and detect formal issues.
What it checks:
  - Sat (counterexample) → axiom is refutable; internal_consistency = 1
  - Unsat → axiom is consistent
  - Pattern detection: vacuous quantifiers (∀x∈∅), contradictions (p∧¬p), tautologies
How it works: kb/ingest/z3_verify.py runs Z3 on the formal statement; results stored in layer2_z3
Speed: ~50ms per item (15s timeout)
Fallback: if formal cannot be parsed → layer2_z3.status = 'unknown'; Layer 3 handles it


## Layer 3: LLM Self-Critique using Z3 Results

Role: Override Layer 1 scores based on Z3 findings.
Auto-corrections applied by Layer 3:
  - Z3 contradiction detected → internal_consistency := 1
  - Z3 vacuous detected → internal_consistency := 2
  - Z3 tautology detected → novelty := 1 (restatement), internal_consistency := 2
  - Citation not peer-reviewed → empirical_grounding := 2
  - Axiom is a principle, not operational → actionability := 2
Self-critique also flags: novelty ≥ 4 without named prior work → novelty := 3


# 3. Prompt Versioning

kb/ingest/lane_b_prompts/v1.md: baseline rubric (no bias correction)
kb/ingest/lane_b_prompts/v2.md: + bias corrections (novelty -0.5, actionability -0.5)
kb/ingest/lane_b_prompts/v3.md: decision trees + failure mode tables (CURRENT STANDARD)
All evaluation runs with --prompt-version v3 (default). v1/v2 are for ablation studies.


# 4. Output Schema

Each prediction saved to lane_b_predictions.json contains:
  id, type, is_distractor, prompt_version
  layer1: {scores, tier, raw, error} — LLM raw output
  layer2_z3: {z3_status, z3_flags, z3_model, z3_time_ms} — Z3 result
  layer3_critique: {corrections, critique, z3_overridden} — LLM self-critique
  final_scores: {...}  — corrected scores (after Z3 + self-critique)
  final_tier: 'easy|medium|hard'
  corrections_applied: {dim: 'z3_auto:N|llm_self_critique:N'}


# 5. Z3 Integration

kb/ingest/z3_verify.py — Z3 wrapper with pattern detection
Supported patterns:
  - Unicode operator normalization (∈ → in, ∧ → and, ¬ → Not)
  - SHAP axiom notation (SI_i, phi_i, f, fhat, beta)
  - SMT-LIB fallback (parse_smtlib_string)
  - Vacuous detection: ∀x∈∅, ForAll...empty set
  - Contradiction detection: p ∧ ¬p, ¬(...∧...)
  - Tautology detection: A ↔ A, ¬A ∨ A


# 6. CLI Commands

axiom-forge lane-b evaluate <node_id> [--prompt-version v3] [--no-z3] [--no-self-critique]
axiom-forge lane-b evaluate-gold [--prompt-version v3]
axiom-forge lane-b scale <N> [--prompt-version v3]
axiom-forge lane-c [--predictions <path>] [--prompt-version v3]


# 7. Convergence Criteria

STOP when: QWK ≥ 0.6 on all 5 dimensions AND tier_accuracy ≥ 75%
If Layer 2 Z3 auto-corrections are applied to > 30% of items → flag in lane_c_feedback.json
