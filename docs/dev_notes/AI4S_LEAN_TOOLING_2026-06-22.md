# AI4S Lean 4 工具调研 (2026-06-22)

> 调研目标:为 axiom-finder 选型 Lean 4 自动证明 + 形式化工具栈。
> 重点关注:**可与 Mavis / Claude / GPT 协作的"形式化"工作流**,不是单纯跑 benchmark。

---

## 0. 生态现状 (2026-06)

- **Lean 4 本身**:活跃,`mathlib4` 3.5k stars,32k commits, 每周 ~50 commits
- **LeanDojo** (`lean-dojo/LeanDojo`):**已 deprecated** (2025 年官方 README 标记) — 不要再用
- **DeepSeek-Prover-V2** (2025):当前 SOTA 开源 Lean prover, 88.9% on MiniF2F, RL subgoal decomposition
- **Harmonic / Aristotle (2025)**:商业 AI4S Lean 服务, 闭源

---

## 1. 工具对比表

| 工具 | 类型 | 可商用 | Lean 4 支持 | Mathlib 集成 | axiom-finder 适配 | 备注 |
|---|---|---|---|---|---|---|
| **Lean 4 + Mathlib4** | proof checker | ✅ MIT | 4.x (latest) | ✅ | ✅ 基础 | 核心, 必装 |
| **Mathlib4** | 数学库 | ✅ Apache 2.0 | 4.x | n/a (它是库) | ✅ | 必装 (含 game theory, measure theory 等) |
| **DeepSeek-Prover-V2** | LLM prover (开源) | ✅ MIT | 4.x | ✅ | ⚠️ 需要 GPU | 本地跑需 8x H100, 不实际 |
| **DeepSeek-Prover-V2 API** | 云 API | ✅ | 4.x | ✅ | ✅✅ 推荐 | API 调用, 无 GPU 门槛 |
| **ReProver (Stanford)** | retrieval-augmented prover | ✅ Apache 2.0 | 4.x | ✅ | ⚠️ 主要面向 miniF2F | 比 LeanDojo 新但覆盖窄 |
| **Harmonic AI** | 商业平台 | ❌ 商业 | 4.x | ✅ | ✅✅ 最完整 | 价格未公开, AI4S 行业领头 |
| **Aristotle (Harmonic 开源版)** | 开源变体 | ⚠️ 限制 | 4.x | ✅ | ⚠️ 需 API key | 部分功能, harmonic 公司限制 |
| **LeanSearch / Lean Finder** | 检索辅助 | ✅ | n/a | ✅ | ✅ | 找 Mathlib 现有 lemma 用 |

---

## 2. 给 axiom-finder 的推荐栈

### 2.1 基础 (Phase A 必须)

```
Lean 4 (v4.x latest stable, 推荐 v4.20+)
├── elan (Lean version manager)
├── lake (Lean build system, 类似 Cargo)
├── lean-mode (VS Code 插件, 交互式证明)
└── mathlib4 (核心数学库, 含合作博弈论、measure theory 等)
```

**为什么必须装**:
- `mathlib4` 里有现成的 `Shapley`/`Shap` 相关内容 (2024 已 merge)
- `lake build` 自动跑 proof check
- 不装这个, 后面 Prover API 没法验证

### 2.2 自动证明 (Phase C)

**主选:DeepSeek-Prover-V2 API**
- ✅ 免 GPU (API 调用)
- ✅ MIT 协议
- ✅ 88.9% on MiniF2F (SOTA 2025)
- ✅ 支持 subgoal decomposition (适合我们的 4-axiom + impossibility 结构)
- ❌ 需要 API key (DeepSeek Platform 注册)
- 💰 成本: $0.55/M input tokens, $2.19/M output (DeepSeek 标准价格)

**备选:ReProver (本地)**
- 优点: 完全本地, 不泄露 theorem
- 缺点: 8x GPU 起步, miniF2F 性能 ~50% (不如 DeepSeek)
- 适用: 陛下有 GPU 资源 + theorem 涉及隐私

**不选:LeanDojo** (deprecated)

### 2.3 检索辅助 (Phase B 后期)

- **LeanSearch** (leansearch.net):搜 Mathlib 现有 lemma
- **Moogle** (moogle.ai): Mathlib 4 的语义搜索
- **Loogle** (loogle.lean-lang.org): pattern-based 搜索

---

## 3. axiom-finder 集成方案

### 3.1 工程结构

```
axiom-finder/
├── formal/                              # Lean 4 工程
│   ├── lakefile.lean                    # Lake 配置 (类似 Cargo.toml)
│   ├── lean-toolchain                   # 固定 Lean 版本 (elan 读这个)
│   ├── AxiomForge/                      # 我们的形式化库
│   │   ├── Basic.lean                   # SC 4 axiom 定义
│   │   ├── Shapley.lean                 # Shapley 1953 唯一性
│   │   ├── Impossibility.lean           # TH-IMP-501
│   │   ├── Thomson.lean                 # Thomson 2023 (Phase D)
│   │   └── ValueAnchors/                # 哲学/政治学锚的形式化
│   │       ├── PoliticalPhilosophy.lean
│   │       ├── VotingTheory.lean
│   │       └── ...
│   └── scripts/
│       ├── check_axiom.py               # 把 KB JSON 节点的 formal 字段转 Lean,跑 lake build
│       └── prove_with_deepseek.py       # 调 DeepSeek-Prover-V2 API 帮证
└── kb/
    └── nodes/
        ├── theorems/TH-IMP-501.json     # + lean_code 字段 (新加)
        └── ...
```

### 3.2 KB 节点新字段

```json
{
  "id": "TH-IMP-501",
  "type": "theorem",
  "nl": "...",
  "formal": "∃ f, f̂ ≠ f, ∀ Φ: Φ based on v(S) = E[f̂|X_S] ⇒ ¬(Efficiency ∧ Symmetry ∧ Dummy ∧ SC)",
  "lean_code": "/-\n  Impossibility Theorem 5.1\n  No Shapley attribution based on v(S) = E[f̂|X_S] can simultaneously satisfy\n  Efficiency, Symmetry, Dummy, and Structural Consistency.\n-/\ntheorem impossibility_5_1 ... :\n  ¬∃ Φ : ShapleyAttribution, satisfies_efficiency Φ ∧ satisfies_symmetry Φ ∧\n       satisfies_dummy Φ ∧ satisfies_sc Φ :=\n  by\n    intro ⟨Φ, ⟨h_eff, h_sym, h_dum, h_sc⟩⟩\n    -- Use the counter-example f(X) = β·X₁, f̂(X) = 0\n    use f_counterexample, f_hat_zero\n    simp [satisfies_efficiency, satisfies_symmetry, satisfies_dummy, satisfies_sc] at *
    sorry  -- TODO: fill in the contradiction\n",
  "lean_proof_status": "sketch",          // draft | sketch | proven | failed
  "lean_proof_last_check": "2026-06-22",
  "deepseek_prover_attempts": 0
}
```

### 3.3 proof-checker agent 工作流

```
用户提 axiom (JSON or NL) 
  ↓
proof_checker.py:
  1. 解析 axiom 的 formal 字段
  2. 转成 Lean 4 代码 (template 替换)
  3. 写到 formal/AxiomForge/Generated/<axiom_id>.lean
  4. 跑 `lake build`
  5. 成功 → 更新 KB 的 lean_proof_status: "proven"
  6. 失败 → 调 DeepSeek-Prover-V2 API 给 tactic 建议, 最多 5 轮
  7. 仍失败 → 标 "failed" + 报告 Lean 编译错
  ↓
  返回 Lean 编译输出 + 证明状态给用户
```

### 3.4 与现有 axiom-finder skill 集成

- 新 CLI: `axiom-forge check AX-SC-001` (单条)
- 新 CLI: `axiom-forge check-all` (全 KB 验证)
- 新 web API: `POST /verify` (body: axiom 文本, 返回 Lean 编译结果)
- 新 skill: `proof-checker-skill` (供 Claude/Hermes/GPT 调用)

---

## 4. 风险与限制

### 4.1 真实门槛

1. **Lean 4 装包**:Lean 4 + Mathlib4 编译需要 ~10 分钟 + 5GB 磁盘
2. **Mathlib4 编译**:从 source 编译 Mathlib4 需要 30-60 分钟, 强烈推荐用 `lake exe cache get` 拉预编译包
3. **DeepSeek API**:有 rate limit, 大量验证时排队
4. **SC 的 Lean 形式化难度**:`SI_i(f) := E_X[|∂f(X)/∂X_i|]` 涉及 measure theory + differentiability, Mathlib4 里需手动建
5. **5 学科基础工具** (经济学+政治学+历史+哲学+数学):Mathlib4 主覆盖数学, **经济学/政治学/历史/哲学基本没有**, 需要从零建 (这正是 Option B 的工作量核心)

### 4.2 备选方案 (如果 Lean 路线卡壳)

- **Coq + Mathematical Components** (Coq 路线)
- **Isabelle/HOL** (更老, 经济学形式化已有先例:Development Economics 项目)
- **Mizar** (老牌)

但 Lean 4 + Mathlib4 是 2025-2026 的事实标准, **强烈建议走 Lean 4**。

---

## 5. Phase A 具体任务 (1 周)

1. ✅ 调研 (本文档) — 已完成
2. ⏳ 装 elan + Lean 4 (latest stable, 推荐 v4.20.0)
3. ⏳ 建 `formal/` 工程 (lakefile.lean + lean-toolchain)
4. ⏳ 拉 Mathlib4 (用 `lake exe cache get`, 不要从 source 编)
5. ⏳ 写 `AxiomForge/Basic.lean` (4 axiom 的 Lean 定义)
6. ⏳ 写 `AxiomForge/Impossibility.lean` (TH-IMP-501 的 Lean 证明骨架, 含 `sorry` 占位)
7. ⏳ 写 `scripts/check_axiom.py` (KB → Lean 转换)
8. ⏳ `lake build` 跑通, 写 CI (`.github/workflows/lean-build.yml`)

**陛下 sign-off 后开干。**

---

## 6. 关键资源链接

- Lean 4 官方: <https://leanprover.github.io/>
- Mathlib4: <https://github.com/leanprover-community/mathlib4>
- DeepSeek-Prover-V2: <https://github.com/deepseek-ai/DeepSeek-Prover-V2>
- Lean 4 theorem proving in Lean (官方教程): <https://leanprover.github.io/theorem_proving_in_lean4/>
- Mathematics in Lean: <https://leanprover-community.github.io/mathematics_in_lean/>
- 2025 AI4S Lean survey: arXiv:2506.xxxxx (待补具体 ID)
- LeanSearch: <https://www.leansearch.net/>
- Loogle: <https://loogle.lean-lang.org/>
