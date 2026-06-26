
# Risk Register

What could go wrong, mitigation, escalation + 3-layer verification risks
Song Xihao (Alan), University of Glasgow  •  2026-06-24


# 1. Active Risks (BLOCKING)

Risk    Impact    Mitigation    Status
R1    MINIMAX_API_KEY unavailable    Fallback: OpenAI GPT-4o or local Llama 3.1 70B    OPEN
R2    Sandbox firewall blocks M3 API    Run Lane B from local terminal    OPEN


# 1a. 3-Layer Verification Risks (NEW)

Risk    Impact    Mitigation    Status
R3    Z3 parse rate < 60% (formal too complex)    Improve z3_verify.py pattern library; add more Unicode normalizations    OPEN
R4    z3_override_impact > 0.3 (Z3 too aggressive)    Review thresholds: contradiction→1 only if sat with concrete model    OPEN
R5    Z3 timeout on > 20% of items    Increase timeout to 30s; mark as 'unknown' for Layer 3    OPEN
R6    LLM self-critique (Layer 3) contradicts Z3    Self-critique is ADVISORY; Z3 auto-correct takes priority; document in paper    OPEN


# 1b. Iteration Loop Risks (NEW)

Risk    Impact    Mitigation
R7    Prompt v1→v2→v3 all fail to reach QWK ≥ 0.6    Pivot paper to diagnostic study: which dimensions cannot be calibrated
R8    Second annotator unavailable    Acknowledge as limitation in paper §5
R9    Expert panel not recruited before Lane D writeup    Start recruitment immediately after Lane C converges


# 2. High-Priority Risks

Risk    Impact    Mitigation
R10    M3 produces unreliable scores (QWK < 0.4 on most dims)    Focus paper on 'diagnostic study' framing; include Z3 coverage analysis
R11    Distractor auto-generation low quality    Tune _generate_distractor(); target mean score 1.8-2.2
R12    Gold standard single-annotator only    Acknowledge limitation; run inter-rater on available data


# 3. Medium-Priority Risks

Risk    Impact    Mitigation
R13    Sandbox proxy down during Lane B    Resume-safe: lane_b_predictions.json saves per item
R14    Lean build takes > 30 min in CI    Use lake exe cache get; add lean-build to separate workflow
R15    Z3 formal notation incompatible with KB node formats    Add per-type parsing rules to z3_verify.py (axiom vs theorem vs assumption)


# 4. Low-Priority Risks

Risk    Impact    Mitigation
R16    Linter flags .lean files as errors    Confirm with lake build; linter is wrong
R17    GitHub Actions timeout (6h)    Keep tests < 5 min; Lean build separate workflow
R18    Literature fetcher produces stale nodes    Set monthly cron; set needs_review flag on LIT-* nodes > 12 months
