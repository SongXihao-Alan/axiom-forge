# Lean 4 formalization

> Formal verification target for Axiom Forge.
> See `../docs/dev_notes/AI4S_LEAN_TOOLING_2026-06-22.md` for tooling choices.

## What's here (2026-06-22)

```
formal/
├── lean-toolchain            # Lean v4.20.0 (elan reads this)
├── lakefile.lean             # Lake build config
├── AxiomForge.lean           # Entry point
└── AxiomForge/
    ├── Basic.lean            # 4 axiom definitions + SI_i structure
    ├── Shapley.lean          # Shapley 1953 uniqueness (skeleton)
    └── Impossibility.lean    # TH-IMP-501 (counter-example skeleton)
```

**Status**: skeleton with `sorry` placeholders. Phase A.3-6 will fill in proofs.

## Setup

```bash
# Install Lean 4 via elan (one-time, ~5 min)
curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh

# Pull Mathlib4 prebuilt oleans (saves 30-60 min)
cd formal
lake exe cache get

# Build (verifies all `sorry` are accounted for)
lake build

# Run the main entry point
lake env lean AxiomForge.lean
```

## Proof status (2026-06-22)

| Node | Lean file | Proof status |
|---|---|---|
| AX-SC-001 (Structural Consistency) | `Basic.lean` (SI_i defn) | `sorry` in `StructuralImportance` |
| TH-IMP-501 (Impossibility 5.1) | `Impossibility.lean` | exists-skeleton + β>0 contradiction; full proof Phase A.3 |
| Shapley 1953 uniqueness | `Shapley.lean` | `sorry` in `shapley_uniqueness` |
| Thomson 2023 | not started | Phase D |
| Value anchors | not started | Phase E |

## Workflow for new theorems

1. Add a new `.lean` file under `AxiomForge/`
2. `import AxiomForge.NewTheorem` in `AxiomForge.lean`
3. `lake build` to verify it compiles
4. Mark `sorry` positions clearly with `TODO` comments

## Workflow for KB node → Lean theorem (proof-checker agent)

The agent `knowledge-base/ingest/proof_checker.py` (Phase C) will:
1. Read KB node's `formal` field
2. Generate Lean 4 template (with `sorry` placeholders)
3. Write to `formal/AxiomForge/Generated/<id>.lean`
4. Run `lake build` to verify it parses
5. (Optional) call DeepSeek-Prover-V2 API to suggest tactics
6. Update KB node's `lean_proof_status` field

## Phasing

- **Phase A.1-A.2** (this week): setup + skeletons ✅
- **Phase A.3-A.6** (1-2 weeks): fill in `impossibility_5_1` proof
- **Phase B** (2-3 weeks): literature-to-KB + Lean correlation
- **Phase C** (1 week): proof-checker agent + DeepSeek API
- **Phase D** (4-8 weeks): Thomson 2023 §1-§3 + cooperative game theory
- **Phase E** (2-3 months): political philosophy + voting theory + history
