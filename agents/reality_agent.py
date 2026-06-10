"""
🌍 Reality Agent
职责:把"现实世界观察"凝练成与文献对话的事实卡片。
MVP 实现:不直接抓外部数据(避免把 demo 复杂化),而是让 LLM 基于其训练知识 + 常见公开数据源
        描述"已知公开现实"和"反常现象"。后续可接 FRED/World Bank API。
"""
from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field

from .llm import M3Client


class RealityCard(BaseModel):
    id: str
    observation: str = Field(..., description="一句话描述的实证观察")
    domain: str
    time_window: str = Field("", description="时间窗口,例如 2010-2024")
    region: str = Field("", description="地区/市场,例如 global / US / EU")
    data_source_hint: str = Field("", description="数据来源线索(WB/FRED/Pew/IMF 等)")
    conflicts_with: List[str] = Field(default_factory=list, description="与哪些文献命题相冲突/不一致")


SYSTEM = """你是一位宏观/实证经济学家。
任务:在指定研究主题下,总结一组**有据可查的现实观察**——这些观察必须能与文献命题形成对照。
约束:
1. 每条 observation 必须是"可被数据支撑的事实型陈述",不要写成观点。
2. 显式标注 time_window、region、data_source_hint。
3. 若该观察与某个**特定文献命题**有张力,写到 conflicts_with 里(用命题 id,例如 P3)。
4. 严格输出 JSON,不要额外文字。
5. 表述精炼,observation 不超过 25 词,conflicts_with 最多 3 个 id。
注意:
- 可以基于你训练知识中常见的公开数据(World Bank、IMF、FRED、OECD、BIS、Bloomberg、AWS price history、Lambda/Vast.ai 报价)描述现实。
- 不必逐条声明精确数据点,在 data_source_hint 中给出可核查的来源名称即可。
- 重点在"现实与理论命题的张力",不需要追求数字精度。"""


def reality_agent(
    client: M3Client,
    domain: str,
    literature_card_ids: List[str],
    n_cards: int = 8,
) -> List[RealityCard]:
    """分轮拉取观察。每轮 3 张。"""
    all_obs: List[RealityCard] = []
    batch_size = 3
    round_idx = 0
    max_rounds = 4
    while len(all_obs) < n_cards and round_idx < max_rounds:
        round_idx += 1
        remaining = n_cards - len(all_obs)
        take = min(batch_size, remaining)
        used_ids = [o.id for o in all_obs]
        start_id = len(all_obs) + 1
        user = f"""
研究主题: {domain}

文献命题 id 列表(供交叉引用): {', '.join(literature_card_ids)}

已有观察 id(避免重复): {used_ids if used_ids else '无'}

请总结 **{take} 条**新观察(从 R{start_id} 开始),严格按以下 JSON:
{{
  "observations": [
    {{
      "id": "R{start_id}",
      "observation": "...",
      "domain": "...",
      "time_window": "...",
      "region": "...",
      "data_source_hint": "...",
      "conflicts_with": ["P3", "..."]
    }}
  ]
}}
"""
        data = client.chat_json(SYSTEM, user, max_tokens=4000)
        obs_raw = data.get("observations", []) if isinstance(data, dict) else []
        if not obs_raw and isinstance(data, dict) and "_raw" in data:
            print(f"      [warn] Reality round {round_idx} 失败,raw 长度={len(data['_raw'])}")
            continue
        for o in obs_raw:
            try:
                all_obs.append(RealityCard(**o))
            except Exception:
                all_obs.append(
                    RealityCard(
                        id=o.get("id", f"R{len(all_obs)+1}"),
                        observation=o.get("observation", ""),
                        domain=o.get("domain", "unknown"),
                        time_window=o.get("time_window", ""),
                        region=o.get("region", ""),
                        data_source_hint=o.get("data_source_hint", ""),
                        conflicts_with=o.get("conflicts_with", []) or [],
                    )
                )
            if len(all_obs) >= n_cards:
                break
    return all_obs[:n_cards]
