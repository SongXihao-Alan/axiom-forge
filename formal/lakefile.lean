import Lake
open Lake DSL

package «AxiomForge» where

-- Lean 4 + Mathlib4 formalization of:
--   Structural Consistency (AX-SC-001)
--   Impossibility Theorem 5.1 (TH-IMP-501)
--   Shapley 1953 uniqueness
--   Thomson 2023 axiomatic mechanism design
--   Social choice + voting theory + political philosophy
--   See ../docs/dev_notes/AI4S_LEAN_TOOLING_2026-06-22.md

@[default_target]
lean_lib «AxiomForge» where
  -- Lean libraries to import (Mathlib4 is the big one)
  roots := #[`AxiomForge]

require mathlib from git
  "https://github.com/leanprover-community/mathlib4.git" @ "v4.20.0"

-- Optional: enable `lake exe cache get` for pre-built Mathlib oleans
-- (saves 30-60 min of compilation; see https://www.leanprover.org/whole-mile-demos/)
@[default_target]
lean_exe «check» where
  root := `scripts.check
  supportInterpreter := true

/- ## Build & run

```
# First time (downloads Mathlib4 prebuilt oleans; ~5 min)
cd formal
lake exe cache get
lake build

# Check our 4 axioms
lake env lean AxiomForge/Basic.lean
```

## Adding new Lean files

1. Create `AxiomForge/<YourTheorem>.lean`
2. `import AxiomForge.YourTheorem` from the entry point
3. `lake build` automatically picks it up
-/
