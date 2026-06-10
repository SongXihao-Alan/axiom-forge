"""
[6/5] Memo Writer
把前 4 步的产物汇总成 PerturbationMemo(v0.2 含 notation_legend)。
"""
from __future__ import annotations
import json
from typing import Dict, List
from datetime import datetime


def render_memo(
    seed_id: str,
    seed_text: str,
    perturbation: Dict,
    value_scores: List[Dict],
    new_axiom: Dict,
    consequences: List[Dict],
) -> str:
    """渲染 PerturbationMemo 为 Markdown。"""
    out = []
    out.append(f"# PerturbationMemo: {seed_id}")
    out.append(f"_Generated: {datetime.utcnow().isoformat()}Z_")
    out.append("")

    # 1. seed summary
    out.append("## 1. 种子文献")
    out.append(seed_text)
    out.append("")

    # 2. perturbation
    out.append("## 2. 扰动方案")
    out.append(f"- **target**: `{perturbation.get('target_id')}` ({perturbation.get('target_kind')})")
    out.append(f"- **type**: `{perturbation.get('perturbation_type_id')}`")
    out.append(f"- **magnitude**: {perturbation.get('magnitude')}")
    out.append(f"- **rationale**: {perturbation.get('rationale', '')}")
    out.append("")
    out.append("**Original**:")
    out.append(f"> {perturbation.get('original')}")
    out.append("")
    out.append("**Modified**:")
    out.append(f"> {perturbation.get('modified')}")
    out.append("")

    # 3. value evaluation
    out.append("## 3. Value 评分(0~1 参数化)")
    if value_scores:
        out.append("| Criterion | Instance | Before | After | Δ | Confidence | Reasoning |")
        out.append("|---|---|---|---|---|---|---|")
        for s in value_scores:
            out.append(
                f"| {s.get('criterion', '?')} | `{s.get('instance_id', '?')}` | "
                f"{s.get('score_before', 0):.2f} | {s.get('score_after', 0):.2f} | "
                f"{s.get('delta', 0):+.2f} | {s.get('confidence', 0):.2f} | "
                f"{s.get('reasoning', '')[:80]} |"
            )
    else:
        out.append("_(empty)_")
    out.append("")

    # 4. new axiom
    out.append("## 4. ★ 新公理(反推)")
    out.append(f"**ID**: `{new_axiom.get('id')}`")
    out.append("")
    out.append("**自然语言陈述**:")
    out.append(f"> {new_axiom.get('statement_nl')}")
    out.append("")
    out.append("**形式化**:")
    out.append("```")
    out.append(new_axiom.get('formalization', ''))
    out.append("```")
    out.append("")

    # 4b. notation legend (v2 新增)
    if new_axiom.get("notation_legend"):
        out.append("### 4b. Notation 体系 (per notation_definer collaboration)")
        legend = new_axiom["notation_legend"]
        # 分 conventional / new
        conv = [d for d in legend if d.get("source") == "conventional"]
        new = [d for d in legend if d.get("source") == "new"]
        if conv:
            out.append("**常规定义**(共享定义库):")
            for d in conv:
                out.append(f"- `{d.get('symbol')}`: {d.get('nl_explanation', d.get('formal_def', ''))}")
        if new:
            out.append("")
            out.append("**本次新定义**:")
            for d in new:
                out.append(f"- `{d.get('symbol')}` ({d.get('name', '')}): {d.get('nl_explanation', d.get('formal_def', ''))}")
                if d.get("constraints"):
                    out.append(f"  - constraints: {d['constraints']}")
        out.append("")

    # 4c. alignment audit (v2 新增)
    if new_axiom.get("alignment_audit"):
        audit = new_axiom["alignment_audit"]
        out.append("### 4c. 对齐审计(自然语言 ↔ 形式化)")
        out.append(f"- **consistency score**: {audit.get('score', 0):.2f}")
        if audit.get("penalties"):
            out.append(f"- **penalties**: {audit['penalties']}")
        else:
            out.append("- **penalties**: (none — fully aligned)")
        out.append("")

    # 4d. completeness audit (v2 新增)
    if new_axiom.get("completeness_audit"):
        ca = new_axiom["completeness_audit"]
        out.append("### 4d. 完整性审计(每个字段 4 维度:句法/主谓/语义/相关性)")
        out.append(f"- **overall before rewrite**: {ca.get('overall_score', 0):.2f}")
        if "after_rewrite_score" in ca:
            out.append(f"- **overall after rewrite**: {ca['after_rewrite_score']:.2f}")
        if ca.get("field_scores"):
            out.append("- **per-field scores**:")
            for f, s in ca["field_scores"].items():
                out.append(f"  - `{f}`: {s:.2f}")
        if ca.get("rewrite_log"):
            out.append("- **rewrite log**:")
            for r in ca["rewrite_log"]:
                out.append(f"  - `{r['field']}`: score {r['old_score']:.2f} → {r['new_score']:.2f}, len {r['old_len']} → {r['new_len']}")
        out.append("")

    out.append("**为什么这是公理而非定理**:")
    out.append(f"> {new_axiom.get('justification')}")
    out.append("")

    out.append("**Preservation analysis** (per DIKT-TH10-OPERATOR-UNINTENDED):")
    out.append(f"- 保留: {', '.join(f'`{x}`' for x in new_axiom.get('preserves', [])) or '(无)'}")
    out.append(f"- 破坏: {', '.join(f'`{x}`' for x in new_axiom.get('breaks', [])) or '(无)'}")
    out.append("")

    out.append("**User-facing 解释** (per DIKT-PROCACCIA-EXPLAIN-SOLUTIONS):")
    out.append(f"> {new_axiom.get('user_facing_explanation')}")
    out.append("")
    if new_axiom.get("falsifiable_predictions"):
        out.append("**Falsifiable predictions**:")
        for fp in new_axiom["falsifiable_predictions"]:
            out.append(f"- {fp}")
        out.append("")
    if new_axiom.get("invariance_class"):
        out.append(f"**Invariance class**: {new_axiom['invariance_class']}")
        out.append("")

    # 5. consequences
    out.append("## 5. 后果预测")
    if consequences:
        for c in consequences:
            out.append(f"### [{c.get('id')}] ({c.get('type')})")
            if c.get("scenario_anchor") and c.get("scenario_anchor") != "none":
                out.append(f"_Scenario anchor: `{c.get('scenario_anchor')}`_")
            out.append(f"> {c.get('statement')}")
            if c.get("user_facing"):
                out.append("_(user-facing)_")
            out.append("")
    else:
        out.append("_(empty)_")

    # 6. existence vs uniqueness report
    out.append("## 6. Existence / Uniqueness report")
    out.append("- **Existence**: 至少有一个 rule 满足新公理体系? 见 Section 4 形式化(若 axiom 自洽,通常存在)")
    out.append("- **Uniqueness**: 新公理体系是否 characterize 唯一 rule? 本 memo **不强行回答**——这是 per DIKT-TH11-IF-AND-ONLY-IF 的有意选择")
    out.append("- **Old result survival**: 见 Section 4 'preserves' 字段")
    out.append("")

    return "\n".join(out)
