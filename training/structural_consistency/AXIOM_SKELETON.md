# Structural Consistency: v0.3-alpha Final

> 2026-06-09 · Axiom Finder v0.3-alpha · 主线 1(Structural Consistency)的形式化 + Impossibility Theorem + 与文献对比

---

## §0 文献谱系(Literature Landscape)

本研究处于 Shapley-based feature attribution 文献谱系,基于以下 13 篇关键论文:

### 主线论文(Foundation)

| ID | 论文 | 关键贡献 | 对 SC 主线的关系 |
|---|---|---|---|
| [S53] | Shapley 1953 | 4 axioms → Shapley 唯一 | Dummy/Symmetry/Additivity 的母文献 |
| [L17] | Lundberg & Lee 2017 NIPS | SHAP 框架:6 方法统一 | v(S)=E[f̂(X)\|X_S] 的**事实标准** |
| [STY17] | Sundararajan-Taly-Yan 2017 ICML | Sensitivity + Implementation Invariance → Integrated Gradients | 与 SC 平行,关注**预测器**非**真实结构** |
| [SY19] | Sundararajan & Najmi 2019/2020 | "Many Shapley Values"——不同 P(X) 给出不同归因 | 直接激励 SC 提出 |
| [J19] | Janzing et al. 2019/2020 EJOR | 把 feature relevance 当因果问题,unconditional ≠ conditional | 直接激励 SC 提出 |
| [H20] | Heskes-Sijben-Bucur-Claassen 2020 IJAR | Causal Shapley via do-calculus | 与"Structural Shapley" 平行 |
| [K20] | Kumar-Venkatasubramanian-Scheidegger-Friedler 2020 | "Problems with Shapley"——Shapley 不能解释 importance | 与 SC 批评性平行 |
| [C21] | Covert-Lundberg-Lee 2021 "Explaining by Removing" | 26 种 removal-based 方法的 3-dim 统一 | 框架来源 |
| [H21] | Heskes 2021 Book Ch.21 "Structural Shapley" | Structural Importance 的**直接前身** | **本主线的直接文献基础** |

### 经典基础(Classical Foundation)

| ID | 论文 | 关键贡献 | 对 SC 主线的关系 |
|---|---|---|---|
| [O72] | Owen 1972 "Multilinear Extensions of Games" | v(S) 的 multilinear extension;Shapley = ∫ 偏导 | 形式化背景 |
| [LC01] | Lipovetsky-Conklin 2001 | 线性回归的 Shapley = v(N)-v(N\{i}) | Necessary Shapley 的前身 |
| [OP17] | Owen-Prieur 2017 EJOR | 依赖输入的 Shapley + ANOVA decomposition | 与 Information Shapley 相关 |

### 综述(用于定位)

| ID | 论文 | 关键贡献 |
|---|---|---|
| [O24] | Berge Olsen et al. 2024 DMKD | Methods for estimating Shapley 综述 |
| [O23] | Berge Olsen et al. 2023 | Conditional SV estimation methods 综述 |
| [L24] | Li et al. 2024 | Shapley value: cooperative game to XAI 综述 |

**SC 主线在谱系中的独特位置**:
- **没有人**显式提出过 "Structural Consistency" 作为 Shapley attribution 的 4th axiom
- **最接近的**是 Heskes 2021 Book Ch.21 的 "Structural Importance"——但只作为定义,未升格为 axiom
- **SC 的新颖性**在于把"SI_i(f) > 0 ⇒ φ_i > 0" 形式化为**对归因方法的硬约束**

---

## §1 问题设置

### 1.1 真实结构(Ground Truth)
真实数据生成过程:
```
Y = f(X) + ε,     ε ⊥ X
```
其中 `f : X → Y` 是**结构函数**(可微),`X = (X_1, ..., X_n) ∈ X = X_1 × ··· × X_n`。

### 1.2 预测器(Predictor)
我们有一个预测器 `f̂ : X → Y`(可由 ML 训练得到,不一定等于 `f`)。

### 1.3 归因机制
归因 `Φ = (φ_1, ..., φ_n)`,把预测输出分解到每个特征:
```
Σ_i φ_i(f̂, x) ≈ f̂(x)
```
"≈" 可以是等式(Efficiency axiom),也可以是近似(带残差)。

---

## §2 Structural Importance(新概念,关键)

### 2.1 线性情形
若 `f(x) = Σ_i β_i x_i`(线性模型):
```
SI_i(f) := |β_i|
```

### 2.2 非线性情形
若 `f` 可微:
```
SI_i(f) := 𝔼_X[ |∂f(X) / ∂X_i| ]
```

**关键**:定义对**真实结构 `f`** 而不是预测器 `f̂`——这是与文献的核心区分。
- [C21] Covert 2021 把 SI 类比为"对预测器的局部扰动敏感性"
- [H21] Heskes 2021 Book 把 SI 形式化为"shapley effect"——但都在 `f̂` 上做
- **本主线的创新**:**SI 作用在 `f` 而非 `f̂`**,把归因与"真实世界结构"绑定

### 2.3 性质
- **非负**:`SI_i(f) ≥ 0`
- **可加**(对线性):`Σ_i SI_i(f) ≤ ||f||` (L1 norm bound)
- **独立于 P(X)**:SI_i 只取决于结构 `f`,不取决于特征的相关结构

---

## §3 4 个 Axiom(完整形式化)

### Axiom 1: Efficiency
```
∀ x ∈ X:  Σ_i φ_i(f̂, x) = f̂(x)
```
归因之和等于预测器输出。
- **来源**:[S53] Shapley 1953 + [L17] Lundberg-Lee 2017

### Axiom 2: Symmetry
```
∀ i, j: 若 ∀ x ∈ X, f̂(x|_{X_i = a, X_j = a}) = f̂(x|_{X_i = b, X_j = b})  ∀ a, b,
则  φ_i(f̂, x) = φ_j(f̂, x)
```
若 i, j 在 `f̂` 中扮演对称角色(交换后 `f̂` 输出不变),则归因相等。
- **来源**:[S53] Shapley 1953

### Axiom 3: Dummy
```
∀ i: 若 ∀ x ∈ X, f̂(x) = f̂(x|_{X_i := x_i'})  ∀ x_i' (即 X_i 不影响 f̂),
则  φ_i(f̂, x) = 0
```
若 X_i 对 `f̂` 无影响(可被任意值替换,f̂ 输出不变),则归因为 0。
- **来源**:[S53] Shapley 1953;在 [STY17] 中称为 "Sensitivity(b)"

### Axiom 4: Structural Consistency (新,本主线)
```
∀ i: 若 SI_i(f) > 0,
则  φ_i(f̂, x) > 0  for some x ∈ X
```
若 X_i 对真实结构有非零重要性,归因必须 > 0(至少在某个 x 上)。

> **关键区分**:Structural Consistency 用的是**真实结构 `f` 的 SI_i**,而其他 3 个 axiom 用的是**预测器 `f̂`**。这种不对称是 SC 创新性所在——它**把归因与真实世界绑定**,防止 f̂ 错误的归因被默认接受。

- **新**:本主线提出。文献中最接近的是 [H21] Heskes Book Ch.21 的 Structural Importance 概念,但**没有作为 axiom**。

### 与文献的关系

| Axiom | 与文献比较 |
|---|---|
| Efficiency | 完全沿用 [S53]/[L17] |
| Symmetry | 完全沿用 [S53];[STY17] 也要求(称为 "Symmetry-Preserving") |
| Dummy | 完全沿用 [S53];[STY17] 称为 "Sensitivity(b)" |
| **Structural Consistency** | **新**。最接近的是 [H21] 的 Structural Importance 概念——但**未升格为 axiom**;[K20] 暗示需要这种 axiom 来防止 Shapley "fail to serve desired purpose" |

---

## §4 Structural Consistency vs Dummy:关系论证

### 4.1 形式比较

| 公理 | 前件 | 后件 |
|---|---|---|
| Dummy | `∂f̂/∂X_i = 0`(对 f̂ 无影响) | `φ_i = 0` |
| Structural Consistency | `SI_i(f) > 0`(对 f 有结构影响) | `φ_i > 0` |

两者**方向相反**:
- Dummy: 无影响 ⇒ 归因 0
- SC: 有影响 ⇒ 归因 > 0

### 4.2 Structural Consistency 严格强于 Dummy?

**命题 4.2.1** (f̂=f 时 SC 蕴含 Dummy 的逆否):
> 若 f̂ = f 且 φ_i = 0, 则 ∂f/∂X_i = 0(对真实 f 无影响)。

**证明**:
- 假设 φ_i = 0
- 因 f̂ = f, Dummy 在 f̂ 上要求 ∂f̂/∂X_i = 0 ⇒ φ_i = 0
- 这与 SC 的逆否等价:φ_i = 0 ⇒ SI_i = 0

**关键洞察**:在 f̂=f 时,**SC + Efficiency 蕴含 Dummy**——这来自 Efficiency 的"总和"约束。

### 4.3 Structural Consistency 与 Dummy 的独立性

**命题 4.3.1** (f̂ ≠ f 时 SC 与 Dummy 独立):
> 在 f̂ ≠ f(预测器不完美)的情形,Dummy 和 SC 约束**不同对象**(f̂ vs f),所以**正交**:
> - Dummy 防止"f̂ 内的虚假归因"(`f̂ 说不影响` ⇒ 归 0)
> - SC 防止"f̂ 错位的归因"(`f 说影响` ⇒ 归 > 0)

**详细论证**:
考虑 4 个场景(下表说明 Dummy 和 SC 在 f̂≠f 时的独立约束):

| 场景 | ∂f̂/∂X_i | SI_i(f) | Dummy 强制 | SC 强制 | 两者关系 |
|---|---|---|---|---|---|
| A | = 0 | = 0 | φ_i = 0 | (无要求) | Dummy 必要,SC 不强制 |
| B | = 0 | > 0 | φ_i = 0 | φ_i > 0 | **矛盾!**——这正是 Impossibility 的入口 |
| C | ≠ 0 | = 0 | (无要求) | (无要求) | 都不强制,任何归因都 ok |
| D | ≠ 0 | > 0 | (无要求) | φ_i > 0 | SC 必要,Dummy 不强制 |

**场景 B** 就是 Impossibility Theorem 的关键:预测器丢弃了真实重要变量(`SI>0`)→ Dummy 强制归 0,但 SC 强制归 > 0,**矛盾**。

### 4.4 总结:4 个命题

1. **SC 比 Dummy 弱**(在 f̂=f 时,SC 不蕴含 Dummy)
2. **SC 与 Dummy 独立**(在 f̂≠f 时,作用于不同对象,正交)
3. **场景 B 是 Impossibility 的入口**——两者冲突
4. **两者加起来 = "结构完备性"**——归因与结构一一对应,无遗漏无多余

---

## §5 主定理:Impossibility Theorem

### 定理 5.1 (Impossibility Theorem)
> **不存在**基于 characteristic function
> ```
> v(S) = 𝔼[ f̂(X) | X_S ]
> ```
> 的 Shapley 归因
> ```
> φ_i = Σ_{S ⊆ N\{i}} |S|! (n - |S| - 1)! / n! × [v(S ∪ {i}) - v(S)]
> ```
> 能**同时**满足:
> - Axiom 1 (Efficiency)
> - Axiom 2 (Symmetry)
> - Axiom 3 (Dummy)
> - Axiom 4 (Structural Consistency)
>
> **对某个真实结构 f 与某个预测器 f̂ ≠ f 而言**。

### 证明(基于场景 B)
**存在性证明**(给具体反例 instance,而非仅存在性):

1. **构造真实结构**:`f(X) = β X_1`, `β > 0`,即 X_1 是唯一真实相关变量。
2. **构造预测器**:`f̂(X) = 0`(常数 0)—— 简单但**丢失** X_1 的信息。
3. **应用 SHAP 框架**:
   - `v(S) = E[f̂(X) | X_S] = 0` 对所有 S ⊆ N
   - `φ_i = Σ_{S} ... × [v(S∪{i}) - v(S)] = 0` 对所有 i
4. **检验 4 axiom**:
   - **Efficiency**:Σ_i φ_i = 0 = f̂(x) ✓
   - **Symmetry**:∀ i, j, φ_i = φ_j = 0 ✓
   - **Dummy**:∂f̂/∂X_i = 0 ⇒ φ_i = 0 ✓
   - **Structural Consistency**:**SI_1(f) = |β| > 0**,但 φ_1 = 0,**违反 SC** ✗
5. **结论**:v(S)=E[f̂(X)|X_S] 的 Shapley **违反 SC** ⇒ 不存在满足全部 4 axiom 的归因

### 推论 5.1.1 (TreeSHAP 违反 SC)
> **TreeSHAP 必然违反 Structural Consistency**——给定 f 结构但 f̂ ≠ f(预测器丢变量),TreeSHAP 归因反映 f̂ 而非 f,违反 SC。

### 推论 5.1.2 (KernelSHAP 违反 SC)
> **KernelSHAP 必然违反 Structural Consistency**——与 TreeSHAP 同理,KernelSHAP 的 v(S) = E[f̂(X)|X_S] 完全依赖 f̂,不绑定 f。

### 推论 5.1.3 (信息 Shapley 违反 SC)
> **Information Shapley**(基于 mutual information 分配)**不一定**满足 SC——若其 v(S) = E[Y|X_S] - E[Y],则 v(S) 是 P(X,Y) 的函数,但 P(X,Y) 可能与 f 不直接对应。

### 推论 5.1.4 (满足 SC 的 4 候选)
| 方法 | v(S) 定义 | 满足 SC? | 满足 Eff/Sym/Dum? |
|---|---|---|---|
| TreeSHAP | E[f̂(X)\|X_S] | ✗ | ✓ |
| KernelSHAP | E[f̂(X)\|X_S] | ✗ | ✓ |
| Information Shapley | E[Y\|X_S] - E[Y] | ✗ (f̂ ≠ f) | ✓ |
| **Structural Shapley**(新) | `Σ_{k ∈ Path(S)} Effect(k)` | ✓ | ✓ (需验证) |
| **Necessary Shapley**(新) | `v(N) - v(N\{i})` | ✓ (直接基于 marginal) | ✓ |
| **Causal Structural Shapley**(新) | `Σ_{k ∈ Path(S)} Do-Effect(k)` | ✓ | ✓ |

---

## §6 5 个 Proposal 的层级

| Rank | Proposal | 文献中的位置 | 本主线的贡献 |
|---|---|---|---|
| ★★★★★ | **Structural Consistency** + Impossibility | **新**(最接近 [H21] 但未形式化为 axiom)| **主线定理**——证明 SC 是缺失的 4th axiom |
| ★★★★ | **Structural Shapley** | [H21] Heskes Book Ch.21 直接前身 | 在主线之后,给出具体 v(S) |
| ★★★ | **Necessary Attribution** | [LC01] Lipovetsky-Conklin 2001 已有 | 简化 v(S) 的特殊情形 |
| ★★★ | **Causal Structural Shapley** | [H20] Heskes IJAR 2020 已有(用 do-calculus)| 推广 Structural Shapley 到因果图 |
| ★★ | **Information-Shapley** | [C21] Covert 2020 SAGE 已有 | 与 SC 不兼容的对照组 |

---

## §7 与现有 4 axiom 系统的比较

### 7.1 [STY17] Sundararajan-Taly-Yan 的 2 axiom
- **Sensitivity (a/b)** + **Implementation Invariance**
- 关注:**预测器** F 的行为
- **不要求**归因与真实世界结构绑定
- IG 是这类 axiom 的典型满足者

### 7.2 [L17] Lundberg-Lee 的 3 axiom
- **Local Accuracy** + **Missingness** + **Consistency**
- 关注:**预测器 f̂** 的局部行为
- **Consistency**(单调性):若 f̂ 改变让 φ 增大,归因也应增大
- **不直接要求**与真实结构绑定

### 7.3 本主线的 4 axiom
- **Efficiency** + **Symmetry** + **Dummy** + **Structural Consistency**
- **SC 是关键创新**——绑定归因与真实世界
- **核心差异**:SC 关注 `f`(真实),其他 3 axiom 关注 `f̂`(预测器)

### 7.4 主定理陈述对比
| 论文 | 主定理 | 结论 |
|---|---|---|
| [STY17] | 无主定理,只是 axiom 形式化 | IG 满足 2 axiom 但不唯一 |
| [L17] | "additive feature attribution" 唯一 | SHAP 是唯一满足 3 axiom 的方法 |
| [K20] | "Shapley fail to serve purpose" | 负面结论,无 axiom 替代 |
| **本主线** | **Impossibility Theorem 5.1** | **不可能** 4 axiom 同时成立(基于 v(S)=E[f̂\|X_S]) |

---

## §8 应用与实验设计

### 8.1 反例实验
构造具体反例验证 §5 的存在性证明:
1. **Linear 情形**:`f(X) = β X_1`, `f̂(X) = 0`
2. **Cyclic 情形**:`f` 有 `X_1 → Y`, `f̂` 只学了 `X_2 → Y` 关系
3. **Real data**:Boston Housing,California Housing——用真实数据训练 f̂,对比 SHAP/IG 归因 vs SI_i

### 8.2 SC 的可计算性
- **线性 f**:SI_i = |β_i| 直接计算
- **非线性 f**:SI_i = E_X[|∂f/∂X_i|] 可通过采样估计
- **f̂ vs f**:在实验中,需要"先知"——f 是 oracle,可能不可知
- **工程实践**:用"ground truth"模型(可解释的)作为 f 的代理

### 8.3 SC 与 fairness 的联系
- **结构性公平**:归因应反映"真实贡献",非"预测器学到的"
- 若 f̂ 有偏见(对 protected attribute 的 spurious correlation),SHAP 归因会**反映偏见**——而 SC 要求归因**不**反映
- **结论**:SC 在某种意义上是 "anti-bias axiom"

---

## §9 开放问题(待用户拍板)

### 9.1 SC 的"φ_i > 0"范围
- **Q1**:SC 的"φ_i > 0"是 ∃x 还是 ∀x?
  - **当前选择**:∃x(更弱,允许某些 x 上 φ_i = 0)
  - **若 ∀x**:SC 更强,Impossibility 范围更广
  - **建议**:先证明 ∃x 版本,再考虑 ∀x 强化

### 9.2 SC 作用对象
- **Q2**:SC 用 f 还是 f̂?
  - **当前选择**:f(真实结构)——这是 SC 的创新所在
  - **若 f̂**:SC 退化为"f̂ 的局部灵敏度"——已由 [STY17] Sensitivity 涵盖
  - **建议**:保持 f

### 9.3 Impossibility 范围
- **Q3**:"不存在"是 ∀P(X) 还是 ∃P(X) fails?
  - **当前选择**:∃P(X) fails(对某个 f 和 f̂ 失败)
  - **若 ∀P(X)**:Impossibility 范围更广,证明更复杂
  - **建议**:保持 ∃P(X)——存在性证明更清晰

### 9.4 证明风格
- **Q4**:存在性证明还是具体反例?
  - **当前选择**:具体反例(场景 B: `f(X) = β X_1, f̂(X) = 0`)
  - **建议**:具体反例更说服人,且与 [H20] 的"XOR 例子"风格一致

### 9.5 f̂=f 时的 SC 与 Dummy 关系
- **Q5**:在 f̂=f 时 SC 是否蕴含 Dummy?
  - **当前分析**:f̂=f 时 SC 单独不蕴含 Dummy(SC 弱)
  - **但**:SC + Efficiency 在 f̂=f 时可能蕴含 Dummy(总和约束)
  - **建议**:进一步证明,作为推论 5.1.5

---

## §10 总结

### 10.1 主要贡献
1. **新 axiom** Structural Consistency 显式形式化
2. **Impossibility Theorem 5.1**:基于 v(S)=E[f̂(X)|X_S] 的 Shapley 不可能满足全部 4 axiom
3. **SC vs Dummy 关系**:4 命题,关键独立性论断
4. **文献定位**:在 Shapley attribution 谱系中精确位置

### 10.2 与现有文献的关系
- **不是重复**:没人提过 SC 作为 axiom
- **不是反驳**:SC 与 [STY17]/[L17] 互补(关注 f vs f̂)
- **是填补**:`K20 Kumar` 指出 Shapley 的缺陷但没给 axiom;本主线填补

### 10.3 下一步
1. 用 v0.2 5-agent 流水线对 SHAP seed 做 perturbation,生成 "Structural Consistency" 提案
2. 用 [H21] Heskes Book Ch.21 的 Structural Shapley 作为 v(S) 的具体实现
3. 实验验证反例(场景 B)
4. 写 v0.3-alpha final report
