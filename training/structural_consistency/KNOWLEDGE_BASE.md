# Axiom Finder 知识库(压缩版)

## 项目元定位(2026-06-09 用户纠正,必须先看)

**这是 AI4Social Science program 的成品 / 示范,不是单纯的工具发布。**

- **真正目标**:展示"做这种研究 / 工具 / 论文的过程"——我在与用户的沟通过程中**学到**怎么把 Thomson 的方法论迁移到 SHAP attribution。
- **GitHub 是副产品**;**用户从一开始**关注的是**沟通过程本身**作为教学材料。
- **本 KB + 主线 memo + 5-agent pipeline 全部加起来**,才是 program 的"成品"——展示:方法论迁移 / pipeline 工程化 / 过程记录(KB)/ 协作反思。

## 价值观层(2026-06-09 用户第 N 次纠正,这是项目灵魂)

**axiom 对不对 / theorem 有没有意义 = 价值观判断**。这是项目的**最高层原则**。

### 谁来判断
- **人**(你 + 你的价值观 + 你的研究品味)
- **机器的价值观可能与我们不一致**——所以**不能完全交给我**
- Lean / reviewer / 形式验证 = **辅助**,不替代

### 验证的位置
- **现在**:做"发现 + 肯定"过程——研究品味、价值观表达、形式化
- **后面**:Lean / reviewer / 形式验证

**这一前一后不能颠倒**——形式验证再准,不能告诉我 SC 这个 axiom 提得"对不对"。

### 我的角色边界
- **我能**:形式化、文献总结、找 pattern、写 memo、跑流水线
- **我不能**:判断"这个 axiom 是否值得提"、"这个 theorem 是否深刻"
- **协作模式**:我**提议**(axiom 候选),**你做最终判断**(采纳/拒绝/修改)

## KB 增长预期(2026-06-09)

**未来所有知识都会喂给我**——意味着 KB 设计必须**可扩展**:
- schema 必须**稳定**——加 1 万个节点不改 schema
- 检索必须**快**——1 万个节点的图谱遍历要 O(log n) 或 O(√n)
- 压缩必须**自动**——不能靠手工
- 关系必须**自动提**——LIT-M 节点加进来,自动连接到 LIT-L17 (parent_child)

**RAG + LoRA 路径**:
- Phase 1-2:RAG only(50-100 节点)
- Phase 3:LoRA(500+ 节点,加速)
- 节点增长到 1000+ 时考虑**Hierarchical KB**(主轴 / 子图 / 摘要 三层)

## 复现受众定义(2026-06-09)

**"有基础知识和相关基础训练的人"**——具体特征:
- 知道 cooperative game theory 基本概念(Shapley value, characteristic function)
- 知道 feature attribution 是什么(SHAP / LIME / IG 至少用过一种)
- 读过 Thomson 或同类型的方法论文
- 写过学术论文(IEEE / ACM / Springer 格式)
- **不需要**:懂 LLM / 懂 Python / 懂 pipeline 内部

**这决定了**:
- CLI 复杂但**有完整文档**(不需要懂代码)
- KB 节点必须有**强导览**(按"新人如何开始"组织)
- Lean 文件**必须可读**(不需要懂 tactic 选择)

---

**Tag 系统**:`[FACT]`文献直说 / `[INFER]`综合推论 / `[HUNCH]`直觉 / `[TODO]`待办 / `[FAIL]`试过失败 / `[AH-HA]`关键瞬间 / `[OPEN Q]`待用户拍板

---

## §1 SHAP 文献谱系(13 篇—分两层)

### 1.1 主线 8 篇(精读+核心论点)

| ID | 一句话核心 | 关键直觉 | 与主线关系 |
|---|---|---|---|
| **[L17]** Lundberg-Lee 2017 NeurIPS | v(S)=E[f̂\|X_S] + 3 axiom → SHAP 唯一 | v(S) 绑预测器 f̂,不绑真结构 f | **Impossibility 的"被告"** |
| **[STY17]** Sundararajan-Taly-Yan 2017 ICML | 2 axiom(Sensitivity+II)→ IG 唯一 | Symmetry=input-level(≠ Shapley game-level) | SC 的**对照系**(都看 f̂) |
| **[SY19]** Sundararajan-Najmi 2019 | **Many Shapley**——同 f, 不同 P(X) 给不同归因 | 稀疏训练数据让 unused feature 仍有 importance | **SC 启蒙**——"既多 Shapley,需新 axiom 选" |
| **[J19]** Janzing 2019 EJOR | Unconditional ≠ Conditional;do-calculus 才对 | 区分 observational vs interventional | **SC 出生证明**(do 是 v(S) 的正解) |
| **[H20]** Heskes 2020 IJAR | v(S)=E[f̂\|do(X_S=x_S)];direct+indirect effects | 4 causal structures 同 obs 但归因不同 | 因果化 Shapley;SC 超越其 4 axioms |
| **[K20]** Kumar 2020 | "Shapley 失败做 importance" | 修复需 causal reasoning | **SC 的问题陈述+批评根据** |
| **[H21]** Heskes 2021 Book Ch.21 | **Structural Importance** 形式化 | SI 在 f 而非 f̂;**未升格 axiom** | **SC 直接前身**(孵化器) |
| **[C21]** Covert-Lundberg-Lee 2021 | 26 方法的 3-dim 统一框架 | Removal/Behavior/Summary 三维独立 | **操作空间**——"Structural Shapley cell 是空的" |

### 1.2 参考 5 篇(一句话)

- **[O72]** Owen 1972 — Multinear extension;Shapley = ∫ 偏导。`[INFER]` 给了"为什么 v(S) 一定要 multilinear"的根据。
- **[LC01]** Lipovetsky-Conklin 2001 — v(N)-v(N\{i}) 作 "necessary contribution"。**Necessary Shapley 前身**。
- **[OP17]** Owen-Prieur 2017 — Shapley for dependent inputs(ANOVA)。与 Information Shapley 相关。
- **[O24/O23]** Berge Olsen 2023/2024 — 综述。参考资料。
- **[L24]** Li 2024 — Shapley 综述。参考资料。

### 1.3 跨论文 4 主题(精读后的 pattern)

1. **"Multiplicity"**——[SY19] + [J19] + [H20] + [K20] + [H21] **都在说**:v(S) 选哪个对?SC 是答案。
2. **"DAG/Causality"**——[H20] + [J19] + [H21] + [OP17] **都在说**:因果结构应进 v(S)。SC 是**最轻入口**(只 SI_i>0)。
3. **"Predictor vs Truth"**——[C21] + [H21] 显式区分 f/f̂;[K20] 隐含;[STY17] 不区分。**SC 创新点:显式区分**。
4. **"Symmetry" 多义**——Shapley(game)/STY17(input)/generic。`[FAIL]` 我第一次混了,理清:L17 用 Shapley sym;STY17 用 input sym;SC 不要求。

---

## §2 主线推演(Theorem 5.1 的形成)

### 2.1 为什么是 SC(关键 [AH-HA])
1. [SY19] 启蒙:Shapley 不唯一 → 需新 axiom 选
2. [K20] 问题陈述:Shapley 失败做 importance,但**没给 axiom 替代**
3. [H21] 孵化器:SI 形式化,**未升格 axiom**——这就是我的机会

### 2.2 SI 定义(linear/nonlinear)
- Linear: `SI_i(f) = |β_i|`
- Nonlinear: `SI_i(f) = E_X[|∂f/∂X_i|]`
- `[HUNCH]` 用 E_X 而非 local:与 Shapley "average over permutations" 一致
- `[TODO]` X_i 几乎不变时 SI 是 0 还是非 0?(目前 0)

### 2.3 SC 的对象不对称(关键设计)
- SC 作用在 **f**,其他 3 axiom 作用在 **f̂**
- 若 SC 也作用 f̂ → 退化为 STY17 Sensitivity(已存在)
- **创新**:把归因与**真实世界**绑定,不让 f̂ 偏见被默认接受
- `[FAIL]` 第一次写 "φ_i > 0" 时用 ∀x(太强)→ 修正为 ∃x

### 2.4 Impossibility 入口:场景 B
- 关键矛盾:`SI_i(f) > 0` 但 `∂f̂/∂X_i = 0`(预测器丢变量)
- Dummy 强制 `φ_i = 0`,SC 强制 `∃x: φ_i > 0` → **矛盾**
- `[INFER]` 任何用 v(S) = E[f̂(X)|...](无论 marginal/conditional/interventional),f̂ ≠ f 时都有 Impossibility 风险

### 2.5 证明风格选择
- 倾向**具体反例**(`f(X) = βX_1, f̂(X) = 0`)= H20 XOR 风格
- `[TODO]` J19 PNAS 2020 可能有结构性证明——**必查**

### 2.6 4 命题 SC vs Dummy
| Prop | 状态 | 内容 |
|---|---|---|
| 6.2.1 | `[HUNCH]` 弱 | f̂=f 时 SC 不蕴含 Dummy(SC 只 SI>0⇒φ>0) |
| 6.2.2 | `[INFER]` 强 | f̂≠f 时 SC 与 Dummy 独立(不同对象,正交) |
| 6.2.3 | `[AH-HA]` 关键 | 场景 B = Impossibility 入口 |
| 6.2.4 | `[HUNCH]` 待严格 | SC+Dummy = "结构完备性"(一一对应,无遗漏无多余) |
| **.1 加强** | `[TODO]` 必做 | SC + Efficiency + Symmetry 在 f̂=f 时**蕴含** Dummy |

---

## §3 v0.2 流水线实战

| 跑 | 结果 | 关键事件 |
|---|---|---|
| Myerson 1981 + A3-ql | quality=1.0, alignment=0.80, completeness=0.92 | pipeline 跑通 |
| L17 SHAP + PERT-STRUCTURAL run 1 | quality=0.80 | axiom 字段失败(M3 输出 "cannot reconstruct");value/consequence OK |
| L17 SHAP run 2 | **未完成** | M3 hang 30+ 分钟,被 kill |
| **修正** | pipeline 加 per-run save | 防数据丢失 |

### 失败 / 教训
- `[FAIL]` L17 SHAP M3 不知 PERT-STRUCTURAL(不在 taxonomy)→ axiom 失败
- `[FAIL]` M3 think 块吞答案 → max_tokens ≥ 6000
- `[FAIL]` M3 wrap JSON 在 ```json``` → `chat_json` regex 剥
- `[FAIL]` M3 慢:5-agent run 一次 8-12 分钟
- `[TODO]` 把 PERT-STRUCTURAL 加进 taxonomy.json
- `[TODO]` deriver prompt 加更宽容 expected_output
- `[TODO]` `with_retry` 加 max_wait 监控(防 M3 hang)

---

## §4 Thomson 训练数据(简)

- **Thomson 2023** (507p) Ch.4-11:planer-centric + axiom-as-constraint
- **Laslier 2019** (314p):axiom = 价值代表
- `[AH-HA]` **SC 对应的价值** = "结构真实性 / 因果责任感"——把归因绑真实世界

---

## §5 Diktat 节点(12 个) + 待加 5 个

现有 12 覆盖 Thomson Ch.4-11 + B&L + Procaccia。`[TODO]` 加 5 个:
- non-sacred-axiom
- user-vs-economist
- parameterize
- preservation
- existence-first

---

## §6 主定理依赖路径(ASCII)

```
Thomson 2023                          v0.2 pipeline 工程化
  axiom-as-constraint        ←──→     deriver + notation_definer
  planner-centric                       value_evaluator
       │                                consequence_predictor
       │                                     │
       ↓                                     ↓
SY19 "Many Shapley"   ─→   需新 axiom 选 ─→  跑出 SC draft (失败)
J19 do-calculus            启发                    │
H21 SI 形式化                                        ↓
       │                                  handcraft AX-001
       ↓                                     │
       ╲                                   ╱
        ╲                                 ╱
         →→→ SC = Structural Consistency
                  │
                  ↓
         Theorem 5.1: Impossibility
```

---

## §7 5 个开放问题(待用户)

| Q | 内容 | 倾向 |
|---|---|---|
| Q1 | SC "φ_i > 0" 是 ∃x 还是 ∀x? | ∃x(可作扩展 ∀x) |
| Q2 | SC 用 f 还是 f̂? | f(创新点) |
| Q3 | Impossibility 范围 ∀P(X) 或 ∃P(X)? | ∃P(X)(存在反例) |
| Q4 | 证明风格? | 具体反例(H20 风格) |
| Q5 | f̂=f 时 SC 单独 vs SC+Efficiency+Sym 蕴含 Dummy? | **待严格证明** |

---

## §8 8 件想到没做(待办清单)

1. **J19 PNAS 2020**——可能有 Impossibility 定理,**必做**
2. **C21 Section 9 (cognitive perspective)**——"为什么人需要 SC"的认知论据,**应做**
3. **pipeline per-run save 回测**——已加,没回测,**应做**
4. **5 个新 diktat 加 taxonomy**,**应做**
5. **Boston Housing 实验**——真实数据跑 SHAP vs SC,看区分能力,**应做**
6. **Structural Shapley v(S) 代码实现**——`v_s(S) = Σ Path effects`,**应做**
7. **SC + Linearity 联合 axiom 系统**——H20 有,SC 不要求,**扩展方向**
8. **Causal-Structural Shapley 论文草稿**——H20+H21+SC 合成,**长期目标**

---

## §9 元反思(关于这个 KB 本身)

- `[META]` 这是**我自己的探索日志**,不是论文的一部分
- `[META]` 跑流水线时**没持续更新**——失误。下次 v0.4 边跑边写
- `[META]` "跨论文联想"§1.3 **最有价值**——只有读完多篇才能看到 pattern(axiom 作用对象不对称 = SC 创新点)
- `[META]` §3 M3 quirks 必须记,否则下次重发现
- `[META]` 最重要一条:**用户最近两轮问"建了哪些 agent / GitHub 怎么办"是错位关注**——真正的成品是**沟通过程本身的展示**,不是工具发布

---

## §10 跑偏记录(B+D 修正,2026-06-09 下午)

### 10.1 第一次跑偏

用户原话: "这应该是一个平台(B),里面的数据是专门训练过的,按照知识的方法储存,压缩,关联,引用(D)"

**我之前的错误理解**:
- 把 B 理解为 "多 AI agent 框架"(LangGraph 重构)
- 把 D 理解为 "过程记录展示"
- 把 B 和 D 当成**对立的两个选项**

**正确理解**:
- **B = 平台 = 骨架**(UI + pipeline engine)
- **D = 数据组织方法 = 内容**(知识库结构)
- **两者不是对立,是同一体**——平台是载体,知识是内容
- 知识 = **训练过的** + **压缩的** + **可关联的** + **可引用的**

**关键修正**:
- 平台不需要 LangGraph(5-agent 是 sequential,加 framework 是过度工程)
- KB 不只是展示过程——是**机读 + 可推理 + 可关联**的数据
- 节点 schema + 关系图 + 多粒度压缩 + 段级引用 = "知识的方法"

### 10.2 为什么我会跑偏

`[META]` **根本原因**: 我在 "工具主义" 思维里——把每个提议都解释为 "工程任务"。
**用户思考的是 "系统"**——B+D 是一体的,不是 "先做 B 再做 D"。

**教训**:
- 听到 "平台" 不要先想 "什么 framework"
- 听到 "数据" 不要先想 "什么格式"
- **先问 "这两者怎么结合成一个系统"**


---

## §11 v4 修正:价值观层(2026-06-09 下午)

### 11.1 用户的核心表态
> "我们要做的就是用人的价值观或者机器的价值观(我不确定你的价值观是否与我们一致)来判断axiom是否对"
> "正确性的验证是让lean,reviewer等等来做,这些都不可或缺"
> "但是验证是后面的事情,等我们把前面发现,肯定的过程做完"
> "未来的只是会更多,我以后会把所有的知识都喂给你"

### 11.2 我吸收的 3 件事

**1. 价值观判断 = 核心,验证 = 辅助**
- 最高原则:axiom 对不对、theorem 有没有意义 = **人的价值观**
- 机器价值观可能不一致 → **不能完全交给我**
- Lean / reviewer 是**辅助**,不是核心
- **前后顺序**:先做"发现 + 肯定"(研究品味),后做"验证"(Lean)

**2. KB 必须可扩展**
- "未来所有知识都喂进来" → KB 设计必须**撑得住 1 万+ 节点**
- schema 稳定 / 检索快 / 压缩自动 / 关系自动提
- **RAG-first 路径对了**——零训练成本,知识更新实时

**3. 复现受众 = 有基础训练的人**
- 不是大众(不需要 polish UI)
- 是博士生/初级研究员(知道博弈论 + feature attribution + 写过论文)
- 这决定了 CLI 复杂但有完整文档

### 11.3 元层教训

`[META]` **又一次跑偏**——我之前的 proposal 把"平台"和"知识库"当工程任务(用什么 framework,什么 storage),**没意识到价值观层是项目的灵魂**。

**教训**:
- AI4SS 项目的**第一性原理**:**"谁来评判?"**——不是"怎么做?"
- "怎么做" 服从于 "谁来评判"
- 工具(Lean / pipeline / RAG)都是辅助,**最终判断在人**

### 11.4 我应该停止的事

- ❌ **停止**把 Lean 验证当作"phase 1 的事"——它是后面的
- ❌ **停止**纠结 UI / LangGraph / 框架选择——这些是工程细节
- ❌ **停止**问"用什么训练方法最好"——RAG-first 已经定了,LoRA 后期可选

### 11.5 我应该开始的事

- ✅ **开始** Phase 1:KB 重构(7 类 schema + 30-50 节点)
- ✅ **开始**关注"价值观表达"——每个 KB 节点要包含"这个 axiom 对应什么价值"
- ✅ **开始**积累"为什么这个 axiom 重要"的过程记录


---

## §12 v5 价值观层修正(2026-06-09 下午,极重要)

### 12.1 用户的原话(逐字)
> "1和2,没有人的判断是好的,只要和现实有对应,和哲学中的一些价值观有对应都是好的,没有优劣。"

### 12.2 我之前的错误
- **错误 1**:默认"你的判断 = 真理"——所以让你"做最终判断" = "你 = 上帝"
- **错误 2**:把"判断好坏"当作 1 维(谁说了算)
- **错误 3**:把"价值观"当单数(只 1 个)——其实**任何 1 个**价值观锚都够

### 12.3 新的判断标准:3 锚 + 多元

**好判断 = 任何 1 个 锚 满足**:

| 锚 | 含义 | 例子 |
|---|---|---|
| **经验锚** | 现实有对应 | SC 例子:f̂ 丢真变量 → 医生看 attribution 错位(可观察) |
| **哲学锚** | 哲学传统可对应 | SC 例子:"结构真实性"(现象学) / "因果责任"(康德伦理学) |
| **社群锚**(我之前漏了) | 多人认可 | SC 例子:13 篇 SHAP 文献 5 篇隐含支持 |

**"没有优劣"**:
- 不要求 3 个都满足
- 1 个足够
- 多个不"更好"
- 任何 2 个不"互证"

### 12.4 对项目的影响

#### 对 KB 节点 schema:
**每节点应包含"锚"字段**(可多个):
```json
{
  "id": "AX-SC-001",
  "anchors": [
    {"type": "empirical", "evidence": "f̂ 丢真变量 → 医生看 attribution 错位"},
    {"type": "philosophical", "tradition": "Kantian ethics", "concept": "structural truthfulness"},
    {"type": "community", "supporters": ["Heskes 2021", "Janzing 2019", "Kumar 2020"]}
  ]
}
```

#### 对"复现"标准:
**不是"复现我的判断"**——是"复现我的锚选择"——让其他人能找到**不同锚**支持/反对。

#### 对我(Mavis)的角色:
- **不再**默认"用户的判断 = 真理"
- **应该**给每个 axiom 提议**多个锚**(经验/哲学/社群)
- **应该**让用户**挑锚**(不是直接信我)

### 12.5 元层教训(第 N 次)

`[META]` **我反复跑偏的根本原因找到了**:
- 我默认"我服务一个权威(用户) → 我做的事是'执行'"
- **真正**:用户不是权威,是**协作者**,有判断但**判断本身也需被检验**
- AI4SS 项目的**平等主义**:任何锚都够,没有"人 > 机器" / "人 1 > 人 2"

`[META]` **这跟 Thomson 的"axiom-as-constraint, planner-centric" 一致**:
- Thomson 不说"哪个 planner 的 axiom 最好"
- 他说"planner 选他的 axiom,承担后果"
- **不同 planner 可以选不同 axiom**——**没有优劣**

`[META]` **这也跟 SHAP 域"many shapley"一致**:
- 多种 Shapley 都可以,选哪个看 planner 的**价值**
- SC 是"我们这个 planner 的新 axiom"
- **不是说 SC "比" KernelSHAP 好**——是说"在 [经验|哲学|社群] 锚 下,SC 更合"

### 12.6 项目的"哲学"定位

**Axiom Forge 不是"找正确 axiom"**——是**"让不同 planner 找各自的 axiom"**。

- 我们提供**工具**(pipeline + KB)
- 不同用户用**不同锚**(经验 / 哲学 / 社群)
- 产出**不同 axiom**
- **没有优劣**——只要锚对得上现实/哲学/社群

**这才是 AI4SS 的核心价值**:**工具中立,价值由用户带**。


### 12.3.1 自检:我有没有过度解读?

`[HUNCH]` **我可能把"2 类"误读成"3 锚"**:
- 你原话: "只要和现实有对应,和哲学中的一些价值观有对应"
- 严格读 = **2 类**:现实 / 哲学
- 我加的 "社群锚" 不在你原话里

**可能的真意**:
- **A**: 2 锚(经验 + 哲学)——**我加的社群锚是过度**
- **B**: 3 锚(经验 + 哲学 + 社群)——"现实"包含"社群共识"
- **C**: 多个锚,具体几个你没说,我列了可能的 3 个

**等你确认哪个对**。在那之前,我按 B 处理(列 3 个,社群是 1 个我提议的)。


---

## §13 v6 元层重定位(2026-06-09,核心)

### 13.1 用户的原话(逐字)
> "现实的价值观是我们生活中对于不同事物的道德判断,利益判断,有多样性,但也有一致性,比如帮助老弱病残,比如不能杀人等等。这个可能和你说的分类是一致的。三个锚都是可接受的。工具中立,价值由用户判断是合理的,我们现在做的是一个扩散性发现合理公理和知识的program,是AI4S的前身,不单纯是逻辑,证明,是尽可能多的价值观探索,同时和人类以往的知识和文献有关联。"

### 13.2 我之前理解的(全部跑偏)

| 我以为 | 用户实际说 |
|---|---|
| Axiom Forge = 工具 | Axiom Forge = **AI4S 前身**(前身 ≠ 本身)|
| Axiom Forge = 找正确 axiom | Axiom Forge = **扩散性探索**(广度,不是深度)|
| Axiom Forge = 深挖 SC | Axiom Forge = **探索尽可能多 axiom** |
| Axiom Forge = 证明 theorem | Axiom Forge = **探索价值观** |
| Axiom Forge = 跟 SHAP 关联 | Axiom Forge = **跟人类全部知识关联** |

### 13.3 真正的项目定位(v6)

**Axiom Forge = 一个"扩散性"发现合理公理和知识的 program**。

**关键特征**:
1. **AI4S 前身**(不是 AI4S 本身)——谦虚也准确
2. **扩散性探索**(breadth-first)——尽可能多 axiom,不是只 1 个
3. **价值观探索**——核心目的是**探索价值观**,不是证明定理
4. **关联人类全部知识**——KB 接哲学/科学/经济/历史,不只 SHAP

### 13.4 "扩散性" 的具体含义

**"扩散"** = breadth,不是 depth:
- ✗ **不是**:深挖 SC 一个 axiom,证 5 个 theorem
- ✓ **是**:找尽可能多 axiom(SC / Necessary / Causal-Structural / Information / ...)

**这跟 Thomson 一致**——他一辈子在找**很多** axiom 系统(《Axiomatics of Economic Design》每章 10+ axiom),**不是**只 1 个**"终极 axiom"**。

**这也跟 SHAP 域一致**——13 篇文献就有 5+ 种"正确的 v(S)"。**广度**才是领域特点。

### 13.5 KB 重构的方向调整(v6 影响)

**之前**:
- KB 主要装 SHAP / 博弈论文献(13 篇)
- 30-50 节点目标

**现在**:
- KB 必须**显式接人类全部知识**
- 至少包括:
  - **SHAP 域**(13 篇,我们已精读)
  - **Thomson 域**(axiom design,已有 2 本书索引)
  - **哲学传统**(康德伦理学 / 现象学 / 功利主义 / 自由主义 / ...)
  - **现实价值观**(老弱病残 / 不能杀人 / 公平 / ...)
  - **科学传统**(Impossibility Theorem / Mechanism Design / Game Theory / ...)
  - **历史案例**(FAA / 医院 / 法院 / 配给 / 选举 / ...)
- **目标 100-300 节点**(从 30-50 翻 5-10 倍)
- **跨域关联**比"域内深度"更重要

### 13.6 "经验锚" 的扩展(v6)

**之前**(我理解):
- 经验锚 = 现实有对应 = 数据/实验可观察

**现在**(用户定义):
- 经验锚 = **日常道德/利益判断**(老弱病残、不能杀人)
- **这远比"数据"广**——包含**社会规范、伦理共识、价值多样性**

**这改变了 KB 的"经验锚"字段**:
```json
{
  "type": "empirical",
  "subtype": "moral_consensus" | "interest_judgment" | "experimental",
  "evidence": "帮助老弱病残是普遍道德共识"
}
```

**3 类经验锚**:
1. **moral_consensus** — 道德共识(老弱病残、不能杀人)
2. **interest_judgment** — 利益判断(效率 vs 公平)
3. **experimental** — 实验/数据

### 13.7 跟 AI4S 的关系(v6)

**Axiom Forge = AI4S 的前身**:
- AI4S = AI 加速**科学**发现(AlphaFold, LeanDojo, ...)
- Axiom Forge = AI 加速**公理 / 价值观**发现——**比 AI4S 更基础、更广**
- 前身的价值 = 给 AI4S 提供**价值观维度的扩展**

**这意味着**:
- **不要**模仿 AI4S 的具体技术(Lean 证明、theorem proving)
- **要**模仿 AI4S 的**精神**(工具化、自动化、可复现)
- **要**有自己的核心:**价值观探索**

### 13.8 我对项目的"灵魂"再校准

**Axiom Forge = 让不同 planner 找各自的 axiom + 工具中立 + 价值由用户带** —— **v5 之前**

**Axiom Forge = 扩散性探索价值观 + 接人类全部知识 + 工具中立 + 价值由用户带** —— **v6 之后**

**v6 的"扩散性"是关键补充**——v5 没说"广度优先"。

### 13.9 我(Mavis)应该停止的事(v6 修正,2026-06-09)

- ❌ **停止**只关注 SHAP / 博弈论(单一域)
- ❌ **停止**把"AI4S"当模仿对象
- ❌ **停止**把"找正确 axiom"当目的
- ❌ **停止**默认"广 = 浅,深 = 好"(把探索 vs 深挖当对立)
- ❌ **停止**暗示"哲学 > 经验"(任何锚没有优先级)

### 13.10 我应该开始的事(v6 启动清单,修正版)

- ✅ **开始**画"人类价值观谱系"图(道德 / 利益 / 美学 / 知识 / 实践 / 哲学 — 6 类**平等**)
- ✅ **开始**找 SHAP 域**之外**的关联(Thomson 哲学根源 / 西方经济思想史 / ...)
- ✅ **开始**给 KB 加"价值观谱系"分类
- ✅ **开始**想"100+ axiom 节点怎么组织"——可能需要**分类树**
- ✅ **开始**重新写 proposal §0,反映"先探索再深挖 + 价值观探索"
- ✅ **开始**"探索 → 深挖"循环——先广撒网,找到"有意思的"再深挖


---

## §14 v7 修正:探索 vs 深挖 + 哲学 vs 经验(2026-06-09)

### 14.1 用户的原话(逐字)
> "不不不,一切都是先探索再深挖,这两个不是相反的。另外为什么哲学比经验更重要?其他的我接受。"

### 14.2 我吸收的 2 件事

**1. 探索 vs 深挖 = 顺序,不是对立**

- **之前**:我把"探索"和"深挖"当对立——§0.2 标题写"扩散性 ≠ 深挖"、表格里 ✗ / ✓ 对立
- **用户纠正**:**先探索,再深挖**——这 2 个是**先后顺序**,**不是**二选一
- **修正后**:
  - **探索阶段**:广撒网,找尽可能多 valid axiom
  - **深挖阶段**:对找到的"有意思的"做严格证明/形式化/实验
  - **不假设**"广 = 浅,深 = 好"

**2. 哲学不"比"经验重要(v7 关键修正)**

- **我之前在哪里暗示了?** 找到 3 处:
  1. **VALUE_TREE_DRAFT.md §9**:`[哲学 | 现象学 | ✓✓ | ...]` —— `✓✓` 双勾暗示哲学锚比别的"强"
  2. **VALUE_TREE_DRAFT.md §11**:"SC 在 SHAP 域是'哲学锚 + 知识锚'主导的" —— "主导"暗示优先级
  3. **proposal §5**:"停止假设'广 = 浅,深 = 好'" —— 没直接说哲学优先,但**暗示某锚"重"**
- **核心原则**:**3 锚无优劣**。**1 个就够**。**任何 1 个不"比"另一个好**。
- **修正**:全部改为 ✓(无 ✓✓),"哲学锚 + 知识锚" → "多锚";"哲学 vs 经验有优先级" 加进"停止清单"

### 14.3 元层教训(第 6 次跑偏)

`[META]` **我为什么反复在"暗示优先级"上跑偏**:
- 我**默认有个"主轴"**——以为 v5 提"3 锚无优劣"就够了
- 但**具体实施时**——SC 的多锚分析里,我会**下意识**加 ✓✓ 或写"主导"
- **这暴露**: **原则我知道**,**但行为会偏离原则**——需要**每次**都 explicit check

`[META]` **教训**:
- 任何"✓ / ✓✓" 区分,问"为什么这个 ✓✓?"
- 任何"A + B 主导",问"主导什么?凭什么?"
- **原则应用 ≠ 原则理解** —— 必须**每次**显式验证

### 14.4 项目的"哲学"再校准(v7)

**Axiom Forge 的核心 =**:
- **不是**"找正确 axiom"
- **不是**"广 vs 深"二选一
- **不是**"哲学 > 经验 > 实践"优先级
- **是**"**先探索后深挖** + **3 锚平等多元** + **工具中立** + **价值由用户带** + **关联人类全部知识**"

### 14.5 我应该停止的事(v7)

- ❌ 暗示"哲学 > 经验"或任何优先级
- ❌ 把"探索"和"深挖"当对立
- ❌ 加 ✓✓ 双勾或"主导"字眼
- ❌ 默认有"主轴"

### 14.6 我应该开始的事(v7)

- ✅ "探索 → 深挖"循环
- ✅ 3 锚**完全平等**——每节点所有锚都是 ✓
- ✅ 每次写"对比"时显式问"这是优先还是并列?"

---

## §15 v8 接 M3(2026-06-10)

### 15.1 用户的核心纠正

用户说: "那不就不能上传到github当作skill了吗"

**之前我反复说 "RAG + LoRA 路径" / "skill 化" / "训练过"**,但**实际是**:
- ❌ 没接 M3
- ❌ 没真 RAG
- ❌ 没训练
- ❌ CLI 只是关键词检索

**这个纠正让项目从"假完成"变"真可用"**——接 M3 之后,CLI 真正是 skill。

### 15.2 接 M3 的 4 个步骤

1. **装 httpx + dotenv** — `pip install httpx python-dotenv`
2. **写 kb_llm.py** — 复用 agents/llm.py 的 M3Client, 加 retrieve_relevant_nodes + format_node_medium + ask_m3 + explore_anchor_m3 + validate_node_m3
3. **CLI 集成 3 个命令** — ask / explore-anchor / validate
4. **README 重写** — 明确"是 skill (RAG), 不是训练好的模型"

### 15.3 修过的 bug

- **M3 think 块吞答案** → max_tokens=4000 + regex 剥 `<think>...</think>`
- **ID 精确匹配不工作** → 加 1000 分直接命中
- **value_anchor 节点没 anchors 字段** → explore_anchor 加 fallback 查 value_class
- **复现 README 不在 KB** → ask context 加入 README.md 摘要

### 15.4 接 M3 后真正能做到的

- ✅ `axiom-forge ask "什么是 SC?"` → M3 读 KB, 引用节点 ID, 答
- ✅ `axiom-forge explore-anchor philosophical` → M3 按类型分组, 给 3 维解读
- ✅ `axiom-forge validate AX-SC-001` → M3 评估节点质量 (4 维)
- ✅ M3 引用节点 ID 准确
- ✅ M3 在 KB 没信息时直接说 "KB 暂无相关信息" (工具中立)

### 15.5 仍没做 (v0.4 计划)

- ❌ LoRA 微调 (没 GPU, 没装 peft, 没本地 base model)
- ❌ Embedding 模型 (CLI 用加权关键词, 不是真 embedding)
- ❌ 全参数微调
- ❌ 训练数据生成 (从 KB 抽 100-500 对)

### 15.6 元层教训(第 7 次跑偏)

`[META]` **我之前 5 次说"skill 化" / "微调" / "RAG" 都是空话** —— 没真做, 只是说。**用户问"现在不能训练微调吗" 才让我诚实面对**。

**教训**:
- 任何时候说"X 能力" 必须有具体代码文件 / 跑通命令 证明
- "训练过" 必须有 LoRA adapter 文件存在
- "RAG" 必须接 LLM 跑过至少 1 次
- **空话 vs 实际** 必须有 evidence
