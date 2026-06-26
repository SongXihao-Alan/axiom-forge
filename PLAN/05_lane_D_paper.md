# Lane D — Paper

From Lane C statistics to publishable calibration study + expert validation
Song Xihao (Alan), University of Glasgow  •  2026-06-23


# 1. Purpose

Lane D produces the final deliverable: an 8-12 page paper suitable for submission to a workshop (NeurIPS AI4SS, ICML Workshop) or archival venue (TMLR, JAIR). The paper reports Lane C's calibration results, interprets where LLMs succeed and fail, discusses the iteration loop findings, and validates results with an expert panel.


# 2. Paper Outline

| Section                              | Content                                                       | Length |
|--------------------------------------|---------------------------------------------------------------|--------|
| Title + Abstract                     | 150-word abstract summarizing the calibration study           | 0.5 page |
| 1. Introduction                      | Why calibrate LLMs as axiom evaluators? Tool neutrality principle. SHAP literature as test bed. | 1 page |
| 2. Related Work                      | LLM evaluation literature; SHAP axiom literature; Z3 / Lean autoformalization | 1.5 pages |
| 3. Method                            | 5-dim rubric; distractor design; LLM evaluator (M3) prompt; auto-distractor generation | 2 pages |
| 4. Results                           | Per-dim QWK / MAE / Pearson / Bland-Altman; tier accuracy; distractor rejection; per-anchor / per-domain breakdown; iteration loop summary (v1→v2→v3) | 2 pages |
| 5. Discussion                        | Which dimensions are easy/hard for LLMs; failure analysis; iteration findings (prompt revision effects); comparison with prior work; limitations | 1.5 pages |
| 5a. Expert Validation (NEW)          | Domain expert panel scores on top-10 axioms; what experts disagree on; real-world plausibility assessment | 1 page |
| 6. Conclusion + Future Work          | Implications for AI-assisted axiom discovery; Lean / Z3 extensions | 0.5 page |
| References                           | 20-30 citations                                              | 1 page |
| Appendix A.1                         | Full rubric                                                  | — |
| Appendix A.2                         | Full prompt (v3)                                             | — |
| Appendix A.3                         | Expert panel scores and notes (NEW)                          | — |
| Appendix A.4                         | Reproducibility instructions                                 | 2 pages |


# 3. Key Claims to Make

Based on expected Lane C results:
1. M3 achieves substantial agreement (QWK ≥ 0.6) on clarity and internal_consistency — the two dimensions that depend on syntactic rather than semantic judgments.
2. M3 struggles with novelty and actionability — it tends to over-rate items (positive bias) and miss subtle distractors.
3. Distractor rejection is high for 'obvious' failure modes (circular, vague_gesture) but lower for subtle ones (premise_mismatch, contradictory).
4. Per-domain breakdown: SHAP-related axioms (feature_attribution) are easier to evaluate than mechanism_design / social_choice axioms.
5. Iteration findings: which prompt revisions improved QWK and which dimensions remained recalcitrant despite revision (a publishable finding in itself).


# 4. Figures (5 main + appendix)

| Figure | Description                              | Data source |
|--------|------------------------------------------|-------------|
| 1      | Per-dim QWK bar chart with 95% CI        | lane_c_stats.json: per_dim_stats |
| 2      | Bland-Altman per dim (5 sub-panels)      | lane_c_stats.json: bland_altman |
| 3      | Tier confusion heatmap                   | lane_c_stats.json: tier_accuracy |
| 4      | Distractor rejection by failure mode     | lane_c_stats.json: distractor_rejection |
| 5      | Per-domain QWK heatmap                   | lane_c_stats.json: per_domain |
| A.1    | Per-prompt-version QWK comparison        | lane_c_stats.json: prompt_versions (NEW) |
| A.2    | Full per-item scatter (LLM vs Gold)      | lane_b_predictions.json + gold.json |


# 5a. Expert Validation Section (NEW — makes this AI for Social Science)

One week before paper submission, a 3-person expert panel reviews the top-10 LLM-rated axioms for real-world validity.

Panel composition:
- Economist (mechanism design / market design)
- Philosopher (ethics / political philosophy)
- Social choice researcher (voting theory / fair division)

Each panelist independently scores:
- Does this axiom make empirical sense in my domain? (1-5)
- Is this axiom novel relative to existing literature? (1-5)
- Would this axiom lead to harmful real-world consequences? (1-5)

Panel results are reported in Appendix A.3 and referenced in §5 (limitations). If ≥ 2/3 panelists rate an axiom ≤ 2 on the first question, that axiom is excluded from the paper's claims.

This step is what transforms the paper from 'AI evaluates axioms' to 'AI assists humans in discovering valid axioms' — the core distinction of AI for Social Science.


# 5. Target Venues

| Venue                                | Deadline           | Fit |
|--------------------------------------|--------------------|-----|
| NeurIPS AI4SS Workshop               | Aug 2026 (typ.)    | Strong fit — AI4SS is the project framing |
| ICML Workshop on AI for Social Good  | TBD                | Good fit — calibration of LLM-as-judge is timely |
| TMLR (Transactions on ML Research)   | Rolling            | Good for longer archival version |
| JAIR (Journal of AI Research)        | Rolling            | Good for comprehensive version with appendix |