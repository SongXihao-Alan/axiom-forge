
# Risk Register

What could go wrong, mitigation, escalation + 3-layer verification risks
Song Xihao (Alan), University of Glasgow  •  2026-06-24

**v0.4 update (2026-06-26)**: Added risks R19-R22 from Phase 2 pipeline
empirical findings. See `PLAN/13_phase2_pipeline.md` for context.
Old risks (R1-R18) left in place for reference.


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

# 4b. Phase 2 Pipeline Risks (NEW — v0.4)

Risk    Impact    Mitigation    Status
R19    M3 thinks but produces empty/garbled JSON for some candidates
                 ~5-10% per call. Retry logic handles 2-3 attempts.
                 After exhaustion: status=formalization_failed.
                 Run: 7/20 v3 candidates failed.    CLOSED via retry (mitigated)
R20    Back-translation sim 0.0 because M3 runs out of tokens
                 Old 1024 max_tokens → 0.0 sim → false-fail.
                 Fixed: bumped to 8192 (Phase 1+2).
                 v3 run: only 1/20 had sim=0.    CLOSED
R21    DNS hiccup terminates long runs at candidate 17-20
                 2026-06-26 v3 run lost 3 candidates to ConnectError.
                 Mitigation: wrap run in retry with backoff, OR run
                 individual candidates on failure.    OPEN (1 hr)
R22    Refute mode finds 0 UNSAT (no impossibility theorems)
                 M3-generated SMT from KB axioms tends to be
                 satisfiable. The interesting case is when KB's own
                 theorems (TH-IMP-501) are properly formalized.
                 Workaround: the new falsifiable_* status captures
                 "negation has a model" (axiom is falsifiable), which
                 is the OPPOSITE of impossibility. Both are useful
                 signals. As of 2026-06-26, no UNSAT found yet.    OPEN (under validation)
R22b   TH-IMP-501 impossibility theorem verification (NEW — v0.4)
                 Tier D in z3_verify.py proves impossibility theorems
                 via counter-example. Logic: instantiate the 4
                 dependent axioms with specific f, f̂ values, ask
                 Z3 if the conjunction is unsat.
                 Result (2026-06-26): TH-IMP-501 counter-example
                 f(X)=βX_1, f̂(X)=0 forces Eff∧Sym∧Dum∧SC jointly
                 unsatisfiable. Tier D returns UNSAT.
                 Single-chunk pipeline run:
                   status=impossibility_medium, z3_tier=D,
                   z3_status=UNSAT, verification_confidence=0.95.
                 Standalone script (scripts/th_imp_501_proof.py):
                   26 ms, UNSAT.    CLOSED (Tier D proves the TH)
