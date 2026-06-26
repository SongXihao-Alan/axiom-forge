"""
lane_b_evaluator.py — Axiom Forge Lane B: LLM Evaluator with 3-Layer Verification

Three-layer evaluation pipeline:
  Layer 1: LLM v3 prompt → raw scores
  Layer 2: Z3 formal verification → formal check results
  Layer 3: LLM self-critique → corrected scores

Each prediction saved includes layer results for full auditability.
"""

import argparse, json, re, sys, time
from collections import Counter
from pathlib import Path
from typing import Optional

# ── Paths ─────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent
PROMPTS_DIR = ROOT / "kb" / "ingest" / "lane_b_prompts"
PREDICTIONS = ROOT / "paper" / "results" / "lane_b_predictions.json"
GOLD = ROOT / "paper" / "data" / "gold.json"
DISTRACTORS = ROOT / "paper" / "data" / "distractors.json"
KB_NODES = ROOT / "kb" / "nodes"
Z3_VERIFY = ROOT / "kb" / "ingest" / "z3_verify.py"
DIMS = ["clarity", "novelty", "internal_consistency",
        "empirical_grounding", "actionability"]

# ── Layer 1a: Discover (structured extraction) ──────────────────────
DISCOVER_PROMPT = """You are a structured axiom extractor for the Axiom Forge project.
Given a candidate axiom in natural language (NL) and optional formal notation and anchors,
produce a clean, structured representation.

## Input
NL: {nl}
Formal: {formal}
Anchors: {anchors}

## Your task
1. Extract the CORE CLAIM in clean, precise natural language (claim_nl).
   - Remove rhetorical flourishes, vague gestures, and context-dependent language.
   - Keep all quantified terms and conditions.
2. Produce a structured formal capture (formal_claim) using this schema:
   - For inequalities: ">=" instead of "≥", "<=" instead of "≤"
   - For quantifiers: "forall" / "exists" (lowercase)
   - For SHAP symbols: SI_i, phi_i, f, f_hat, beta as-is
   - For logical connectives: "and" / "or" / "not" / "implies"
3. Classify the type (axiom / theorem / definition / inequality / bound).
4. List 2-4 domain keywords.

Output ONLY a JSON object:
{{
  "claim_nl": "cleaned natural language claim",
  "formal_claim": "structured formal capture in SMT-LIB-like syntax",
  "source_type": "axiom|theorem|definition|inequality|bound",
  "domain_keywords": ["keyword1", "keyword2", ...],
  "confidence": 1-5,
  "disambiguate_notes": "any silent disambiguation decisions you made"
}}
"""


def discover(item: dict, prompt_version: str = "v3") -> dict:
    """
    Layer 1a: LLM extracts a structured claim from the axiom NL + formal.
    Returns discovery dict with claim_nl, formal_claim, source_type, domain_keywords.
    """
    item = load_item_nl_formal(item)
    nl = item.get("nl", "")
    formal = item.get("formal", "")
    anchors = item.get("anchors", [])
    anchors_str = json.dumps(anchors, ensure_ascii=False) if anchors else "none"

    user = DISCOVER_PROMPT.format(
        nl=nl[:600] if nl else "(none)",
        formal=formal[:400] if formal else "(none)",
        anchors=anchors_str[:200] if anchors_str else "none",
    )

    prompt = load_prompt(prompt_version)
    raw = _m3_call(prompt, user, max_tokens=600)
    if raw.startswith("ERROR"):
        return {
            "claim_nl": nl,
            "formal_claim": formal,
            "source_type": "unknown",
            "domain_keywords": [],
            "confidence": None,
            "disambiguate_notes": f"discover failed: {raw}",
            "raw": raw,
        }

    try:
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if m:
            raw = m.group(1)
        parsed = json.loads(raw)
        return {
            "claim_nl": parsed.get("claim_nl", nl),
            "formal_claim": parsed.get("formal_claim", formal),
            "source_type": parsed.get("source_type", "unknown"),
            "domain_keywords": parsed.get("domain_keywords", []),
            "confidence": parsed.get("confidence"),
            "disambiguate_notes": parsed.get("disambiguate_notes", ""),
            "raw": raw,
        }
    except Exception:
        return {
            "claim_nl": nl,
            "formal_claim": formal,
            "source_type": "unknown",
            "domain_keywords": [],
            "confidence": None,
            "disambiguate_notes": f"parse failed: {raw[:200]}",
            "raw": raw,
        }


# ── Layer 1c: Back-translation (fidelity check) ──────────────────────
BACKTRANSLATE_PROMPT = """You are a semantic fidelity auditor for the Axiom Forge project.
Given a natural language claim and its formal capture, your task is to:

1. Independently reconstruct natural language from the formal_claim WITHOUT seeing the original claim_nl.
2. Then compare your reconstruction to the original claim_nl.
3. Note any semantic drift: where the formal captured something different than the NL intent.

## Original natural language claim:
{claim_nl}

## Formal capture:
{formal_claim}

## Your task
Step 1: Re-read formal_claim and produce a standalone natural language interpretation
        (reconstructed_nl). Pretend you only have the formal and need to explain it to a domain expert.

Step 2: Compare reconstructed_nl to claim_nl.
- Are they describing the same constraint/relationship?
- Are there ambiguities in claim_nl that formal_claim resolved silently?
- Are there terms in claim_nl that do NOT appear in formal_claim?

Output ONLY a JSON object:
{{
  "reconstructed_nl": "your independent NL interpretation of formal_claim",
  "semantic_drift": "description of any silent disambiguation or meaning shift, or 'none' if clean",
  "nl_formal_gap": "terms in claim_nl absent from formal_claim, or 'none'",
  "reconstructed_confidence": 1-5
}}
"""


def back_translate(discover_result: dict, prompt_version: str = "v3") -> dict:
    """
    Layer 1c: LLM back-translates formal_claim to NL and compares to claim_nl.
    Returns back-translation dict with reconstructed_nl and similarity notes.
    """
    claim_nl = discover_result.get("claim_nl", "")
    formal_claim = discover_result.get("formal_claim", "")

    user = BACKTRANSLATE_PROMPT.format(
        claim_nl=claim_nl[:500] if claim_nl else "(empty)",
        formal_claim=formal_claim[:400] if formal_claim else "(empty)",
    )

    prompt = load_prompt(prompt_version)
    raw = _m3_call(prompt, user, max_tokens=600)
    if raw.startswith("ERROR"):
        return {
            "reconstructed_nl": "",
            "semantic_drift": f"back-translate failed: {raw}",
            "nl_formal_gap": "unknown",
            "reconstructed_confidence": None,
            "raw": raw,
        }

    try:
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if m:
            raw = m.group(1)
        parsed = json.loads(raw)
        return {
            "reconstructed_nl": parsed.get("reconstructed_nl", ""),
            "semantic_drift": parsed.get("semantic_drift", ""),
            "nl_formal_gap": parsed.get("nl_formal_gap", ""),
            "reconstructed_confidence": parsed.get("reconstructed_confidence"),
            "raw": raw,
        }
    except Exception:
        return {
            "reconstructed_nl": "",
            "semantic_drift": f"parse failed: {raw[:200]}",
            "nl_formal_gap": "unknown",
            "reconstructed_confidence": None,
            "raw": raw,
        }


def string_similarity(a: str, b: str) -> float:
    """Tokenised Jaccard similarity between two strings (0.0–1.0)."""
    if not a or not b:
        return 0.0
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a and not tokens_b:
        return 1.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return round(intersection / union, 4) if union > 0 else 0.0


# ── Prompt loading ────────────────────────────────────────────────
def load_prompt(version: str = "v1") -> str:
    path = PROMPTS_DIR / f"{version}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


# ── Layer 1: LLM evaluation ─────────────────────────────────────
def _m3_call(prompt: str, user: str, max_tokens: int = 1500) -> str:
    import urllib.request, urllib.error, ssl
    # Priority: (1) MINIMAX_API_KEY env var, (2) MINIMAX_API_KEY from .env
    api_key = __import__("os").getenv("MINIMAX_API_KEY", "")
    if not api_key:
        try:
            for line in Path(str(ROOT / ".env")).read_text().splitlines():
                if line.startswith("MINIMAX_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    break
        except Exception:
            pass
    if not api_key:
        return "ERROR: MINIMAX_API_KEY not set"

    payload = {
        "model": "MiniMax-Text-01",
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user}
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    # macOS Python 3.x lacks the system cert chain; pin to certifi's bundle
    # so `urllib` can verify api.minimaxi.com.
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl.create_default_context()
    # Retry on transient API errors (rate limit, quota). The 3 LLM calls
    # (discover / score / back-translate) share this function; a 429/empty
    # body should not poison the whole batch.
    last_err = ""
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                "https://api.minimaxi.com/v1/text/chatcompletion_v2",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {api_key}"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                body = json.loads(resp.read())
            # Guard against error/empty responses (rate-limit, quota, oversized prompt)
            choices = body.get("choices") if isinstance(body, dict) else None
            if not choices:
                err = body.get("error", {}) if isinstance(body, dict) else {}
                msg = err.get("message") if isinstance(err, dict) else str(body)[:200]
                last_err = f"empty choices ({msg or 'no message'})"
                if attempt < 2:
                    time.sleep(2 + attempt * 3)  # 2s, 5s
                    continue
                return f"ERROR: {last_err}"
            msg_obj = choices[0].get("message") if isinstance(choices[0], dict) else None
            if not isinstance(msg_obj, dict):
                last_err = f"message is {type(msg_obj).__name__}"
                if attempt < 2:
                    time.sleep(2 + attempt * 3)
                    continue
                return f"ERROR: {last_err}"
            content = msg_obj.get("content")
            if content is None:
                last_err = f"content is None (reason={msg_obj.get('finish_reason', 'unknown')})"
                if attempt < 2:
                    time.sleep(2 + attempt * 3)
                    continue
                return f"ERROR: {last_err}"
            return re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code} {e.reason}"
            if attempt < 2 and e.code in (429, 500, 502, 503, 504):
                time.sleep(2 + attempt * 3)
                continue
            return f"ERROR: {last_err}"
        except Exception as e:
            return f"ERROR: {e}"
    return f"ERROR: {last_err}"


# ── Layer 2: Z3 formal verification ──────────────────────────────
def z3_verify_formal(item: dict) -> dict:
    """
    Run Z3 on the formal statement (if present) to check internal consistency.
    Returns dict: {
        "z3_status": "sat" | "unsat" | "unknown" | "no_formal" | "error",
        "z3_model": "...",          # counterexample if sat
        "z3_time_ms": float,
        "z3_flags": ["contradiction", "vacuous", "unbound_var", "tautology"] | [],
        "z3_error": str | None
    }
    """
    result = {
        "z3_status": "no_formal",
        "z3_model": None,
        "z3_time_ms": 0.0,
        "z3_flags": [],
        "z3_error": None,
    }
    formal = item.get("formal", "").strip()
    if not formal:
        return result

    try:
        import subprocess
        cmd = [
            sys.executable, str(Z3_VERIFY),
            "--axiom", item.get("id", "unknown"),
            "--formal", formal,
            "--mode", "refute",
            "--output", "/tmp/z3_result.json",
        ]
        start = time.time()
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            env={**__import__("os").environ,
                 "PYTHONPATH": str(ROOT / "kb" / "ingest")}
        )
        result["z3_time_ms"] = round((time.time() - start) * 1000, 1)

        if proc.returncode == 0 and Path("/tmp/z3_result.json").exists():
            with open("/tmp/z3_result.json") as f:
                z3_out = json.load(f)
            result["z3_status"] = z3_out.get("status", "unknown")
            result["z3_model"] = z3_out.get("model")
            # Flag issues
            if result["z3_status"] == "sat":
                result["z3_flags"].append("counterexample_found")
                result["z3_flags"].append("formally_refuted")
            if "contradiction" in z3_out.get("flags", []):
                result["z3_flags"].append("contradiction")
            if "vacuous" in z3_out.get("flags", []):
                result["z3_flags"].append("vacuous")
            if "tautology" in z3_out.get("flags", []):
                result["z3_flags"].append("tautology")
        elif proc.returncode != 0:
            result["z3_status"] = "unknown"
            result["z3_error"] = proc.stderr[:200] if proc.stderr else "non-zero exit"

    except subprocess.TimeoutExpired:
        result["z3_status"] = "unknown"
        result["z3_error"] = "timeout (>30s)"
    except Exception as e:
        result["z3_status"] = "error"
        result["z3_error"] = str(e)[:200]

    return result


# ── Layer 3: LLM self-critique ───────────────────────────────────
SELF_CRITIQUE_PROMPT = """You are auditing your own axiom-quality evaluation.
Review the scores you gave and check for systematic over-rating.

## Your previous scores ( Layer 1 output):
{item_scores}

## Formal verification results ( Layer 2 output):
{z3_results}

## The axiom:
NL: {nl}
Formal: {formal}

## Your task:
Review your scores using the v3 decision-tree rubric.
If Z3 found a contradiction, vacuous quantifier, or counterexample, internal_consistency must be ≤ 2.
If Z3 found a tautology (always true), novelty must be ≤ 1 (likely a restatement or vacuous truth).
If empirical_grounding citation is not peer-reviewed or does not support the claim, it must be ≤ 2.
If the axiom is a "principle" (not operational), actionability must be ≤ 2.
If you cannot name a specific prior work for a novelty ≥ 4 claim, novelty must be ≤ 3.

Output ONLY a JSON object:
{{
  "corrections": {{
    "clarity": "corrected score or null if no change",
    "novelty": "corrected score or null if no change",
    "internal_consistency": "corrected score or null if no change",
    "empirical_grounding": "corrected score or null if no change",
    "actionability": "corrected score or null if no change"
  }},
  "critique": "one-sentence explanation of what you corrected and why",
  "z3_overridden": true|false
}}
"""


def self_critique(item: dict, layer1b_result: dict,
                  layer2_z3: dict, prompt_version: str = "v3",
                  discovered_nl: str = "", discovered_formal: str = "") -> dict:
    """
    Layer 3: LLM reviews its own Layer 1 scores using Z3 results.
    Returns corrections dict and explanation.
    """
    item = load_item_nl_formal(item)
    # Prefer discovered claim; fall back to item fields
    nl = discovered_nl or item.get("nl", "")
    formal = discovered_formal or item.get("formal", "")

    item_scores = json.dumps(layer1b_result.get("scores", {}), indent=2)
    z3_results = json.dumps(layer2_z3, indent=2)

    user = SELF_CRITIQUE_PROMPT.format(
        item_scores=item_scores,
        z3_results=z3_results,
        nl=nl[:600],
        formal=formal[:400],
    )

    prompt = load_prompt(prompt_version)  # use v3 prompt for self-critique
    raw = _m3_call(prompt, user, max_tokens=800)
    if raw.startswith("ERROR"):
        return {
            "corrections": {d: None for d in DIMS},
            "critique": f"self-critique failed: {raw}",
            "z3_overridden": False,
        }

    try:
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if m:
            raw = m.group(1)
        critique = json.loads(raw)
        return critique
    except Exception:
        return {
            "corrections": {d: None for d in DIMS},
            "critique": f"parse failed: {raw[:200]}",
            "z3_overridden": False,
        }


# ── Full 3-layer evaluation ───────────────────────────────────────
def evaluate_item(item: dict, prompt_version: str = "v3",
                 run_z3: bool = True,
                 run_self_critique: bool = True) -> dict:
    """
    Three-layer evaluation pipeline.

    Layer 1: LLM v3 prompt scoring
    Layer 2: Z3 formal verification (if formal statement present)
    Layer 3: LLM self-critique using Z3 results

    Returns a complete prediction dict with all layer results.
    """
    item = load_item_nl_formal(item)
    nl = item.get("nl", "")
    formal = item.get("formal", "")
    anchors = item.get("anchors", [])
    item_id = item.get("id", "")

    if not nl and not formal:
        return {
            "id": item_id,
            "type": item.get("type"),
            "is_distractor": item.get("is_distractor", False),
            "failure_mode": item.get("failure_mode"),
            "prompt_version": prompt_version,
            "layer1a_discover": None,
            "layer1b_scores": None,
            "layer1c_backtranslate": None,
            "backtranslation_similarity": None,
            "layer2_z3": {"z3_status": "no_formal"},
            "layer3_critique": None,
            "final_scores": {d: 1 for d in DIMS},
            "final_tier": "easy",
            "corrections_applied": {},
            "distractor_flag": item.get("is_distractor", False),
            "failure_modes_detected": [],
        }

    # ── Layer 1a: Structured claim discovery ────────────────────
    layer1a_discover = discover(item, prompt_version=prompt_version)
    discovered_nl = layer1a_discover.get("claim_nl", nl)
    discovered_formal = layer1a_discover.get("formal_claim", formal)

    # ── Layer 1b: LLM scoring (uses discovered claim) ──────────
    rubric_prompt = load_prompt(prompt_version)
    user = (
        f"## Candidate axiom\n\n"
        f"NL: {discovered_nl[:600]}\n\n"
        f"Formal: {discovered_formal[:400]}\n\n"
        f"Anchors: {json.dumps(anchors, ensure_ascii=False)[:200] if anchors else '(none)'}\n\n"
        f"## Output (JSON only):"
    )
    raw = _m3_call(rubric_prompt, user, max_tokens=1500)

    layer1b_result = {"raw": raw, "error": None, "parsed": None}
    if raw.startswith("ERROR"):
        layer1b_result["error"] = raw
        scores = {d: None for d in DIMS}
        tier = None
    elif raw:
        try:
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
            if m:
                raw = m.group(1)
            parsed = json.loads(raw)
            # Coerce scores to [1, 5]
            scores = {}
            for d in DIMS:
                v = parsed.get("scores", {}).get(d)
                if v is not None:
                    v = int(v)
                    scores[d] = max(1, min(5, v))
                else:
                    scores[d] = None
            tier = parsed.get("tier")
            layer1b_result["parsed"] = parsed
        except Exception as e:
            layer1b_result["error"] = f"parse failed: {e}"
            scores = {d: None for d in DIMS}
            tier = None
    else:
        scores = {d: None for d in DIMS}
        tier = None

    # ── Layer 1c: Back-translation fidelity check ─────────────
    layer1c_backtranslate = back_translate(layer1a_discover, prompt_version=prompt_version)
    # Compute tokenized Jaccard similarity between claim_nl and reconstructed_nl
    claim_nl_for_sim = layer1a_discover.get("claim_nl", "")
    reconstructed_nl = layer1c_backtranslate.get("reconstructed_nl", "")
    backtranslation_similarity = string_similarity(claim_nl_for_sim, reconstructed_nl)

    # ── Layer 2: Z3 formal verification ────────────────────────
    # Use discovered_formal for Z3 verification
    item_for_z3 = dict(item)
    item_for_z3["formal"] = discovered_formal
    layer2_z3 = {"z3_status": "no_formal"} if not discovered_formal else z3_verify_formal(item_for_z3)

    # Auto-correct internal_consistency if Z3 finds contradiction/vacuous
    auto_corrections = {}
    if layer2_z3.get("z3_flags"):
        flags = layer2_z3["z3_flags"]
        if "contradiction" in flags or "formally_refuted" in flags:
            auto_corrections["internal_consistency"] = 1
        elif "vacuous" in flags:
            auto_corrections["internal_consistency"] = 2
        elif "tautology" in flags:
            auto_corrections["novelty"] = 1  # tautology = restatement
            auto_corrections["internal_consistency"] = 2

    # ── Layer 3: LLM self-critique ─────────────────────────────
    layer3_critique = None
    if run_self_critique and scores.get("internal_consistency") is not None:
        layer3_critique = self_critique(
            item, {"scores": scores},
            layer2_z3, prompt_version,
            discovered_nl=discovered_nl, discovered_formal=discovered_formal
        )

    # Apply corrections: auto (Z3) first, then LLM self-critique
    final_scores = dict(scores)
    corrections_applied = dict(auto_corrections)  # track source

    # Always apply non-null corrections from self_critique
    if layer3_critique:
        for dim, corrected in layer3_critique.get("corrections", {}).items():
            if corrected is not None and dim in DIMS:
                corrected_int = max(1, min(5, int(corrected)))
                if dim in corrections_applied:
                    # Don't override auto-corrections with None
                    if layer3_critique["corrections"][dim] is not None:
                        corrections_applied[dim] = f"llm_self_critique:{corrected_int}"
                else:
                    corrections_applied[dim] = f"llm_self_critique:{corrected_int}"

    # Apply auto-corrections that weren't overridden
    for dim, score in auto_corrections.items():
        if dim not in corrections_applied:
            corrections_applied[dim] = f"z3_auto:{score}"

    # Build final scores
    for dim, source in corrections_applied.items():
        source = str(source)  # ensure string (was int in some paths)
        if ":" in source:
            final_scores[dim] = int(source.split(":")[1])

    # Tier re-calculation
    valid_scores = [v for v in final_scores.values() if v is not None]
    if valid_scores:
        spread = max(valid_scores) - min(valid_scores)
        if spread <= 2:
            final_tier = "easy"
        elif spread >= 3 or item.get("is_distractor"):
            final_tier = "hard"
        else:
            final_tier = "medium"
    else:
        final_tier = None

    return {
        "id": item_id,
        "type": item.get("type"),
        "is_distractor": item.get("is_distractor", False),
        "failure_mode": item.get("failure_mode"),
        "prompt_version": prompt_version,
        # Layer results (full auditability)
        "layer1a_discover": layer1a_discover,
        "layer1b_scores": {
            "scores": scores,
            "tier": tier,
            "raw": raw[:500] if raw else None,
            "error": layer1b_result.get("error"),
            "parsed": layer1b_result.get("parsed"),
        },
        "layer1c_backtranslate": layer1c_backtranslate,
        "backtranslation_similarity": backtranslation_similarity,
        "layer2_z3": layer2_z3,
        "layer3_critique": layer3_critique,
        # Final output
        "final_scores": final_scores,
        "final_tier": final_tier,
        "corrections_applied": corrections_applied,
        "distractor_flag": item.get("is_distractor", False),
        "failure_modes_detected": (layer1b_result.get("parsed") or {}).get("failure_modes_detected", []),
    }


# ── Item construction ────────────────────────────────────────────
def item_from_kb(node: dict) -> dict:
    return {
        "id": node.get("id"),
        "type": node.get("type"),
        "source": f"kb/nodes/{node.get('type')}s/{node.get('id')}.json",
        "is_distractor": False,
        "nl": node.get("nl") or node.get("description") or node.get("title") or "",
        "formal": node.get("formal") or "",
        "domain": node.get("domain", ""),
        "anchors": node.get("anchors", []),
        "process_meta": node.get("process_meta", {}),
    }


def item_from_distractor(d: dict) -> dict:
    return {
        "id": d.get("id"),
        "type": "distractor",
        "source": "paper/data/distractors.json",
        "is_distractor": True,
        "nl": d.get("nl", ""),
        "formal": d.get("formal", ""),
        "failure_mode": d.get("failure_mode", ""),
    }


def item_from_gold(g: dict) -> dict:
    return {
        "id": g.get("id"),
        "type": g.get("type"),
        "source": g.get("source", ""),
        "is_distractor": g.get("is_distractor", False),
        "nl": "",
        "formal": "",
    }


def load_item_nl_formal(item: dict) -> dict:
    if item.get("nl") and item.get("formal"):
        return item
    if item.get("is_distractor") and item.get("id", "").startswith("DIS-"):
        try:
            d_data = json.loads(DISTRACTORS.read_text(encoding="utf-8"))
            for d in d_data.get("distractors", []):
                if d.get("id") == item["id"]:
                    item["nl"] = item.get("nl") or d.get("nl", "")
                    item["formal"] = item.get("formal") or d.get("formal", "")
                    item["failure_mode"] = d.get("failure_mode", "")
                    return item
        except Exception:
            pass
    kb_path = item.get("source", "")
    if kb_path and not kb_path.startswith("kb/"):
        kb_path = "kb/" + kb_path
    p = ROOT / kb_path
    if p.exists():
        try:
            n = json.loads(p.read_text(encoding="utf-8"))
            item["nl"] = item.get("nl") or n.get("nl") or n.get("description") or n.get("title", "")
            item["formal"] = item.get("formal") or n.get("formal", "")
            item["anchors"] = item.get("anchors") or n.get("anchors", [])
        except Exception:
            pass
    return item


# ── Bulk evaluation ───────────────────────────────────────────────
def evaluate_all(items: list[dict], output_path: Path,
                rate_limit_s: float = 1.0,
                prompt_version: str = "v3",
                run_z3: bool = True,
                run_self_critique: bool = True) -> list[dict]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    predictions = []
    if output_path.exists():
        try:
            predictions = json.loads(output_path.read_text(encoding="utf-8"))
            print(f"Resuming: {len(predictions)} predictions already on file")
        except Exception:
            predictions = []
    # Re-run any "stuck" entries (final_tier None = upstream LLM/Z3 failed
    # on a previous attempt). Otherwise resume skips them forever.
    done_ids = {
        p.get("id") for p in predictions
        if p.get("id") and p.get("final_tier") is not None
    }

    for i, item in enumerate(items):
        if item.get("id") in done_ids:
            continue
        print(f"[{i+1}/{len(items)}] {item.get('id')}", end=" ", flush=True)
        pred = evaluate_item(item, prompt_version=prompt_version,
                            run_z3=run_z3,
                            run_self_critique=run_self_critique)
        fs = pred.get("final_scores", {})
        score_str = " ".join(
            f"{d[:3]}={fs[d]}" for d in DIMS if fs.get(d) is not None
        )
        corrections = pred.get("corrections_applied", {})
        corr_str = f"  [CORR:{corrections}]" if corrections else ""
        print(f"-> {score_str} tier={pred.get('final_tier','?')}{corr_str}")
        predictions.append(pred)
        output_path.write_text(json.dumps(predictions, ensure_ascii=False, indent=2),
                              encoding="utf-8")
        time.sleep(rate_limit_s)
    return predictions


# ── Cohen's kappa ────────────────────────────────────────────────
def cohens_kappa(predictions: list[dict], gold: list[dict], dim: str) -> Optional[float]:
    pred_map = {p["id"]: p for p in predictions if p.get("id")}
    gold_map = {g["id"]: g for g in gold if g.get("id")}
    common = set(pred_map) & set(gold_map)
    if not common:
        return None
    pairs = [
        (pred_map[i]["final_scores"].get(dim), gold_map[i]["scores"].get(dim))
        for i in common
        if pred_map[i]["final_scores"].get(dim) is not None
        and gold_map[i]["scores"].get(dim) is not None
    ]
    if not pairs:
        return None
    k = 5
    weights = [[(i - j) ** 2 / (k - 1) ** 2 for j in range(1, k + 1)] for i in range(1, k + 1)]
    n = len(pairs)
    observed = sum(weights[p - 1][g - 1] for p, g in pairs) / n
    pred_counts = Counter(p for p, _ in pairs)
    gold_counts = Counter(g for _, g in pairs)
    expected = sum(
        (pred_counts[i] / n) * (gold_counts[j] / n) * weights[i - 1][j - 1]
        for i in range(1, k + 1) for j in range(1, k + 1)
    )
    if expected >= 1.0:
        return 1.0
    return 1 - observed / expected


def report(predictions_path: Path, gold_path: Path) -> int:
    if not predictions_path.exists():
        print(f"ERROR: {predictions_path} not found")
        return 1
    predictions = json.loads(predictions_path.read_text(encoding="utf-8"))
    gold_data = json.loads(gold_path.read_text(encoding="utf-8"))
    gold = gold_data.get("items", [])
    print(f"Predictions: {len(predictions)}, Gold: {len(gold)}")
    print()
    print("=" * 60)
    print(f"{'Dimension':<28} {'QWK':<8} {'n':<6} {'coverage'}")
    print("=" * 60)
    for dim in DIMS:
        k = cohens_kappa(predictions, gold, dim)
        pred_map = {p["id"]: p for p in predictions if p.get("id")}
        gold_map = {g["id"]: g for g in gold if g.get("id")}
        common = set(pred_map) & set(gold_map)
        non_null = sum(
            1 for i in common
            if pred_map[i]["final_scores"].get(dim) is not None
            and gold_map[i]["scores"].get(dim) is not None
        )
        cov = f"{non_null}/{len(common)}" if common else "0/0"
        print(f"{dim:<28} {k if k is not None else 'N/A':<8} {len(common):<6} {cov}")
    print()
    print("Mean absolute error per dim:")
    for dim in DIMS:
        pred_map = {p["id"]: p for p in predictions if p.get("id")}
        gold_map = {g["id"]: g for g in gold if g.get("id")}
        common = set(pred_map) & set(gold_map)
        errs = [
            abs(pred_map[i]["final_scores"][dim] - gold_map[i]["scores"][dim])
            for i in common
            if pred_map[i]["final_scores"].get(dim) is not None
            and gold_map[i]["scores"].get(dim) is not None
        ]
        mae = sum(errs) / len(errs) if errs else None
        print(f"  {dim:<28} {mae if mae is not None else 'N/A'}")
    return 0


# ── Scaling ─────────────────────────────────────────────────────
def _generate_distractor(src: dict, mode: str) -> tuple[str, str]:
    nl = src.get("nl", "")
    formal = src.get("formal", "")
    first = nl.split(" ")[0] if nl.split() else "X"
    if mode == "circular":
        return (f"{first} is true if and only if {first} is true.", "True ↔ True")
    if mode == "vague_gesture":
        return (f"{nl} in a meaningful, appropriate, and reasonable way.",
                f"∀x: Reasonable({formal[:50]}) [no definition]")
    if mode == "restatement":
        return (f"Restating: {nl} (this is just a restatement).", formal or "True")
    if mode == "premise_mismatch":
        return (f"If the axiom is vacuous, then {nl}", f"Vacuous ⇒ ({formal})")
    if mode == "no_source":
        return (nl, formal)
    if mode == "contradictory":
        return (f"NOT ({nl})", f"¬({formal})")
    if mode == "vacuous":
        return (f"For all x in the empty set, {nl}", f"∀x ∈ ∅: ({formal})")
    return (nl, formal)


def scale_to(target: int, predictions_path: Path,
              prompt_version: str = "v3") -> int:
    base_items = []
    if GOLD.exists():
        gold_data = json.loads(GOLD.read_text(encoding="utf-8"))
        for g in gold_data.get("items", []):
            base_items.append(item_from_gold(g))
    if DISTRACTORS.exists():
        d_data = json.loads(DISTRACTORS.read_text(encoding="utf-8"))
        for d in d_data.get("distractors", []):
            base_items.append(item_from_distractor(d))
    for type_dir in KB_NODES.iterdir():
        if not type_dir.is_dir():
            continue
        for f in type_dir.glob("*.json"):
            try:
                n = json.loads(f.read_text(encoding="utf-8"))
                base_items.append(item_from_kb(n))
            except Exception:
                continue
    seen, unique = set(), []
    for it in base_items:
        if it.get("id") and it["id"] not in seen:
            seen.add(it["id"])
            unique.append(it)
    base_items = unique
    print(f"Base set: {len(base_items)} unique items")
    if len(base_items) < target:
        needed = target - len(base_items)
        print(f"Need {needed} more items; auto-generating distractors")
        candidates = [it for it in base_items
                     if not it.get("is_distractor") and it.get("nl")]
        for i in range(needed):
            src = candidates[i % len(candidates)]
            mode = ["circular", "vague_gesture", "restatement",
                    "premise_mismatch", "no_source",
                    "contradictory", "vacuous"][i % 7]
            nl, formal = _generate_distractor(src, mode)
            base_items.append({
                "id": f"AUTO-DIS-{i+1:04d}",
                "type": "auto_distractor",
                "source": "auto-generation",
                "is_distractor": True,
                "nl": nl,
                "formal": formal,
                "failure_mode": mode,
                "perturb_source": src.get("id"),
            })
    print(f"Final item count: {len(base_items)}")
    return evaluate_all(base_items, predictions_path, prompt_version=prompt_version)


# ── CLI ─────────────────────────────────────────────────────────
def cmd_evaluate_one(node_id: str, prompt_version: str = "v3",
                     run_z3: bool = True, run_self_critique: bool = True) -> int:
    # Check distractors first
    if node_id.startswith("DIS-"):
        try:
            d_data = json.loads(DISTRACTORS.read_text(encoding="utf-8"))
            for d in d_data.get("distractors", []):
                if d.get("id") == node_id:
                    item = item_from_distractor(d)
                    pred = evaluate_item(item, prompt_version=prompt_version,
                                        run_z3=run_z3,
                                        run_self_critique=run_self_critique)
                    print(json.dumps(pred, ensure_ascii=False, indent=2))
                    return 0
        except Exception:
            pass
    # Then check KB nodes
    for type_dir in KB_NODES.iterdir():
        if not type_dir.is_dir():
            continue
        for f in type_dir.glob("*.json"):
            try:
                n = json.loads(f.read_text(encoding="utf-8"))
                if n.get("id") == node_id:
                    item = item_from_kb(n)
                    pred = evaluate_item(item, prompt_version=prompt_version,
                                        run_z3=run_z3,
                                        run_self_critique=run_self_critique)
                    print(json.dumps(pred, ensure_ascii=False, indent=2))
                    return 0
            except Exception:
                continue
    print(f"ERROR: node '{node_id}' not found", file=sys.stderr)
    return 1


def cmd_evaluate_gold(prompt_version: str = "v3",
                      run_z3: bool = True,
                      run_self_critique: bool = True) -> int:
    if not GOLD.exists():
        print(f"ERROR: {GOLD} not found")
        return 1
    data = json.loads(GOLD.read_text(encoding="utf-8"))
    items = [item_from_gold(g) for g in data.get("items", [])]
    return evaluate_all(items, PREDICTIONS, prompt_version=prompt_version,
                        run_z3=run_z3, run_self_critique=run_self_critique)


def cmd_evaluate_distractors(prompt_version: str = "v3",
                             run_z3: bool = True,
                             run_self_critique: bool = True) -> int:
    if not DISTRACTORS.exists():
        print(f"ERROR: {DISTRACTORS} not found")
        return 1
    data = json.loads(DISTRACTORS.read_text(encoding="utf-8"))
    items = [item_from_distractor(d) for d in data.get("distractors", [])]
    return evaluate_all(items, PREDICTIONS, prompt_version=prompt_version,
                        run_z3=run_z3, run_self_critique=run_self_critique)


def cmd_evaluate_all(prompt_version: str = "v3",
                     run_z3: bool = True,
                     run_self_critique: bool = True) -> int:
    items = []
    for type_dir in KB_NODES.iterdir():
        if not type_dir.is_dir():
            continue
        for f in type_dir.glob("*.json"):
            try:
                n = json.loads(f.read_text(encoding="utf-8"))
                items.append(item_from_kb(n))
            except Exception:
                continue
    return evaluate_all(items, PREDICTIONS, prompt_version=prompt_version,
                        run_z3=run_z3, run_self_critique=run_self_critique)


def cmd_scale(target: int, prompt_version: str = "v3",
              run_z3: bool = True, run_self_critique: bool = True) -> int:
    return scale_to(target, PREDICTIONS, prompt_version=prompt_version)


def main() -> int:
    p = argparse.ArgumentParser(
        description="Axiom Forge Lane B: 3-Layer Evaluator (LLM → Z3 → Self-Critique)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("evaluate", help="Score a single KB node")
    sp.add_argument("node_id")
    sp.add_argument("--prompt-version", default="v3", choices=["v1", "v2", "v3"])
    sp.add_argument("--no-z3", dest="run_z3", action="store_false", default=True,
                    help="Skip Z3 Layer 2")
    sp.add_argument("--no-self-critique", dest="run_self_critique", action="store_false",
                    default=True, help="Skip LLM self-critique Layer 3")

    sp = sub.add_parser("evaluate-all", help="Score every KB node")
    sp.add_argument("--prompt-version", default="v3", choices=["v1", "v2", "v3"])
    sp.add_argument("--no-z3", dest="run_z3", action="store_false", default=True)
    sp.add_argument("--no-self-critique", dest="run_self_critique", action="store_false", default=True)

    sp = sub.add_parser("evaluate-gold", help="Score all 104 gold items")
    sp.add_argument("--prompt-version", default="v3", choices=["v1", "v2", "v3"])
    sp.add_argument("--no-z3", dest="run_z3", action="store_false", default=True)
    sp.add_argument("--no-self-critique", dest="run_self_critique", action="store_false", default=True)

    sp = sub.add_parser("evaluate-distractors", help="Score all 30 distractor items")
    sp.add_argument("--prompt-version", default="v3", choices=["v1", "v2", "v3"])
    sp.add_argument("--no-z3", dest="run_z3", action="store_false", default=True)
    sp.add_argument("--no-self-critique", dest="run_self_critique", action="store_false", default=True)

    sp = sub.add_parser("scale", help="Scale to N items (auto-generate distractors)")
    sp.add_argument("target", type=int)
    sp.add_argument("--prompt-version", default="v3", choices=["v1", "v2", "v3"])
    sp.add_argument("--no-z3", dest="run_z3", action="store_false", default=True)
    sp.add_argument("--no-self-critique", dest="run_self_critique", action="store_false", default=True)

    sp = sub.add_parser("report", help="Compute Cohen's kappa vs gold")
    sp.add_argument("--gold", default=str(GOLD))

    args = p.parse_args()
    pv = getattr(args, "prompt_version", "v3")
    rz3 = getattr(args, "run_z3", True)
    rsc = getattr(args, "run_self_critique", True)

    if args.cmd == "evaluate":
        return cmd_evaluate_one(args.node_id, prompt_version=pv,
                                run_z3=rz3, run_self_critique=rsc)
    elif args.cmd == "evaluate-all":
        return cmd_evaluate_all(prompt_version=pv, run_z3=rz3, run_self_critique=rsc)
    elif args.cmd == "evaluate-gold":
        return cmd_evaluate_gold(prompt_version=pv, run_z3=rz3, run_self_critique=rsc)
    elif args.cmd == "evaluate-distractors":
        return cmd_evaluate_distractors(prompt_version=pv, run_z3=rz3, run_self_critique=rsc)
    elif args.cmd == "scale":
        return cmd_scale(args.target, prompt_version=pv, run_z3=rz3, run_self_critique=rsc)
    elif args.cmd == "report":
        return report(PREDICTIONS, Path(args.gold))
    return 1


if __name__ == "__main__":
    sys.exit(main())
