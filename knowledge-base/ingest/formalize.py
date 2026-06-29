"""
kb/ingest/formalize.py
axiom-forge v0.3 — Step F: structured formalization

call_2_formalize(): takes an AxiomCandidateNL and produces a structured
formal representation, including an SMT-LIB2 fragment for Z3.

Critical design: the model MUST name which interpretation it chose AND
list alternatives. This is the primary mechanism for detecting semantic
ambiguity before back-translation.
"""

from __future__ import annotations

import os
import re
import uuid
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from discover import AxiomCandidateNL
from m3_client import call_m3_structured, check_api_key as m3_api_key_set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain-specific vocabulary hints (injected into prompt)
# ---------------------------------------------------------------------------

_DOMAIN_HINTS: dict[str, str] = {
    "game_theory": """\
Standard game theory formalisms:
  - Players: i, j ∈ N
  - Coalition: S ⊆ N
  - Characteristic function: v: 2^N → ℝ
  - Value/payoff: φ_i (Shapley), x_i (generic)
  - Marginal contribution of i to S: v(S∪{i}) − v(S)
Common interpretation ambiguities:
  symmetry vs anonymity vs equal_treatment vs interchangeability
  efficiency vs budget_balance vs strong_efficiency
""",
    "mechanism_design": """\
Standard mechanism design formalisms:
  - Types: θ_i ∈ Θ_i
  - Allocation: x ∈ X
  - Transfer: t_i ∈ ℝ
  - Utility: u_i(x, t_i, θ_i)
Common interpretation ambiguities:
  IC_dominant vs IC_Bayes vs IC_ex_post
  IR_ex_ante vs IR_interim vs IR_ex_post
""",
    "social_choice": """\
Standard social choice formalisms:
  - Preference profile: P = (P_1, ..., P_n)
  - Alternative set: A
  - Social welfare function: f: P^n → ordering on A
  - Social choice function: g: P^n → A
Common interpretation ambiguities:
  IIA (independence of irrelevant alternatives) — weak vs strong
  Pareto (weak vs strict)
  non-dictatorship vs anonymity
""",
    "ml_fairness": """\
SHAP and ML fairness formalisms:
  - Feature values: x_i ∈ ℝ
  - Shapley value: φ_i (attribution to feature i)
  - Model: f: ℝ^d → ℝ
  - Approximate model: f̂
  - Coalition: S ⊆ {1,...,d}
  - Characteristic function: v(S) = E[f(x) | x_S]
Standard SHAP axioms: efficiency, symmetry, dummy, linearity
Common interpretation ambiguities:
  conditional SHAP vs interventional SHAP vs marginal SHAP
  symmetry (equal marginals) vs anonymity (permutation invariance)
""",
    "welfare_economics": """\
Standard welfare formalisms:
  - Agent utility: u_i: X → ℝ
  - Allocation: x ∈ X
  - Social welfare function: W(u_1,...,u_n)
Common interpretation ambiguities:
  Pareto improvement vs Pareto optimality vs Kaldor-Hicks
  anonymity vs impartiality vs symmetry in welfare
""",
}

_DEFAULT_HINT = "Use standard first-order logic notation with explicit variable declarations."


# ---------------------------------------------------------------------------
# Pydantic model for structured output
# ---------------------------------------------------------------------------

VALID_QUANTIFIERS   = {"forall", "exists", "forall_exists", "none"}
VALID_FORMAL_TYPES  = {"equality", "inequality", "implication", "iff",
                       "negation", "existential", "conjunction", "disjunction"}


class FormalRepresentation(BaseModel):
    """Structured formalization of a normative claim."""

    quantifier: str = Field(
        description="One of: forall | exists | forall_exists | none"
    )
    bound_variables: list[str] = Field(
        description="Variable names used in the formal expression "
                    "(e.g. ['i', 'j', 'S', 'v']). Max 8.",
        max_length=8,
    )
    condition: str = Field(
        description="The antecedent / IF part in symbolic notation. "
                    "Empty string '' if no condition (unconditional axiom)."
    )
    conclusion: str = Field(
        description="The consequent / THEN part (or the full claim if no condition)."
    )
    formal_type: str = Field(
        description="One of: equality | inequality | implication | iff | "
                    "negation | existential | conjunction | disjunction"
    )

    # SMT-LIB2 fragment — the most important field for Z3
    smt_fragment: str = Field(
        description="Valid SMT-LIB2 string (declare-const + assert only). "
                    "Write CANNOT_FORMALIZE if first-order SMT-LIB2 is impossible "
                    "(e.g. requires second-order quantification)."
    )

    # Ambiguity tracking — MANDATORY
    interpretation_chosen: str = Field(
        description="Name the specific interpretation you chose, e.g. "
                    "'symmetry (equal marginal contributions imply equal payoffs)' "
                    "vs 'anonymity (permutation invariance)'. "
                    "NEVER leave this blank — naming your choice is mandatory."
    )
    alternative_interpretations: list[str] = Field(
        description="Other valid formalizations you did NOT choose. "
                    "List at least 1 alternative if any exist. "
                    "Empty list [] only if the claim has exactly one formalization.",
        max_length=5,
    )
    formalization_confidence: float = Field(
        ge=0.0, le=1.0,
        description="How confident you are in this formalization. "
                    "Lower if the claim is ambiguous or informal."
    )

    # SHAP-specific (only populated when domain == ml_fairness)
    shap_variables: dict = Field(
        default_factory=dict,
        description="For ml_fairness domain: map of symbolic names used to "
                    "their SHAP interpretation, e.g. "
                    "{'phi_i': 'Shapley value of feature i', 'v': 'char function'}. "
                    "Empty dict for other domains."
    )

    @field_validator("quantifier")
    @classmethod
    def validate_quantifier(cls, v: str) -> str:
        if v not in VALID_QUANTIFIERS:
            raise ValueError(f"quantifier must be one of {VALID_QUANTIFIERS}")
        return v

    @field_validator("formal_type")
    @classmethod
    def validate_formal_type(cls, v: str) -> str:
        if v not in VALID_FORMAL_TYPES:
            raise ValueError(f"formal_type must be one of {VALID_FORMAL_TYPES}")
        return v


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------

@dataclass
class AxiomCandidateFormal:
    # Identity — same candidate_id as the NL input
    candidate_id: str
    formalization_id: str       # new uuid for this formalization attempt

    # Formal representation
    quantifier: str
    bound_variables: list[str]
    condition: str
    conclusion: str
    formal_type: str

    # SMT-LIB2 for Z3
    smt_fragment: str

    # Ambiguity tracking
    interpretation_chosen: str
    alternative_interpretations: list[str]
    formalization_confidence: float

    # SHAP-specific
    shap_variables: dict = field(default_factory=dict)

    # Provenance: keep a copy of the input NL for traceability
    claim_nl_snapshot: str = ""
    domain: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def cannot_formalize(self) -> bool:
        return self.smt_fragment == "CANNOT_FORMALIZE" or not self.smt_fragment


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a formal logic assistant specializing in social science axioms.
Your task is to translate a normative claim into a structured formal
representation and an SMT-LIB2 string that Z3 can verify.

Critical requirement: many social science terms have MULTIPLE valid
formalizations. You MUST:
  1. Name the specific interpretation you chose (interpretation_chosen).
  2. List at least one alternative formalization if any exists.
This is not optional — it is the primary output quality signal.

SMT-LIB2 rules:
  - Use (declare-const name Type) for all free variables.
  - Types: Real, Int, or Bool only.
  - One (assert ...) statement only.
  - No (check-sat), no (get-model), no (push/pop).
  - No lambda, no second-order quantifiers.
  - If first-order SMT-LIB2 cannot express the claim, write CANNOT_FORMALIZE.
"""

_USER_TEMPLATE = """\
Domain: {domain}
Normative claim: {claim_nl}
Entities: {entities}
Claim type: {claim_type}

{domain_hint}

Formalize this claim into the following JSON structure:

  quantifier: "forall" | "exists" | "forall_exists" | "none"
  bound_variables: list of variable names
  condition: antecedent in symbolic notation (empty string if unconditional)
  conclusion: consequent in symbolic notation
  formal_type: "equality" | "inequality" | "implication" | "iff" | ...
  smt_fragment: SMT-LIB2 string (declare-const + assert) or "CANNOT_FORMALIZE"
  interpretation_chosen: NAME the specific interpretation you chose
  alternative_interpretations: list other valid formalizations you did NOT choose
  formalization_confidence: float 0-1
  shap_variables: dict mapping symbolic names to SHAP meanings (ml_fairness only)

IMPORTANT: naming interpretation_chosen and alternative_interpretations is
mandatory. Leaving interpretation_chosen blank or writing "N/A" is an error.
"""


# ---------------------------------------------------------------------------
# SMT-LIB2 post-processing
# ---------------------------------------------------------------------------

def _clean_smt(smt: str) -> str:
    """Strip markdown fences and normalize whitespace."""
    smt = smt.strip()
    smt = re.sub(r"^```[\w]*\n?", "", smt)
    smt = re.sub(r"\n?```$", "", smt)
    return smt.strip()


def _validate_smt_structure(smt: str) -> bool:
    """
    Basic structural check: must have at least one (assert ...) and
    all (declare-const ...) before the assert.
    Not a full parser — that's Z3's job.
    """
    if smt == "CANNOT_FORMALIZE":
        return True
    if not smt:
        return False
    has_assert   = bool(re.search(r"\(assert\b", smt))
    has_balanced = smt.count("(") == smt.count(")")
    return has_assert and has_balanced


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def call_2_formalize(
    candidate: AxiomCandidateNL,
    model: str = "MiniMax-M3",
) -> Optional[AxiomCandidateFormal]:
    """
    Formalize a single AxiomCandidateNL into a structured formal representation.

    Returns AxiomCandidateFormal, or None if the API call fails entirely.
    A CANNOT_FORMALIZE smt_fragment is a valid (non-None) return.
    """
    if not m3_api_key_set():
        logger.warning("MINIMAX_API_KEY not set; call_2_formalize returning None")
        return None

    domain_hint = _DOMAIN_HINTS.get(candidate.domain, _DEFAULT_HINT)

    user_prompt = _USER_TEMPLATE.format(
        domain=candidate.domain,
        claim_nl=candidate.claim_nl,
        entities=", ".join(candidate.entities),
        claim_type=candidate.claim_type,
        domain_hint=domain_hint,
    )

    response: Optional[FormalRepresentation] = call_m3_structured(
        system=_SYSTEM_PROMPT,
        user=user_prompt,
        schema=FormalRepresentation,
        max_retries=2,
        max_tokens=16384,  # bumped from 4096: FormalRepresentation has 11 fields
                            # incl. smt_fragment, alternative_interpretations
                            # (up to 5), interpretation_chosen. M3 reasoning
                            # burns 2-4k tokens. 16k is the practical cap.
        model=model,
        temperature=0.2,
    )
    if response is None:
        logger.warning("call_2_formalize: M3 returned no valid schema for candidate %s",
                       candidate.candidate_id)
        return None

    smt_clean = _clean_smt(response.smt_fragment)
    if not _validate_smt_structure(smt_clean):
        logger.warning(
            "Candidate %s: SMT structure check failed, setting CANNOT_FORMALIZE. "
            "Raw SMT: %s", candidate.candidate_id, smt_clean[:100]
        )
        smt_clean = "CANNOT_FORMALIZE"

    formal = AxiomCandidateFormal(
        candidate_id=candidate.candidate_id,
        formalization_id=str(uuid.uuid4()),
        quantifier=response.quantifier,
        bound_variables=response.bound_variables,
        condition=response.condition,
        conclusion=response.conclusion,
        formal_type=response.formal_type,
        smt_fragment=smt_clean,
        interpretation_chosen=response.interpretation_chosen,
        alternative_interpretations=response.alternative_interpretations,
        formalization_confidence=response.formalization_confidence,
        shap_variables=response.shap_variables,
        claim_nl_snapshot=candidate.claim_nl,
        domain=candidate.domain,
    )

    logger.info(
        "Candidate %s formalized: type=%s interpretation='%s' alts=%d smt_ok=%s",
        candidate.candidate_id,
        formal.formal_type,
        formal.interpretation_chosen[:40],
        len(formal.alternative_interpretations),
        not formal.cannot_formalize,
    )
    return formal


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

def batch_formalize(
    candidates: list[AxiomCandidateNL],
    model: str = "MiniMax-M3",
) -> list[AxiomCandidateFormal]:
    """
    Formalize a list of NL candidates.
    Skips candidates where call_2 returns None (API failure).
    """
    results = []
    for i, c in enumerate(candidates):
        logger.info("Formalizing %d/%d: %s", i + 1, len(candidates), c.candidate_id)
        formal = call_2_formalize(c, model=model)
        if formal is not None:
            results.append(formal)
        else:
            logger.warning("Skipping candidate %s (formalization failed)",
                           c.candidate_id)

    logger.info("batch_formalize complete: %d/%d succeeded",
                len(results), len(candidates))
    return results


# ---------------------------------------------------------------------------
# CLI self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    from discover import AxiomCandidateNL
    from datetime import datetime, timezone

    print("=== formalize.py self-test (prompt inspection, no API call) ===\n")

    sample = AxiomCandidateNL(
        candidate_id="test-cand-001",
        chunk_id="chunk-001",
        source_paper="Shapley 1953",
        domain="game_theory",
        claim_nl=(
            "If two players are interchangeable in a game, they must receive "
            "the same payoff under any fair allocation rule."
        ),
        claim_type="axiom",
        entities=["player", "game", "payoff", "allocation"],
        normative_strength="must",
        confidence=0.92,
        raw_quote="symmetric players must receive equal payoffs",
        low_confidence=False,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    domain_hint = _DOMAIN_HINTS.get(sample.domain, _DEFAULT_HINT)
    user_prompt = _USER_TEMPLATE.format(
        domain=sample.domain,
        claim_nl=sample.claim_nl,
        entities=", ".join(sample.entities),
        claim_type=sample.claim_type,
        domain_hint=domain_hint,
    )

    print("Input claim_nl:")
    print(f"  {sample.claim_nl}\n")
    print("User prompt (first 600 chars):")
    print(user_prompt[:600])
    print("\nPydantic schema for structured output:")
    print(json.dumps(FormalRepresentation.model_json_schema(), indent=2)[:800])
    print("\nNote: interpretation_chosen is MANDATORY — empty string is an error.")
    print("Set ANTHROPIC_API_KEY to run live formalization.")
