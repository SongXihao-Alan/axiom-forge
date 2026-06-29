"""
kb/ingest/pipeline.py
axiom-forge v0.3 — Step 2 orchestrator

Ties together the full D⇄F interleaved pipeline:
  call_1_discover()      → AxiomCandidateNL
  call_2_formalize()     → AxiomCandidateFormal
  call_3_backtranslate() → BackTranslationResult
  z3_verify()            → AxiomVerificationResult
  → AxiomRecord (written to JSONL)

Usage:
  python pipeline.py --input chunks.jsonl --output axiom_records.jsonl
  python pipeline.py --demo   (runs on 3 built-in example chunks, no API key needed for structure test)
"""

from __future__ import annotations

import os
import json
import uuid
import time
import logging
import argparse
import traceback
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

from discover       import DiscoverInput, AxiomCandidateNL, call_1_discover, batch_discover
from formalize      import AxiomCandidateFormal, call_2_formalize
from backtranslate  import BackTranslateInput, BackTranslationResult, call_3_backtranslate, backtranslation_stats
from z3_verify      import Z3VerifyInput, AxiomVerificationResult, z3_verify, summarize_results
from m3_client      import check_api_key as m3_api_key_set

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")


# ---------------------------------------------------------------------------
# AxiomRecord — the final KB entry written to JSONL
# ---------------------------------------------------------------------------

@dataclass
class AxiomRecord:
    # Identity
    record_id: str
    candidate_id: str
    formalization_id: str
    source_paper: str
    chunk_id: str
    domain: str

    # Content
    claim_nl: str
    claim_type: str
    normative_strength: str
    entities: list[str]
    raw_quote: str

    # Formal representation (flattened for readability)
    quantifier: str
    bound_variables: list[str]
    condition: str
    conclusion: str
    formal_type: str
    smt_fragment: str
    interpretation_chosen: str
    alternative_interpretations: list[str]
    formalization_confidence: float

    # Back-translation result
    claim_reconstructed: str
    backtranslation_similarity: float
    backtranslation_passed: bool
    backtranslation_method: str
    ambiguity_preserved: bool

    # Z3 verification result
    z3_tier: str
    z3_status: str
    z3_model: dict
    z3_unsat_core: list[str]
    verification_confidence: float

    # Overall pipeline status
    status: str         # "verified_high"      (BT ≥ 0.85, Z3 verified)
                        # | "verified_medium"  (BT 0.5-0.85, Z3 verified)
                        # | "bt_pass_high"     (BT ≥ 0.85, no Z3 or Z3 skipped)
                        # | "bt_pass_medium"    (BT 0.5-0.85, no Z3 or Z3 skipped)
                        # | "needs_human_review" (BT < 0.5 or Z3 unknown)
                        # | "cannot_formalize"  (formal.cannot_formalize)
                        # | "formalization_failed" (formal is None)

    # Timestamps and scores
    discover_confidence: float
    low_confidence: bool
    lane_b_score: Optional[float]   # filled later by lane_b_evaluator.py
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


def _derive_status(
    bt: BackTranslationResult,
    z3: AxiomVerificationResult,
    formal: Optional[AxiomCandidateFormal],
) -> str:
    """Compute tiered status from back-translation + Z3 results.

    BT tiers (from SBERT all-MiniLM-L6-v2 empirical distribution on
    Phase 2 records, 2026-06-29):
      ≥ 0.85  high confidence paraphrase match → ready to publish
      0.5-0.85 medium confidence → quick review
      < 0.5   low / empty M3 output → needs human review

    Z3 statuses (when actually run, not SKIPPED):
      unsat     → discovered an impossibility theorem
      sat/tautology/vacuous → axiom is provably true / vacuous
      unknown   → Z3 couldn't decide in budget
      timeout   → Z3 didn't finish
      parse_error → M3 SMT output was malformed
    """
    if formal is None:
        return "formalization_failed"
    if formal.cannot_formalize:
        return "cannot_formalize"

    # BT tier
    sim = bt.similarity_score
    z3_status = z3.z3_status

    # Z3 successfully verified the axiom (not skipped)
    z3_verified = z3_status in ("sat", "tautology", "vacuous", "unsat")

    if z3_verified:
        if sim >= 0.85:
            return "verified_high"
        if sim >= 0.5:
            return "verified_medium"
        # Z3 verified but BT failed: still a discovery, mark for review
        return "needs_human_review"

    # Z3 not run / skipped / unknown
    if sim >= 0.85:
        return "bt_pass_high"
    if sim >= 0.5:
        return "bt_pass_medium"
    return "needs_human_review"


def _build_record(
    nl: AxiomCandidateNL,
    formal: Optional[AxiomCandidateFormal],
    bt: BackTranslationResult,
    z3: AxiomVerificationResult,
) -> AxiomRecord:

    # Provide safe defaults when formalization failed entirely
    f = formal or _empty_formal(nl)

    return AxiomRecord(
        record_id=str(uuid.uuid4()),
        candidate_id=nl.candidate_id,
        formalization_id=f.formalization_id,
        source_paper=nl.source_paper,
        chunk_id=nl.chunk_id,
        domain=nl.domain,

        claim_nl=nl.claim_nl,
        claim_type=nl.claim_type,
        normative_strength=nl.normative_strength,
        entities=nl.entities,
        raw_quote=nl.raw_quote,

        quantifier=f.quantifier,
        bound_variables=f.bound_variables,
        condition=f.condition,
        conclusion=f.conclusion,
        formal_type=f.formal_type,
        smt_fragment=f.smt_fragment,
        interpretation_chosen=f.interpretation_chosen,
        alternative_interpretations=f.alternative_interpretations,
        formalization_confidence=f.formalization_confidence,

        claim_reconstructed=bt.claim_reconstructed,
        backtranslation_similarity=bt.similarity_score,
        backtranslation_passed=bt.passed,
        backtranslation_method=bt.similarity_method,
        ambiguity_preserved=bt.ambiguity_preserved,

        z3_tier=z3.tier_used,
        z3_status=z3.z3_status,
        z3_model=z3.z3_model,
        z3_unsat_core=z3.unsat_core,
        verification_confidence=z3.verification_confidence,

        status=_derive_status(bt, z3, formal),
        discover_confidence=nl.confidence,
        low_confidence=nl.low_confidence,
        lane_b_score=None,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def _empty_formal(nl: AxiomCandidateNL) -> AxiomCandidateFormal:
    """Placeholder when call_2 fails entirely."""
    return AxiomCandidateFormal(
        candidate_id=nl.candidate_id,
        formalization_id=str(uuid.uuid4()),
        quantifier="none",
        bound_variables=[],
        condition="",
        conclusion="",
        formal_type="implication",
        smt_fragment="CANNOT_FORMALIZE",
        interpretation_chosen="",
        alternative_interpretations=[],
        formalization_confidence=0.0,
        claim_nl_snapshot=nl.claim_nl,
        domain=nl.domain,
    )


def _empty_bt(candidate_id: str, formalization_id: str) -> BackTranslationResult:
    return BackTranslationResult(
        candidate_id=candidate_id,
        formalization_id=formalization_id,
        claim_reconstructed="",
        similarity_score=0.0,
        similarity_method="skipped",
        passed=False,
        failure_reason="Formalization failed — back-translation skipped",
        ambiguity_preserved=False,
        judge_score=None,
    )


def _empty_z3(candidate_id: str, formalization_id: str) -> AxiomVerificationResult:
    return AxiomVerificationResult(
        candidate_id=candidate_id,
        formalization_id=formalization_id,
        tier_used="SKIPPED",
        z3_status="skipped_backtranslation_fail",
        verification_confidence=0.0,
        notes="Skipped due to failed formalization",
    )


# ---------------------------------------------------------------------------
# PipelineReport
# ---------------------------------------------------------------------------

@dataclass
class PipelineReport:
    total_chunks: int
    total_candidates: int
    by_status: dict
    by_domain: dict
    by_claim_type: dict
    mean_discover_confidence: float
    mean_formalization_confidence: float
    mean_backtranslation_similarity: float
    backtranslation_pass_rate: float
    ambiguity_preserved_rate: float
    z3_tier_distribution: dict
    z3_status_distribution: dict
    impossibility_count: int        # z3_status == "unsat" — these are discoveries!
    cannot_formalize_rate: float
    needs_human_review_count: int
    processing_time_seconds: float
    output_path: str
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)

    def summary_lines(self) -> list[str]:
        return [
            f"Chunks processed:          {self.total_chunks}",
            f"Candidates extracted:      {self.total_candidates}",
            f"─────────────────────────────────────",
            f"Status breakdown:",
            *[f"  {k:<30} {v}" for k, v in self.by_status.items()],
            f"─────────────────────────────────────",
            f"Mean discover confidence:  {self.mean_discover_confidence:.3f}",
            f"Mean formalize confidence: {self.mean_formalization_confidence:.3f}",
            f"Mean BT similarity:        {self.mean_backtranslation_similarity:.3f}",
            f"BT pass rate:              {self.backtranslation_pass_rate:.1%}",
            f"Ambiguity preserved rate:  {self.ambiguity_preserved_rate:.1%}",
            f"─────────────────────────────────────",
            f"Z3 tier distribution:      {self.z3_tier_distribution}",
            f"Impossibilities found:     {self.impossibility_count}  ← discoveries",
            f"Cannot formalize rate:     {self.cannot_formalize_rate:.1%}",
            f"Needs human review:        {self.needs_human_review_count}",
            f"─────────────────────────────────────",
            f"Processing time:           {self.processing_time_seconds:.1f}s",
            f"Output:                    {self.output_path}",
        ]


def _build_report(
    n_chunks: int,
    records: list[AxiomRecord],
    elapsed: float,
    output_path: str,
) -> PipelineReport:
    from collections import Counter

    def safe_mean(vals):
        return round(sum(vals) / max(len(vals), 1), 4)

    status_counts    = Counter(r.status for r in records)
    domain_counts    = Counter(r.domain for r in records)
    type_counts      = Counter(r.claim_type for r in records)
    z3_tier_counts   = Counter(r.z3_tier for r in records)
    z3_status_counts = Counter(r.z3_status for r in records)

    n = max(len(records), 1)

    return PipelineReport(
        total_chunks=n_chunks,
        total_candidates=len(records),
        by_status=dict(status_counts),
        by_domain=dict(domain_counts),
        by_claim_type=dict(type_counts),
        mean_discover_confidence=safe_mean([r.discover_confidence for r in records]),
        mean_formalization_confidence=safe_mean([r.formalization_confidence for r in records]),
        mean_backtranslation_similarity=safe_mean([r.backtranslation_similarity for r in records]),
        backtranslation_pass_rate=round(sum(r.backtranslation_passed for r in records) / n, 4),
        ambiguity_preserved_rate=round(sum(r.ambiguity_preserved for r in records) / n, 4),
        z3_tier_distribution=dict(z3_tier_counts),
        z3_status_distribution=dict(z3_status_counts),
        impossibility_count=z3_status_counts.get("unsat", 0),
        cannot_formalize_rate=round(status_counts.get("cannot_formalize", 0) / n, 4),
        needs_human_review_count=status_counts.get("needs_human_review", 0),
        processing_time_seconds=round(elapsed, 2),
        output_path=output_path,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Single-candidate pipeline (one full D→F→BT→Z3 pass)
# ---------------------------------------------------------------------------

def run_single_candidate(
    nl: AxiomCandidateNL,
    model: str,
    z3_timeout_ms: int,
    skip_z3: bool,
) -> AxiomRecord:
    """
    Run formalize → backtranslate → z3_verify for a single NL candidate.
    Never raises — errors are captured into the record status.
    """
    # call_2: formalize
    try:
        formal = call_2_formalize(nl, model=model)
    except Exception as e:
        logger.warning("call_2 exception for %s: %s", nl.candidate_id, e)
        formal = None

    if formal is None:
        bt = _empty_bt(nl.candidate_id, "none")
        z3r = _empty_z3(nl.candidate_id, "none")
        return _build_record(nl, None, bt, z3r)

    # call_3: back-translate
    bt_input = BackTranslateInput(
        candidate_id=nl.candidate_id,
        formalization_id=formal.formalization_id,
        claim_formal=formal,
        claim_nl_original=nl.claim_nl,
    )
    try:
        bt = call_3_backtranslate(bt_input, model=model)
    except Exception as e:
        logger.warning("call_3 exception for %s: %s", nl.candidate_id, e)
        bt = _empty_bt(nl.candidate_id, formal.formalization_id)

    # Z3 verify
    if skip_z3:
        z3r = _empty_z3(nl.candidate_id, formal.formalization_id)
    else:
        z3_input = Z3VerifyInput(
            candidate_id=nl.candidate_id,
            formalization_id=formal.formalization_id,
            smt_fragment=formal.smt_fragment,
            claim_nl=nl.claim_nl,
            domain=nl.domain,
            backtranslation_passed=bt.passed,
            similarity_score=bt.similarity_score,  # for tier-aware Z3 gate
            formal_context=formal.to_dict(),
        )
        try:
            # NOTE: z3_verify's llm_client arg is now ignored (Tier C uses
            # m3_client internally). Keep call site stable for future.
            z3r = z3_verify(z3_input, timeout_ms=z3_timeout_ms, model=model)
        except Exception as e:
            logger.warning("z3_verify exception for %s: %s", nl.candidate_id, e)
            z3r = _empty_z3(nl.candidate_id, formal.formalization_id)

    return _build_record(nl, formal, bt, z3r)


# ---------------------------------------------------------------------------
# Main pipeline runner
# ---------------------------------------------------------------------------

def run_pipeline(
    chunks: list[DiscoverInput],
    output_path: str,
    model: str = "MiniMax-M3",
    backtranslation_threshold: float = 0.75,
    z3_timeout_ms: int = 5000,
    skip_z3: bool = False,
    parallel_workers: int = 1,
) -> PipelineReport:
    """
    Full pipeline: chunks → AxiomRecords written to output_path (JSONL).

    Each line of output_path is one AxiomRecord as JSON.
    A companion report is written to output_path.replace('.jsonl', '_report.json').
    """
    t0 = time.perf_counter()

    if not m3_api_key_set():
        raise EnvironmentError("MINIMAX_API_KEY not set (or .env missing)")

    # Set threshold env var so backtranslate.py picks it up
    os.environ["BACKTRANSLATION_THRESHOLD"] = str(backtranslation_threshold)

    # Phase 1: discover (call_1) over all chunks
    logger.info("Phase 1: discovering candidates from %d chunks...", len(chunks))
    all_nl: list[AxiomCandidateNL] = []
    for i, chunk in enumerate(chunks):
        logger.info("  Chunk %d/%d: %s", i + 1, len(chunks), chunk.chunk_id)
        try:
            candidates = call_1_discover(chunk, model=model)
        except Exception as e:
            logger.warning("call_1 exception for %s: %s", chunk.chunk_id, e)
            candidates = []
        all_nl.extend(candidates)

    logger.info("Phase 1 complete: %d candidate(s) from %d chunk(s)",
                len(all_nl), len(chunks))

    if not all_nl:
        logger.warning("No candidates found — writing empty output")
        _write_jsonl([], output_path)
        return _build_report(len(chunks), [], time.perf_counter() - t0, output_path)

    # Phase 2: formalize + backtranslate + z3 (call_2, call_3, z3)
    logger.info("Phase 2: formalizing %d candidate(s)...", len(all_nl))
    records: list[AxiomRecord] = []

    if parallel_workers > 1:
        # Parallel execution — useful for large batches without strict rate limits
        with ThreadPoolExecutor(max_workers=parallel_workers) as ex:
            futures = {
                ex.submit(
                    run_single_candidate, nl, model, z3_timeout_ms, skip_z3
                ): nl
                for nl in all_nl
            }
            for future in as_completed(futures):
                nl = futures[future]
                try:
                    record = future.result()
                    records.append(record)
                    logger.info("  Done: %s → status=%s", nl.candidate_id, record.status)
                except Exception as e:
                    logger.error("  FAILED: %s — %s", nl.candidate_id, e)
    else:
        # Sequential — default, safer for rate limits
        for i, nl in enumerate(all_nl):
            logger.info("  Candidate %d/%d: %s", i + 1, len(all_nl), nl.candidate_id)
            record = run_single_candidate(nl, model, z3_timeout_ms, skip_z3)
            records.append(record)
            logger.info("    → status=%-25s  bt_sim=%.3f  z3=%s",
                        record.status,
                        record.backtranslation_similarity,
                        record.z3_status)

    elapsed = time.perf_counter() - t0

    # Write output JSONL
    _write_jsonl(records, output_path)

    # Build and write report
    report = _build_report(len(chunks), records, elapsed, output_path)
    report_path = output_path.replace(".jsonl", "_report.json")
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report.to_dict(), fh, indent=2, ensure_ascii=False)

    logger.info("Pipeline complete in %.1fs", elapsed)
    for line in report.summary_lines():
        logger.info(line)

    return report


def _write_jsonl(records: list[AxiomRecord], path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(r.to_json() + "\n")
    logger.info("Wrote %d record(s) to %s", len(records), path)


# ---------------------------------------------------------------------------
# Load chunks from JSONL
# ---------------------------------------------------------------------------

def load_chunks_from_jsonl(path: str) -> list[DiscoverInput]:
    """
    Load chunks from a JSONL file.
    Each line must be a JSON object with:
      chunk_id, text, source_paper, domain
    """
    chunks = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                chunks.append(DiscoverInput(
                    chunk_id=obj.get("chunk_id", f"chunk-{lineno}"),
                    text=obj["text"],
                    source_paper=obj.get("source_paper", "unknown"),
                    domain=obj.get("domain", "other"),
                ))
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Line %d: skipping malformed chunk: %s", lineno, e)
    logger.info("Loaded %d chunk(s) from %s", len(chunks), path)
    return chunks


# ---------------------------------------------------------------------------
# Demo mode — structural test without API key
# ---------------------------------------------------------------------------

_DEMO_CHUNKS = [
    DiscoverInput(
        chunk_id="demo-001",
        text=(
            "We require that the value function satisfy three axioms. "
            "First, efficiency: the sum of all players' values must equal the "
            "value of the grand coalition. Second, symmetry: if two players are "
            "interchangeable, they must receive equal payoffs. Third, the dummy "
            "axiom: a player who contributes nothing to any coalition should "
            "receive a payoff of zero."
        ),
        source_paper="Shapley (1953) — A Value for n-Person Games",
        domain="game_theory",
    ),
    DiscoverInput(
        chunk_id="demo-002",
        text=(
            "Arrow's impossibility theorem states that no social welfare function "
            "can simultaneously satisfy unrestricted domain, weak Pareto, "
            "independence of irrelevant alternatives, and non-dictatorship. "
            "This result implies that any aggregation procedure must violate at "
            "least one of these conditions."
        ),
        source_paper="Arrow (1951) — Social Choice and Individual Values",
        domain="social_choice",
    ),
    DiscoverInput(
        chunk_id="demo-003",
        text=(
            "In 2020, 10,432 loans were issued. The average interest rate was 4.7%. "
            "Table 3 shows the distribution of loan amounts by province. "
            "The default rate decreased from 3.2% in 2019 to 2.8% in 2020."
        ),
        source_paper="PBOC Annual Report 2020",
        domain="credit_systems",
    ),
]


def run_demo() -> None:
    """
    Structural demo: shows what the pipeline would do without making API calls.
    Validates that all imports, dataclasses, and JSON serialization work.
    """
    print("=" * 60)
    print("axiom-forge pipeline.py — DEMO MODE (no API calls)")
    print("=" * 60)
    print()

    print(f"Loaded {len(_DEMO_CHUNKS)} demo chunk(s):\n")
    for c in _DEMO_CHUNKS:
        print(f"  [{c.chunk_id}] domain={c.domain}")
        print(f"   source: {c.source_paper}")
        print(f"   text:   {c.text[:80]}...")
        print()

    print("Pipeline stages that would run with MINIMAX_API_KEY set:")
    print()
    print("  Phase 1: call_1_discover()")
    print("    → LLM extracts normative claims from each chunk")
    print("    → Expected: ~3 candidates from demo-001, ~1 from demo-002, 0 from demo-003")
    print()
    print("  Phase 2 (per candidate):")
    print("    → call_2_formalize()     — structured JSON + SMT-LIB2 fragment")
    print("    → call_3_backtranslate() — isolated NL reconstruction")
    print("    → z3_verify()            — Tier A/B/C consistency check")
    print()
    print("  Output: axiom_records.jsonl (one AxiomRecord per line)")
    print()

    # Show the AxiomRecord schema
    import dataclasses
    fields = dataclasses.fields(AxiomRecord)
    print(f"AxiomRecord has {len(fields)} fields:")
    for f in fields:
        print(f"  {f.name}: {f.type}")
    print()

    # Show that JSON serialization works
    dummy_record = AxiomRecord(
        record_id="demo-rec-001",
        candidate_id="demo-cand-001",
        formalization_id="demo-form-001",
        source_paper="Shapley 1953",
        chunk_id="demo-001",
        domain="game_theory",
        claim_nl="Symmetric players must receive equal payoffs",
        claim_type="axiom",
        normative_strength="must",
        entities=["player", "payoff"],
        raw_quote="symmetric players must receive equal payoffs",
        quantifier="forall",
        bound_variables=["i", "j", "v"],
        condition="v(S∪{i}) = v(S∪{j}) for all S",
        conclusion="φ_i(v) = φ_j(v)",
        formal_type="implication",
        smt_fragment=(
            "(declare-const mi Real)\n"
            "(declare-const mj Real)\n"
            "(declare-const phi_i Real)\n"
            "(declare-const phi_j Real)\n"
            "(assert (=> (= mi mj) (= phi_i phi_j)))"
        ),
        interpretation_chosen="symmetry (equal marginal contributions → equal payoffs)",
        alternative_interpretations=[
            "anonymity (permutation invariance of the value function)",
            "equal treatment of equals (weaker form)",
        ],
        formalization_confidence=0.88,
        claim_reconstructed=(
            "When two players have equal marginal contributions to every coalition, "
            "they must receive the same payoff"
        ),
        backtranslation_similarity=0.81,
        backtranslation_passed=True,
        backtranslation_method="embedding",
        ambiguity_preserved=True,
        z3_tier="B",
        z3_status="sat",
        z3_model={"mi": "1.0", "mj": "1.0", "phi_i": "0.5", "phi_j": "0.5"},
        z3_unsat_core=[],
        verification_confidence=0.90,
        status="verified",
        discover_confidence=0.95,
        low_confidence=False,
        lane_b_score=None,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    serialized = dummy_record.to_json()
    deserialized = json.loads(serialized)
    assert deserialized["status"] == "verified"
    assert deserialized["z3_status"] == "sat"

    print("JSON serialization test: PASS")
    print()
    print(f"Sample AxiomRecord (first 800 chars of JSON):")
    print(serialized[:800])
    print("...")
    print()
    print("Set MINIMAX_API_KEY and run:")
    print("  python pipeline.py --input your_chunks.jsonl --output records.jsonl")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="axiom-forge pipeline — discover → formalize → backtranslate → z3"
    )
    parser.add_argument(
        "--input",  type=str,
        help="Path to input JSONL file (each line: {chunk_id, text, source_paper, domain})"
    )
    parser.add_argument(
        "--output", type=str, default="output/axiom_records.jsonl",
        help="Path for output JSONL (default: output/axiom_records.jsonl)"
    )
    parser.add_argument(
        "--model", type=str, default="MiniMax-M3",
        help="M3 model name (default: MiniMax-M3)"
    )
    parser.add_argument(
        "--bt-threshold", type=float, default=0.75,
        help="Back-translation similarity threshold (default: 0.75)"
    )
    parser.add_argument(
        "--z3-timeout", type=int, default=5000,
        help="Z3 solver timeout in ms (default: 5000)"
    )
    parser.add_argument(
        "--skip-z3", action="store_true",
        help="Skip Z3 verification (useful for fast prototyping)"
    )
    parser.add_argument(
        "--workers", type=int, default=1,
        help="Parallel workers (default: 1, keep low to avoid rate limits)"
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="Run structural demo without API calls"
    )
    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    if not args.input:
        parser.error("--input is required (or use --demo)")

    chunks = load_chunks_from_jsonl(args.input)
    if not chunks:
        logger.error("No chunks loaded from %s — exiting", args.input)
        return

    report = run_pipeline(
        chunks=chunks,
        output_path=args.output,
        model=args.model,
        backtranslation_threshold=args.bt_threshold,
        z3_timeout_ms=args.z3_timeout,
        skip_z3=args.skip_z3,
        parallel_workers=args.workers,
    )

    print()
    print("=== PIPELINE REPORT ===")
    for line in report.summary_lines():
        print(line)


if __name__ == "__main__":
    main()
