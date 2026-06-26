
# Lane C — Calibration Statistics

QWK, MAE, Bland-Altman + 3-layer verification feedback + convergence criteria
Song Xihao (Alan), University of Glasgow  •  2026-06-24


# 1. Purpose

Lane C measures agreement between Lane B's 3-layer predictions and Lane A's gold standard. The headline metric is quadratic-weighted Cohen's kappa (QWK) per dimension. Lane C is NOT terminal — outputs feed back into Lane B prompt revision.


# 2. Metrics

Metric    Formula    Interpretation
QWK    1 - (Σ w_ij * O_ij)/(Σ w_ij * E_ij)    1.0=perfect; 0=random; <0=worse than random
MAE    Σ|p_i - g_i|/n    Lower is better
Pearson    cov(p,g)/(σ_p*σ_g)    1=perfect linear
Bland-Altman LoA    mean_diff ± 1.96*sd_diff    95% interval of prediction errors
Tier accuracy    (tier_pred == tier_gold)/n    ≥ 75% is good
Distractor rejection    P(mean<2.5 | is_distractor)    Higher is better


# 2a. Lane C → Lane B Feedback Loop

After each Lane C run, paper/results/lane_c_feedback.json is generated:
  converged: true if QWK ≥ 0.6 on ALL 5 dims AND tier_accuracy ≥ 0.75
  dims_needing_revision: dims where QWK < 0.6 OR MAE > 1.0
  per_dim: {qwk, mae, bias} per dimension
  z3_coverage: fraction of items where Z3 gave a verdict (target: ≥ 0.8)
  z3_override_rate: fraction of items where Z3 auto-corrected LLM score (target: < 0.3)
  distractor_weaknesses: rejection rate by failure mode


# 3. Z3 Coverage Metrics (NEW)

Since Layer 2 Z3 is new, Lane C tracks its effectiveness:
  z3_parse_rate: % of formal items successfully parsed by Z3
  z3_verdict_rate: % of parsed items with sat/unsat verdict
  z3_override_impact: how often Z3 auto-correction changed LLM score
  z3_vs_llm_disagreements: count of items where Z3 and LLM disagree
If z3_override_impact > 0.3: Z3 is being too aggressive → review z3_verify.py thresholds


# 4. Implementation

File: paper/data/lane_c_stats.py (updated for 3-layer schema)
Key change: predictions now use final_scores (Layer 3 corrected), not layer1 scores
Run: axiom-forge lane-c [--predictions <path>] [--prompt-version v3]
Output: lane_c_stats.json + lane_c_report.md + lane_c_feedback.json


# 5. Convergence Criteria

Iteration STOP condition: QWK ≥ 0.6 on ALL 5 dimensions AND tier_accuracy ≥ 0.75
Per-dimension revision trigger: QWK < 0.6 OR MAE > 1.0 OR |bias| > 0.5
Z3-specific trigger: z3_override_impact > 0.3 → review z3 thresholds before next iteration


# 6. Stratified Analyses

QWK broken down by: tier / failure_mode / anchor_type / domain / z3_verdict (sat/unsat/unknown)
This lets us see: do Z3-verified items have higher QWK than Z3-unknown items?
