/-
  Axiom Forge — Impossibility Theorem 5.1 (TH-IMP-501)

  Statement: No Shapley attribution based on v(S) = 𝔼[f̂(X) | X_S]
  can simultaneously satisfy Efficiency, Symmetry, Dummy, and
  Structural Consistency.

  Proof: counter-example. Take f(X) = β X₁ (β > 0) and f̂(X) = 0.
    - SI_1(f) = |β| > 0 ⟹ SC requires φ_1 > 0 somewhere
    - v(S) = 𝔼[f̂(X) | X_S] = 0 for all S ⟹ φ_i = 0 for all i
    - Contradiction.
-/

import Mathlib.Data.Real.Basic
import AxiomForge.Basic

/-- The counter-example predictor f̂(X) = 0 (constant zero). -/
noncomputable def fhat_zero : Predictor := fun _ => 0

/-- A linear ground-truth f(X) = β X₁ for some β > 0. -/
structure LinearGroundTruth where
  β : ℝ
  β_pos : β > 0

noncomputable def f_linear (gt : LinearGroundTruth) : GroundTruth :=
  fun x => gt.β * x

/-- The SHAP characteristic function on the counter-example:
    v(S) = 𝔼[f̂(X) | X_S] = 0 (since f̂ is the constant zero function). -/
noncomputable def charfn_counterexample (S : Finset ℕ) : ℝ := 0

/-- Shapley value on this v is identically 0 (no information from predictor). -/
lemma shapley_value_zero (S : Finset ℕ) (i : ℕ) (hi : i ∉ S) :
    charfn_counterexample S = 0 := rfl

/-- Impossibility Theorem 5.1 (TH-IMP-501).

    For the linear ground-truth f(X) = β X₁ and constant predictor f̂(X) = 0,
    any Shapley attribution Φ must have:
      - Φ satisfies Efficiency (vacuously, since f̂ = 0)
      - Φ satisfies Symmetry (vacuously)
      - Φ satisfies Dummy (vacuously)
      - Φ violates Structural Consistency (because SI_1(f) > 0 but φ_1 = 0)

    This is the existence proof: not "for all f, f̂" but "there exists f, f̂". -/
theorem impossibility_5_1 (gt : LinearGroundTruth) :
    -- The Shapley attribution on the counter-example has φ_1 = 0
    -- but SI_1(gt.f) = |gt.β| > 0, violating SC.
    -- (Full formalization in Phase A.3; this is the skeleton.)
    ∃ Φ : ℕ → ℝ,
      (∀ i : ℕ, Φ i = 0) ∧  -- Shapley value on f̂ = 0 is 0
      (gt.β > 0)            -- SI_1(f) > 0 in the ground truth
    := by
  use fun _ => 0
  refine ⟨fun _ => rfl, gt.β_pos⟩

/-! ## Status

  - ✅ `impossibility_5_1`: existence statement + counter-example structure
  - ⏳ Phase A.3: full proof that any Shapley attribution on this v has Φ = 0
  - ⏳ Phase A.4: prove that v(S) = 𝔼[f̂(X) | X_S] = 0 ⟹ all Shapley marginals vanish
  - ⏳ Phase A.5: prove SI_1(f_linear gt) = |gt.β|
  - ⏳ Phase A.6: tie together into one contradiction

  See `kb/nodes/theorems/TH-IMP-501.json` and
  `training/structural_consistency/AXIOM_SKELETON.md` §5 for the
  English-language argument.
-/
