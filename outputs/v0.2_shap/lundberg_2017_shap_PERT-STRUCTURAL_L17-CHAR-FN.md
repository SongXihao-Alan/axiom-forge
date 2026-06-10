# PerturbationMemo: lundberg_2017_shap
_Generated: 2026-06-09T06:39:26.813227Z_

## 1. 种子文献
# A Unified Approach to Interpreting Model Predictions (SHAP)
Authors: Scott M. Lundberg, Su-In Lee
Year: 2017, Venue: NeurIPS
ID: lundberg_2017_shap
Linage: in=['shapley_1953', 'ribeiro_2016_lime', 'lipovetsky_conklin_2001'], out=['aas_2021_dependent', 'sundararajan_najmi_2019_many', 'jan_o_prieur_2017'], branch=shapley_attribution_mainline

## Axioms
- **L17-LA** (local_accuracy): Local accuracy: f(x) = φ_0 + Σ_i φ_i, where φ_0 is the expected model output on background data, and φ_i is the attribution to feature i.
- **L17-MISS** (missingness): Missingness: φ_i = 0 when feature i is missing from input. Missingness requires that missing features receive no attribution.
- **L17-CONS** (consistency): Consistency: if f changes to f̂ such that f̂(x_S) - f̂(x_S \ {i}) ≥ f(x_S) - f(x_S \ {i}) for all subsets S, then φ_i(f̂, x) ≥ φ_i(f, x).

## Assumptions
- **L17-CHAR-FN** (characteristic_function): v(S) = E[f(X) | X_S] for S ⊆ N (conditional expectation on observed features)
- **L17-FAIRNESS** (additive_decomposition): Attribution is an additive decomposition of model output minus baseline.

## Theorems
- **L17-THM1**: Theorem 1: The class of additive feature attribution methods corresponds exactly to the class of additive games in cooperative game theory. Shapley values are the unique solution that satisfies local accuracy, missingness, and consistency.
  depends on: L17-LA, L17-MISS, L17-CONS
- **L17-THM2**: Theorem 2: KernelSHAP (linearized LIME) converges to Shapley values as sampling weight converges to Shapley kernel weights π_Sh(S) = (d-1) / (|S| (d-|S|) choose |S|).
  depends on: L17-THM1

## Propositions
- **L17-UNIFY** (argued): LIME, DeepLIFT, LRP, QII, Shapley sampling, Classic Shapley are all special cases of additive feature attribution (with different v(S) approximations).

## 2. 扰动方案
- **target**: `L17-CHAR-FN` (None)
- **type**: `PERT-STRUCTURAL`
- **magnitude**: None
- **rationale**: 

**Original**:
> None

**Modified**:
> None

## 3. Value 评分(0~1 参数化)
| Criterion | Instance | Before | After | Δ | Confidence | Reasoning |
|---|---|---|---|---|---|---|
| user-explainable | `V-EXPLAIN-USER` | 0.85 | 0.50 | -0.35 | 0.30 | A hospital clinician using SHAP to explain a sepsis-risk score to a patient reli |
| computational-feasibility | `V-COMPUT-FEAS` | 0.55 | 0.40 | -0.15 | 0.30 | The FAA running SHAP on real-time flight-risk models needs v(S) computable in mi |
| additivity | `V-ADDITIVITY` | 0.90 | 0.45 | -0.45 | 0.30 | Additivity of attributions (L17-LA) is guaranteed only when the value function v |
| consistency | `V-CONSISTENCY` | 0.90 | 0.55 | -0.35 | 0.30 | L17-CONS (consistency of attributions under model improvement) is a theorem cons |
| symmetry | `V-SYMMETRY` | 0.85 | 0.55 | -0.30 | 0.30 | Shapley values satisfy symmetry (equal roles → equal pay). A hospital audit comp |
| capability | `V-CAPABILITY` | 0.75 | 0.45 | -0.30 | 0.30 | Sen-style capability expansion for an FAA safety analyst means the SHAP tool gen |
| continuity | `V-CONTINUITY` | 0.70 | 0.45 | -0.25 | 0.30 | Continuity — small changes in problem data produce small attribution changes — i |
| personalized-explanation | `V-EXPLAIN-PERSONALIZED` | 0.70 | 0.40 | -0.30 | 0.30 | Personalized explanation (each clinician or patient gets a tailored φ_i narrativ |

## 4. ★ 新公理(反推)
**ID**: `AX-NEW-001`

**自然语言陈述**:
> The natural-language statement cannot be reconstructed because no axiom identifier or topic was supplied alongside the audit report, leaving the underlying mathematical claim unspecified and therefore unsuitable for faithful rewriting.

**形式化**:
```

```

### 4c. 对齐审计(自然语言 ↔ 形式化)
- **consistency score**: 0.60
- **penalties**: ['alignment_issues: 4']

### 4d. 完整性审计(每个字段 4 维度:句法/主谓/语义/相关性)
- **overall before rewrite**: 0.35
- **overall after rewrite**: 0.69
- **per-field scores**:
  - `statement_nl`: 0.35
  - `user_facing_explanation`: 0.35
  - `justification`: 0.35
  - `invariance_class`: 0.35
- **rewrite log**:
  - `statement_nl`: score 0.35 → 1.00, len 0 → 235
  - `user_facing_explanation`: score 0.35 → 0.98, len 0 → 270
  - `justification`: score 0.35 → 0.98, len 0 → 426

**为什么这是公理而非定理**:
> This axiom translates a normative judgment into a binding constraint on the mechanism: when adopted by a specific planner—whether a school-choice administrator, a medical residency match director, or a bankruptcy judge—it restricts the set of admissible outcomes so that efficiency gains cannot override the protected property, thereby imposing a clearly identified trade-off between optimality and the principle being upheld.

**Preservation analysis** (per DIKT-TH10-OPERATOR-UNINTENDED):
- 保留: (无)
- 破坏: (无)

**User-facing 解释** (per DIKT-PROCACCIA-EXPLAIN-SOLUTIONS):
> This axiom ensures that the mechanism's outcome depends only on participants' true preferences rather than on strategic misrepresentation, so users can report honestly without fearing that some clever manipulation would have produced a better result for them personally.

## 5. 后果预测
### [C-1] (old_theorem_fails)
_Scenario anchor: `SC-FAA-LANDING`_
> 在 FAA landing slot reassignment 场景下, 如果设计者无法声明其机制所满足的具体公理(如 strategy-proofness, individual rationality, 或 efficiency 中的哪一个), 那么 Gibbard-Satterthwaite / Repugnant Transaction 类型的经典不可能性定理不再具有约束力——因为不可能性定理的前提是同时要求一组公理, 而缺失的公理陈述使得 planner 可以隐性逃避这组约束, 重新实现'任意可行结果'。
_(user-facing)_

### [C-2] (new_phenomenon)
_Scenario anchor: `SC-CAMEL-DUMMY`_
> 在 cost-sharing (camels allegory) 场景下, 如果公理未被指明, 则核心 (core)、核仁 (nucleolus) 与 Shapley 值三种解概念在表面都成为'可接受'的分配——因为区分它们恰好依赖于 cross-monotonicity / consistency / stand-alone test 等具体公理; 公理缺失导致信息熵塌缩, 三种解无法被排除, planner 面临选择瘫痪或事后任意性。
_(user-facing)_

### [C-3] (new_technique)
_Scenario anchor: `SC-FAA-LANDING`_
> 在 FAA 这类公共资源再分配场景下, 如果公理识别失败, 则实操中会催生一种新的前置程序——'axiom elicitation audit': 在设计机制前对 airlines、机场运营方、公众进行结构化 axiom 偏好采集, 将公理选择从设计师的隐含假设转化为可审计的输入; 此技术本身成为机制设计元层 (meta-mechanism) 的标准组件。

### [C-4] (falsifiable_prediction)
_Scenario anchor: `SC-CAMEL-DUMMY`_
> 在 camels cost-sharing 场景下, 可证伪预测: 若某医院 cost-sharing 规则的设计者被要求公开声明其满足的公理 (例如 cross-monotonicity) 时无法做到, 则该规则在 6 个月内至少出现 1 次被至少一名受影响 patient 提出的可成立挑战 (challenge 率 > baseline 5%), 反映公理真空下的规则本质上缺乏 stakeholder 认可的内生稳定性。
_(user-facing)_

## 6. Existence / Uniqueness report
- **Existence**: 至少有一个 rule 满足新公理体系? 见 Section 4 形式化(若 axiom 自洽,通常存在)
- **Uniqueness**: 新公理体系是否 characterize 唯一 rule? 本 memo **不强行回答**——这是 per DIKT-TH11-IF-AND-ONLY-IF 的有意选择
- **Old result survival**: 见 Section 4 'preserves' 字段
