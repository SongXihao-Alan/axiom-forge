"""
📚 Literature Agent
职责:把领域相关的"命题/假设/方法"提炼成结构化命题卡片。
输入:领域描述 + 关键文献/概念(可以由 Orchestrator 提供种子,也可以用领域知识库)
输出:List[PropositionCard]
"""
from __future__ import annotations
from typing import List, Dict, Any
from pydantic import BaseModel, Field

from .llm import M3Client


class PropositionCard(BaseModel):
    id: str
    claim: str = Field(..., description="用一句话陈述的命题")
    domain: str = Field(..., description="该命题所属的子领域,例如 mechanism_design / general_equilibrium")
    assumptions: List[str] = Field(default_factory=list, description="该命题成立所依赖的假设")
    scope: str = Field("", description="适用范围与边界")
    evidence: str = Field("", description="该命题在文献中的支撑类型(定理/实验/案例/直觉)")
    source_hint: str = Field("", description="出处线索(作者/年份/概念名),不要求是真实引用")


SYSTEM = """你是一位严谨的经济学/机制设计研究者。
任务:基于给定的"研究主题"和"种子文献/概念",提炼一组**互不重叠、可被独立检验**的命题卡片。
约束:
1. 每张卡片聚焦**一个**命题,不要把多个命题塞进同一张。
2. 假设(assumptions)必须显式列出——这是后续找 Gap 的关键。
3. 适用范围(scope)要写明"在什么条件下成立、在什么条件下失效"。
4. evidence 字段若为定理/命题,标注"theorem";若为直觉/思想实验,标注"intuition"。
5. 严格输出 JSON,不要有额外文字。
6. 表述尽量精炼,claim 不超过 30 词,assumptions 每条不超过 12 词。"""


def literature_agent(
    client: M3Client,
    domain: str,
    seed_concepts: List[str],
    n_cards: int = 8,
) -> List[PropositionCard]:
    """分轮拉取命题卡片。每轮限定 3 张,提高 JSON 稳定性。"""
    all_cards: List[PropositionCard] = []
    batch_size = 3
    round_idx = 0
    max_rounds = 4
    while len(all_cards) < n_cards and round_idx < max_rounds:
        round_idx += 1
        remaining = n_cards - len(all_cards)
        take = min(batch_size, remaining)
        used_ids = [c.id for c in all_cards]
        start_id = len(all_cards) + 1
        user = f"""
研究主题: {domain}

种子文献/概念(用作先验,不必逐条对应):
{chr(10).join('- ' + s for s in seed_concepts)}

已有命题 id(避免重复): {used_ids if used_ids else '无'}

请提炼 **{take} 张**新的命题卡片(从 P{start_id} 开始编号),按以下 JSON 模式返回:
{{
  "cards": [
    {{
      "id": "P{start_id}",
      "claim": "...",
      "domain": "mechanism_design|general_equilibrium|fair_division|...",
      "assumptions": ["...", "..."],
      "scope": "...",
      "evidence": "theorem|empirical|intuition|case_study",
      "source_hint": "..."
    }}
  ]
}}
"""
        data = client.chat_json(SYSTEM, user, max_tokens=4000)
        cards_raw = data.get("cards", []) if isinstance(data, dict) else []
        if not cards_raw and isinstance(data, dict) and "_raw" in data:
            print(f"      [warn] Literature round {round_idx} 失败,raw 长度={len(data['_raw'])}")
            continue
        for c in cards_raw:
            try:
                all_cards.append(PropositionCard(**c))
            except Exception:
                all_cards.append(
                    PropositionCard(
                        id=c.get("id", f"P{len(all_cards)+1}"),
                        claim=c.get("claim", ""),
                        domain=c.get("domain", "unknown"),
                        assumptions=c.get("assumptions", []) or [],
                        scope=c.get("scope", ""),
                        evidence=c.get("evidence", "intuition"),
                        source_hint=c.get("source_hint", ""),
                    )
                )
            if len(all_cards) >= n_cards:
                break
    return all_cards[:n_cards]
