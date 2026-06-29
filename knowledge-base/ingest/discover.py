"""
kb/ingest/discover.py
axiom-forge v0.3 — Step D: normative claim discovery

call_1_discover(): free-form NL extraction of axiom candidates from text.

Design principles:
  - No schema anchoring: the prompt asks for normative claims in plain English,
    NOT for claims matching a pre-defined template.
  - Returns 0–5 candidates per chunk. Most chunks return 0–2.
  - Structured output via instructor (JSON schema enforced).
  - Low-confidence candidates are kept but flagged, not discarded.
"""

from __future__ import annotations

import os
import uuid
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator

from m3_client import call_m3_structured, check_api_key as m3_api_key_set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain registry
# ---------------------------------------------------------------------------

VALID_DOMAINS = {
    "game_theory",
    "mechanism_design",
    "social_choice",
    "welfare_economics",
    "credit_systems",
    "political_philosophy",
    "ml_fairness",
    "history",
    "math",
    "other",
}

VALID_CLAIM_TYPES = {
    "axiom",            # universal, formal, intended to be part of a characterization
    "principle",        # informal, contextual, not necessarily universal
    "constraint",       # a boundary condition imposed on a mechanism or outcome
    "impossibility",    # a claim that no mechanism / allocation can satisfy X and Y
    "characterization", # a claim that X is the unique solution satisfying A, B, C
}

VALID_NORMATIVE_STRENGTH = {"must", "should", "may", "must_not"}


# ---------------------------------------------------------------------------
# Pydantic models for instructor structured output
# ---------------------------------------------------------------------------

class RawCandidateItem(BaseModel):
    """One normative claim extracted from a text chunk."""

    claim_nl: str = Field(
        description="The normative claim restated clearly in one complete English sentence. "
                    "Must begin with a normative word (agents should / mechanisms must / "
                    "allocations ought to / it is required that). "
                    "Max 80 words."
    )
    claim_type: str = Field(
        description="One of: axiom | principle | constraint | impossibility | characterization"
    )
    entities: list[str] = Field(
        description="Key entities or variables mentioned (e.g. agent, coalition, allocation, "
                    "value function, mechanism). Max 6 items.",
        max_length=6,
    )
    normative_strength: str = Field(
        description="One of: must | should | may | must_not"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="How confident you are this is a normative (not descriptive) claim. "
                    "0 = definitely descriptive, 1 = definitely normative."
    )
    raw_quote: str = Field(
        description="Verbatim sentence(s) from the source text that contain this claim. "
                    "Must be an exact substring of the input text. Max 200 chars."
    )

    @field_validator("claim_type")
    @classmethod
    def validate_claim_type(cls, v: str) -> str:
        if v not in VALID_CLAIM_TYPES:
            raise ValueError(f"claim_type must be one of {VALID_CLAIM_TYPES}, got '{v}'")
        return v

    @field_validator("normative_strength")
    @classmethod
    def validate_normative_strength(cls, v: str) -> str:
        if v not in VALID_NORMATIVE_STRENGTH:
            raise ValueError(f"normative_strength must be one of {VALID_NORMATIVE_STRENGTH}")
        return v


class RawCandidateList(BaseModel):
    """Container so instructor can return a list from a single call."""
    candidates: list[RawCandidateItem] = Field(
        description="All normative claims found. Empty list [] if none found.",
        max_length=5,
    )


# ---------------------------------------------------------------------------
# Input / output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DiscoverInput:
    chunk_id: str
    text: str
    source_paper: str
    domain: str

    def __post_init__(self):
        if self.domain not in VALID_DOMAINS:
            raise ValueError(f"domain '{self.domain}' not in VALID_DOMAINS")


@dataclass
class AxiomCandidateNL:
    candidate_id: str
    chunk_id: str
    source_paper: str
    domain: str
    claim_nl: str
    claim_type: str
    entities: list[str]
    normative_strength: str
    confidence: float
    raw_quote: str
    low_confidence: bool        # True if confidence < LOW_CONF_THRESHOLD
    timestamp: str

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an axiom extraction system for social science literature.
Your task is to identify NORMATIVE claims — statements about how agents,
mechanisms, allocations, or outcomes SHOULD, MUST, or OUGHT TO behave.

Key distinctions you must make:
  NORMATIVE (include):  "agents should receive equal shares if symmetric"
                        "no mechanism can simultaneously satisfy A and B"
                        "the allocation must be Pareto optimal"
  DESCRIPTIVE (exclude): "agents typically receive unequal shares"
                          "the authors find that efficiency decreases"
                          "Shapley (1953) defined the value as..."

You extract only normative claims. Definitions, empirical findings, and
literature reviews are NOT normative claims and must be excluded.
"""

_USER_TEMPLATE = """\
Domain: {domain}
Source: {source_paper}

TEXT:
{text}

Extract all normative claims from the text above.
Return a JSON object with a single key "candidates" containing a list of
claim objects. Return {{"candidates": []}} if no normative claims are found.

For each claim, provide:
  claim_nl: one clear English sentence starting with a normative word
  claim_type: axiom | principle | constraint | impossibility | characterization
  entities: key variables/entities (max 6)
  normative_strength: must | should | may | must_not
  confidence: float 0-1 (how sure you are this is normative, not descriptive)
  raw_quote: verbatim sentence(s) from the text (exact substring, max 200 chars)

Rules:
  - At most 5 claims per chunk. Pick the most important ones if more exist.
  - If a claim is borderline descriptive (confidence < 0.5), still include it
    but set confidence accordingly — do not silently exclude borderline cases.
  - If the text is a definition or proof step with no normative content, return [].
"""


# ---------------------------------------------------------------------------
# Threshold
# ---------------------------------------------------------------------------

LOW_CONF_THRESHOLD = float(os.environ.get("DISCOVER_LOW_CONF_THRESHOLD", "0.5"))
MIN_TEXT_LENGTH    = int(os.environ.get("DISCOVER_MIN_TEXT_LENGTH", "100"))


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def call_1_discover(
    discover_input: DiscoverInput,
    model: str = "MiniMax-M3",
) -> list[AxiomCandidateNL]:
    """
    Extract normative axiom candidates from a single text chunk.

    Returns a list of AxiomCandidateNL (may be empty).
    Never raises on LLM errors — returns [] with a logged warning instead.

    Backed by MiniMax-M3 via m3_client.call_m3_structured (was previously
    anthropic + instructor; the .env / env var MINIMAX_API_KEY drives auth).
    """
    # Guard: skip very short chunks
    if len(discover_input.text.strip()) < MIN_TEXT_LENGTH:
        logger.debug("Chunk %s too short (%d chars), skipping",
                     discover_input.chunk_id, len(discover_input.text))
        return []

    if not m3_api_key_set():
        logger.warning("MINIMAX_API_KEY not set; call_1_discover returning []")
        return []

    user_prompt = _USER_TEMPLATE.format(
        domain=discover_input.domain,
        source_paper=discover_input.source_paper,
        text=discover_input.text[:4000],   # hard cap to avoid token overrun
    )

    response: Optional[RawCandidateList] = call_m3_structured(
        system=_SYSTEM_PROMPT,
        user=user_prompt,
        schema=RawCandidateList,
        max_retries=2,
        max_tokens=8192,  # bumped from 1024: RawCandidateList can be 5+ items ×
                            # ~150 tokens each = ~750-1000 tokens JSON, but
                            # M3 burns 1-2k tokens on <think> reasoning.
                            # 8192 leaves headroom for both.
        model=model,
        temperature=0.2,
    )
    if response is None:
        logger.warning("call_1_discover: M3 returned no valid schema for chunk %s",
                       discover_input.chunk_id)
        return []

    now = datetime.now(timezone.utc).isoformat()
    results = []
    for item in response.candidates:
        results.append(AxiomCandidateNL(
            candidate_id=str(uuid.uuid4()),
            chunk_id=discover_input.chunk_id,
            source_paper=discover_input.source_paper,
            domain=discover_input.domain,
            claim_nl=item.claim_nl,
            claim_type=item.claim_type,
            entities=item.entities,
            normative_strength=item.normative_strength,
            confidence=item.confidence,
            raw_quote=item.raw_quote,
            low_confidence=(item.confidence < LOW_CONF_THRESHOLD),
            timestamp=now,
        ))

    logger.info("Chunk %s → %d candidate(s)", discover_input.chunk_id, len(results))
    return results


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

def batch_discover(
    inputs: list[DiscoverInput],
    model: str = "MiniMax-M3",
) -> list[AxiomCandidateNL]:
    """
    Run call_1_discover over a list of chunks.
    Returns all candidates from all chunks in a flat list.
    """
    all_candidates = []
    for i, inp in enumerate(inputs):
        logger.info("Discovering %d/%d: %s", i + 1, len(inputs), inp.chunk_id)
        candidates = call_1_discover(inp, model=model)
        all_candidates.extend(candidates)

    logger.info("batch_discover complete: %d chunks → %d total candidates",
                len(inputs), len(all_candidates))
    return all_candidates


# ---------------------------------------------------------------------------
# CLI self-test (no API key needed — shows prompt structure)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    sample_texts = [
        {
            "chunk_id": "test-001",
            "source_paper": "Shapley 1953",
            "domain": "game_theory",
            "text": (
                "We require that the value function satisfy three axioms. "
                "First, efficiency: the sum of all players' values must equal the "
                "value of the grand coalition. Second, symmetry: if two players are "
                "interchangeable, they must receive equal payoffs. Third, dummy: a "
                "player who contributes nothing to any coalition should receive zero."
            ),
        },
        {
            "chunk_id": "test-002",
            "source_paper": "Arrow 1951",
            "domain": "social_choice",
            "text": (
                "Arrow proved that no social welfare function can simultaneously "
                "satisfy unrestricted domain, Pareto efficiency, independence of "
                "irrelevant alternatives, and non-dictatorship. This impossibility "
                "theorem implies that any aggregation procedure must violate at "
                "least one of these desiderata."
            ),
        },
        {
            "chunk_id": "test-003",
            "source_paper": "Empirical study 2020",
            "domain": "welfare_economics",
            "text": (
                "The dataset contains 10,000 loan records from 2015 to 2020. "
                "The average default rate was 3.2%. Table 2 shows descriptive "
                "statistics. The Gini coefficient for income inequality was 0.41."
            ),
        },
    ]

    print("=== discover.py self-test (prompt inspection, no API call) ===\n")
    for t in sample_texts:
        print(f"Chunk: {t['chunk_id']} | Domain: {t['domain']}")
        print(f"Text:  {t['text'][:80]}...")
        inp = DiscoverInput(**t)
        user_prompt = _USER_TEMPLATE.format(
            domain=inp.domain,
            source_paper=inp.source_paper,
            text=inp.text,
        )
        print("Prompt (first 200 chars):", user_prompt[:200].replace("\n", " "))
        print(f"Would call API: model=claude-sonnet-4-6, "
              f"response_model=RawCandidateList")
        print()

    print("Pydantic schema for structured output:")
    print(json.dumps(RawCandidateList.model_json_schema(), indent=2)[:600])
    print("...\n")
    print("Set ANTHROPIC_API_KEY to run live extraction.")
