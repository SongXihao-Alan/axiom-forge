
# Lean 4 + Z3 Integration

Phase 4 long-term + Z3 short-term + 3-layer verification integration
Song Xihao (Alan), University of Glasgow  •  2026-06-24


# 1. The Tool Spectrum

From fast/specific to slow/general:
Tool    Speed    Expressiveness    Role in 3-layer pipeline
Z3 (PySAT)    ms    Propositional / first-order    Layer 2: internal_consistency check
PySAT    ms    Boolean    Fallback for pure SAT problems
Lean 4 + Mathlib    min-hours    Full dependent type theory    Milestone L3: full formal proof
Coq / Isabelle    min-hours    CIC / HOL    Optional backup


# 2. Z3 in the 3-Layer Pipeline

Z3 is Layer 2 of the evaluation pipeline. It runs on EVERY item that has a formal statement.
kb/ingest/z3_verify.py handles:
  - Pattern-based detection (vacuous, contradiction, tautology) — instant
  - Z3 sat/unsat checking with 15s timeout
  - Unicode operator normalization for SHAP notation
  - Fallback to SMT-LIB parser for complex formulas
Results stored in layer2_z3 of each prediction JSON.


# 3. Z3 Decision Rules

When Z3 returns 'sat' (counterexample found):
  → Layer 3 auto-corrects: internal_consistency = 1
  → novelty may also be downgraded if the counterexample shows the axiom is a trivial restatement
When Z3 returns 'unsat' (consistent):
  → Layer 1 score on internal_consistency is confirmed; no override
When Z3 returns 'unknown' (timeout or parse error):
  → Layer 3 handles via self-critique; Z3 result is advisory


# 4. Lean Integration Milestones

Milestone L1 (Now): CI integration
  Add lean-build to .github/workflows/ci.yml — formal/ always builds on main

Milestone L2 (After Lane C converges): Axiom verification
  Select top-3 highest-scoring candidate axioms from Lane B
  Run Z3 (ms-level) to check internal consistency
  If Z3 SAT → refuted (document in paper §5)
  If Z3 UNSAT → consistent (advance to Milestone L3)

Milestone L3 (Post-Lane-D): Full formal proof
  Choose 1-2 Z3-verified axioms for Lean 4 formalization
  Target: AxiomForge/Shapley.lean or AxiomForge/Thomson.lean
  Publish as supplementary material alongside paper

Milestone L4 (Discovery path):
  Any new axiom confirmed by expert panel → formal proof in Lean 4
  → New KB node (AX-NEW-*) with lean_proof_url field


# 5. Why This Matters for AI for Social Science

An axiom proposed for real-world mechanism design MUST be proven correct. A flawed axiom in a live system causes real harm. Z3 is not academic gatekeeping — it is the only way to be certain that an axiom has no hidden counterexamples. This is the ethical dimension of the tool spectrum.
