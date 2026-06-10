# PerturbationMemo: AX-STRUCTURAL-CONSISTENCY-001
_Handcrafted 2026-06-09 · v0.3-alpha final candidate_

> 来源:perturbation PERT-STRUCTURAL on L17-CHAR-FN(SHAP 的 predictive v(S))
> 文献谱系:L17(SHAP) → H20(Heskes Causal Shapley)→ H21(Structural Shapley)→ **本主线 (AX-NEW)**

---

## 1. 种子文献(Lundberg & Lee 2017 SHAP)
... (同前,省略)

## 2. 扰动方案
- **target**: `L17-CHAR-FN`(SHAP 的 characteristic function)
- **type**: `PERT-STRUCTURAL` —— 把 v(S) 从 predictive 改为 structural
- **rationale**:SHAP 的 v(S) = E[f̂(X)|X_S] 完全依赖预测器 f̂;当 f̂ ≠ f(真实结构),归因反映 f̂ 而非 f。这正是 [K20] Kumar 2020 "Problems with Shapley" 批评的核心——归因 ≠ 重要性。

## 3. Value 评分(8 维,与 v0.2 流水线对齐)
| Criterion | Instance | Before (SHAP) | After (Structural) | Δ | Reasoning |
|---|---|---|---|---|---|
| user-explainable | V-EXPLAIN-USER | 0.85 | **0.90** | +0.05 | Structural v_s(S) 反映"真实路径效应",用户更能理解"为什么这个特征重要" |
| computational-feasibility | V-COMPUT-FEAS | 0.55 | **0.30** | -0.25 | Structural v_s 需要 DAG,在高维时 NP-hard(需要指定因果图) |
| additivity | V-ADDITIVITY | 0.90 | **0.90** | 0 | Additivity(总和) 保留(SC 是 per-feature 约束,不影响总和) |
| consistency | V-CONSISTENCY | 0.90 | **0.95** | +0.05 | Structural v_s 不会因 f̂ 变化而改变,稳定性更好 |
| symmetry | V-SYMMETRY | 0.85 | **0.85** | 0 | Symmetry 在因果图无差异时仍成立 |
| capability | V-CAPABILITY | 0.75 | **0.85** | +0.10 | Structural v_s 拓展 Sen-style capability——可识别"真实贡献",对弱势群体更重要 |
| continuity | V-CONTINUITY | 0.70 | **0.80** | +0.10 | Structural v_s 不依赖 P(X) 的连续性,只依赖 DAG 和 f 的连续性 |
| personalized-explanation | V-EXPLAIN-PERSONALIZED | 0.70 | **0.80** | +0.10 | Structural v_s 给出"因果路径",每个 patient 故事更清晰 |

**加权 Δ** = (0.05 - 0.25 + 0 + 0.05 + 0 + 0.10 + 0.10 + 0.10) / 8 = +0.019 → **net positive 0.019**

## 4. ★ 新公理(Structural Consistency)

**ID**: `AX-STRUCTURAL-CONSISTENCY-001`

### 4.1 自然语言陈述
> **Structural Consistency (SC)**: For any feature i, if the structural importance SI_i(f) of feature i in the ground-truth data-generating process f is strictly positive, then the attribution φ_i(f̂, x) must be strictly positive for some input x ∈ X.
>
> 直觉:如果 X_i 对真实世界结构"有影响"(SI_i > 0),那么归因不能全部为 0——归因必须**至少在某些 x** 上反映这种影响。

### 4.2 形式化

```
Axiom 4 (Structural Consistency):
∀ i ∈ N: [ SI_i(f) > 0 ] ⟹ [ ∃ x ∈ X : φ_i(f̂, x) > 0 ]

where:
- N = {1, ..., n} is the feature set
- f : X → Y is the ground-truth data-generating function
- f̂ : X → Y is the predictor (may differ from f)
- φ_i(f̂, x) is the attribution to feature i for input x under predictor f̂
- SI_i(f) is the Structural Importance of feature i in f:
    SI_i(f) = |β_i|                              (linear: f = Σ_i β_i X_i)
    SI_i(f) = E_{X}[ |∂f(X)/∂X_i| ]             (differentiable)
```

### 4.3 关键术语对齐表
| 自然语言 | 形式化符号 | 约束 |
|---|---|---|
| 真实结构函数 | f | given, ground truth |
| 预测器 | f̂ | trained, may ≠ f |
| 特征 i | i ∈ N | index |
| 归因 | φ_i | Shapley value or any solution concept |
| 结构重要性 | SI_i | non-negative, depends only on f |
| 至少存在 | ∃ | existential quantifier |
| 严格大于 | > 0 | strict inequality |

### 4.4 Notation Legend
```
N         : feature set, |N| = n
X         : feature space, X = X_1 × ··· × X_n
Y         : response space (e.g., R)
f         : ground-truth function X → Y
f̂        : predictor X → Y
Φ        : (φ_1, ..., φ_n) attribution vector
SI_i(f)   : Structural Importance of feature i in f (non-negative)
v(S)      : characteristic function S → R
```

### 4.5 SC 与现有 3 Axiom 的关系表
| Axiom | 前件 | 后件 | 作用对象 |
|---|---|---|---|
| Efficiency | (always) | Σ_i φ_i = f̂(x) | f̂ |
| Symmetry | f̂ 不变 | φ_i = φ_j | f̂ |
| Dummy | ∂f̂/∂X_i = 0 | φ_i = 0 | f̂ |
| **Structural Consistency** | **SI_i(f) > 0** | **∃x: φ_i > 0** | **f** |

> **关键不对称**:SC 关注 `f`(真实),其他 3 axiom 关注 `f̂`(预测器)

### 4.6 为什么这是公理(per DIKT-INJECTION 的"user-facing"标准)
- **绑定归因与真实世界**:不依赖 f̂ 的内部分布
- **公平性意义**:若 f̂ 有偏见(对 protected attribute 的 spurious correlation),SC 要求 φ 不完全反映
- **可证伪性**:给定 f,可计算 SI_i,然后检验 ∃x: φ_i > 0
- **简洁性**:1 个 quantifier (∃x),不需要 ∀x(更强也更难满足)

## 5. 主定理:Impossibility Theorem 5.1

### 5.1 定理陈述
> **Theorem 5.1 (Impossibility)**: There is no Shapley attribution based on characteristic function
> ```
> v(S) = E_{X_{S̄} | X_S = x_S}[ f̂(X_S, X_{S̄}) ]
> ```
> that can simultaneously satisfy all four axioms:
> 1. Efficiency
> 2. Symmetry
> 3. Dummy
> 4. Structural Consistency
>
> for some ground-truth f and predictor f̂ ≠ f.

### 5.2 证明(具体反例)

**构造反例(场景 B)**:
- 真实结构:f(X) = β X_1, β > 0,即 X_1 是唯一真实相关变量
- 预测器:f̂(X) = 0(常数预测,完全丢失 X_1 信息)
- 真实结构重要性:SI_1(f) = |β| > 0;SI_2(f) = ... = SI_n(f) = 0

**计算 SHAP 归因**:
- v(S) = E[f̂(X)|X_S] = E[0|X_S] = 0, ∀ S ⊆ N
- φ_i = Σ_{S ⊆ N\{i}} |S|!(n-|S|-1)!/n! × [v(S∪{i}) - v(S)] = 0, ∀ i

**检验 4 axiom**:
| Axiom | 检验 | 结果 |
|---|---|---|
| Efficiency | Σ_i φ_i = 0 = f̂(x) | ✓ |
| Symmetry | φ_i = φ_j = 0 | ✓ |
| Dummy | ∂f̂/∂X_i = 0 ⇒ φ_i = 0 | ✓ |
| **Structural Consistency** | **SI_1(f) = β > 0, but φ_1 = 0** | **✗ 违反** |

**结论**:基于 v(S)=E[f̂(X)|X_S] 的 Shapley 归因,违反 SC ⇒ Impossibility 成立 □

### 5.3 推论

**Corollary 5.3.1 (TreeSHAP 违反 SC)**: TreeSHAP uses the same v(S) = E[f̂(X)|X_S] approximation (with tree-based sampling); therefore TreeSHAP violates SC when f̂ ≠ f.

**Corollary 5.3.2 (KernelSHAP 违反 SC)**: Same as 5.3.1 — KernelSHAP violates SC when f̂ ≠ f.

**Corollary 5.3.3 (Information Shapley 违反 SC)**: Information Shapley uses v(S) = E[Y|X_S] - E[Y], which depends on the joint P(X,Y). When f̂ ≠ f, v(S) may not reflect SI_i(f) → SC violated.

**Corollary 5.3.4 (满足 SC 的候选)**:
- **Structural Shapley**: v_s(S) = Σ_{k ∈ Path(S)} Effect(k) — only depends on DAG and f
- **Necessary Shapley**: φ_i = v(N) - v(N\{i}) — direct marginal contribution
- **Causal Structural Shapley**: v_cs(S) = Σ_{k ∈ Path(S)} Do-Effect(k) — Pearl do-calculus

## 6. SC vs Dummy:独立公理论证

### 6.1 形式比较
| 公理 | 前件 | 后件 |
|---|---|---|
| Dummy | ∂f̂/∂X_i = 0 (f̂ 角度) | φ_i = 0 |
| SC | SI_i(f) > 0 (f 角度) | ∃x: φ_i > 0 |

两者**方向相反**,**对象不同**:
- Dummy: 约束 φ_i 上界(φ_i 不可 > 0 若 f̂ 说不影响)
- SC: 约束 φ_i 下界(φ_i 必须 > 0 若 f 说影响)

### 6.2 4 命题

**Prop 6.2.1 (f̂ = f 时 SC 不蕴含 Dummy)**: 若 f̂ = f 且 SC 满足,Dummy 不自动满足——SC 弱(只要求 SI>0 ⇒ φ>0,不要求 SI=0 ⇒ φ=0)。

**Prop 6.2.2 (f̂ ≠ f 时 SC 与 Dummy 独立)**: Dummy 约束 f̂(对 f̂ 不影响 ⇒ φ=0),SC 约束 f(对 f 影响 ⇒ φ>0)。两者作用不同对象,正交。

**Prop 6.2.3 (场景 B 是 Impossibility 入口)**: 当 f̂ ≠ f 且 SI_i(f) > 0 但 ∂f̂/∂X_i = 0(预测器丢变量),Dummy 要求 φ_i = 0,SC 要求 ∃x: φ_i > 0,**矛盾**——这正是 Impossibility 的核心。

**Prop 6.2.4 (SC + Dummy = 结构完备性)**: "Dummy 防止过度归因" + "SC 防止归因错位" = "归因与结构一一对应,无遗漏无多余"。

### 6.3 实际场景表
| 场景 | ∂f̂/∂X_i | SI_i(f) | Dummy 强制 | SC 强制 | 两者关系 |
|---|---|---|---|---|---|
| A | = 0 | = 0 | φ_i = 0 | (无) | Dummy 必要,SC 不强制 |
| **B** | **= 0** | **> 0** | **φ_i = 0** | **∃x: φ_i > 0** | **矛盾!→ Impossibility 入口** |
| C | ≠ 0 | = 0 | (无) | (无) | 都不强制,任意 φ 都 ok |
| D | ≠ 0 | > 0 | (无) | ∃x: φ_i > 0 | SC 必要 |

## 7. 5 个 Proposal 的 SOTA 定位
| Rank | Proposal | 文献中的位置 | 状态 |
|---|---|---|---|
| ★★★★★ | **SC + Impossibility** | 没人提过 SC axiom;Heskes 2021 Book Ch.21 有 SI 概念但未升格 | **本主线** |
| ★★★★ | **Structural Shapley** | Heskes 2021 Book Ch.21 直接前身 | 已有,本主线增强 |
| ★★★ | **Necessary Attribution** | Lipovetsky-Conklin 2001 + Owen 1972 | 已有,本主线简化情形 |
| ★★★ | **Causal-Structural Shapley** | Heskes IJAR 2020 + Frye 2020 | 已有,本主线推广 |
| ★★ | **Information-Shapley** | Covert 2020 SAGE | 已有,与 SC 不兼容 |

## 8. 实验设计(可执行)
1. **反例验证**:Boston Housing 数据,训练 f̂ = 常数 0,验证 SHAP 归因 = 0 而 SI_1 > 0 → SC 违反 ✓
2. **satisfying 方法对比**:在 Boston Housing 上跑 SHAP vs Structural Shapley vs Necessary Shapley,比较归因质量
3. **公平性测试**:Adult Income 数据,训练 f̂ 用 gender 作 feature,验证 SC 防止归因偏向 gender

## 9. 关键引用(主定理需要)
- [S53] Shapley 1953, "A Value for n-Person Games" — 4 axioms 母文献
- [L17] Lundberg & Lee 2017, NeurIPS — SHAP 框架
- [J19] Janzing, Minorics, Blöbaum 2019/2020, EJOR — Feature relevance as causal problem
- [SY19] Sundararajan & Najmi 2019/2020 — Many Shapley Values
- [H20] Heskes et al. 2020, IJAR — Causal Shapley Values
- [H21] Heskes 2021, Book Ch.21 — Structural Shapley Values(SC 直接前身)
- [K20] Kumar et al. 2020 — Problems with Shapley-value-based explanations
- [C21] Covert, Lundberg, Lee 2021 — Explaining by Removing(unified framework)
- [OP17] Owen & Prieur 2017, EJOR — Shapley for dependent inputs
- [O72] Owen 1972, Management Science — Multilinear Extensions of Games
- [LC01] Lipovetsky & Conklin 2001 — Analysis of regression in game theory approach
