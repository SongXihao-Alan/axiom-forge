"""
Completeness Rewriter:根据 completeness_auditor 的 issues,重写字段。

关键设计:不重写整个 axiom,只重写 audit score < 0.6 的字段。
对每个需要重写的字段:
- 把原字段和 issues 一起给 M3
- 让 M3 修复(扩展、补充结论、改写)
- 再次 audit 直到 score >= 0.6 或 max_cycles 达到
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.llm import M3Client
from training.diktat_injection import DIKTAT_INJECTION
from .completeness_auditor import audit_text


REWRITE_SYSTEM = """你是公理文本的精修专家。**只输出 JSON**,无额外文字。

任务:给定一个 axiom 字段的当前文本,以及该字段的 audit 报告(具体问题列表),重写该字段,使 audit score 提升。

核心要求:
1. **保持核心内容不变**(不能改 axiom 本身的数学意义)
2. **修复 audit 指出的问题**:
   - "too_short": 扩展,补充相关数学/概念细节
   - "does_not_end_with_punct": 改成完整句子
   - "ends_with_ellipsis": 把省略号处补全
   - "no_verb_no_subject" / "no_verb_zh": 补主谓
   - "truncated": 把中间截断处接上
   - "not_self_contained": 让这一句独立可读
   - "off_topic": 把话拉回 axiom 主题
3. **保持自然语言的学术风格**——一句话,信息密度高,不要口水
4. **如果原字段已经很好**(score >= 0.7),可以微小调整而不重写
"""


def rewrite_field(
    client: M3Client,
    field: str,
    current_text: str,
    issues: List[str],
    context: Dict,
    max_cycles: int = 2,
) -> str:
    """重写一个字段,直到 audit score >= 0.6。"""
    best_text = current_text
    best_score = audit_text(
        client, current_text, field,
        axiom_id=context.get("axiom_id", ""),
        axiom_statement=context.get("axiom_statement", ""),
        do_semantic_check=True, do_relevance_check=True,
    )["score"]

    user_base = f"""字段名: {field}
axiom_id: {context.get('axiom_id', '')}
axiom 主题: {context.get('axiom_statement', '')[:300]}

当前文本:
\"\"\"{current_text}\"\"\"

audit 报告(必须修复):
{chr(10).join(f'- {i}' for i in issues)}

请按 audit 报告的问题**重写**该字段,严格按以下 JSON:
{{
  "rewritten": "<新文本,一句话,符合 audit 要求>"
}}
"""
    system = REWRITE_SYSTEM + "\n\n" + DIKTAT_INJECTION

    for cycle in range(max_cycles):
        raw = client.chat_json(system, user_base, max_tokens=4000)
        if not isinstance(raw, dict):
            continue
        rewritten = raw.get("rewritten", "")
        if not rewritten:
            continue
        audit = audit_text(
            client, rewritten, field,
            axiom_id=context.get("axiom_id", ""),
            axiom_statement=context.get("axiom_statement", ""),
            do_semantic_check=True, do_relevance_check=True,
        )
        if audit["score"] > best_score:
            best_text = rewritten
            best_score = audit["score"]
        if best_score >= 0.8:
            break
    return best_text, best_score


def rewrite_audit_findings(
    client: M3Client,
    axiom: Dict,
    audit_result: Dict,
    max_fields_to_rewrite: int = 3,
) -> Dict:
    """对 audit 找出的需要 rewrite 的字段,逐一 rewrite。"""
    axiom_id = axiom.get("id", "")
    axiom_statement = axiom.get("statement_nl", "")
    new_axiom = axiom.copy()

    findings = audit_result.get("needs_rewrite", [])
    # 按 score 升序排(最差的先修)
    findings.sort(key=lambda f: f.get("score", 0.5))
    findings = findings[:max_fields_to_rewrite]

    rewrite_log = []
    for finding in findings:
        field = finding["field"]
        if field.startswith("consequence."):
            # Consequence rewrite 单独处理
            continue
        rewritten, new_score = rewrite_field(
            client,
            field=field,
            current_text=finding["current"],
            issues=finding["issues"],
            context={"axiom_id": axiom_id, "axiom_statement": axiom_statement},
            max_cycles=2,
        )
        new_axiom[field] = rewritten
        rewrite_log.append({
            "field": field,
            "old_score": finding.get("score", 0.0),
            "new_score": new_score,
            "old_len": len(finding["current"]),
            "new_len": len(rewritten),
        })

    return {"axiom": new_axiom, "rewrite_log": rewrite_log}
