"""
[4b/5] Notation Definer (协作式)

与 axiom_deriver 并行,不是独立前置步骤。

工作模式:
- 收到 axiom_deriver 的 draft(自然语言 + 形式化)
- 用 LLM 提取所有引用到的符号(比 regex 更准)
- 对每个符号,先查"常规定义库"——如果库里有,直接用
- 如果库里没有,起草新定义
- 给出对齐审计:自然语言 ↔ 形式化 字面一致性
- 反馈给 axiom_deriver 修订
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


# ============================================================
# 常规定义库
# ============================================================

CONVENTIONAL_DEFINITIONS = {
    "N": "Set of agents, indexed i = 1, ..., n.",
    "X": "Set of outcomes / allocations.",
    "T": "Set of possible transfers / payments (typically ℝ).",
    "Θ": "Set of agent types.",
    "V_i": "Valuation function v_i: X × Θ → ℝ, mapping outcomes to monetary valuations.",
    "F": "Common prior distribution over Θ (in Bayesian setting).",
    "s_i": "Strategy of agent i: a function from type space to message space.",
    "Σ_i": "Strategy space of agent i (set of all admissible strategies).",
    "M_i": "Message space of agent i.",
    "g": "Allocation rule g: M_1 × ... × M_n → X.",
    "t_i": "Payment rule t_i: M_1 × ... × M_n → ℝ.",
    "u_i": "Utility function of agent i, takes outcome, transfer, and (in leaky form) strategy.",
    "τ_i(v_i)": "Truth-telling strategy: τ_i(v_i) = (v_i, v_i, ..., v_i), i.e., report one's type directly.",
    "DSIC": "Dominant-Strategy IC: ∀v_i, ∀s_i', E_{-v_i}[u_i(τ_i(v_i))] ≥ E_{-v_i}[u_i(s_i')].",
    "BIC": "Bayesian IC: ∀v_i, ∀s_i', E_{-v_i, s_{-i}~F}[u_i(τ_i(v_i))] ≥ E_{-v_i, s_{-i}~F}[u_i(s_i')].",
    "ex_post_IC": "Ex-post IC: ∀v_i, ∀s_i', ∀v_{-i}, u_i(τ_i(v_i), v_{-i}) ≥ u_i(s_i', v_{-i}).",
    "IR": "Individual Rationality: participating yields non-negative expected utility.",
    "K(·)": "Kolmogorov complexity / descriptive complexity of a string.",
    "ε-IC": "Approximate IC: deviation gains at most ε.",
    "Ψ": "Designer / planner.",
    "ℝ≥0": "Non-negative reals.",
    "ℕ": "Natural numbers (used for complexity measurements).",
}


# ============================================================
# 数据结构
# ============================================================

class Definition(BaseModel):
    symbol: str
    name: str
    formal_def: str
    nl_explanation: str
    constraints: str
    source: str  # "conventional" | "new"


# ============================================================
# Notation Definer
# ============================================================

NOTATION_DEFINER_SYSTEM = """你是机制设计的形式化专家。**不要输出思考过程**,直接以 JSON 回答。

任务:给定 axiom_deriver 起草的公理(自然语言 + 形式化),你需要做 4 件事:

1. **提取符号**:用 LLM 智能提取形式化里**所有真正被作为符号引用**的对象(变量、函数、常量、set)。
   - **忽略**这些常见的"非符号"误识别: axiom 引用(如 A3, P1)、theorem 引用、单字符章节标记等
   - 重点关注: 集合(N, X, Θ, Σ_i, M_i)、函数(g, t_i, v_i, u_i, c, σ, K, F)、变量(i, v_i, s_i, x_i, t_i, ε, κ, λ, φ, ψ)
   - 如果文中已有 "Definitions of the objects used" 段,**优先从那里**提取

2. **区分 conventional vs new**:
   - 在常规定义库里的(下面给出): 标 source="conventional",直接给定义
   - 不在的: 标 source="new",起草定义(必须给符号、形式定义、自然语言、约束)

3. **对齐审计**:
   - 检查自然语言里出现的每个关键术语,是否对应形式化里的一个符号
   - 形式化里每个符号,是否在 natural language 中提及
   - 如果有不一致,标 alignment_issues

4. **输出严格 JSON**,包含:
   - definitions: 所有符号定义
   - nl_to_symbol: 自然语言术语 → 形式化符号
   - symbol_to_nl: 形式化符号 → 自然语言术语
   - alignment_issues: 任何不一致
   - extracted_symbols: 你提取到的所有符号(用于后续审计)
"""

CONVENTIONAL_DEFINITIONS_TEXT = "\n".join(
    f"- {sym}: {desc}" for sym, desc in CONVENTIONAL_DEFINITIONS.items()
)


def notation_definer(
    client: M3Client,
    axiom_draft: Dict,
    max_new_defs: int = 5,
) -> Dict:
    """notation_definer 的核心:接收 axiom_deriver 的 draft,产出 (definitions, alignment)。"""
    formal = axiom_draft.get("formalization", "")

    # 用 LLM 提取符号(比 regex 准)
    extract_user = f"""形式化文本:
```
{formal}
```

请提取形式化里**真正被作为符号引用**的对象。

**只提取这些类型**:
- 集合:N, X, T, Θ, M_i, Σ_i 等
- 函数:g, t_i, v_i, u_i, c, σ, K, F, φ, ε, λ, κ 等
- 变量:i, j, n, v_i, s_i, x_i, t_i, ε, δ, κ, λ, ψ 等
- 谓词/操作:=, ∈, ≤, ≥, ∼, ↦, ≺, ⊂, ∪, ∩ 等
- 常见常量:0, 1, ε, κ, λ

**忽略这些**:
- axiom/assumption/theorem 引用(如 A1-bic, M3-rational, P1, T-revenue-eq)
- 章节标记、版本号
- 自然语言里出现的术语但形式化里没引用

返回 JSON:
{{
  "extracted_symbols": ["<symbol 1>", "<symbol 2>", "..."]
}}
"""
    system_extract = """你是符号提取专家。**只输出 JSON**,无额外文字。从形式化文本中精确提取数学符号。"""
    raw_extract = client.chat_json(system_extract, extract_user, max_tokens=2000)
    if isinstance(raw_extract, dict):
        candidate_symbols = raw_extract.get("extracted_symbols", [])
    else:
        candidate_symbols = []

    # 区分 conventional vs new
    conventional_used = []
    new_candidate = []
    for sym in candidate_symbols:
        if sym in CONVENTIONAL_DEFINITIONS:
            conventional_used.append(sym)
        else:
            new_candidate.append(sym)

    # 让 M3 起草新定义 + 检查对齐
    user = f"""axiom_deriver 起草的公理:

自然语言: {axiom_draft.get('statement_nl', '')}

形式化:
```
{formal}
```

已提取的符号(LLM 智能识别): {candidate_symbols}
- 已在常规定义库: {conventional_used}
- 需要新定义: {new_candidate}

user-facing 解释: {axiom_draft.get('user_facing_explanation', '')}

**常规定义库**(共享):
{CONVENTIONAL_DEFINITIONS_TEXT}

请:
1. 为每个候选符号"需要新定义"的,起草定义(最多 {max_new_defs} 个)
   - 给出: 符号、形式定义(可用 ∀/∈/≤/→/∃ 等一阶逻辑符号)、自然语言解释、约束(如 "non-negative", "computable", "monotone")
2. 给"自然语言 ↔ 形式化"对齐表:
   - nl_to_symbol: {{自然语言术语: 形式化符号}}
   - symbol_to_nl: {{形式化符号: 自然语言术语}}
3. 列出 alignment_issues(如果自然语言和形式化字面不一致)

按以下 JSON 输出:
{{
  "definitions": [
    {{
      "symbol": "...",
      "name": "...",
      "formal_def": "<一阶逻辑 / 集合论 / 数学定义>",
      "nl_explanation": "<1-2 句>",
      "constraints": "<monotone / non-negative / computable / ...>",
      "source": "conventional|new"
    }}
  ],
  "nl_to_symbol": {{"truth-telling": "τ_i", "leaky cost": "c(s_i)"}},
  "symbol_to_nl": {{"τ_i": "truth-telling strategy", "c(s_i)": "leaky cost term"}},
  "alignment_issues": ["<issue 1>", "..."],
  "extracted_symbols": {candidate_symbols}
}}
"""
    system = NOTATION_DEFINER_SYSTEM + "\n\n" + DIKTAT_INJECTION
    raw = client.chat_json(system, user, max_tokens=6000)

    # 后处理:把 conventional symbols 也加进 definitions
    if isinstance(raw, dict):
        for sym in conventional_used:
            raw.setdefault("definitions", [])
            if not any(d.get("symbol") == sym for d in raw["definitions"]):
                raw["definitions"].append({
                    "symbol": sym,
                    "name": sym,
                    "formal_def": CONVENTIONAL_DEFINITIONS[sym],
                    "nl_explanation": CONVENTIONAL_DEFINITIONS[sym],
                    "constraints": "",
                    "source": "conventional",
                })
        raw["conventional_used"] = conventional_used
        raw["new_defined"] = [d.get("symbol") for d in raw.get("definitions", []) if d.get("source") == "new"]
        raw.setdefault("extracted_symbols", candidate_symbols)
    return raw


def consistency_check(
    nl_statement: str,
    formalization: str,
    definitions: List[Dict],
    nl_to_symbol: Dict[str, str],
    symbol_to_nl: Dict[str, str],
    alignment_issues: List[str],
) -> Dict:
    """给 axiom 的一致性打分。"""
    score = 1.0
    penalties = []
    if alignment_issues:
        score -= 0.1 * min(len(alignment_issues), 5)
        penalties.append(f"alignment_issues: {len(alignment_issues)}")
    # 检查形式化里出现的所有符号是否在 definitions 里
    defined_syms = {d.get("symbol") for d in definitions}
    # 从 definitions 提取所有 symbol 名(包括带下标的简化版)
    # 简化:如果 symbol 是 X, 也认 X_i, X_{-i}
    defined_set = set(defined_syms)
    for ds in defined_syms:
        if ds and len(ds) <= 3:
            defined_set.add(ds + "_i")
            defined_set.add(ds + "i")
            defined_set.add(ds + "_{-i}")
    # 找形式化里的"大写希腊字母+下标"
    import re
    referenced = set(re.findall(r"[A-Z][a-z]?_[-\w\{}]*|Σ|ℝ|ℕ|Θ|τ|σ|φ|ε|λ|κ|ψ|δ", formalization))
    # 过滤掉 axiom/theorem 引用
    referenced = {r for r in referenced if not (r.startswith("A") and len(r) <= 6) and not r.startswith("T-") and not r.startswith("P-")}
    # 简化:去掉 _i / _ {-i} 后比较
    referenced_base = {re.sub(r"_[-\w\{}]*$", "", r) for r in referenced}
    defined_base = {re.sub(r"_[-\w\{}]*$", "", d) for d in defined_set}
    undefined = referenced_base - defined_base - {""}
    if undefined:
        score -= 0.05 * min(len(undefined), 10)
        penalties.append(f"undefined base symbols: {sorted(undefined)[:8]}")
    # 检查 nl_to_symbol 是否对称
    if nl_to_symbol and symbol_to_nl:
        for nl, sym in nl_to_symbol.items():
            if symbol_to_nl.get(sym) and symbol_to_nl.get(sym) != nl:
                score -= 0.05
                penalties.append(f"asymmetry: {nl} <-> {sym} vs {symbol_to_nl.get(sym)}")
    return {"score": max(score, 0.0), "penalties": penalties}
