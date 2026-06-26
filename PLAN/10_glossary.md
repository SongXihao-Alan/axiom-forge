# Glossary

Technical terms used in the project + new iteration/discovery terms
Song Xihao (Alan), University of Glasgow  •  2026-06-23


# 1. SHAP & Feature Attribution

| Term              | Definition |
|-------------------|------------|
| SHAP              | SHapley Additive exPlanations; a method for explaining individual predictions of any ML model using Shapley values from cooperative game theory. |
| Shapley value     | From cooperative game theory (Shapley 1953); a unique way to distribute a 'surplus' among players satisfying 4 axioms (Efficiency, Symmetry, Dummy, Additivity). |
| characteristic function v(S) | In SHAP, v(S) = E[f̂(X) \| X_S = x_S]; the expected prediction conditioned on knowing features in S. |
| Structural Importance (SI) | SI_i(f) := E_X[\|∂f(X)/∂X_i\|] for differentiable f, or \|β_i\| for linear f; the gradient magnitude of the ground-truth function w.r.t. feature i. |
| AX-SC-001         | The Structural Consistency axiom: SI_i(f) > 0 ⇒ ∃x: φ_i(f̂, x) > 0. Binds attribution to ground-truth structure, not just predictor behavior. |
| TH-IMP-501        | Impossibility Theorem 5.1: No Shapley attribution based on v(S) = E[f̂\|X_S] can simultaneously satisfy Efficiency, Symmetry, Dummy, and SC. |


# 2. Cooperative Game Theory & Mechanism Design

| Term                  | Definition |
|-----------------------|------------|
| Strategy-Proofness    | Truth-telling is a dominant strategy for all agents. |
| No-Envy               | No agent prefers another's allocation to their own. |
| Population Monotonicity | If a subset of agents leaves, the remaining agents should not be worse off. |
| Efficiency            | Allocation fully exhausts the resource; no waste. |
| Impossibility Theorem | A proof that a set of desired properties cannot all hold simultaneously under any rule. |


# 3. Knowledge Base & Tooling

| Term              | Definition |
|-------------------|------------|
| KB                | Knowledge Base; in axiom-finder, 85 hand-curated JSON nodes across 8 types. |
| Anchor            | A piece of supporting evidence for a KB node. Three types: empirical, philosophical, community. |
| Diktat            | A Thomson-style tacit evaluation perspective; not an axiom but a lens to evaluate axioms. |
| Tool neutrality   | Project principle: 3 anchors (empirical / philosophical / community) are fully equal; no priority implied. |
| Lane A / B / C / D | The 4 phases of the calibration study. A = gold standard; B = LLM evaluation; C = statistics; D = paper. |
| Distractor        | A hand-built or auto-generated item designed to fail on 1+ rubric dimensions. Used to test LLM's ability to reject low-quality axioms. |


# 4. LLM Evaluation Metrics

| Term                  | Definition |
|-----------------------|------------|
| QWK                   | Quadratic-weighted Cohen's kappa; measures agreement between two raters on ordinal scales, with quadratic penalty for distant disagreements. |
| MAE                   | Mean Absolute Error; average of \|prediction - gold\|. |
| Pearson correlation   | Linear correlation between predictions and gold. |
| Bland-Altman LoA      | 95% limits of agreement: mean_diff ± 1.96 × sd_diff. Captures the spread of pairwise differences. |
| Tier accuracy         | Fraction of items where LLM-assigned tier (easy/medium/hard) matches gold tier. |
| Distractor rejection rate | P(mean_score < 2.5 \| is_distractor). Higher is better. |
| Inter-rater reliability | Agreement between two independent annotators on the same items, measured by QWK. Required for a rigorous gold standard. |


# 5. Iteration and Discovery (NEW)

| Term                   | Definition |
|------------------------|------------|
| Iteration loop         | The closed feedback cycle: Lane B → Lane C → Lane B prompt revision → Lane C re-run, until convergence criteria met. |
| Convergence criterion  | STOP condition for the iteration loop: QWK ≥ 0.6 on all 5 dimensions, or after v3. |
| Prompt version         | The versioned system-prompt used for Lane B. Saved as kb/ingest/lane_b_prompts/v1.md, v2.md, v3.md. |
| gap_finder.py          | Agent that identifies evidence gaps in the KB — missing empirical anchors, unexplored value tradeoffs, unproven theorem implications — to drive axiom discovery. |
| Expert panel           | A 3-person review board (economist + philosopher + social choice researcher) that validates the real-world plausibility of top candidate axioms post-Lane-C. |
| Discovery path         | The post-calibration pipeline: gap_finder → candidate axiom generation → Z3 verification → Lean 4 proof → expert panel → KB node publication. |
| lane_c_feedback.json   | Machine-readable output of Lane C containing per-dimension QWK/MAE/bias, convergence flag, and list of dims needing revision. |