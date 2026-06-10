#!/usr/bin/env python3
"""
Phase 1.3: 批量补 80+ KB 节点

策略:用脚本生成常见节点的 JSON 模板,减少手写。
目标:补到 100+ 节点,覆盖:
- 8 个 SHAP 文献(已有 7,加 C21)
- 2 本 Thomson 书
- 12 个 diktat(从 training/graph/diktats/ 复制)
- 30-50 个 value_anchor(6 大类 × 5-8 个)
- 5-10 个 scenario(Thomson + 现实)
- 3-5 个 tradeoff(已有 Hurwicz)
- Impossibility 4 推论(theorem 节点)
"""
import json
from pathlib import Path

KB = Path(__file__).resolve().parent
NODES = KB / "nodes"


def write_node(type_dir, filename, data):
    path = NODES / type_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✓ {type_dir}/{filename}")


# ========== 1. 剩余 6 篇 SHAP 文献 ==========
print("=== 文献节点 (已有 7,加 1) ===")

c21 = {
    "id": "LIT-C21-EXPLAINING-BY-REMOVING",
    "type": "literature",
    "version": "1.0", "created": "2026-06-10", "status": "seed",
    "title": "Explaining by Removing: A Unified Framework for Model Explanation",
    "authors": ["Ian C. Covert", "Scott Lundberg", "Su-In Lee"],
    "year": 2021, "venue": "JMLR",
    "domain": "feature_attribution",
    "tags": ["unified_framework", "removal_based", "26_methods"],
    "anchors": [
        {"type": "community", "supporters": ["JMLR 2021"]},
        {"type": "empirical", "subtype": "experimental", "evidence": "26 种方法统一化"}
    ],
    "abstract_nl": "Methods that explain predictions by simulating feature removal can be unified along 3 dimensions: feature removal, model behavior, summary technique.",
    "key_contributions": [
        "3-dim 框架: feature removal / model behavior / summary technique",
        "26 种 removal-based 方法统一",
        "Section 5: 6 种 set function v(S)",
        "Section 7: Shapley 唯一满足 Symmetry+Dummy+Additivity+Marginalism"
    ],
    "linage_in": ["LIT-L17-SHAP", "LIT-SY19-MANY", "LIT-H20-CAUSAL-SHAP"],
    "linage_out": ["LIT-AXIOM-FINDER-2026"],
    "source": {"primary": "PDF: d4e1caa2__0df0c9c2-5dfb-4299-83d4-9b26b8f51d76.pdf"},
    "process_meta": {
        "[AH-HA]": "C21 给了 '操作空间' —— Structural Shapley 这个 cell 是空的, SC 主线填这个"
    }
}
write_node("literature", "LIT-C21-EXPLAINING-BY-REMOVING.json", c21)


# ========== 2. Thomson 两本书 ==========
print("=== Thomson 文献节点 ===")

thomson2023 = {
    "id": "LIT-THOMSON-2023",
    "type": "literature",
    "version": "1.0", "created": "2026-06-10", "status": "seed",
    "title": "The Axiomatics of Economic Design, Vol. 1: An Introduction to Theory and Methods",
    "authors": ["William Thomson"],
    "year": 2023, "venue": "Springer",
    "domain": "mechanism_design",
    "tags": ["thomson", "axiomatic_methodology", "training_data"],
    "anchors": [
        {"type": "community", "supporters": ["Springer 2023", "Cooperative game theory 经典教材"]},
        {"type": "philosophical", "tradition": "axiomatic_method", "concept": "axiom-as-constraint"}
    ],
    "abstract_nl": "Comprehensive treatment of axiomatic methods in economic design, covering consistency, no-envy, strategy-proofness, and existence/uniqueness results.",
    "key_contributions": [
        "axiom-as-constraint + planner-centric 方法论",
        "Ch.4 Population Monotonicity",
        "Ch.7 Consistency",
        "Ch.8 No-Envy",
        "Ch.10 Strategy-Proofness",
        "Ch.11 Existence/Uniqueness"
    ],
    "linage_out": ["LIT-AXIOM-FINDER-2026"],
    "source": {"primary": "PDF: 9fec3554__47c04025-bf30-4d39-99b2-ef962102f72b.pdf"},
    "process_meta": {
        "[AH-HA]": "Thomson 的方法论 = Axiom Forge 的'训练数据' —— 不是模仿 AI4S, 是按 Thomson 思路做"
    }
}
write_node("literature", "LIT-THOMSON-2023.json", thomson2023)

laslier2019 = {
    "id": "LIT-LASLIER-2019",
    "type": "literature",
    "version": "1.0", "created": "2026-06-10", "status": "seed",
    "title": "The Future of Economic Design",
    "authors": ["Jean-François Laslier", "Hervé Moulin", "M. Remzi Sanver", "William S. Zwicker"],
    "year": 2019, "venue": "Springer Studies in Economic Design",
    "domain": "mechanism_design",
    "tags": ["laslier", "future_economic_design"],
    "anchors": [
        {"type": "community", "supporters": ["Springer 2019"]}
    ],
    "abstract_nl": "The continuing development of economic design as envisioned by its researchers.",
    "key_contributions": [
        "axiom = 价值代表(每个 axiom 对应某个 stakeholder 的核心价值)"
    ],
    "linage_out": ["LIT-AXIOM-FINDER-2026"],
    "source": {"primary": "PDF: c954d254__1ff10052-e397-4ccc-b305-721ec5a98fce.pdf"},
    "process_meta": {
        "[AH-HA]": "Laslier 启发: axiom 应当对应一种价值, 不是数学游戏"
    }
}
write_node("literature", "LIT-LASLIER-2019.json", laslier2019)


# ========== 3. Impossibility 4 推论 (theorem 节点) ==========
print("=== Theorem 推论 ===")

corollaries = [
    {
        "id": "TH-COR-501-1",
        "nl": "TreeSHAP violates SC: Given f structure but f̂ ≠ f, TreeSHAP reflects f̂, violates SC",
        "formal": "TreeSHAP(AS-SHAP-CHARFN-tree) ⇒ ¬SC in general",
        "evidence": "TreeSHAP uses tree-distribution to approximate v(S), not structural"
    },
    {
        "id": "TH-COR-501-2",
        "nl": "KernelSHAP violates SC: Same as TreeSHAP",
        "formal": "KernelSHAP(AS-SHAP-CHARFN) ⇒ ¬SC in general",
        "evidence": "KernelSHAP uses kernel sampling, not structural"
    },
    {
        "id": "TH-COR-501-3",
        "nl": "Information Shapley violates SC: v(S) = E[Y|X_S] - E[Y] depends on P(X,Y), not f structure",
        "formal": "InformationShapley ⇒ ¬SC in general",
        "evidence": "v(S) may not reflect SI_i(f) when f̂ ≠ f"
    },
    {
        "id": "TH-COR-501-4",
        "nl": "Methods satisfying SC: Structural Shapley v_s(S) = Σ_{k∈Path(S)} Effect(k), Necessary Shapley, Causal Structural Shapley",
        "formal": "StructuralShapley(SI_i) ⇒ SC",
        "evidence": "v_s(S) defined on f directly, not via f̂"
    }
]
for c in corollaries:
    c.update({
        "type": "theorem", "version": "1.0", "created": "2026-06-10", "status": "seed",
        "depends_on": ["TH-IMP-501"], "domain": "feature_attribution",
        "tags": ["corollary", "mainline"],
        "anchors": [
            {"type": "empirical", "subtype": "logical", "evidence": c["evidence"]},
            {"type": "community", "supporters": ["Heskes 2021 隐含"]}
        ],
        "source": {"primary": "AXIOM_SKELETON.md §5.3"}
    })
    write_node("theorems", f"{c['id']}.json", c)


# ========== 4. 4 个 SC vs Dummy 命题 (theorem 节点) ==========
print("=== SC vs Dummy 命题 ===")

propositions = [
    {
        "id": "TH-PROP-621",
        "nl": "Prop 6.2.1: When f̂ = f, SC alone does NOT entail Dummy (SC is weak)",
        "status": "sketch"
    },
    {
        "id": "TH-PROP-622",
        "nl": "Prop 6.2.2: When f̂ ≠ f, SC and Dummy are INDEPENDENT (different objects, orthogonal)",
        "status": "argued"
    },
    {
        "id": "TH-PROP-623",
        "nl": "Prop 6.2.3: Scenario B (f̂ ≠ f, SI>0, ∂f̂=0) is the Impossibility entry point",
        "status": "proved"
    },
    {
        "id": "TH-PROP-624",
        "nl": "Prop 6.2.4: SC + Dummy = structural completeness (one-to-one correspondence)",
        "status": "argued"
    }
]
for p in propositions:
    p.update({
        "type": "theorem", "version": "1.0", "created": "2026-06-10",
        "domain": "feature_attribution", "tags": ["proposition", "sc_vs_dummy"],
        "anchors": [{"type": "empirical", "subtype": "logical", "evidence": p["nl"]}],
        "source": {"primary": "AXIOM_SKELETON.md §4"}
    })
    write_node("theorems", f"{p['id']}.json", p)


# ========== 5. Value Anchor 6 大类 × 5-8 个 = 30-50 个 ==========
print("=== Value Anchor 6 大类 ===")

anchors_data = [
    # 道德 (5)
    ("VA-MORAL-HELP-WEAK", "moral", "universal_kindness", "帮助老弱病残", "Help the weak and disabled", "high", "universal"),
    ("VA-MORAL-NO-KILL", "moral", "universal_prohibition", "不能杀人", "Prohibition of killing", "high", "universal"),
    ("VA-MORAL-HONESTY", "moral", "general", "诚实不欺骗", "Honesty", "high", "general"),
    ("VA-MORAL-FAIRNESS", "moral", "general", "公平不偏私", "Fairness", "high", "general"),
    ("VA-MORAL-AUTONOMY", "moral", "general", "尊重自主选择", "Respect autonomy", "medium", "general"),
    ("VA-MORAL-CULTURAL", "moral", "cultural_specific", "特殊文化习俗", "Cultural conventions", "low", "cultural"),
    # 利益 (5)
    ("VA-INTEREST-UTIL-IND", "interest", "individual", "个人效用最大化", "Individual utility", "medium", "economic"),
    ("VA-INTEREST-UTIL-SOC", "interest", "social", "社会总福利", "Social welfare", "medium", "economic"),
    ("VA-INTEREST-POWER", "interest", "power", "权力分配", "Power distribution", "low", "political"),
    ("VA-INTEREST-EQUAL", "interest", "equality", "平等分配", "Equal distribution", "medium", "political"),
    ("VA-INTEREST-LONGTERM", "interest", "longterm", "长期利益", "Long-term interest", "medium", "general"),
    # 美学 (4)
    ("VA-AESTHETIC-SYMMETRY", "aesthetic", "symmetry", "对称", "Symmetry", "medium", "general"),
    ("VA-AESTHETIC-SIMPLE", "aesthetic", "simplicity", "简洁", "Simplicity", "medium", "general"),
    ("VA-AESTHETIC-ELEGANCE", "aesthetic", "elegance", "优雅", "Elegance", "low", "expert"),
    ("VA-AESTHETIC-UNITY", "aesthetic", "unity", "统一", "Unity", "medium", "general"),
    # 知识 (5)
    ("VA-EPISTEMIC-TRUTH", "epistemic", "truth", "对应现实", "Truth (empirical)", "high", "universal"),
    ("VA-EPISTEMIC-CONSISTENCY", "epistemic", "consistency", "逻辑一致", "Logical consistency", "high", "universal"),
    ("VA-EPISTEMIC-FALSIFIABLE", "epistemic", "falsifiability", "可证伪", "Falsifiability", "medium", "scientific"),
    ("VA-EPISTEMIC-INTERPRETABLE", "epistemic", "interpretability", "可解释", "Interpretability", "medium", "scientific"),
    ("VA-EPISTEMIC-UNIVERSAL", "epistemic", "universality", "普遍适用", "Universality", "medium", "scientific"),
    # 实践 (5)
    ("VA-PRACTICAL-EFFICIENCY", "practical", "efficiency", "效率", "Efficiency", "medium", "engineering"),
    ("VA-PRACTICAL-SCALABLE", "practical", "scalability", "可扩展", "Scalability", "medium", "engineering"),
    ("VA-PRACTICAL-REPRODUCIBLE", "practical", "reproducibility", "可复现", "Reproducibility", "high", "scientific"),
    ("VA-PRACTICAL-MAINTAINABLE", "practical", "maintainability", "可维护", "Maintainability", "medium", "engineering"),
    ("VA-PRACTICAL-TEACHABLE", "practical", "teachability", "可教学", "Teachability", "medium", "educational"),
    # 哲学 (8)
    ("VA-PHIL-KANT", "philosophical", "kantian_ethics", "康德伦理学", "Kantian ethics", "medium", "philosophical"),
    ("VA-PHIL-UTIL", "philosophical", "utilitarianism", "功利主义", "Utilitarianism", "medium", "philosophical"),
    ("VA-PHIL-RAWLS", "philosophical", "rawls", "罗尔斯正义论", "Rawls' theory of justice", "medium", "philosophical"),
    ("VA-PHIL-NOZICK", "philosophical", "libertarian", "自由主义", "Libertarianism", "medium", "philosophical"),
    ("VA-PHIL-PHENOM", "philosophical", "phenomenology", "现象学", "Phenomenology", "medium", "philosophical"),
    ("VA-PHIL-VIRTUE", "philosophical", "virtue_ethics", "德性伦理", "Virtue ethics", "medium", "philosophical"),
    ("VA-PHIL-PRAGMA", "philosophical", "pragmatism", "实用主义", "Pragmatism", "medium", "philosophical"),
    ("VA-PHIL-EXIST", "philosophical", "existentialism", "存在主义", "Existentialism", "medium", "philosophical"),
]

for aid, vclass, vsubclass, label_zh, label_en, consistency, cultural in anchors_data:
    data = {
        "id": aid,
        "type": "value_anchor",
        "version": "1.0", "created": "2026-06-10",
        "status": "user_provided" if vclass == "moral" and vsubclass in ("universal_kindness", "universal_prohibition") else "seed",
        "value_class": vclass,
        "value_subclass": vsubclass,
        "label_zh": label_zh,
        "label_en": label_en,
        "description": f"{label_zh} ({label_en}) - value anchor in {vclass} class, subclass {vsubclass}",
        "cross_cultural_consistency": consistency,
        "domain": vclass,
        "tags": [vclass, vsubclass],
        "anchors_self": [
            {"type": "empirical", "subtype": "moral_consensus" if vclass == "moral" else "interest_judgment",
             "evidence": f"Examples of {label_en.lower()} in various contexts"}
        ],
        "source": {"primary": "用户原话(2026-06-09)" if "USER" in aid or "HELP-WEAK" in aid or "NO-KILL" in aid else "compiled from VALUE_TREE_DRAFT.md"}
    }
    write_node("value_anchors", f"{aid}.json", data)


# ========== 6. 12 个 diktat(从已有 JSON 复制并加 anchors 字段) ==========
print("=== Diktat 节点(已有 12 个,转 KB schema) ===")

import shutil
src_diktats = Path("/workspace/axiom-finder/training/graph/diktats")
for f in sorted(src_diktats.glob("DIKT-*.json")):
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        # 加 KB schema 通用字段
        d["type"] = "diktat"
        d["version"] = "1.0"
        d["created"] = "2026-06-10"
        d["updated"] = "2026-06-10"
        d["status"] = "seed"
        d["domain"] = "methodology"
        d["tags"] = ["diktat", "thomson_style", "evaluation_perspective"]
        # 加 anchors 字段(3 锚,完全平等)
        if "anchors" not in d:
            d["anchors"] = [
                {"type": "community", "supporters": ["Thomson 风格"]},
                {"type": "philosophical", "tradition": d.get("stance", {}).get("value_priority", "unknown")},
                {"type": "empirical", "subtype": "evaluation_perspective"}
            ]
        # process_meta
        if "process_meta" not in d:
            d["process_meta"] = {"[HUNCH]": "从 Thomson 风格抽出的 tacit judgment"}
        # source
        if "source" not in d:
            d["source"] = {"primary": f"training/graph/diktats/{f.name}"}
        write_node("diktats", f.name, d)
    except Exception as e:
        print(f"  [warn] {f.name}: {e}")


# ========== 7. Scenario 节点 ==========
print("=== Scenario 节点 ===")

scenarios_data = [
    {
        "id": "SC-CAMEL-DUMMY",
        "name_zh": "Cost-sharing(骆驼寓言)",
        "name_en": "Cost-sharing (Camels allegory)",
        "description": "Three travelers must share cost of goods. How to split fairly?",
        "stakeholders": ["3 旅客", "成本 c(N)"],
        "key_question": "如何拆 cost 让每个旅客愿参与?",
        "domain": "real_world",
        "tags": ["thomson", "fair_division", "cost_sharing"]
    },
    {
        "id": "SC-FAA-LANDING",
        "name_zh": "FAA 机场跑道分配",
        "name_en": "FAA airport landing slot allocation",
        "description": "FAA allocates landing slots among airlines. Tradeoff: efficiency vs fairness.",
        "stakeholders": ["航空公司", "机场", "乘客"],
        "key_question": "在效率和安全之间如何平衡?",
        "domain": "real_world",
        "tags": ["faa", "real_world", "efficiency_fairness"]
    },
    {
        "id": "SC-HOSPITAL-COSTSHARE",
        "name_zh": "医院 cost-sharing",
        "name_en": "Hospital cost-sharing",
        "description": "Hospital decides cost-sharing rules for patients. Tradeoff: cost recovery vs patient burden.",
        "stakeholders": ["医院", "病人", "保险公司"],
        "key_question": "如何分担成本让 patient 能负担?",
        "domain": "real_world",
        "tags": ["hospital", "fairness"]
    },
    {
        "id": "SC-COURT-DIVORCE",
        "name_zh": "法院离婚财产分配",
        "name_en": "Court divorce property division",
        "description": "Court divides property in divorce. Tradeoff: equal split vs contribution-based.",
        "stakeholders": ["夫妻", "子女", "社会"],
        "key_question": "平等 vs 贡献?",
        "domain": "real_world",
        "tags": ["court", "fairness"]
    },
    {
        "id": "SC-ELECTION-VOTING",
        "name_zh": "选举投票机制",
        "name_en": "Election voting mechanism",
        "description": "Design voting mechanism. Tradeoff: simplicity vs expressiveness.",
        "stakeholders": ["选民", "候选人", "社会"],
        "key_question": "如何让投票结果反映民意?",
        "domain": "real_world",
        "tags": ["election", "voting"]
    },
    {
        "id": "SC-ML-ATTR-SHAP",
        "name_zh": "ML 特征归因(SHAP 域)",
        "name_en": "ML feature attribution (SHAP domain)",
        "description": "ML model explains why prediction is X. Multiple Shapley variants exist.",
        "stakeholders": ["模型", "用户", "监管"],
        "key_question": "哪个 Shapley variant 该用?",
        "domain": "real_world",
        "tags": ["ml", "shap", "explanation"]
    }
]
for s in scenarios_data:
    sid = s.pop("id")
    data = {
        "id": sid,
        "type": "scenario",
        "version": "1.0", "created": "2026-06-10", "status": "seed",
        "anchors": [
            {"type": "empirical", "subtype": "interest_judgment", "evidence": s.get("description", "")},
            {"type": "community", "supporters": ["Thomson 经典案例"]}
        ],
        "source": {"primary": "training/graph/scenarios/"}
    }
    data.update(s)
    write_node("scenarios", f"{sid}.json", data)


# ========== 8. Tradeoff 节点 ==========
print("=== Tradeoff 节点 ===")

tradeoffs_data = [
    {
        "id": "TR-HURWICZ-1972",
        "name": "Hurwicz 1972 informational efficiency vs incentive compatibility",
        "description": "Mechanisms 必须在信息效率(只用必要信息)和激励相容(诚实是占优策略)之间权衡",
        "conflicting_values": ["informational_efficiency", "incentive_compatibility"],
        "domain": "mechanism_design"
    },
    {
        "id": "TR-EFFICIENCY-EQUITY",
        "name": "效率 vs 公平(Efficiency-Equity)",
        "description": "分配机制可在效率(总福利最大化)和公平(分配公正)之间权衡",
        "conflicting_values": ["efficiency", "equity"],
        "domain": "mechanism_design"
    },
    {
        "id": "TR-PREDICTIVE-STRUCTURAL",
        "name": "Predictive vs Structural (SHAP 域)",
        "description": "归因可在'反映预测器'(v(S)=E[f̂|X_S])和'反映真实结构'(v(S)=structural)之间权衡",
        "conflicting_values": ["predictive_accuracy", "structural_truthfulness"],
        "domain": "feature_attribution"
    },
    {
        "id": "TR-SIMPLICITY-FAITHFULNESS",
        "name": "简洁 vs 忠实(Simplicity-Faithfulness)",
        "description": "axiom 系统可在简洁(少 axiom)和忠实(多 axiom 反映所有约束)之间权衡",
        "conflicting_values": ["simplicity", "faithfulness"],
        "domain": "methodology"
    }
]
for t in tradeoffs_data:
    tid = t.pop("id")
    data = {
        "id": tid,
        "type": "tradeoff",
        "version": "1.0", "created": "2026-06-10", "status": "seed",
        "anchors": [
            {"type": "empirical", "subtype": "interest_judgment"},
            {"type": "community", "supporters": ["经典权衡"]}
        ],
        "source": {"primary": "VALUE_TREE_DRAFT.md + Thomson Ch.4-11"}
    }
    data.update(t)
    write_node("tradeoffs", f"{tid}.json", data)


# ========== 完成 ==========
print("\n=== 节点生成完成 ===")
total = 0
for d in NODES.iterdir():
    if d.is_dir():
        n = len(list(d.glob("*.json")))
        print(f"  {d.name}: {n}")
        total += n
print(f"  TOTAL: {total}")