"""
Completeness Auditor:检查 axiom 字段的句子完整性。

4 个检查维度:
1. **Syntactic**: 是否以标点/围栏结尾
2. **Subject-Predicate**: 主谓是否完整
3. **Semantic**: 语义是否完整(没被截断)
4. **Relevance**: 是否与 axiom 主题相关

每个 sentence 给出 0~1 综合分,低于 0.6 触发 rewrite 循环。
"""
from __future__ import annotations
import re
import sys
from pathlib import Path
from typing import Dict, List
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.llm import M3Client
from training.diktat_injection import DIKTAT_INJECTION


# ============================================================
# 字段 → 完整性期望
# ============================================================

# 不同字段有不同的"完整"标准
FIELD_COMPLETENESS_RULES = {
    "statement_nl": {
        "min_length": 30,           # 至少 30 字符
        "max_length": 500,         # 不超过 500 字符
        "require_subject": True,   # 必须有主语
        "require_punct_end": True,  # 必须以句号/问号/感叹号结尾
        "require_verb": True,       # 必须有动词
    },
    "user_facing_explanation": {
        "min_length": 50,
        "max_length": 400,
        "require_subject": True,
        "require_punct_end": True,
        "require_verb": True,
    },
    "justification": {
        "min_length": 100,
        "max_length": 1000,
        "require_subject": True,
        "require_punct_end": True,
        "require_verb": True,
    },
    "invariance_class": {
        "min_length": 50,
        "max_length": 800,
        "require_subject": True,
        "require_punct_end": True,
        "require_verb": True,
    },
    "consequence.statement": {
        "min_length": 80,
        "max_length": 600,
        "require_subject": True,
        "require_punct_end": True,
        "require_verb": True,
    },
}


# ============================================================
# 检查函数
# ============================================================

def check_syntactic(text: str, require_punct_end: bool = True) -> Dict:
    """1. 句法检查:长度、围栏、标点结尾。"""
    issues = []
    score = 1.0

    text_stripped = text.strip()
    if not text_stripped:
        return {"score": 0.0, "issues": ["EMPTY"]}

    # 是否以围栏结束(多行字段)
    if text_stripped.endswith("```"):
        pass  # OK
    elif require_punct_end:
        last = text_stripped[-1]
        valid_end_chars = '.?!。?!")\']'
        if last not in valid_end_chars:
            issues.append(f"does_not_end_with_punct: '{last}'")
            score -= 0.3

    # 是否包含未闭合的围栏
    fence_open = text_stripped.count("```")
    if fence_open % 2 != 0:
        issues.append("unclosed_code_fence")
        score -= 0.2

    # 是否包含"截断"标记(.../等等,英文中...)
    if re.search(r"\betc\.?\s*$", text_stripped) or text_stripped.endswith("...") or text_stripped.endswith("……"):
        issues.append("ends_with_ellipsis")
        score -= 0.2

    return {"score": max(score, 0.0), "issues": issues}


def check_subject_verb_heuristic(text: str, lang: str = "auto") -> Dict:
    """2. 主谓完整启发式检查(中英文)。"""
    issues = []
    score = 1.0
    text = text.strip()
    if not text:
        return {"score": 0.0, "issues": ["EMPTY"]}

    # 自动检测语言
    has_cjk = bool(re.search(r"[\u4e00-\u9fff]", text))
    lang = "zh" if has_cjk else "en"

    if lang == "en":
        # 英文:需要主语(代词或名词) + 动词(is/has/will/can/may/should/等)
        # 简化:看是否有常见动词
        verb_patterns = [
            r"\b(is|are|was|were|has|have|had|will|can|may|must|should|would|could)\b",
            r"\b(satisfies|requires|asserts|states|implies|defines|extends|preserves|replaces|breaks|holds|derives|follows|ensures|guarantees)\b",
            r"\b(the mechanism|the axiom|the agent|the designer|we|this|it)\b",
        ]
        has_verb = any(re.search(p, text, re.IGNORECASE) for p in verb_patterns[:2])
        if not has_verb:
            # 看是否有主语 + 名词短语
            has_subject = bool(re.search(r"^[A-Z][a-z]+", text))
            if not has_subject:
                issues.append("no_verb_no_subject")
                score -= 0.3
    else:
        # 中文:必须有"是/有/会/能/应该/可以/需要/意味着/等价于"等动词或系动词
        verb_chars = "是有的会能应该可以需要意味着等价于表示"
        if not any(c in text for c in verb_chars):
            issues.append("no_verb_zh")
            score -= 0.3

    return {"score": max(score, 0.0), "issues": issues}


def check_semantic_with_llm(client: M3Client, text: str, field: str, context: str = "") -> Dict:
    """3. 语义完整性:用 LLM 判断这句话是否"被截断"或"语义不完整"。"""
    user = f"""字段: {field}
上下文: {context}

待检查的句子/段落:
\"\"\"{text}\"\"\"

请判断:
1. **截断?**: 这句话是否在中间被打断(类似 "...", 或者突然切到另一个话题)?
2. **自包含?**: 不依赖其他段落,这句话能否独立被读者理解?
3. **有结论?**: 这句话是否给出了"结论"或"主张",而不是停在半路?

按以下 JSON 输出:
{{
  "is_truncated": <bool>,
  "is_self_contained": <bool>,
  "has_conclusion": <bool>,
  "issues": ["<issue 1>", "..."],
  "score": <0~1 整体完整度, 1=完全完整, 0=严重截断>
}}
"""
    system = """你是文本完整性审计员。**只输出 JSON**,无额外文字。"""
    raw = client.chat_json(system, user, max_tokens=2000)
    if isinstance(raw, dict):
        return raw
    return {"is_truncated": False, "is_self_contained": True, "has_conclusion": True, "issues": [], "score": 0.7}


def check_relevance_with_llm(client: M3Client, text: str, field: str, axiom_id: str, axiom_statement: str) -> Dict:
    """4. 相关性:用 LLM 判断这句话是否与 axiom 主题相关。"""
    user = f"""待检查字段: {field} (axiom {axiom_id})
axiom 主题: {axiom_statement[:200]}

待检查的句子/段落:
\"\"\"{text}\"\"\"

请判断:
1. **主题相关?**: 这句话是否在讨论 axiom 的核心,还是离题?
2. **关键信息?**: 这句话是否提供了与 axiom 相关的关键信息(preservation, justification, etc.)?

按以下 JSON 输出:
{{
  "is_on_topic": <bool>,
  "provides_key_info": <bool>,
  "issues": ["<issue 1>", "..."],
  "score": <0~1 相关性>
}}
"""
    system = """你是相关性审计员。**只输出 JSON**,无额外文字。"""
    raw = client.chat_json(system, user, max_tokens=2000)
    if isinstance(raw, dict) and "score" in raw:
        return raw
    return {"is_on_topic": True, "provides_key_info": True, "issues": [], "score": 0.7}


# ============================================================
# 综合检查
# ============================================================

def audit_text(
    client: M3Client,
    text: str,
    field: str,
    axiom_id: str = "",
    axiom_statement: str = "",
    do_semantic_check: bool = True,
    do_relevance_check: bool = True,
) -> Dict:
    """综合 4 个维度检查一个字段。"""
    rules = FIELD_COMPLETENESS_RULES.get(field, FIELD_COMPLETENESS_RULES["statement_nl"])

    syntactic = check_syntactic(text, require_punct_end=rules.get("require_punct_end", True))
    sv_heuristic = check_subject_verb_heuristic(text)

    semantic = {"score": 1.0, "issues": []}
    if do_semantic_check and text.strip():
        semantic = check_semantic_with_llm(client, text, field, context=axiom_statement)

    relevance = {"score": 1.0, "issues": []}
    if do_relevance_check and text.strip() and axiom_id:
        relevance = check_relevance_with_llm(client, text, field, axiom_id, axiom_statement)

    # 加权综合分
    overall = (
        0.25 * syntactic["score"]
        + 0.20 * sv_heuristic["score"]
        + 0.35 * semantic.get("score", 0.7)
        + 0.20 * relevance.get("score", 0.7)
    )

    all_issues = []
    all_issues.extend(syntactic["issues"])
    all_issues.extend(sv_heuristic["issues"])
    all_issues.extend(semantic.get("issues", []))
    all_issues.extend(relevance.get("issues", []))

    # 长度检查
    if "min_length" in rules and len(text) < rules["min_length"]:
        all_issues.append(f"too_short: {len(text)} < {rules['min_length']}")
        overall -= 0.2
    if "max_length" in rules and len(text) > rules["max_length"]:
        all_issues.append(f"too_long: {len(text)} > {rules['max_length']}")
        overall -= 0.1

    return {
        "score": max(overall, 0.0),
        "issues": all_issues,
        "syntactic": syntactic,
        "sv_heuristic": sv_heuristic,
        "semantic": semantic,
        "relevance": relevance,
    }


def audit_axiom(
    client: M3Client,
    axiom: Dict,
    consequences: List[Dict] = None,
    do_relevance_check: bool = True,
) -> Dict:
    """审计 axiom 的所有字段 + consequences。"""
    axiom_id = axiom.get("id", "")
    axiom_statement = axiom.get("statement_nl", "")

    result = {"fields": {}, "overall_score": 0.0, "needs_rewrite": []}
    field_scores = []

    for field in ["statement_nl", "user_facing_explanation", "justification", "invariance_class"]:
        text = axiom.get(field, "")
        audit = audit_text(
            client, text, field,
            axiom_id=axiom_id,
            axiom_statement=axiom_statement,
            do_semantic_check=True,
            do_relevance_check=do_relevance_check,
        )
        result["fields"][field] = audit
        field_scores.append(audit["score"])
        if audit["score"] < 0.6:
            result["needs_rewrite"].append({
                "field": field,
                "current": text,
                "issues": audit["issues"],
                "score": audit["score"],
            })

    # Consequences
    if consequences:
        result["consequences"] = []
        for c in consequences:
            c_audit = audit_text(
                client, c.get("statement", ""), "consequence.statement",
                axiom_id=axiom_id, axiom_statement=axiom_statement,
                do_semantic_check=True, do_relevance_check=do_relevance_check,
            )
            result["consequences"].append({"id": c.get("id"), "audit": c_audit})
            field_scores.append(c_audit["score"])
            if c_audit["score"] < 0.6:
                result["needs_rewrite"].append({
                    "field": f"consequence.{c.get('id')}",
                    "current": c.get("statement", ""),
                    "issues": c_audit["issues"],
                    "score": c_audit["score"],
                })

    result["overall_score"] = sum(field_scores) / len(field_scores) if field_scores else 0.0
    return result
