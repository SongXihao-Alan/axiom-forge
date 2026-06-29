# Phase 2 Pipeline — D⇄F Interleaved D-F-BT-Z3

End-to-end axiom discovery pipeline that takes text chunks → structured
axiom records. Sibling to Lane B but uses a different architecture:
discovery-first (no schema anchoring) + formal verification with Z3.

Song Xihao (Alan), University of Glasgow  •  2026-06-26


# 1. Pipeline architecture

```
  Text chunk (DiscoverInput)
    │
    ▼  call_1_discover (M3) — free-form NL extraction
    │  returns 0-5 AxiomCandidateNL per chunk
    ▼
  AxiomCandidateNL
    │
    ▼  call_2_formalize (M3) — structured JSON + SMT-LIB2 fragment
    │  returns AxiomCandidateFormal (or None on failure)
    ▼
  AxiomCandidateFormal
    │
    ▼  call_3_backtranslate (M3) — NL reconstruction from formal ONLY
    │  returns BackTranslationResult with similarity_score
    ▼
  BackTranslationResult
    │
    ▼  z3_verify (M3 + Z3) — Tier A/B/C verification
    │  returns AxiomVerificationResult
    ▼
  AxiomRecord (35 fields, JSONL on disk)
```

Three independent LLM calls + one Z3 verification. Crucial:
call_3 does NOT see claim_nl_original — it only sees the formal
representation. This is what makes back-translation a meaningful
fidelity gate, not a tautology.


# 2. M3 (minimaxi) integration

Replaces the original anthropic+instructor LLM stack. Implementation in
`knowledge-base/ingest/m3_client.py`:

  call_m3_structured(system, user, schema, max_retries, max_tokens, model)
    - Single M3 chat call with json_mode=True
    - Strips <think>...</think> + ``` fences
    - Validates response against pydantic schema
    - Retries on validation failure (with augmented user prompt)
    - Returns None on total failure (caller logs + skips)

  call_m3_chat(system, user, max_tokens, model)
    - Plain text completion
    - Used by backtranslate (reconstruction) and z3_verify Tier C
      (SMT regeneration)

  check_api_key()
    - True iff MINIMAX_API_KEY is in env or .env

M3 uses 1-2k tokens on <think> reasoning before emitting the actual
response. Default max_tokens (1024) leaves zero room for output.
Bumped across the pipeline:
  call_1_discover       1024 → 8192
  call_2_formalize      4096 → 16384 (max practical cap)
  call_3_backtranslate  1024 → 8192
  _llm_judge             200 → 2048
  tier_c_reformalize     512 → 4096


# 3. SBERT back-translation similarity

Phase 2 was failing because back-translation similarity was based on
token-level overlap (TF-IDF / token Jaccard), which is near 0 when
original uses formal math notation and reconstruction is plain
language (e.g. "SI_i(f) := E[|∂f/∂X_i|]" vs "the gradient magnitude
of the ground-truth function").

Replaced with SBERT all-MiniLM-L6-v2 via raw transformers (the
sentence-transformers pip package has a v5.6.0 bug with model Pooling
that crashes on import). Mean-pooled embeddings, L2-normalized,
cosine similarity.

`_get_embeddings` (in `backtranslate.py`):
  1. SBERT all-MiniLM-L6-v2 (primary, ~80 MB local model, no API call)
  2. TF-IDF + cosine (fallback if SBERT load fails)
  3. Identity matrix (forces manual review on every pair)

Comparison on 5 axiom paraphrase pairs:

  Method          Score range     Key case (SI formula vs plain English)
  TF-IDF          0.000-0.671     0.000 (false negative on math notation)
  Token Jaccard   0.000-0.385     0.000
  Char3-Jaccard   0.018-0.399     0.018
  SBERT (new)     0.930-1.000     0.930 (catches semantic equivalence)

Empirical BT distribution on 20 v2 records (after max_tokens fix):
  Mean: 0.635    Median: 0.624
  ≥ 0.85 (high): 5/20 (25%)
  0.5-0.85:      10/20 (50%)
  < 0.5:         5/20 (25%)


# 4. Tiered status taxonomy

Replaces the binary "verified / needs_human_review" with 9 levels.
See `pipeline.py:_derive_status` for the full decision tree.

  impossibility_high   (BT ≥ 0.85, Z3 refute UNSAT)  ← headline result
  impossibility_medium (BT 0.5-0.85, Z3 refute UNSAT) ← headline result
  falsifiable_high     (BT ≥ 0.85, Z3 refute SAT)     ← new in v0.4 (2026-06-26)
  falsifiable_medium   (BT 0.5-0.85, Z3 refute SAT)   ← new in v0.4
  verified_high        (BT ≥ 0.85, Z3 consistency sat/tautology/vacuous)
  verified_medium      (BT 0.5-0.85, Z3 consistency sat/tautology/vacuous)
  bt_pass_high         (BT ≥ 0.85, no Z3 or skipped)
  bt_pass_medium       (BT 0.5-0.85, no Z3 or skipped)
  needs_human_review   (BT < 0.5, or Z3 unknown/timeout/parse_error)
  cannot_formalize     (SMT was 'CANNOT_FORMALIZE')
  formalization_failed (no FormalRepresentation returned)

Review queue: sort by status, work top-down. impossibility_* and
verified_* can be cited; falsifiable_* are candidates for negation
or further analysis; the rest need a second look.

The key distinction: in **consistency** mode, sat means "model exists
(axiom is satisfiable, possibly a real theorem)". In **refute** mode,
sat means "model exists for the negation (axiom can be falsified)".
These are opposite semantically — keeping them in separate status
buckets makes downstream filtering tractable.


# 5. Z3 verification modes

`--z3-mode {consistency,refute}`

  consistency (default): assert smt, expect sat
    - SAT: a satisfying model exists, axiom may be false in some world
    - UNSAT: original is contradictory (malformed formalization)

  refute: assert (not smt), expect unsat
    - SAT: a counterexample to the negation exists, original is falsifiable
    - UNSAT: original axiom is logically necessary
              → IMPOSSIBILITY THEOREM CANDIDATE
              → status flips to impossibility_high/medium

Refute mode uses `z3.parse_smt2_string` to extract the conjunction of
assertions, then asserts Not() of each. Falls back to string-level
`(assert (not <orig>))` if parse fails.

Project headline: "no Shapley attribution based on v(S) = E[f̂|X_S]
can satisfy Efficiency + Symmetry + Dummy + SC" → run refute mode
on TH-IMP-501 to get the SAT/UNSAT verdict on the impossibility.


# 6. KB-to-chunks adapter

`scripts/kb_to_chunks.py` walks `knowledge-base/nodes/{axioms,theorems,
assumptions,literature,value_anchors,scenarios}` and emits
`DiscoverInput` JSONL with text sourced from:

  1. node.nl_long (long-form natural language, on axioms/theorems)
  2. node.description (verbose prose)
  3. concatenated aliases + nl (fallback synthesis)
  4. synthetic prose from title + abstract_nl + summary + content
     (for literature / value_anchors / scenarios that lack `nl`)
  5. node.nl alone (canonical formal statement)

Domain mapping: KB uses free-form tags ("feature_attribution", "moral",
"scenarios") but DiscoverInput has a fixed whitelist (game_theory /
mechanism_design / social_choice / welfare_economics / credit_systems
/ political_philosophy / ml_fairness / history / math / other). Map
domain during conversion.

Current 51-chunk input spans:
  axioms:        3/8   (5 too short, skipped)
  theorems:      3/10
  assumptions:   1/2
  literature:   10/10
  value_anchors: 33/33
  scenarios:     1/6
  total:         51 chunks → 20 candidates after Phase 1


# 7. Pipeline performance

End-to-end timing on 51 chunks:
  Phase 1 (discover):     51 × 8-15s   =   8-13 min
  Phase 2 (formalize+BT+Z3): 20 × 30-60s = 10-20 min
  Total:                              ≈ 30-50 min per full run

M3 API calls per run: ~130 (51 Phase 1 + ~80 Phase 2 with retries)
SBERT model loaded once per process, ~80 MB download, ~1s load time


# 8. Known issues & future work

  - **M3 reliability**: 1-2 candidates per run get empty/garbled JSON
    output. Retry logic handles 2-3 attempts. Beyond that, the
    candidate is recorded with status=formalization_failed.

  - **DNS hiccups at end of long runs**: last 2-3 candidates sometimes
    fail with ConnectError. Re-run those candidates individually
    (will need a per-candidate CLI flag) or wrap the run loop in retry
    with backoff.

  - **BT sim ceiling around 0.9**: M3's reconstruction is a paraphrase,
    not a verbatim restatement. SBERT all-MiniLM-L6-v2 caps at ~0.95
    even for semantically equivalent pairs. Higher BT sim would need
    a larger model (e.g. bge-large) or a domain-tuned model.

  - **Lane C integration**: Phase 2 records don't have 5-dim rubric
    scores. To feed into Lane C stats, would need a converter that
    derives 5-dim scores from claim_nl / formalize_confidence /
    backtranslation_similarity. Not built yet.

  - **Refute mode → no UNSAT yet (as of 2026-06-26)**: refutation
    needs axioms that are TRULY necessary truths. M3-generated SMT
    from KB axioms tends to be satisfiable (models exist for Shapley
    axioms). The interesting case is when KB's own theorems like
    TH-IMP-501 (impossibility) are properly formalized — those
    should UNSAT in refute mode.


# 9. CLI usage

  # Run with default Z3 (consistency) on the 51 KB chunks
  python3 scripts/kb_to_chunks.py --output /tmp/ax-test/kb_chunks.jsonl
  python3 knowledge-base/ingest/pipeline.py \\
      --input /tmp/ax-test/kb_chunks.jsonl \\
      --output /tmp/ax-test/kb_records.jsonl

  # Run in refute mode (look for impossibility theorems)
  python3 knowledge-base/ingest/pipeline.py \\
      --input /tmp/ax-test/kb_chunks.jsonl \\
      --output /tmp/ax-test/kb_records_refute.jsonl \\
      --z3-mode refute

  # Quick structural demo without API calls
  python3 knowledge-base/ingest/pipeline.py --demo

  # Filter records by status
  python3 -c "
  import json
  recs = [json.loads(l) for l in open('/tmp/ax-test/kb_records_refute.jsonl')]
  for r in recs:
      if 'impossibility' in r['status']:
          print('IMPOSSIBILITY:', r['candidate_id'], r['chunk_id'], r['claim_nl'])
      elif 'falsifiable' in r['status']:
          print('FALSIFIABLE:  ', r['candidate_id'], r['chunk_id'], r['claim_nl'])
  "


# 10. Files

  knowledge-base/ingest/m3_client.py    (190 lines)  M3 wrapper
  knowledge-base/ingest/discover.py     (363 lines)  Phase 1
  knowledge-base/ingest/formalize.py    (448 lines)  Phase 2 step 1
  knowledge-base/ingest/backtranslate.py (523 lines) Phase 2 step 2
  knowledge-base/ingest/z3_verify.py    (700+ lines) Phase 2 step 3
  knowledge-base/ingest/pipeline.py     (780+ lines) Orchestrator
  knowledge-base/SPEC_cn.md            (416 lines)  Chinese tech spec
  scripts/kb_to_chunks.py               (180 lines)  KB-to-DiscoverInput adapter
  scripts/recompose_lane_b.py           (260 lines)  Lane B recompose (separate)
  scripts/build_inventory.py            (570+ lines) Downloads inventory

Run results (most recent):
  /tmp/ax-test/kb_records.jsonl         (20 records, max_tokens=1024,  BT 0.23)
  /tmp/ax-test/kb_records_v2.jsonl      (18 records, max_tokens=8192,  BT 0.64)
  /tmp/ax-test/kb_records_v3.jsonl      (20 records, run Z3 by default, 6 SAT)
  /tmp/ax-test/kb_records_refute.jsonl  (refute mode, in progress)
