"""
[4/5 v2] Axiom Deriver + Notation Definer 协作版

不再是单 agent,而是 deriver <-> definer 互相通信:
- deriver 起草公理(自然语言 + 形式化)
- definer 看到 draft,提供 definition + alignment feedback
- deriver 据此改写形式化,使之与自然语言字面一致
- 循环(最多 3 轮)
- 最终产出:自然语言 + 自洽形式化 + 完整 notation 体系

产物结构(给 memo_writer):
- statement_nl: 自然语言
- formalization: 形式化(经过 notation 校正)
- notation_legend: 完整符号表(传统 + 新定义)
- alignment_audit: 自然语言 ↔ 形式化 对齐检查结果
- preserves / breaks / user_facing_explanation / falsifiable_predictions / invariance_class: 同前
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
from .notation_definer import (
    notation_definer,
    consistency_check,
    CONVENTIONAL_DEFINITIONS,
)


class CandidateAxiom(BaseModel):
    id: str
    statement_nl: str
    formalization: str
    notation_legend: List[Dict] = Field(default_factory=list)  # [{symbol, name, formal_def, nl_explanation, constraints, source}]
    alignment_audit: Dict = Field(default_factory=dict)  # {score, penalties, alignment_issues}
    completeness_audit: Dict = Field(default_factory=dict)  # {overall_score, field_scores, needs_rewrite, rewrite_log, after_rewrite_score}
    justification: str
    preserves: List[str] = Field(default_factory=list)
    breaks: List[str] = Field(default_factory=list)
    user_facing_explanation: str
    falsifiable_predictions: List[str] = Field(default_factory=list)
    invariance_class: str = ""


# ============================================================
# 协作循环
# ============================================================

AXIOM_DERIVE_SYSTEM_V2 = """你是机制设计的反推专家。**不要输出思考过程**,直接以 JSON 回答。

任务:给定一个公理扰动方案,推导新公理(填补扰动后留下的位置)。

**严格的两阶段输出**:
- **第一阶段**:先给自然语言(1-2 句陈述)+ 形式化(包含用到的所有符号)
- **第二阶段**:notation_definer 会返回完整符号表 + 对齐检查 + 反馈
- **最终阶段**:根据反馈,重写形式化使其与自然语言字面一致

**核心约束**:
1. 形式化必须自洽(不能与保留的旧 axiom 冲突)
2. **每个用到的符号**必须有定义(notation_definer 会帮你做,但你起草时要意识到)
3. **自然语言 ↔ 形式化字面一致**:自然语言说"X",形式化里就有一个 X 对应的符号,反之亦然
4. user-facing 解释:1-2 句非专家能读懂
5. falsifiable predictions:可被数据/实验证伪的预测
6. invariance_class:该公理保护哪类不变量
7. justification:为什么这是公理(规范性)不是定理

输出严格 JSON,无额外文字。
"""


def _axiom_first_draft(
    client: M3Client,
    seed_text: str,
    perturbation: Dict,
    value_scores: List[Dict],
) -> Dict:
    """第一轮:deriver 单独起草(自然语言 + 形式化)。"""
    score_lines = []
    for s in value_scores:
        score_lines.append(
            f"- {s.get('instance_id', '?')}: {s.get('score_before', 0.5):.2f} → "
            f"{s.get('score_after', 0.5):.2f} (delta {s.get('delta', 0):+.2f})"
        )
    scores_text = "\n".join(score_lines) if score_lines else "(no scores)"

    user = f"""
种子文献(简版): {seed_text[:1500]}...

扰动方案:
- target: {perturbation.get('target_id')} ({perturbation.get('target_kind')})
- type: {perturbation.get('perturbation_type_id')}
- original: {perturbation.get('original', '')[:200]}
- modified: {perturbation.get('modified', '')[:200]}

Value 评分(扰动对各 criterion 的影响):
{scores_text}

请先只输出**自然语言陈述** + **形式化草稿**(形式化可以稍后被 notation_definer 修订),按以下 JSON:
{{
  "id": "AX-NEW-001",
  "statement_nl": "<自然语言, 1-2 句>",
  "formalization": "<一阶逻辑/集合论/数学形式化, 包含用到的符号>"
}}
"""
    system = AXIOM_DERIVE_SYSTEM_V2 + "\n\n" + DIKTAT_INJECTION
    raw = client.chat_json(system, user, max_tokens=4000)
    if not isinstance(raw, dict):
        return {"id": "AX-NEW-001", "statement_nl": "", "formalization": ""}
    return raw


def _axiom_revise_with_notation(
    client: M3Client,
    seed_text: str,
    perturbation: Dict,
    draft: Dict,
    notation_feedback: Dict,
) -> Dict:
    """第二轮及之后:deriver 收到 notation 反馈,修订公理(补 justification / preservation / falsifiable 等)。"""
    defs_text = "\n".join(
        f"- {d.get('symbol', '?')}: {d.get('nl_explanation', '')}"
        for d in notation_feedback.get("definitions", [])
    )
    alignment = notation_feedback.get("alignment_issues", [])

    user = f"""
公理草稿(已起草 notation):
- 自然语言: {draft.get('statement_nl', '')}
- 形式化:
```
{draft.get('formalization', '')}
```

已确立的 notation 体系:
{defs_text}

对齐问题(自然语言 ↔ 形式化):
{chr(10).join('- ' + a for a in alignment) if alignment else '(no alignment issues)'}

请**修订**公理(基于 notation 反馈,使形式化与自然语言字面一致),并补全其他字段:
- **preserves**: 保留的旧 axiom/assumption id 列表
- **breaks**: 破坏的旧 axiom/assumption id 列表
- **justification**: 为什么这是公理而非定理
- **user_facing_explanation**: 1-2 句非专家能读懂
- **falsifiable_predictions**: 可被数据/实验证伪的预测(列表)
- **invariance_class**: 该公理保护哪类不变量

按以下 JSON:
{{
  "id": "{draft.get('id', 'AX-NEW-001')}",
  "statement_nl": "<修订后>",
  "formalization": "<修订后,与自然语言字面一致>",
  "preserves": [...],
  "breaks": [...],
  "justification": "...",
  "user_facing_explanation": "...",
  "falsifiable_predictions": [...],
  "invariance_class": "..."
}}
"""
    system = AXIOM_DERIVE_SYSTEM_V2 + "\n\n" + DIKTAT_INJECTION
    raw = client.chat_json(system, user, max_tokens=6000)
    if not isinstance(raw, dict):
        return draft
    return raw


def derive_axiom_v2(
    client: M3Client,
    seed_text: str,
    perturbation: Dict,
    value_scores: List[Dict],
    max_cycles: int = 3,
    do_completeness_audit: bool = True,
) -> CandidateAxiom:
    """协作式 axiom derivation:deriver 起草 → definer 反馈 → deriver 修订 → completeness audit + rewrite → 循环。"""
    # Round 1: 起草
    draft = _axiom_first_draft(client, seed_text, perturbation, value_scores)
    notation_legend: List[Dict] = []
    audit: Dict = {}
    final_axiom_dict = draft.copy()
    rewrite_log: List[Dict] = []

    for cycle in range(max_cycles):
        # Notation definer 处理
        nf = notation_definer(client, draft, max_new_defs=5)
        notation_legend = nf.get("definitions", [])

        # Consistency check
        audit = consistency_check(
            draft.get("statement_nl", ""),
            draft.get("formalization", ""),
            notation_legend,
            nf.get("nl_to_symbol", {}),
            nf.get("symbol_to_nl", {}),
            nf.get("alignment_issues", []),
        )

        # 决定是否还要再循环
        if audit["score"] >= 0.9 or cycle == max_cycles - 1:
            # 用 notation legend 作为 final 的一部分
            final_axiom_dict["notation_legend"] = notation_legend
            final_axiom_dict["alignment_audit"] = audit
            break

        # Round 2+: deriver 修订
        draft = _axiom_revise_with_notation(client, seed_text, perturbation, draft, nf)
        final_axiom_dict = draft.copy()

    # ★ Completeness audit + rewrite (在 deriver-definer 循环之后)
    if do_completeness_audit:
        from .completeness_auditor import audit_axiom
        from .completeness_rewriter import rewrite_audit_findings
        comp_audit = audit_axiom(
            client,
            final_axiom_dict,
            do_relevance_check=True,
        )
        final_axiom_dict["completeness_audit"] = {
            "overall_score": comp_audit["overall_score"],
            "field_scores": {f: a["score"] for f, a in comp_audit["fields"].items()},
            "needs_rewrite": [f["field"] for f in comp_audit["needs_rewrite"]],
        }
        if comp_audit["needs_rewrite"]:
            rewrite_res = rewrite_audit_findings(
                client,
                final_axiom_dict,
                comp_audit,
                max_fields_to_rewrite=3,
            )
            final_axiom_dict = rewrite_res["axiom"]
            rewrite_log = rewrite_res["rewrite_log"]
            final_axiom_dict["completeness_audit"]["rewrite_log"] = rewrite_log
            # rewrite 后再 audit 一次
            comp_audit2 = audit_axiom(client, final_axiom_dict, do_relevance_check=True)
            final_axiom_dict["completeness_audit"]["after_rewrite_score"] = comp_audit2["overall_score"]

    # 兜底
    final_axiom_dict.setdefault("notation_legend", notation_legend)
    final_axiom_dict.setdefault("alignment_audit", audit)
    final_axiom_dict.setdefault("preserves", [])
    final_axiom_dict.setdefault("breaks", [])
    final_axiom_dict.setdefault("justification", "")
    final_axiom_dict.setdefault("user_facing_explanation", "")
    final_axiom_dict.setdefault("falsifiable_predictions", [])
    final_axiom_dict.setdefault("invariance_class", "")

    try:
        return CandidateAxiom(**final_axiom_dict)
    except Exception as e:
        # Pydantic 兜底
        return CandidateAxiom(
            id=final_axiom_dict.get("id", "AX-NEW-001"),
            statement_nl=final_axiom_dict.get("statement_nl", ""),
            formalization=final_axiom_dict.get("formalization", ""),
            notation_legend=notation_legend,
            alignment_audit=audit,
            completeness_audit=final_axiom_dict.get("completeness_audit", {}),
            justification=final_axiom_dict.get("justification", ""),
            preserves=final_axiom_dict.get("preserves", []) or [],
            breaks=final_axiom_dict.get("breaks", []) or [],
            user_facing_explanation=final_axiom_dict.get("user_facing_explanation", ""),
            falsifiable_predictions=final_axiom_dict.get("falsifiable_predictions", []) or [],
            invariance_class=final_axiom_dict.get("invariance_class", ""),
        )
