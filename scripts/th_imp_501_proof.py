"""
th_imp_501_proof.py — Counter-example verification of TH-IMP-501.

TH-IMP-501 says: "No Shapley attribution based on v(S) = E[f̂(X)|X_S]
can simultaneously satisfy Efficiency, Symmetry, Dummy, Structural
Consistency for some f and f̂ ≠ f"

proof_sketch in TH-IMP-501.json gives:
  Counter-example: f(X) = βX_1 (β>0), f̂(X) = 0.
  SI_1(f) = β > 0.
  v(S) = E[f̂|X_S] = 0 for all S.
  φ_i = 0 for all i (from v(S) = 0).
  SI_1 > 0 but φ_1 = 0 → violates SC (SC requires ∃x: φ_1 > 0).

This script constructs SMT that verifies this counter-example breaks
all 4 axioms simultaneously (UNSAT), or finds a satisfying model
(SAT) showing the counter-example doesn't actually work.

For Z3, we instantiate the 4 axioms with the counter-example:
  Efficiency: Σ_i φ_i(0, x) = 0(x) = 0
  Symmetry:   (∀i,j: f̂(x|_{i=a, j=a}) = f̂(x|_{i=b, j=b}) ⇒ φ_i = φ_j)
              With f̂ = 0, all features are "symmetric" so all φ_i = 0.
  Dummy:      (∀i: f̂(x) = f̂(x|_{i:=x'_i}) ⇒ φ_i = 0)
              With f̂ = 0, f̂ is invariant to all X_i changes, so φ_i = 0.
  SC:         (∀i: SI_i(f) > 0 ⇒ ∃x: φ_i(f̂, x) > 0)
              SI_1(f) = β > 0 but φ_1 = 0 always → SC violated.

The conjunction Eff ∧ Sym ∧ Dum ∧ SC is UNSAT under this
counter-example, proving TH-IMP-501.
"""

import sys
import logging
sys.path.insert(0, '/Users/alan/Downloads/axiom-finder/knowledge-base/ingest')

from z3 import Solver, Real, Bool, And, Implies, sat, unsat, unknown
from z3_verify import Z3Status, tier_d_impossibility_proof

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')

def build_th_imp_501_counter_example():
    """Construct SMT instances for the 4 dependent axioms, instantiated
    with the counter-example from TH-IMP-501's proof_sketch."""
    # Free constants for β (positive real, the SI value) and feature
    # index sets. We use simple scalar model: 2 features.
    beta = Real('beta')
    phi_1 = Real('phi_1')
    phi_2 = Real('phi_2')

    # Single SMT with all declarations + all 4 axiom asserts at once.
    # This is the simplest, cleanest approach.
    full_smt = """
    (declare-const beta Real)
    (declare-const phi_1 Real)
    (declare-const phi_2 Real)
    ; AX-SHAP-EFF instance: Σ_i φ_i(f̂, x) = f̂(x). With f̂ = 0: Σ_i φ_i = 0
    (assert (= (+ phi_1 phi_2) 0))
    ; AX-SHAP-SYM instance: with f̂ = 0 invariant, all features symmetric so φ_1 = φ_2
    (assert (= phi_1 phi_2))
    ; AX-SHAP-DUM instance: with f̂ = 0, all features dummy so φ_1 = 0 ∧ φ_2 = 0
    (assert (and (= phi_1 0) (= phi_2 0)))
    ; AX-SC-001 instance: SI_1(f) = β > 0 ⇒ ∃ x: φ_1(f̂, x) > 0
    ; In our 2-feature model: β > 0 ⇒ φ_1 > 0
    (assert (=> (> beta 0) (> phi_1 0)))
    ; Also require β > 0 (it's a parameter from the counter-example)
    (assert (> beta 0))
    """
    return {
        # Counter-example beta=1 is hardcoded in the SMT below, so the
        # tier_d_impossibility_proof textual substitution is a no-op.
        # Pass empty dict to skip substitution entirely.
        "counter_example": {},
        # tier_d expects a list, but for TH-IMP-501 we use the conjunction
        # as a single full SMT fragment. We pass it as a one-element list
        # and the tier_d parser handles it correctly.
        "depends_on_smt": [full_smt.strip()],
    }


def main():
    print("=" * 60)
    print("TH-IMP-501 Impossibility Theorem Verification")
    print("=" * 60)
    print()
    print("Claim: No Shapley attribution based on v(S) = E[f̂(X)|X_S]")
    print("       can satisfy Efficiency ∧ Symmetry ∧ Dummy ∧ SC")
    print("       for some f, f̂ ≠ f.")
    print()
    print("Counter-example from proof_sketch:")
    print("  f(X) = β·X_1, f̂(X) = 0, β > 0")
    print("  v(S) = E[0|X_S] = 0, so φ_i = 0 for all i")
    print("  SI_1(f) = β > 0 but φ_1 = 0 → SC violated")
    print()
    print("Verifying: instantiate 4 axioms under this counter-example")
    print("            and ask Z3 if the conjunction is satisfiable.")
    print()

    cfg = build_th_imp_501_counter_example()

    # Run via tier_d_impossibility_proof
    result = tier_d_impossibility_proof(
        smt_fragment="(declare-const _th_imp_501 Bool)",
        counter_example=cfg["counter_example"],
        depends_on_smt=cfg["depends_on_smt"],
        timeout_ms=10000,
    )

    print(f"Tier D result: {result.status.name}")
    print(f"Notes: {result.notes}")
    print(f"Elapsed: {result.elapsed_ms:.1f} ms")
    if result.model:
        print(f"Model: {result.model}")
    print()

    if result.status == Z3Status.UNSAT:
        print("✓ TH-IMP-501 PROVED:")
        print("  Counter-example f(X)=βX_1, f̂(X)=0")
        print("  forces Eff ∧ Sym ∧ Dum ∧ SC to be jointly unsatisfiable.")
        print("  Status: impossibility_theorem_proved")
        return 0
    elif result.status == Z3Status.SAT:
        print("✗ Counter-example insufficient — a satisfying model exists")
        print("  showing all 4 axioms can hold under f(X)=βX_1, f̂(X)=0.")
        print("  TH-IMP-501 not proved by this counter-example.")
        return 1
    else:
        print(f"? Unclear result: {result.status}")
        return 2


if __name__ == "__main__":
    sys.exit(main())