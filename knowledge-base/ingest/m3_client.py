"""
m3_client.py — M3 (minimaxi) wrapper with Pydantic schema validation.

Provides drop-in replacement for `anthropic.Anthropic + instructor.from_anthropic`
pattern used in 第二步 pipeline files. Uses MINIMAX_API_KEY (already required
elsewhere in the project) instead of ANTHROPIC_API_KEY.

Functions:
    call_m3_structured(system, user, schema, max_retries=2) -> schema instance
        Single LLM call + JSON parse + pydantic validation. Returns None on
        total failure (caller decides whether to retry or skip).

    call_m3_chat(system, user, max_tokens=1024) -> str
        Plain text chat completion (for tier_c_reformalize in z3_verify).

    batch_discover / batch_formalize helpers stay in discover.py / formalize.py —
    they wrap call_m3_structured per item.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import logging
from pathlib import Path
from typing import Any, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

# Reuse the existing M3Client (already proven in Lane B / lane_b_evaluator).
# agents/llm.py is on sys.path because web_api.py adds ROOT/agents.
# For Phase 2 modules in knowledge-base/ingest/, we add it explicitly.
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "agents"))

from llm import M3Client  # noqa: E402

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _check_key() -> Optional[str]:
    """Return MINIMAX_API_KEY if set, else None. Also tries .env file."""
    key = os.environ.get("MINIMAX_API_KEY", "")
    if key:
        return key
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("MINIMAX_API_KEY="):
                key = line.split("=", 1)[1].strip()
                if key:
                    return key
    return None


def call_m3_structured(
    system: str,
    user: str,
    schema: Type[T],
    max_retries: int = 2,
    max_tokens: int = 2048,
    model: str = "MiniMax-M3",
    temperature: float = 0.2,
) -> Optional[T]:
    """
    Single LLM call returning a pydantic-validated instance of `schema`.

    Flow:
      1. Call M3.chat(json_mode=True) which strips <think> blocks + fences
      2. Parse JSON
      3. Validate against `schema` (pydantic v2)
      4. On validation error: retry with appended "fix JSON" instruction
         (up to max_retries times)
      5. Return None on total failure (caller logs + skips)

    Why not instructor:
      instructor.from_anthropic / from_openai both expect specific client
      APIs. M3's chat endpoint is OpenAI-compatible but we don't want to
      add an OpenAI wrapper dep. Manual JSON + pydantic is ~30 lines and
      matches what kb_llm.py.ask_m3 already does for unstructured calls.
    """
    if not _check_key():
        return None

    client = M3Client(model=model, temperature=temperature)
    user_augmented = user
    last_err: Optional[str] = None

    for attempt in range(max_retries + 1):
        try:
            raw = client.chat(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_augmented},
                ],
                json_mode=True,
                max_tokens=max_tokens,
            )
        except (httpx.HTTPError, KeyError, ValueError) as e:
            last_err = f"API error: {type(e).__name__}: {e}"
            time.sleep(1 + attempt)
            continue

        # Clean: <think>...</think> + ``` fences
        cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, flags=re.DOTALL)
        if fence:
            cleaned = fence.group(1).strip()
        # Extract first { ... last } block if M3 added extra prose
        if not cleaned.startswith("{"):
            start, end = cleaned.find("{"), cleaned.rfind("}")
            if start != -1 and end > start:
                cleaned = cleaned[start:end + 1]

        try:
            data = json.loads(cleaned)
            instance = schema.model_validate(data)
            return instance
        except (json.JSONDecodeError, ValidationError) as e:
            last_err = f"{type(e).__name__}: {str(e)[:200]}"
            # DEBUG: dump raw response so we can see what M3 actually sent
            logger.debug(
                "M3 structured call failed (attempt %d/%d):\n"
                "  raw=%s\n  cleaned=%s\n  err=%s",
                attempt + 1, max_retries + 1, raw[:600], cleaned[:600], last_err,
            )
            # Tell M3 what to fix on retry
            user_augmented = (
                user
                + f"\n\n=== REMINDER (retry {attempt + 1}/{max_retries}) ===\n"
                + f"Your previous response failed validation: {last_err}\n"
                + "Output ONLY the JSON object matching the schema. No prose, no fences."
            )
            time.sleep(0.5 + attempt)

    # All retries exhausted
    return None


def call_m3_chat(
    system: str,
    user: str,
    max_tokens: int = 1024,
    model: str = "MiniMax-M3",
    temperature: float = 0.2,
) -> Optional[str]:
    """Plain text completion (used by z3_verify Tier C)."""
    if not _check_key():
        return None
    client = M3Client(model=model, temperature=temperature)
    try:
        raw = client.chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            json_mode=False,
            max_tokens=max_tokens,
        )
        # Strip <think> blocks if M3 emits them
        cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        return cleaned
    except (httpx.HTTPError, KeyError, ValueError):
        return None


def check_api_key() -> bool:
    """Public helper — True iff MINIMAX_API_KEY is available."""
    return bool(_check_key())


if __name__ == "__main__":
    # Smoke test
    print("MINIMAX_API_KEY set:", check_api_key())
    if check_api_key():
        from pydantic import BaseModel, Field

        class TestSchema(BaseModel):
            name: str
            count: int = Field(..., ge=0)

        out = call_m3_structured(
            "Return a JSON object. Nothing else.",
            "Output {\"name\": \"shapley\", \"count\": 4}",
            TestSchema,
            max_retries=0,
        )
        print("structured:", out)
        txt = call_m3_chat(
            "You are concise.",
            "What is the value of 2+2? One number, no prose.",
            max_tokens=10,
        )
        print("chat:", txt)