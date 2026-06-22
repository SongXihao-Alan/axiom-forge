"""
[5/5] Consequence Predictor
预测新公理的后果:
- 旧定理的失效条件
- 新现象
- 新技术
- 可证伪预测
锚到真实场景(SC-* 节点)。
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Dict, List
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.llm import M3Client
from training.diktat_injection import DIKTAT_INJECTION


class Consequence(BaseModel):
    id: str
    statement: str
    type: str  # "old_theorem_fails" | "new_phenomenon" | "new_technique" | "falsifiable_prediction"
    scenario_anchor: str = Field("", description="锚到哪个 SC-* 场景,或 'none'")
    user_facing: bool = Field(False, description="是否对 user 容易解释")


def load_scenarios() -> List[Dict]:
    out = []
    d = ROOT / "training" / "graph" / "scenarios"
    if d.exists():
        for p in d.glob("*.json"):
            out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


CONS_PRED_SYSTEM = """你是机制设计的后果预测专家。**不要输出思考过程**,直接以 JSON 形式回答。
任务:给定一个新公理,预测它在真实场景里会产生什么后果。
预测 4 类: old_theorem_fails / new_phenomenon / new_technique / falsifiable_prediction。
核心要求:
- 每条预测必须 anchor 到具体场景(FAA / frontier lab / 算力 spot market / cost-sharing / 学校选择)
- 每条预测必须是"在 X 场景下, 如果 Y 条件, 发生 Z"
- user_facing: 1 句能向非专家解释则 true
- 不预测无法证伪的东西
输出严格 JSON,无额外文字。"""


def predict_consequences(
    client: M3Client,
    seed_text: str,
    perturbation: Dict,
    new_axiom: Dict,
    n_consequences: int = 4,
) -> List[Consequence]:
    """预测新公理的后果。"""
    scenarios = load_scenarios()
    scenario_dump = "\n".join(
        f"- {s.get('id')}: {s.get('scenario')}" for s in scenarios
    ) or "(no scenario nodes)"

    user = f"""扰动方案: {perturbation.get('target_id')} ({perturbation.get('perturbation_type_id')})
原: {perturbation.get('original', '')[:150]}
改: {perturbation.get('modified', '')[:150]}

新公理: {new_axiom.get('statement_nl', '')[:200]}
形式化: {new_axiom.get('formalization', '')[:200]}

可用真实场景(SC-* 节点):
{scenario_dump}

请预测 {n_consequences} 条后果,严格按以下 JSON:
{{
  "consequences": [
    {{
      "id": "C-1",
      "statement": "<在 X 场景下, 如果 Y 条件, 发生 Z>",
      "type": "old_theorem_fails|new_phenomenon|new_technique|falsifiable_prediction",
      "scenario_anchor": "<SC-* id 或 'none'>",
      "user_facing": <bool>
    }}
  ]
}}
"""
    system = CONS_PRED_SYSTEM + "\n\n" + DIKTAT_INJECTION
    raw = client.chat_json(system, user, max_tokens=6000)
    cs = raw.get("consequences", []) if isinstance(raw, dict) else []
    out = []
    for c in cs:
        try:
            out.append(Consequence(
                id=c.get("id", f"C-{len(out)+1}"),
                statement=c.get("statement", ""),
                type=c.get("type", "new_phenomenon"),
                scenario_anchor=c.get("scenario_anchor", "none"),
                user_facing=bool(c.get("user_facing", False)),
            ))
        except Exception as e:
            print(f"      [warn] consequence parse err: {e}")
    return out
