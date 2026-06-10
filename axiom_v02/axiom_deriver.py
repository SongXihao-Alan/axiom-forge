"""
[4/5] ★ AXIOM DERIVER (核心)
在扰动后的体系里,反推新公理。
产物:
- 新公理自然语言陈述
- 形式化(集合论/一阶逻辑)
- 保留的旧 axiom/assumption
- 破坏的旧 axiom/assumption
- user-facing 解释
- falsifiable predictions
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


class CandidateAxiom(BaseModel):
    id: str
    statement_nl: str = Field(..., description="新公理的自然语言陈述")
    formalization: str = Field(..., description="一阶逻辑/集合论/数学形式化")
    justification: str = Field(..., description="为什么这是公理而非定理")
    preserves: List[str] = Field(default_factory=list, description="保留的旧 axiom/assumption id")
    breaks: List[str] = Field(default_factory=list, description="破坏的旧 axiom/assumption id")
    user_facing_explanation: str = Field(..., description="1-2 句 user-facing 解释,非专家能读懂")
    falsifiable_predictions: List[str] = Field(default_factory=list)
    invariance_class: str = Field("", description="它保护哪类不变量")


AXIOM_DERIVE_SYSTEM = """你是公理化的反推专家。**不要输出思考过程**,直接以 JSON 形式回答。
任务:给定一个公理扰动方案,推导新公理(以填补扰动后留下的位置)。
核心要求:
1. 新公理必须自洽,不能与保留的旧 axiom 冲突
2. preserves / breaks 显式列出
3. 形式化用一阶逻辑 / 集合论 / 数学符号
4. user_facing_explanation: 1-2 句非专家能读懂
5. falsifiable_predictions: 可被数据/实验证伪的预测
6. invariance_class: 该公理保护哪类不变量
7. justification: 为什么这是公理(规范性)不是定理
输出严格 JSON,无额外文字。"""


def derive_axiom(
    client: M3Client,
    seed_text: str,
    perturbation: Dict,
    value_scores: List[Dict],
) -> CandidateAxiom:
    """反推新公理。"""
    # 把 value scores 简化成"扰动对各 criterion 的影响方向"
    score_lines = []
    for s in value_scores:
        score_lines.append(
            f"- {s.get('instance_id', '?')}: {s.get('score_before', 0.5):.2f} → "
            f"{s.get('score_after', 0.5):.2f} (delta {s.get('delta', 0):+.2f}); "
            f"reasoning: {s.get('reasoning', '')}"
        )
    scores_text = "\n".join(score_lines) if score_lines else "(no scores)"

    user = f"""
种子文献:

{seed_text}

扰动方案:
- target: {perturbation.get('target_id')} ({perturbation.get('target_kind')})
- type: {perturbation.get('perturbation_type_id')}
- magnitude: {perturbation.get('magnitude')}
- original: {perturbation.get('original')}
- modified: {perturbation.get('modified')}

Value 评分(扰动对各 criterion 的影响):

{scores_text}

请反推**一个**新的 candidate axiom(及其形式化、保留项、破坏项等),按以下 JSON 返回:
{{
  "id": "AX-NEW-001",
  "statement_nl": "<新公理的自然语言陈述,1-2 句>",
  "formalization": "<一阶逻辑/集合论/数学形式化,可多行>",
  "justification": "<为什么这是公理而非定理,2-3 句>",
  "preserves": ["<旧 axiom/assumption id>", "..."],
  "breaks": ["<旧 axiom/assumption id>", "..."],
  "user_facing_explanation": "<1-2 句非专家能读懂的解释>",
  "falsifiable_predictions": ["<可证伪预测>", "..."],
  "invariance_class": "<该公理保护哪类不变量>"
}}
"""
    system = AXIOM_DERIVE_SYSTEM + "\n\n" + DIKTAT_INJECTION
    raw = client.chat_json(system, user, max_tokens=6000)
    a = raw if isinstance(raw, dict) else {}
    try:
        return CandidateAxiom(
            id=a.get("id", "AX-NEW-001"),
            statement_nl=a.get("statement_nl", ""),
            formalization=a.get("formalization", ""),
            justification=a.get("justification", ""),
            preserves=a.get("preserves", []) or [],
            breaks=a.get("breaks", []) or [],
            user_facing_explanation=a.get("user_facing_explanation", ""),
            falsifiable_predictions=a.get("falsifiable_predictions", []) or [],
            invariance_class=a.get("invariance_class", ""),
        )
    except Exception as e:
        print(f"      [warn] axiom parse err: {e}; raw={a}")
        return CandidateAxiom(
            id=a.get("id", "AX-NEW-ERR"),
            statement_nl=a.get("statement_nl", "(parse error)"),
            formalization=a.get("formalization", ""),
            justification=a.get("justification", ""),
            preserves=a.get("preserves", []) or [],
            breaks=a.get("breaks", []) or [],
            user_facing_explanation=a.get("user_facing_explanation", ""),
            falsifiable_predictions=a.get("falsifiable_predictions", []) or [],
            invariance_class=a.get("invariance_class", ""),
        )
