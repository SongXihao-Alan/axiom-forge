# KB Schema v1.0 (Phase 1.1)

> 8 类节点 + 1 类关系 + 1 类压缩视图 + 1 类训练信号。
> 4 维组织:储存(8 类 schema) / 压缩(多粒度) / 关联(6 类型) / 引用(段级)。
> **3 锚完全平等**(无优先级)。**先探索再深挖**(顺序,非对立)。

---

## 0. 通用字段(所有节点)

```json
{
  "id": "TYPE-UNIQUE_ID",
  "type": "axiom|assumption|theorem|literature|diktat|scenario|tradeoff|value_anchor",
  "version": "1.0",
  "created": "2026-06-09",
  "updated": "2026-06-09",
  "status": "draft|seed|verified|handcrafted",
  "tags": ["...", "..."],
  "domain": "...",  // 跨域分类: feature_attribution | mechanism_design | moral | philosophical | ...
  "anchors": [...],  // 3 锚完全平等
  "source": {...},  // 引用(段级)
  "process_meta": {...}  // 过程标记
}
```

---

## 1. axiom 节点

```json
{
  "id": "AX-SC-001",
  "type": "axiom",
  "nl": "For any feature i, if SI_i(f) > 0 then ∃x: φ_i(f̂, x) > 0",
  "formal": "∀ i ∈ N: [SI_i(f) > 0] ⇒ [∃ x ∈ X: φ_i(f̂, x) > 0]",
  "aliases": ["Structural Consistency", "SC"],
  "depends_on": ["AX-SHAP-EFF", "AX-SHAP-SYM", "AX-SHAP-DUM"],
  "domain": "feature_attribution",
  "anchors": [
    {"type": "empirical", "subtype": "moral_consensus", "evidence": "f̂ 错位时医生误导"},
    {"type": "philosophical", "tradition": "phenomenology", "concept": "回到事物本身"},
    {"type": "community", "supporters": ["LIT-H21-SHAP", "LIT-K20-SHAP"]}
  ],
  "source": {
    "primary": "MEMO-AX-STRUCTURAL-CONSISTENCY-001",
    "citations": [
      {"cite": "Heskes 2021 Book Ch.21 Section 3.2", "page": 17, "line": "12-18"}
    ]
  },
  "process_meta": {
    "[AH-HA]": "SC 作用在 f, 其他 axiom 作用在 f̂ —— 这不对称是创新点",
    "user_evaluation": "用户已确认(2026-06-09)"
  }
}
```

## 2. assumption 节点

```json
{
  "id": "AS-SHAP-CHARFN",
  "type": "assumption",
  "nl": "SHAP's characteristic function: v(S) = E[f(X) | X_S]",
  "formal": "v(S) := E_{X_{S̄} | X_S = x_S}[f(X_S, X_{S̄})]",
  "domain": "feature_attribution",
  "anchors": [
    {"type": "empirical", "subtype": "experimental", "evidence": "Kernel SHAP 的 ML 实验"},
    {"type": "community", "supporters": ["LIT-L17-SHAP", "LIT-SY19-MANY"]}
  ],
  "source": {
    "primary": "LIT-L17-SHAP Section 2",
    "citations": [{"cite": "Lundberg & Lee 2017 NeurIPS p.2"}]
  },
  "process_meta": {
    "[HUNCH]": "v(S) 绑预测器 f̂ 不绑真结构 f, 这是 SC 反命题的入口"
  }
}
```

## 3. theorem 节点

```json
{
  "id": "TH-IMP-501",
  "type": "theorem",
  "nl": "Impossibility Theorem 5.1: No Shapley attribution based on v(S) = E[f̂|X_S] can simultaneously satisfy Efficiency, Symmetry, Dummy, Structural Consistency",
  "formal": "∃ f, f̂ ≠ f, ∀ Φ: Φ 基于 v(S) = E[f̂|X_S] ⇒ ¬(Efficiency ∧ Symmetry ∧ Dummy ∧ SC)",
  "proof_sketch": "Counter-example: f(X) = βX_1, f̂(X) = 0. SI_1 > 0 but φ_1 = 0. Violates SC.",
  "depends_on": ["AX-SHAP-EFF", "AX-SHAP-SYM", "AX-SHAP-DUM", "AX-SC-001"],
  "domain": "feature_attribution",
  "anchors": [
    {"type": "empirical", "subtype": "logical", "evidence": "具体反例构造"},
    {"type": "philosophical", "tradition": "phenomenology"},
    {"type": "community", "supporters": ["LIT-H20-SHAP"]}
  ],
  "source": {
    "primary": "AXIOM_SKELETON.md §5",
    "citations": []
  }
}
```

## 4. literature 节点

```json
{
  "id": "LIT-L17-SHAP",
  "type": "literature",
  "title": "A Unified Approach to Interpreting Model Predictions",
  "authors": ["Scott M. Lundberg", "Su-In Lee"],
  "year": 2017,
  "venue": "NeurIPS",
  "domain": "feature_attribution",
  "anchors": [
    {"type": "community", "supporters": ["1000+ 引用"]},
    {"type": "empirical", "subtype": "experimental", "evidence": "Tree SHAP, Kernel SHAP 等应用"}
  ],
  "abstract_nl": "We propose SHAP (SHapley Additive exPlanations), a unified framework for interpreting predictions...",
  "key_contributions": [
    "v(S) = E[f̂(X)|X_S] 的 characteristic function",
    "3 axiom: Local Accuracy, Missingness, Consistency",
    "6 方法统一: LIME, DeepLIFT, LRP, QII, Shapley sampling, Classic Shapley"
  ],
  "key_quotes": [
    {"verbatim": "SHAP values as a unified measure of feature importance", "page": 1, "line": "5-8"}
  ],
  "linage_in": ["LIT-SHAPLEY-1953", "LIT-LIME-2016", "LIT-LC01"],
  "linage_out": ["LIT-SY19-MANY", "LIT-A21-DEPENDENT", "LIT-H21-STRUCTURAL"],
  "source": {
    "primary": "PDF: 9a0bfe62... (Lundberg-Lee 2017 NeurIPS)",
    "pdf_path": "/workspace/attachments/9a0bfe62__49cde759-7a72-4e3d-b377-79875bf595a2.pdf"
  },
  "process_meta": {
    "[AH-HA]": "L17 的 'uniqueness' 是循环论证 —— 'additive' 已经预设了 'SHAP-like'"
  }
}
```

## 5. diktat 节点

```json
{
  "id": "DIKT-PROCACCIA-EXPLAIN-SOLUTIONS",
  "type": "diktat",
  "stance": {
    "value_priority": "user_explainability > technical_correctness",
    "implicit_norm": "用户应该能理解机制结果",
    "trigger": "axiom 提出 technical 但不可解释",
    "verdict_pattern": "user-facing explanation 必填",
    "rhetorical_device": "metaphor + worked example"
  },
  "domain": "methodology",
  "anchors": [
    {"type": "philosophical", "tradition": "pragmatism"},
    {"type": "empirical", "subtype": "interest_judgment", "evidence": "用户对机制有解释权"}
  ],
  "counter_example": "axiom 完美但用户不理解 → 失败",
  "origin_story": "Procaccia 在 AAAI 2013 谈 'explaining solutions' 时强调: 任何 mechanism 都该 user-facing",
  "source": {
    "primary": "training/graph/diktats/DIKT-PROCACCIA-EXPLAIN-SOLUTIONS.json"
  }
}
```

## 6. scenario 节点

```json
{
  "id": "SC-CAMEL-DUMMY",
  "type": "scenario",
  "name": "Cost-sharing (camels allegory)",
  "domain": "real_world",
  "description": "Three travelers must share cost of goods. How to split fairly?",
  "stakeholders": ["3 旅客", "成本 c(N)"],
  "key_question": "如何拆 cost 让每个旅客愿参与?",
  "anchors": [
    {"type": "empirical", "subtype": "moral_consensus", "evidence": "公平拆账的普遍诉求"},
    {"type": "community", "supporters": ["Thomson 多次引用"]}
  ],
  "source": {
    "primary": "training/graph/scenarios/SC-CAMEL-DUMMY.json"
  }
}
```

## 7. tradeoff 节点

```json
{
  "id": "TR-HURWICZ-1972",
  "type": "tradeoff",
  "name": "Hurwicz 1972 informational efficiency vs incentive compatibility",
  "description": "Mechanisms 必须在信息效率(只用必要信息)和激励相容(诚实是占优策略)之间权衡",
  "conflicting_values": ["informational_efficiency", "incentive_compatibility"],
  "anchors": [
    {"type": "philosophical", "tradition": "pragmatism"},
    {"type": "community", "supporters": ["Hurwicz 1972"]}
  ],
  "source": {
    "primary": "training/graph/tradeoffs/TR-HURWICZ-1972.json"
  }
}
```

## 8. value_anchor 节点(新加,Phase 1 重点)

```json
{
  "id": "VA-MORAL-HELP-WEAK",
  "type": "value_anchor",
  "value_class": "moral",
  "value_subclass": "universal_kindness",
  "label_zh": "帮助老弱病残",
  "label_en": "Help the weak and disabled",
  "description": "A universal moral consensus across cultures: helping those in need",
  "cross_cultural_consistency": "high",
  "anchors_self": [
    {"type": "empirical", "subtype": "moral_consensus", "evidence": "几乎所有已知社会的伦理体系都包含此原则"}
  ],
  "source": {
    "primary": "用户原话(2026-06-09)",
    "user_provided": true
  },
  "process_meta": {
    "[AH-HA]": "用户把 '价值锚' 直接对应 '现实道德' —— 不是数据/实验"
  }
}
```

## 9. relations(独立文件,不在 nodes/ 里)

```json
{
  "from": "AX-SC-001",
  "to": "AS-SHAP-CHARFN",
  "type": "constraints",
  "strength": 0.9,
  "evidence": "Impossibility 5.1 证明"
}
```

**6 种关系类型**:
- `parent_child` — 谱系(谁从谁推出)
- `generalization` — 推广(A 是 B 的一般化)
- `contradicts` — 矛盾
- `same_intuition` — 共享直觉
- `citation` — 文献引用
- `process_[AH-HA/HUNCH/FAIL]` — 过程标记
- `cross_domain` — 跨域关联(SC ↔ 现象学)

---

## 10. compressed_views(独立文件)

每节点有 3 档:
- `full` — 完整 JSON(机读 + 人读)
- `medium` — 200-500 字 markdown(给 M3 prompt)
- `tiny` — 1 句话(UI tooltip / 索引)

跨节点压缩:
- `shap_survey_compressed.md` — 13 篇 SHAP 文献摘要
- `sc_mainline_summary.md` — SC 主线摘要

---

## 11. training_signals(Phase 3 准备)

```json
{
  "good_axioms": [
    "AX-SHAP-EFF",      // Local Accuracy
    "AX-SHAP-CONS",     // Consistency
    "AX-SC-001"         // SC(我们提的)
  ],
  "bad_axioms": [
    // 反例:不 user-facing 的 axiom
  ],
  "value_score_calibration": {
    "user-explainable": {"baseline": 0.5, "good": 0.8, "bad": 0.3}
  }
}
```

---

## 12. 命名约定

- `AX-XXX-NNN` — axiom
- `AS-XXX-NNN` — assumption
- `TH-XXX-NNN` — theorem
- `LIT-XXX-NNN` — literature
- `DIKT-XXX` — diktat
- `SC-XXX-NNN` — scenario
- `TR-XXX-NNN` — tradeoff
- `VA-XXX-NNN` — value_anchor
- `REL-NNN` — relation

---

## 13. Phase 1 目标节点数

| 类型 | 数量目标 | 来源 |
|---|---|---|
| axiom | 10-20 | SHAP (3) + 价值谱系 (10+) |
| assumption | 5-10 | SHAP v(S) 等 |
| theorem | 5-10 | Impossibility 5.1 + 推论 |
| literature | 15-20 | 13 SHAP + Thomson 2 + 1-2 哲学 |
| diktat | 12 | 已有 12 |
| scenario | 5-10 | 已有 + 价值观谱系案例 |
| tradeoff | 3-5 | 已有 + 跨域 |
| value_anchor | 30-50 | 6 大类 × 5-8 子类 |
| **总计** | **85-135** | **接近 100-300 目标** |
