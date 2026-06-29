"""
kb/ingest/z3_verify.py
axiom-forge v0.3 — Step 3: Z3 Verification

Three-tier verification:
  Tier A: regex pattern check (vacuous / tautology / contradiction) — no Z3
  Tier B: direct Z3 parse and check — milliseconds
  Tier C: LLM re-formalization to SMT-LIB2, then Z3

Integrates with formalize.py output via AxiomCandidateFormal.
"""

from __future__ import annotations

import os
import re
import json
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum

import z3

from m3_client import call_m3_chat, check_api_key as m3_api_key_set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

class Z3Status(str, Enum):
    SAT                          = "sat"
    UNSAT                        = "unsat"
    UNKNOWN                      = "unknown"
    VACUOUS                      = "vacuous"            # Tier A
    TAUTOLOGY                    = "tautology"          # Tier A
    CONTRADICTION                = "contradiction"      # Tier A
    CANNOT_FORMALIZE             = "cannot_formalize"
    SKIPPED_BACKTRANSLATION_FAIL = "skipped_backtranslation_fail"
    PARSE_ERROR                  = "parse_error"
    TIMEOUT                      = "timeout"


@dataclass
class Z3RawResult:
    status: Z3Status
    model: dict = field(default_factory=dict)
    unsat_core: list[str] = field(default_factory=list)
    notes: str = ""
    elapsed_ms: float = 0.0


@dataclass
class Z3VerifyInput:
    candidate_id: str
    formalization_id: str
    smt_fragment: str
    claim_nl: str
    domain: str
    backtranslation_passed: bool
    # optional: the full formal dict for Tier C context
    formal_context: dict = field(default_factory=dict)


@dataclass
class AxiomVerificationResult:
    candidate_id: str
    formalization_id: str
    tier_used: str                          # "A" | "B" | "C" | "SKIPPED" | "CANNOT"
    z3_status: str                          # Z3Status value
    z3_model: dict = field(default_factory=dict)
    counterexample: dict = field(default_factory=dict)
    unsat_core: list[str] = field(default_factory=list)
    verification_confidence: float = 0.0
    notes: str = ""
    elapsed_ms: float = 0.0
    smt_used: str = ""                      # actual SMT string sent to Z3

    def to_dict(self) -> dict:
        return asdict(self)


class CannotFormalizeError(Exception):
    pass


# ---------------------------------------------------------------------------
# Tier A: pattern-based checks (no Z3, instant)
# ---------------------------------------------------------------------------

# Patterns that indicate trivially vacuous / tautological / contradictory axioms
_VACUOUS_PATTERNS = [
    r"\(assert\s+true\b",
    r"\(assert\s+\(\s*=\s+(\w+)\s+\1\s*\)\s*\)",   # (assert (= x x))
]

_CONTRADICTION_PATTERNS = [
    r"\(assert\s+false\b",
    r"\(assert\s+\(\s*and\s+(\w+)\s+\(\s*not\s+\1\s*\)\s*\)\s*\)",
    r"\(assert\s+\(\s*not\s+true\b",
]

_TAUTOLOGY_PATTERNS = [
    r"\(assert\s+\(\s*or\s+(\w+)\s+\(\s*not\s+\1\s*\)\s*\)\s*\)",  # (assert (or p (not p)))
    r"\(assert\s+\(\s*=>\s+\S+\s+true\b",
]


def _matches_any(text: str, patterns: list[str]) -> bool:
    for p in patterns:
        if re.search(p, text.strip(), re.IGNORECASE):
            return True
    return False


def tier_a_check(smt_fragment: str) -> Optional[Z3RawResult]:
    """
    Returns a Z3RawResult if a trivial pattern is detected, else None.
    None means: proceed to Tier B.
    """
    s = smt_fragment.strip()
    if not s:
        return None

    if _matches_any(s, _CONTRADICTION_PATTERNS):
        return Z3RawResult(
            status=Z3Status.CONTRADICTION,
            notes="Tier A: pattern detected contradiction (assert false or p∧¬p)"
        )
    if _matches_any(s, _TAUTOLOGY_PATTERNS):
        return Z3RawResult(
            status=Z3Status.TAUTOLOGY,
            notes="Tier A: pattern detected tautology (assert true or p∨¬p)"
        )
    if _matches_any(s, _VACUOUS_PATTERNS):
        return Z3RawResult(
            status=Z3Status.VACUOUS,
            notes="Tier A: pattern detected vacuous axiom (assert x=x or assert true)"
        )

    # SHAP-specific symbol validation
    shap_symbols = {"SI_i", "phi_i", "phi_j", "f", "f_hat", "beta", "v_N"}
    declared = set(re.findall(r"\(declare-const\s+(\S+)", s))
    used = set(re.findall(r"\b(SI_i|phi_i|phi_j|f|f_hat|beta|v_N)\b", s))
    undeclared = used - declared
    if undeclared:
        logger.debug("Tier A note: SHAP symbols used but not declared: %s", undeclared)
        # Not a fatal error — Tier B will catch parse failures

    return None  # proceed to Tier B


# ---------------------------------------------------------------------------
# Tier B: direct Z3 parse + solve
# ---------------------------------------------------------------------------

def _model_to_dict(model: z3.ModelRef) -> dict:
    """Convert a Z3 model to a plain Python dict."""
    result = {}
    for decl in model.decls():
        val = model[decl]
        try:
            result[str(decl)] = str(val)
        except Exception:
            result[str(decl)] = repr(val)
    return result


def _core_to_list(core) -> list[str]:
    return [str(c) for c in core]


def tier_b_check(
    smt_fragment: str,
    timeout_ms: int = 5000,
) -> Optional[Z3RawResult]:
    """
    Attempt direct Z3 verification.
    Returns Z3RawResult if successful, None if the fragment cannot be parsed
    (signalling Tier C should be attempted).
    """
    t0 = time.perf_counter()
    try:
        solver = z3.Solver()
        solver.set("timeout", timeout_ms)
        solver.from_string(smt_fragment)

        result = solver.check()
        elapsed = (time.perf_counter() - t0) * 1000

        if result == z3.sat:
            return Z3RawResult(
                status=Z3Status.SAT,
                model=_model_to_dict(solver.model()),
                elapsed_ms=elapsed,
                notes="Tier B: Z3 found satisfying assignment"
            )
        elif result == z3.unsat:
            try:
                core = _core_to_list(solver.unsat_core())
            except Exception:
                core = []
            return Z3RawResult(
                status=Z3Status.UNSAT,
                unsat_core=core,
                elapsed_ms=elapsed,
                notes="Tier B: Z3 proved unsatisfiable (possible impossibility theorem)"
            )
        else:
            return Z3RawResult(
                status=Z3Status.UNKNOWN,
                elapsed_ms=elapsed,
                notes="Tier B: Z3 returned unknown (timeout or undecidable)"
            )

    except z3.Z3Exception as e:
        logger.debug("Tier B Z3 parse/solve error: %s", e)
        return None  # signal to try Tier C

    except Exception as e:
        logger.warning("Tier B unexpected error: %s", e)
        return None


# ---------------------------------------------------------------------------
# Tier C: LLM re-formalization → SMT-LIB2 → Z3
# ---------------------------------------------------------------------------

# SHAP domain standard SMT-LIB2 templates
_SHAP_TEMPLATES = {
    "efficiency": """
(declare-const phi_sum Real)
(declare-const f_x Real)
(assert (= phi_sum f_x))
""",
    "symmetry": """
(declare-const marginal_i Real)
(declare-const marginal_j Real)
(declare-const phi_i Real)
(declare-const phi_j Real)
(assert (=> (= marginal_i marginal_j) (= phi_i phi_j)))
""",
    "dummy": """
(declare-const phi_i Real)
(declare-const marginal_i Real)
(assert (=> (= marginal_i 0.0) (= phi_i 0.0)))
""",
    "linearity": """
(declare-const phi_f Real)
(declare-const phi_g Real)
(declare-const phi_combined Real)
(assert (= phi_combined (+ phi_f phi_g)))
""",
    "monotonicity": """
(declare-const phi_i Real)
(declare-const phi_j Real)
(declare-const marginal_i Real)
(declare-const marginal_j Real)
(assert (=> (>= marginal_i marginal_j) (>= phi_i phi_j)))
""",
}


def _try_shap_template(claim_nl: str, domain: str) -> Optional[str]:
    """
    Quick heuristic: if the claim looks like a known SHAP axiom,
    return a pre-built SMT-LIB2 template without an LLM call.
    """
    if domain != "ml_fairness":
        return None
    nl_lower = claim_nl.lower()
    for axiom_name, template in _SHAP_TEMPLATES.items():
        if axiom_name in nl_lower:
            logger.debug("Tier C: matched SHAP template '%s'", axiom_name)
            return template.strip()
    return None


def tier_c_reformalize(
    claim_nl: str,
    domain: str,
    original_fragment: str,
    formal_context: dict,
    timeout_ms: int = 5000,
    llm_client=None,  # kept for back-compat with old call sites; ignored
    model: str = "MiniMax-M3",
) -> Z3RawResult:
    """
    Use LLM to produce a valid SMT-LIB2 string, then run Z3.

    Backed by MiniMax-M3 via m3_client.call_m3_chat (was previously anthropic
    Claude). The `llm_client` parameter is kept for backwards-compat with
    old call sites but is ignored — Tier C routes through the project's
    standard M3 client now.
    """
    # 1. Try SHAP template shortcut
    shap_smt = _try_shap_template(claim_nl, domain)
    if shap_smt:
        result = tier_b_check(shap_smt, timeout_ms)
        if result is not None:
            result.notes = "Tier C (SHAP template shortcut): " + result.notes
            return result

    # 2. LLM re-formalization via M3
    if not m3_api_key_set():
        return Z3RawResult(
            status=Z3Status.CANNOT_FORMALIZE,
            notes="Tier C: MINIMAX_API_KEY not set",
        )

    context_str = ""
    if formal_context:
        context_str = f"""
Additional context from previous formalization attempt:
  quantifier: {formal_context.get('quantifier', '')}
  condition: {formal_context.get('condition', '')}
  conclusion: {formal_context.get('conclusion', '')}
  interpretation: {formal_context.get('interpretation_chosen', '')}
"""

    prompt = f"""You are an SMT-LIB2 expert. Translate the following normative claim
into a valid SMT-LIB2 string that Z3 can parse and verify.

Rules:
- Use only first-order logic. No lambda. No second-order quantifiers.
- Declare all free variables with (declare-const name Type).
- Use a single (assert ...) statement.
- Types must be: Real, Int, or Bool.
- Do NOT use (check-sat) or (get-model) — just declare-const and assert.
- If the claim is fundamentally not expressible in first-order SMT-LIB2
  (e.g. requires reasoning about all possible functions or sets of sets),
  output exactly the string: CANNOT_FORMALIZE

Domain: {domain}
Claim: {claim_nl}
Previous fragment (may be syntactically invalid): {original_fragment}
{context_str}
Output the SMT-LIB2 string only. No explanation. No markdown fences."""

    t0 = time.perf_counter()
    smt_string = call_m3_chat(
        system="You are an SMT-LIB2 expert. Output only the SMT-LIB2 string or CANNOT_FORMALIZE.",
        user=prompt,
        max_tokens=4096,  # bumped from 512: M3 reasoning burns 1-2k tokens
                          # before emitting SMT-LIB2 (~100-300 tokens). 512
                          # left 0 room after reasoning.
        model=model,
        temperature=0.0,
    )
    elapsed_llm = (time.perf_counter() - t0) * 1000

    if smt_string is None:
        return Z3RawResult(
            status=Z3Status.CANNOT_FORMALIZE,
            elapsed_ms=elapsed_llm,
            notes="Tier C: M3 chat call failed",
        )

    # Strip markdown fences if LLM added them despite instructions
    smt_string = re.sub(r"^```[\w]*\n?", "", smt_string)
    smt_string = re.sub(r"\n?```$", "", smt_string)
    smt_string = smt_string.strip()

    if smt_string == "CANNOT_FORMALIZE":
        return Z3RawResult(
            status=Z3Status.CANNOT_FORMALIZE,
            elapsed_ms=elapsed_llm,
            notes="Tier C: LLM determined claim cannot be expressed in first-order SMT-LIB2"
        )

    # Run Z3 on the LLM-produced SMT string
    result = tier_b_check(smt_string, timeout_ms)
    if result is None:
        return Z3RawResult(
            status=Z3Status.PARSE_ERROR,
            elapsed_ms=elapsed_llm,
            notes="Tier C: LLM produced SMT-LIB2 but Z3 still could not parse it",
            model={"smt_attempted": smt_string[:200]}
        )

    result.notes = f"Tier C (LLM→Z3, {elapsed_llm:.0f}ms LLM): " + result.notes
    return result


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def z3_verify(
    verify_input: Z3VerifyInput,
    timeout_ms: int = 5000,
    llm_client=None,
    model: str = "claude-sonnet-4-6",
) -> AxiomVerificationResult:
    """
    Run three-tier Z3 verification on a formalized axiom candidate.

    Tier routing:
      CANNOT_FORMALIZE flag → return immediately, no Z3
      backtranslation_passed=False → SKIPPED, no Z3
      Tier A pattern match → return immediately
      Tier B direct parse → return if successful
      Tier C LLM re-formalize → fallback

    Returns AxiomVerificationResult with full provenance.
    """
    cid = verify_input.candidate_id
    fid = verify_input.formalization_id
    smt = verify_input.smt_fragment

    # Gate 0: backtranslation failed — skip Z3
    if not verify_input.backtranslation_passed:
        return AxiomVerificationResult(
            candidate_id=cid,
            formalization_id=fid,
            tier_used="SKIPPED",
            z3_status=Z3Status.SKIPPED_BACKTRANSLATION_FAIL,
            verification_confidence=0.0,
            notes="Skipped: backtranslation similarity below threshold. "
                  "Formalization may not accurately represent the original claim.",
        )

    # Gate 1: cannot formalize flag from LLM
    if smt == "CANNOT_FORMALIZE" or not smt:
        return AxiomVerificationResult(
            candidate_id=cid,
            formalization_id=fid,
            tier_used="CANNOT",
            z3_status=Z3Status.CANNOT_FORMALIZE,
            verification_confidence=0.0,
            notes="SMT fragment marked CANNOT_FORMALIZE by formalization step.",
            smt_used=smt,
        )

    # Tier A
    tier_a_result = tier_a_check(smt)
    if tier_a_result is not None:
        return AxiomVerificationResult(
            candidate_id=cid,
            formalization_id=fid,
            tier_used="A",
            z3_status=tier_a_result.status,
            notes=tier_a_result.notes,
            elapsed_ms=tier_a_result.elapsed_ms,
            verification_confidence=0.95,
            smt_used=smt,
        )

    # Tier B
    tier_b_result = tier_b_check(smt, timeout_ms)
    if tier_b_result is not None:
        conf = _confidence_from_status(tier_b_result.status)
        return AxiomVerificationResult(
            candidate_id=cid,
            formalization_id=fid,
            tier_used="B",
            z3_status=tier_b_result.status,
            z3_model=tier_b_result.model,
            unsat_core=tier_b_result.unsat_core,
            notes=tier_b_result.notes,
            elapsed_ms=tier_b_result.elapsed_ms,
            verification_confidence=conf,
            smt_used=smt,
        )

    # Tier C
    logger.info("Candidate %s: Tier B failed, escalating to Tier C", cid)
    tier_c_result = tier_c_reformalize(
        claim_nl=verify_input.claim_nl,
        domain=verify_input.domain,
        original_fragment=smt,
        formal_context=verify_input.formal_context,
        timeout_ms=timeout_ms,
        llm_client=llm_client,
        model=model,
    )
    conf = _confidence_from_status(tier_c_result.status) * 0.85  # slight penalty for Tier C
    return AxiomVerificationResult(
        candidate_id=cid,
        formalization_id=fid,
        tier_used="C",
        z3_status=tier_c_result.status,
        z3_model=tier_c_result.model,
        unsat_core=tier_c_result.unsat_core,
        notes=tier_c_result.notes,
        elapsed_ms=tier_c_result.elapsed_ms,
        verification_confidence=conf,
        smt_used=smt,
    )


def _confidence_from_status(status: Z3Status) -> float:
    return {
        Z3Status.SAT:            0.90,
        Z3Status.UNSAT:          0.95,   # strongest: proved impossibility
        Z3Status.TAUTOLOGY:      0.95,
        Z3Status.CONTRADICTION:  0.95,
        Z3Status.VACUOUS:        0.80,
        Z3Status.UNKNOWN:        0.30,
        Z3Status.CANNOT_FORMALIZE: 0.0,
        Z3Status.PARSE_ERROR:    0.10,
        Z3Status.TIMEOUT:        0.20,
    }.get(status, 0.0)


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

def batch_verify(
    inputs: list[Z3VerifyInput],
    timeout_ms: int = 5000,
    llm_client=None,
    model: str = "claude-sonnet-4-6",
) -> list[AxiomVerificationResult]:
    """
    Run z3_verify on a list of inputs. Sequential (Z3 is fast enough).
    Returns results in the same order as inputs.
    """
    results = []
    for i, inp in enumerate(inputs):
        logger.info("Verifying %d/%d: %s", i + 1, len(inputs), inp.candidate_id)
        result = z3_verify(inp, timeout_ms, llm_client, model)
        results.append(result)
    return results


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------

def summarize_results(results: list[AxiomVerificationResult]) -> dict:
    """
    Produce a summary dict for lane_c_feedback.json.
    """
    from collections import Counter

    status_counts = Counter(r.z3_status for r in results)
    tier_counts   = Counter(r.tier_used for r in results)

    verified = [r for r in results if r.z3_status == Z3Status.SAT]
    impossible = [r for r in results if r.z3_status == Z3Status.UNSAT]

    mean_conf = (
        sum(r.verification_confidence for r in results) / len(results)
        if results else 0.0
    )

    return {
        "total":                     len(results),
        "by_status":                 dict(status_counts),
        "by_tier":                   dict(tier_counts),
        "verified_count":            len(verified),
        "impossibility_count":       len(impossible),
        "mean_verification_confidence": round(mean_conf, 4),
        "cannot_formalize_rate":     round(
            status_counts.get(Z3Status.CANNOT_FORMALIZE, 0) / max(len(results), 1), 4
        ),
        "skipped_rate":              round(
            status_counts.get(Z3Status.SKIPPED_BACKTRANSLATION_FAIL, 0) / max(len(results), 1), 4
        ),
    }


# ---------------------------------------------------------------------------
# CLI entry point (for testing)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="axiom-forge z3_verify — test runner")
    parser.add_argument("--smt",    type=str, help="SMT-LIB2 string to verify directly")
    parser.add_argument("--claim",  type=str, help="Natural language claim (for Tier C)")
    parser.add_argument("--domain", type=str, default="game_theory")
    parser.add_argument("--bt-passed", action="store_true", default=True,
                        help="Treat backtranslation as passed (default True)")
    args = parser.parse_args()

    if args.smt:
        inp = Z3VerifyInput(
            candidate_id="cli-test",
            formalization_id="cli-test-f",
            smt_fragment=args.smt,
            claim_nl=args.claim or "",
            domain=args.domain,
            backtranslation_passed=args.bt_passed,
        )
        result = z3_verify(inp)
        print(json.dumps(result.to_dict(), indent=2))
    else:
        # Self-test with known examples
        print("Running built-in self-tests...\n")

        tests = [
            # Tier A: tautology
            {
                "label": "Tier A tautology",
                "smt": "(assert (or p (not p)))",
                "claim": "Either p holds or p does not hold",
                "bt_passed": True,
                "expected_tier": "A",
                "expected_status": Z3Status.TAUTOLOGY,
            },
            # Tier A: contradiction
            {
                "label": "Tier A contradiction",
                "smt": "(assert false)",
                "claim": "False",
                "bt_passed": True,
                "expected_tier": "A",
                "expected_status": Z3Status.CONTRADICTION,
            },
            # Tier B: SAT — Shapley symmetry (satisfiable — there exist values satisfying it)
            {
                "label": "Tier B SAT — Shapley symmetry",
                "smt": """
(declare-const marginal_i Real)
(declare-const marginal_j Real)
(declare-const phi_i Real)
(declare-const phi_j Real)
(assert (=> (= marginal_i marginal_j) (= phi_i phi_j)))
""",
                "claim": "If two agents have equal marginal contributions, they receive equal payoffs",
                "bt_passed": True,
                "expected_tier": "B",
                "expected_status": Z3Status.SAT,
            },
            # Tier B: UNSAT — an impossibility
            {
                "label": "Tier B UNSAT — simple impossibility",
                "smt": """
(declare-const x Real)
(assert (and (> x 0) (< x 0)))
""",
                "claim": "x is both positive and negative",
                "bt_passed": True,
                "expected_tier": "B",
                "expected_status": Z3Status.UNSAT,
            },
            # Backtranslation failed — should skip
            {
                "label": "Skipped — backtranslation failed",
                "smt": "(assert (= phi_i phi_j))",
                "claim": "Agents receive equal payoffs",
                "bt_passed": False,
                "expected_tier": "SKIPPED",
                "expected_status": Z3Status.SKIPPED_BACKTRANSLATION_FAIL,
            },
            # Tier B: efficiency (satisfiable)
            {
                "label": "Tier B SAT — efficiency axiom",
                "smt": """
(declare-const phi_sum Real)
(declare-const f_x Real)
(assert (= phi_sum f_x))
""",
                "claim": "The sum of all Shapley values equals the model output",
                "bt_passed": True,
                "expected_tier": "B",
                "expected_status": Z3Status.SAT,
            },
        ]

        passed = 0
        for t in tests:
            inp = Z3VerifyInput(
                candidate_id=f"test-{t['label'][:20]}",
                formalization_id="test-f",
                smt_fragment=t["smt"],
                claim_nl=t["claim"],
                domain="game_theory",
                backtranslation_passed=t["bt_passed"],
            )
            result = z3_verify(inp, timeout_ms=3000)
            ok_tier   = result.tier_used   == t["expected_tier"]
            ok_status = result.z3_status   == t["expected_status"]
            status_str = "PASS" if (ok_tier and ok_status) else "FAIL"
            if ok_tier and ok_status:
                passed += 1
            print(f"  [{status_str}] {t['label']}")
            print(f"         tier={result.tier_used}  status={result.z3_status}  conf={result.verification_confidence:.2f}")
            if not (ok_tier and ok_status):
                print(f"         expected tier={t['expected_tier']}  status={t['expected_status']}")
            print()

        print(f"Results: {passed}/{len(tests)} passed")
