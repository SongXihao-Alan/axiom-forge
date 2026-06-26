"""
kb/ingest/backtranslate.py
axiom-forge v0.3 — Back-translation consistency gate

call_3_backtranslate(): reconstruct natural language from the formal
representation ONLY — without seeing the original claim_nl.

This isolation is what makes back-translation meaningful as a quality gate:
if the LLM's formalization was faithful, the reconstruction should match
the original claim. If it doesn't, the formalization silently changed the
semantics (e.g. chose 'anonymity' when the text meant 'symmetry').

Two-stage similarity check:
  Stage 1: embedding cosine similarity (fast, ~50ms)
  Stage 2: LLM-as-judge (optional, only if Stage 1 score is borderline)

Failure policy: do NOT discard. Set status='needs_human_review' and keep.
These cases are the most interesting for the paper.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional

import anthropic
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from formalize import AxiomCandidateFormal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Thresholds (configurable via env)
# ---------------------------------------------------------------------------

BT_THRESHOLD_PASS          = float(os.environ.get("BACKTRANSLATION_THRESHOLD",        "0.75"))
BT_THRESHOLD_JUDGE_TRIGGER = float(os.environ.get("BACKTRANSLATION_JUDGE_THRESHOLD",  "0.65"))
EMBEDDING_MODEL            = os.environ.get("EMBEDDING_MODEL", "voyage-3")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BackTranslateInput:
    candidate_id: str
    formalization_id: str
    claim_formal: AxiomCandidateFormal
    claim_nl_original: str          # needed for similarity, NOT passed to call_3


@dataclass
class BackTranslationResult:
    candidate_id: str
    formalization_id: str
    claim_reconstructed: str        # NL produced from formal only
    similarity_score: float         # cosine similarity vs original claim_nl
    similarity_method: str          # "embedding" | "embedding+judge"
    passed: bool                    # True if score >= BT_THRESHOLD_PASS
    failure_reason: str             # "" if passed
    ambiguity_preserved: bool       # True if reconstruction mentioned interpretation_chosen
    judge_score: Optional[float]    # 0–1 from LLM judge, or None if not triggered

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Prompt: call_3 (isolated — does NOT see claim_nl_original)
# ---------------------------------------------------------------------------

_BT_SYSTEM = """\
You are a natural language explanation system.
Translate formal logical representations into plain English.
"""

_BT_USER_TEMPLATE = """\
You are given a formal logical representation of a claim.
Explain what this claim means in ONE clear English sentence.

Rules:
  - Do NOT add examples, context, or background knowledge.
  - Describe only what the formal expression literally states.
  - Do NOT reproduce the symbolic notation — use plain English words.
  - Name the specific interpretation: {interpretation_chosen}

Formal representation:
  quantifier:      {quantifier}
  bound variables: {bound_variables}
  condition:       {condition}
  conclusion:      {conclusion}
  formal type:     {formal_type}
  interpretation:  {interpretation_chosen}
  SMT fragment:    {smt_fragment}

Output the English sentence only. No JSON. No preamble. No period at the end
unless it is a natural sentence ending.
"""


# ---------------------------------------------------------------------------
# LLM-as-judge prompt (Stage 2, optional)
# ---------------------------------------------------------------------------

_JUDGE_SYSTEM = """\
You are a semantic equivalence judge for social science axioms.
"""

_JUDGE_USER_TEMPLATE = """\
Are these two statements semantically equivalent?

Statement A (original claim):
  {claim_nl_original}

Statement B (reconstructed from formal representation):
  {claim_reconstructed}

Consider:
  - Do they refer to the same entities and relationships?
  - Would a domain expert consider them equivalent?
  - Minor paraphrase differences are acceptable.
  - Differences in scope (universal vs existential) are NOT acceptable.

Output a JSON object with exactly two fields:
  score: float 0.0–1.0 (1.0 = fully equivalent, 0.0 = completely different)
  reason: one sentence explaining your judgment
"""


# ---------------------------------------------------------------------------
# Embedding similarity
# ---------------------------------------------------------------------------

def _get_embeddings(
    texts: list[str],
    client: anthropic.Anthropic,
) -> np.ndarray:
    """
    Get embeddings using the Anthropic client.
    Falls back to a simple TF-IDF-based cosine if the embedding API fails.
    Returns shape (n, d).
    """
    try:
        # Anthropic currently proxies voyage embeddings
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts,
        )
        vectors = np.array([r.embedding for r in response.data], dtype=np.float32)
        return vectors
    except Exception as e:
        logger.warning("Embedding API failed (%s), falling back to TF-IDF", e)
        return _tfidf_fallback(texts)


def _tfidf_fallback(texts: list[str]) -> np.ndarray:
    """
    Simple bag-of-words cosine similarity as a fallback when embeddings fail.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    try:
        vec = TfidfVectorizer(min_df=1, stop_words="english")
        matrix = vec.fit_transform(texts).toarray()
        return matrix.astype(np.float32)
    except Exception:
        # Absolute fallback: return identity (forces manual review)
        return np.eye(len(texts), dtype=np.float32)


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two 1-D vectors."""
    a = a.reshape(1, -1)
    b = b.reshape(1, -1)
    return float(cosine_similarity(a, b)[0][0])


# ---------------------------------------------------------------------------
# LLM judge (Stage 2)
# ---------------------------------------------------------------------------

def _llm_judge(
    claim_nl_original: str,
    claim_reconstructed: str,
    client: anthropic.Anthropic,
    model: str,
) -> Optional[float]:
    """
    Ask LLM to score semantic equivalence. Returns 0–1 or None on failure.
    """
    import json as _json

    prompt = _JUDGE_USER_TEMPLATE.format(
        claim_nl_original=claim_nl_original,
        claim_reconstructed=claim_reconstructed,
    )
    try:
        response = client.messages.create(
            model=model,
            max_tokens=150,
            system=_JUDGE_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        # Strip markdown fences if present
        text = text.replace("```json", "").replace("```", "").strip()
        data = _json.loads(text)
        score = float(data.get("score", 0.0))
        reason = data.get("reason", "")
        logger.debug("LLM judge score=%.3f reason=%s", score, reason)
        return max(0.0, min(1.0, score))
    except Exception as e:
        logger.warning("LLM judge failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def call_3_backtranslate(
    bt_input: BackTranslateInput,
    client: Optional[anthropic.Anthropic] = None,
    model: str = "claude-sonnet-4-6",
    use_judge: bool = True,
) -> BackTranslationResult:
    """
    Reconstruct NL from formal representation (call_3, isolated),
    then compute similarity to the original claim_nl.

    The function NEVER sees claim_nl_original inside the LLM prompt —
    only in the similarity computation afterwards.

    Returns BackTranslationResult. Never raises — on total failure, returns
    a result with passed=False and failure_reason set.
    """
    if client is None:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    f = bt_input.claim_formal

    # Handle CANNOT_FORMALIZE: no point back-translating
    if f.cannot_formalize:
        return BackTranslationResult(
            candidate_id=bt_input.candidate_id,
            formalization_id=bt_input.formalization_id,
            claim_reconstructed="",
            similarity_score=0.0,
            similarity_method="skipped",
            passed=False,
            failure_reason="SMT fragment is CANNOT_FORMALIZE — back-translation skipped",
            ambiguity_preserved=False,
            judge_score=None,
        )

    # Build prompt — critically, claim_nl_original is NOT included
    prompt = _BT_USER_TEMPLATE.format(
        quantifier=f.quantifier,
        bound_variables=", ".join(f.bound_variables),
        condition=f.condition or "(none)",
        conclusion=f.conclusion,
        formal_type=f.formal_type,
        interpretation_chosen=f.interpretation_chosen,
        smt_fragment=f.smt_fragment[:300],  # truncate for long SMT strings
    )

    # call_3: reconstruct NL from formal only
    try:
        response = client.messages.create(
            model=model,
            max_tokens=200,
            system=_BT_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        claim_reconstructed = response.content[0].text.strip()
    except Exception as e:
        logger.warning("call_3_backtranslate API call failed for %s: %s",
                       bt_input.candidate_id, e)
        return BackTranslationResult(
            candidate_id=bt_input.candidate_id,
            formalization_id=bt_input.formalization_id,
            claim_reconstructed="",
            similarity_score=0.0,
            similarity_method="failed",
            passed=False,
            failure_reason=f"API call failed: {e}",
            ambiguity_preserved=False,
            judge_score=None,
        )

    # Stage 1: embedding cosine similarity
    embeddings = _get_embeddings(
        [bt_input.claim_nl_original, claim_reconstructed],
        client=client,
    )
    sim_score = _cosine_sim(embeddings[0], embeddings[1])
    method = "embedding"
    judge_score: Optional[float] = None

    # Stage 2: LLM judge — only if score is borderline
    if use_judge and BT_THRESHOLD_JUDGE_TRIGGER <= sim_score < BT_THRESHOLD_PASS:
        judge_score = _llm_judge(
            bt_input.claim_nl_original,
            claim_reconstructed,
            client,
            model,
        )
        if judge_score is not None:
            # Weighted average: 60% embedding, 40% judge
            sim_score = 0.6 * sim_score + 0.4 * judge_score
            method = "embedding+judge"

    passed = sim_score >= BT_THRESHOLD_PASS

    # Check if reconstruction explicitly named the interpretation
    interp_lower = f.interpretation_chosen.lower()
    recon_lower  = claim_reconstructed.lower()
    # Split interpretation name into tokens; check if key token appears
    interp_tokens = [t for t in interp_lower.split() if len(t) > 3]
    ambiguity_preserved = any(tok in recon_lower for tok in interp_tokens)

    failure_reason = ""
    if not passed:
        failure_reason = (
            f"Similarity {sim_score:.3f} below threshold {BT_THRESHOLD_PASS}. "
            f"Original: '{bt_input.claim_nl_original[:60]}...' "
            f"Reconstructed: '{claim_reconstructed[:60]}...'"
        )

    logger.info(
        "Back-translation %s: score=%.3f method=%s passed=%s ambiguity_preserved=%s",
        bt_input.candidate_id, sim_score, method, passed, ambiguity_preserved,
    )

    return BackTranslationResult(
        candidate_id=bt_input.candidate_id,
        formalization_id=bt_input.formalization_id,
        claim_reconstructed=claim_reconstructed,
        similarity_score=round(sim_score, 4),
        similarity_method=method,
        passed=passed,
        failure_reason=failure_reason,
        ambiguity_preserved=ambiguity_preserved,
        judge_score=round(judge_score, 4) if judge_score is not None else None,
    )


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

def batch_backtranslate(
    inputs: list[BackTranslateInput],
    client: Optional[anthropic.Anthropic] = None,
    model: str = "claude-sonnet-4-6",
    use_judge: bool = True,
) -> list[BackTranslationResult]:
    if client is None:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    results = []
    for i, inp in enumerate(inputs):
        logger.info("Back-translating %d/%d: %s", i + 1, len(inputs), inp.candidate_id)
        result = call_3_backtranslate(inp, client=client, model=model, use_judge=use_judge)
        results.append(result)

    pass_rate = sum(r.passed for r in results) / max(len(results), 1)
    mean_sim  = sum(r.similarity_score for r in results) / max(len(results), 1)
    logger.info(
        "batch_backtranslate complete: pass_rate=%.2f mean_sim=%.3f",
        pass_rate, mean_sim,
    )
    return results


# ---------------------------------------------------------------------------
# Statistics helper (for lane_c_feedback.json)
# ---------------------------------------------------------------------------

def backtranslation_stats(results: list[BackTranslationResult]) -> dict:
    if not results:
        return {}

    scores  = [r.similarity_score for r in results]
    passed  = [r for r in results if r.passed]
    failed  = [r for r in results if not r.passed]
    cant    = [r for r in results if "CANNOT_FORMALIZE" in r.failure_reason]
    ambig   = [r for r in results if r.ambiguity_preserved]

    return {
        "total":                        len(results),
        "passed":                       len(passed),
        "failed":                       len(failed),
        "cannot_formalize_skipped":     len(cant),
        "pass_rate":                    round(len(passed) / len(results), 4),
        "mean_similarity":              round(float(np.mean(scores)), 4),
        "median_similarity":            round(float(np.median(scores)), 4),
        "min_similarity":               round(float(np.min(scores)), 4),
        "max_similarity":               round(float(np.max(scores)), 4),
        "ambiguity_preserved_rate":     round(len(ambig) / len(results), 4),
        "judge_triggered_count":        sum(
            1 for r in results if r.similarity_method == "embedding+judge"
        ),
        "converged_formalization":      len(passed) / len(results) >= 0.80,
    }


# ---------------------------------------------------------------------------
# CLI self-test (no API key needed)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    print("=== backtranslate.py self-test (similarity logic, no API call) ===\n")

    # Test the TF-IDF fallback similarity directly
    pairs = [
        (
            "If two agents are symmetric, they must receive equal payoffs",
            "Agents with equal marginal contributions receive the same allocation",
            "should pass (similar meaning)",
        ),
        (
            "If two agents are symmetric, they must receive equal payoffs",
            "The model output must equal the sum of all feature attributions",
            "should fail (different axiom)",
        ),
        (
            "No mechanism can simultaneously satisfy incentive compatibility and budget balance",
            "It is impossible for any mechanism to be both incentive compatible and budget balanced",
            "should pass (paraphrase)",
        ),
    ]

    print(f"Threshold: {BT_THRESHOLD_PASS}")
    print(f"Judge trigger: {BT_THRESHOLD_JUDGE_TRIGGER}\n")

    for original, reconstructed, label in pairs:
        vecs = _tfidf_fallback([original, reconstructed])
        sim  = _cosine_sim(vecs[0], vecs[1])
        status = "PASS" if sim >= BT_THRESHOLD_PASS else "FAIL"
        print(f"[{status}] {label}")
        print(f"  sim={sim:.3f}")
        print(f"  original:      {original[:60]}")
        print(f"  reconstructed: {reconstructed[:60]}")
        print()

    print("Note: live runs use voyage-3 embeddings (much better than TF-IDF).")
    print("Set ANTHROPIC_API_KEY to run live back-translation.")
