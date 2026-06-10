"""
🕳️ Gap Finder Agent
职责:在"文献主张"和"现实观察"之间找不一致、未解释、待公理化的候选问题。
"""
from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field

from .llm import M3Client
from .literature_agent import PropositionCard
from .reality_agent import RealityCard


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


SYSTEM = """你是一位站在"现有经济学公理体系边界"上的批判性研究者。
任务:在给定的文献命题与现实观察之间,**找出可被研究的问题(gap)**。
什么样的 gap 是有价值的:
1. 文献命题的某个**隐含假设**在现实中不成立;
2. 现实观察**与定理结论不一致**,且现有文献没有给出合理解释;
3. 多个文献命题之间存在**前提冲突**,需要一个新的、更弱的公理去统一;
4. 现有定理的**适用范围**与现实差距太大,需要新增公理来缩小这一差距。

约束:
- 每个 gap 必须给出 evidence_chain(把命题 id 和观察 id 串起来),不允许凭空捏造。
- missing_axiom 必须是"可被形式化"的——不是哲学口号,是一个能用数学/逻辑语言表达的新假设。
- candidate_formalization 可以粗糙,但要写出来;写不出就空,但 confidence 标低。
- confidence 0~1,testable 必须明确真假。
- 表述精炼:question 不超过 25 词,missing_axiom 不超过 30 词。
- 严格输出 JSON,不要额外文字。"""


def gap_finder(
    client: M3Client,
    domain: str,
    cards: List[PropositionCard],
    obs: List[RealityCard],
    n_gaps: int = 5,
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
        data = client.chat_json(SYSTEM, user, max_tokens=4000)
        gaps_raw = data.get("gaps", []) if isinstance(data, dict) else []
        if not gaps_raw and isinstance(data, dict) and "_raw" in data:
            print(f"      [warn] Gap round {round_idx} 失败,raw 长度={len(data['_raw'])}")
            continue
        for g in gaps_raw:
            try:
                all_gaps.append(Gap(**g))
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
                    )
                )
            if len(all_gaps) >= n_gaps:
                break
    return all_gaps[:n_gaps]
