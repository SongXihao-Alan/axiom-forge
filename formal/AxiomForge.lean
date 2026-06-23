/-
  Axiom Forge — Lean 4 formalization
  Entry point. Re-exports all submodules.
-/
import AxiomForge.Basic
import AxiomForge.Shapley
import AxiomForge.Impossibility
import AxiomForge.Thomson
-- Phase E additions (uncomment as we formalize more):
-- import AxiomForge.ValueAnchors.PoliticalPhilosophy
-- import AxiomForge.ValueAnchors.VotingTheory
-- import AxiomForge.ValueAnchors.HistoricalInstitutionalism

/-
  Axiom Forge v0.3-alpha — formal verification target.

  Goal: every node in `kb/nodes/` that has a `formal` field should have a
  corresponding Lean theorem that is `lake build` clean (i.e. no `sorry`).

  Status (2026-06-22):
    AX-SC-001      : defined, proof sketch with `sorry` (Impossibility 5.1)
    TH-IMP-501     : defined, proof sketch with `sorry`
    Shapley 1953   : to be formalized
    Thomson 2023   : Phase D, several weeks of work

  See `../docs/dev_notes/AI4S_LEAN_TOOLING_2026-06-22.md` for tooling.
-/
