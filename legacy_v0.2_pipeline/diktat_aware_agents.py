"""
Diktat-aware 版本的 3 个 agent。
在 v0.1 基础上,把 DIKTAT_INJECTION 注入到 system prompt 末尾。
"""
from __future__ import annotations
from typing import List
import sys
from pathlib import Path

# 让 v0.2 能找到 training/ 和 v0.1 的 agents/
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.llm import M3Client
from agents.literature_agent import PropositionCard, SYSTEM as LIT_SYSTEM
from agents.reality_agent import RealityCard, SYSTEM as REAL_SYSTEM
from agents.gap_finder import Gap, SYSTEM as GAP_SYSTEM
from training.diktat_injection import DIKTAT_INJECTION


def literature_agent_diktat(
    client: M3Client,
    domain: str,
    seed_concepts: List[str],
    n_cards: int = 8,
) -> List[PropositionCard]:
    """带 diktat 注入的 literature agent。"""
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
      "domain": "...",
      "assumptions": ["...", "..."],
      "scope": "...",
      "evidence": "theorem|empirical|intuition|case_study",
      "source_hint": "..."
    }}
  ]
}}
"""
        system = LIT_SYSTEM + "\n\n" + DIKTAT_INJECTION
        raw = client.chat_json(system, user, max_tokens=4000)
        cards_raw = raw.get("cards", []) if isinstance(raw, dict) else []
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


def reality_agent_diktat(
    client: M3Client,
    domain: str,
    literature_card_ids: List[str],
    n_cards: int = 8,
) -> List[RealityCard]:
    """带 diktat 注入的 reality agent。"""
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
        system = REAL_SYSTEM + "\n\n" + DIKTAT_INJECTION
        raw = client.chat_json(system, user, max_tokens=4000)
        obs_raw = raw.get("observations", []) if isinstance(raw, dict) else []
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


def gap_finder_diktat(
    client: M3Client,
    domain: str,
    cards: List[PropositionCard],
    obs: List[RealityCard],
    n_gaps: int = 5,
) -> List[Gap]:
    """带 diktat 注入的 gap finder。"""
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
        system = GAP_SYSTEM + "\n\n" + DIKTAT_INJECTION
        raw = client.chat_json(system, user, max_tokens=4000)
        gaps_raw = raw.get("gaps", []) if isinstance(raw, dict) else []
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
