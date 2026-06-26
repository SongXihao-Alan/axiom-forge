"""
🕳️ Gap Finder Agent
职责:在"文献主张"和"现实观察"之间找不一致、未解释、待公理化的候选问题。
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field

from .llm import M3Client
from .literature_agent import PropositionCard
from .reality_agent import RealityCard


PROMPTS_DIR = Path(__file__).parent / "gap_finder_prompts"


def load_prompt(version: str = "v1") -> str:
    """Load system prompt from prompts directory."""
    prompt_file = PROMPTS_DIR / f"{version}.md"
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
    return prompt_file.read_text(encoding="utf-8")


class Gap(BaseModel):
    id: str
    question: str = Field(..., description="可被研究的问题陈述")
    evidence_chain: List[str] = Field(
        default_factory=list,
        description="支持该问题存在的事实链,例如 ['P3 says X', 'R2 shows not X under Y']",
    )
    missing_axiom: str = Field(..., description="现有文献缺失的、可能需要新增的公理/假设(自然语言)")
    candidate_formalization: str = Field(
        "",
        description="对 candidate_axiom 的初步形式化(可使用一阶逻辑/集合论/数学语言,不必完备)",
    )
    confidence: float = Field(0.5, ge=0.0, le=1.0, description="对该 gap 真实存在的置信度")
    testable: bool = Field(False, description="是否可被经验/数据证伪")
    prompt_version: str = Field("v1", description="使用的prompt版本")


def gap_finder(
    client: M3Client,
    domain: str,
    cards: List[PropositionCard],
    obs: List[RealityCard],
    n_gaps: int = 5,
    prompt_version: str = "v1",
) -> List[Gap]:
    """分轮拉取 gap,每轮 2 个。"""
    lit_dump = "\n".join(
        f"[{c.id}] claim={c.claim} | assumptions={c.assumptions} | scope={c.scope}"
        for c in cards
    )
    real_dump = "\n".join(
        f"[{o.id}] obs={o.observation} | time={o.time_window} | region={o.region} | "
        f"data={o.data_source_hint} | conflicts_with={o.conflicts_with}"
        for o in obs
    )

    all_gaps: List[Gap] = []
    batch_size = 2
    round_idx = 0
    max_rounds = 4
    while len(all_gaps) < n_gaps and round_idx < max_rounds:
        round_idx += 1
        remaining = n_gaps - len(all_gaps)
        take = min(batch_size, remaining)
        used_ids = [g.id for g in all_gaps]
        start_id = len(all_gaps) + 1
        user = f"""
研究主题: {domain}

=== 文献命题 ===
{lit_dump}

=== 现实观察 ===
{real_dump}

已有 gap id(避免重复): {used_ids if used_ids else '无'}

请找出 **{take} 个**新的、有价值的 gap(从 G{start_id} 开始),严格按以下 JSON:
{{
  "gaps": [
    {{
      "id": "G{start_id}",
      "question": "...",
      "evidence_chain": ["P3 says ...", "R2 shows ...", "..."],
      "missing_axiom": "...",
      "candidate_formalization": "...",
      "confidence": 0.0,
      "testable": true
    }}
  ]
}}
"""
        system_prompt = load_prompt(prompt_version)
        data = client.chat_json(system_prompt, user, max_tokens=4000)
        gaps_raw = data.get("gaps", []) if isinstance(data, dict) else []
        if not gaps_raw and isinstance(data, dict) and "_raw" in data:
            print(f"      [warn] Gap round {round_idx} 失败,raw 长度={len(data['_raw'])}")
            continue
        for g in gaps_raw:
            try:
                gap = Gap(**g)
                gap.prompt_version = prompt_version
                all_gaps.append(gap)
            except Exception:
                all_gaps.append(
                    Gap(
                        id=g.get("id", f"G{len(all_gaps)+1}"),
                        question=g.get("question", ""),
                        evidence_chain=g.get("evidence_chain", []) or [],
                        missing_axiom=g.get("missing_axiom", ""),
                        candidate_formalization=g.get("candidate_formalization", ""),
                        confidence=float(g.get("confidence", 0.5) or 0.5),
                        testable=bool(g.get("testable", False)),
                        prompt_version=prompt_version,
                    )
                )
            if len(all_gaps) >= n_gaps:
                break
    return all_gaps[:n_gaps]


# ── CLI ─────────────────────────────────────────────────────────────────
def main() -> int:
    p = argparse.ArgumentParser(description="Gap Finder Agent")
    p.add_argument("--domain", required=True, help="Research domain")
    p.add_argument("--cards", required=True, help="JSON file with PropositionCards")
    p.add_argument("--obs", required=True, help="JSON file with RealityCards")
    p.add_argument("--out", default="gaps.json", help="Output file for gaps")
    p.add_argument("--n-gaps", type=int, default=5, help="Number of gaps to find")
    p.add_argument(
        "--prompt-version",
        default="v1",
        choices=["v1", "v2"],
        help="Prompt version to use (default: v1)",
    )
    args = p.parse_args()

    cards_data = json.loads(Path(args.cards).read_text(encoding="utf-8"))
    obs_data = json.loads(Path(args.obs).read_text(encoding="utf-8"))

    cards = [PropositionCard(**c) for c in cards_data]
    obs = [RealityCard(**o) for o in obs_data]

    client = M3Client()
    gaps = gap_finder(client, args.domain, cards, obs, args.n_gaps, args.prompt_version)

    gaps_out = [g.model_dump(mode="json") for g in gaps]
    Path(args.out).write_text(json.dumps(gaps_out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(gaps_out)} gaps to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
