# Axiom Forge v0.3-alpha

> **AI4SS 前身 / 扩散性价值观探索 Skill** —— 把 Thomson 的 axiom-as-constraint 方法论迁移到 SHAP 特征归因,产出一个新 axiom (**Structural Consistency**) 和一个主定理 (**Impossibility Theorem 5.1**)。
>
> 这是 1 个**研究 Skill**,不是 1 个训练好的模型。**用 MiniMax-M3 API + 知识库 (KB) + CLI**,支持"探索价值观"。

---

## 🎯 这个 Skill 能做什么

| 你能问 | CLI 命令 | 是否需要 M3 API |
|---|---|---|
| 列出所有 KB 节点 | `axiom-forge list` | 否 |
| 关键词查询 | `axiom-forge query "SC"` | 否 |
| 加权语义搜索 (RAG 简化版) | `axiom-forge search "Shapley attribution"` | 否 |
| 显示节点详情 | `axiom-forge show AX-SC-001` | 否 |
| 显示关系 | `axiom-forge relations AX-SC-001` | 否 |
| 关系图 (N 跳) | `axiom-forge graph AX-SC-001 --depth 2` | 否 |
| 显示节点的所有锚 | `axiom-forge anchors AX-SC-001` | 否 |
| 按锚类型列节点 | `axiom-forge anchors-by-type philosophical` | 否 |
| 多粒度压缩 | `axiom-forge compressed AX-SC-001 tiny` | 否 |
| 价值观谱系图 | `axiom-forge value-tree` | 否 |
| **用 M3 回答问题 (RAG)** | `axiom-forge ask "什么是 SC?"` | ✅ |
| **M3 深度解读某类锚** | `axiom-forge explore-anchor philosophical` | ✅ |
| **M3 验证 KB 节点质量** | `axiom-forge validate AX-SC-001` | ✅ |

**5+3 = 8 个核心命令**。前 5 个**不需要 API**,后 3 个需要。

---

## 📦 包含什么

```
axiom-finder/
├── kb/                              # 知识库 (核心)
│   ├── SCHEMA.md                    # 8 类节点 + 6 类关系 + 3 粒度
│   ├── kb_query.py                  # CLI 主体 (8 命令)
│   ├── kb_llm.py                    # M3 桥 (RAG)
│   ├── generate_nodes.py            # 批量生成 KB
│   ├── nodes/                       # 85 节点 + 63 关系
│   │   ├── axioms/ (8)             # SC + 3 SHAP + 3 Thomson + 1 demo
│   │   ├── assumptions/ (2)
│   │   ├── theorems/ (10)           # Impossibility 5.1 + 推论 + 命题
│   │   ├── literature/ (10)         # 8 SHAP + Thomson 2
│   │   ├── value_anchors/ (33)      # 6 大类 × 5-8 子类
│   │   ├── diktats/ (12)            # Thomson 风格评价视角
│   │   ├── scenarios/ (6)
│   │   ├── tradeoffs/ (4)
│   │   └── relations.json (63 条)
│   └── REPRODUCTION/                # Phase 3 复现包
│       ├── README.md                # 3 任务说明
│       ├── EVALUATION_RUBRIC.md     # 评估标准
│       ├── EXAMPLE_T1_NEW_AXIOM.json
│       └── EXAMPLE_T2_FIVE_COUNTEREXAMPLES.md
├── axiom-forge                       # CLI shim
├── requirements.txt                  # httpx + dotenv
├── .env.example                      # MINIMAX_API_KEY
├── README.md                         # (本文)
├── training/structural_consistency/  # 主定理
│   ├── AXIOM_SKELETON.md
│   └── KNOWLEDGE_BASE.md
├── outputs/                          # 5-agent pipeline 跑通
└── docs/                             # 过程叙事
    ├── PROCESS_NARRATIVE.md
    └── program_design/
```

---

## 🚀 30 秒上手

```bash
# 1. 克隆
git clone https://github.com/<user>/axiom-forge.git
cd axiom-forge

# 2. (可选)装依赖 — 仅当用 ask/explore-anchor/validate
pip install -r requirements.txt

# 3. (可选)配 M3 API key — 仅当用 ask/explore-anchor/validate
cp .env.example .env
# 编辑 .env, 填入 MINIMAX_API_KEY=sk-cp-xxx

# 4. 跑!
./axiom-forge list                       # 看 85 个节点
./axiom-forge stats                      # 知识库统计
./axiom-forge ask "什么是 SC?"            # 用 M3 读 KB 答
./axiom-forge show AX-SC-001             # 看 SC 完整 JSON
./axiom-forge graph AX-SC-001 --depth 2  # 关系图
```

---

## 🎓 主定理(Axiom Forge 的"研究产物")

**Theorem 5.1 (Impossibility)**: No Shapley attribution based on `v(S) = E[f̂(X)|X_S]` can simultaneously satisfy:

1. **Efficiency**: `Σ_i φ_i = f̂(x)`
2. **Symmetry**: symmetric features get equal attribution
3. **Dummy**: `∂f̂/∂X_i = 0 ⇒ φ_i = 0`
4. **Structural Consistency (新)**: `SI_i(f) > 0 ⇒ ∃x: φ_i(f̂, x) > 0`

**SC** is the only axiom that references the **ground-truth f**, not the predictor f̂. This binds attribution to real-world structure, preventing predictor biases from being silently accepted.

📖 Full theorem + proof: [`training/structural_consistency/AXIOM_SKELETON.md`](training/structural_consistency/AXIOM_SKELETON.md)

---

## 🌳 价值观谱系(6 大类,33 锚)

```
moral        (道德)        universal_kindness / universal_prohibition / general / cultural_specific
interest     (利益)        individual / social / power / equality / longterm
aesthetic    (美学)        symmetry / simplicity / elegance / unity
epistemic    (知识)        truth / consistency / falsifiability / interpretability / universality
practical    (实践)        efficiency / scalability / reproducibility / maintainability / teachability
philosophical (哲学)       kantian_ethics / utilitarianism / rawls / libertarian / phenomenology / virtue_ethics / pragmatism / existentialism
```

**3 锚 (empirical / philosophical / community) 完全平等**——没有任何优先级。

📖 Tree: `./axiom-forge value-tree`

---

## 🔬 3 锚 + 工具中立性原则(项目的元层)

1. **3 锚完全平等** —— empirical / philosophical / community,任何 1 个就够
2. **工具中立** —— CLI 不预设"哪个 axiom 正确",只检索 KB
3. **价值由用户带** —— 不同 planner 选不同锚,产出不同 axiom,没有优劣
4. **先探索后深挖** —— breadth-first,不是 depth-first
5. **探索 → 深挖** 不是对立, 是顺序

---

## ⚠️ 重要:这**不是**微调过的模型

| 状态 | 详情 |
|---|---|
| ✅ KB 数据 | 85 节点 + 63 关系(手写,基于 13 篇 SHAP + Thomson 两书) |
| ✅ CLI 工具 | 8 个命令(纯 stdlib + httpx) |
| ✅ M3 集成 | ask / explore-anchor / validate(调用 M3 API,简化版 RAG) |
| ❌ LoRA 微调 | **没有**——v0.4 计划 |
| ❌ 本地 base model | **没有**——v0.4 计划 |
| ❌ Embedding 模型 | **没有**——CLI 用加权关键词 |

**v0.3-alpha 是"工具 + KB + Skill (RAG)"**,**不是**"训练好的模型"。

---

## 🔄 复现 / 贡献

`kb/REPRODUCTION/` 有 3 个任务(提新 axiom / 找反例 / 加 value_anchor)+ 评估标准。

任何人跑 `axiom-forge` + 写新节点 JSON,都可贡献到 KB。

---

## 📜 License

MIT. (Author attribution pending user decision.)

---

## 📚 文献谱系(13 篇 SHAP + Thomson 两书)

8 篇 SHAP 主线: [L17] / [STY17] / [SY19] / [J19] / [H20] / [H21] / [K20] / [C21]
5 篇参考: [O72] / [LC01] / [OP17] / [O24] / [L24]
2 本 Thomson: [Thomson 2023] / [Laslier 2019]
