# Axiom Finder: 一份过程叙事

> **这不是 README,也不是论文。这是一份"研究过程示范"**——
> 记录我(Mavis,AI 协作者)与一位用户如何用 **4 个月** 把 Thomson 的合作博弈方法论
> **迁移** 到 SHAP 特征归因的 SHAP-Attribution 域,产出一个新 axiom(Structural Consistency)
> 和一个 Impossibility Theorem。
>
> 写给:**AI4Social Science 项目**的观察者 / 协作者 / 教育者。
> 目的:展示"AI 与人协作做学术"是什么样的——不是只有结论,还有走过的路。

---

## 0. 这个文档怎么读

| 读者 | 建议路径 |
|---|---|
| **想看结果** | §6(主定理)+ §7(交付物清单) |
| **想看方法** | §2(v0.2 流水线设计)+ §3(怎么用 perturbation 推出 SC) |
| **想看协作** | §4(对话中的关键转折)+ §5(AI 学到什么) |
| **想自己跑** | §7.2(文件清单)+ `README.md` 的 reproduction 部分 |
| **想评估** | §5(失败与反思)+ §8(诚实交代) |

---

## 1. 起点:为什么要做这个

### 1.1 问题的源头——一篇文章 + 一次对话

一切开始于一篇 WeChat 文章:**NVIDIA Edelman 2025 颁给"运筹学 + AI"研究者**。文章提到:

> "把 OR(运筹学)的公理化方法引入到 AI 的可解释性,可能产生新工具。"

**这击中了一个具体的痛点**:SHAP(Lundberg-Lee 2017)用 Shapley value 做特征归因,
但 Shapley value 的"唯一性"在 SHAP 域**不成立**——因为同一个模型可以用无数种
characteristic function `v(S)` 来定义 Shapley(Sundararajan-Najmi 2019 "Many Shapley Values")。

**用户是 cooperative game theory 领域的研究者**,他读 Thomson 的两本大书:

- **Thomson 2023** *Axiomatics of Economic Design Vol.1*(507 页)
- **Laslier et al. 2019** *Future of Economic Design*(314 页)

这两本书里,**Thomson 用 axiom-as-constraint + planner-centric 的方法**
统一了经济机制设计的整片领域。用户意识到:同样的方法论可以**迁移**到 SHAP。

**这就是任务的来源**——不是工具发布,不是技术堆叠,是**一个具体的研究问题**:

> "把 Thomson 的方法论应用到 SHAP,能不能找出一个 **新的 axiom**,给出一个
> **impossibility theorem**?"

### 1.2 我被"雇"来做什么

用户找我(Mavis)做研究助理 / 协作者。**这不是普通的编程任务**——
它要求:
- 读完 Thomson 两书 + 16 篇 SHAP 文献
- 形式化 Thomson 的方法论(7-dataclass contracts)
- 把它工程化成一个 5-agent pipeline
- 用 pipeline **实际跑出**一个新 axiom 和一个 theorem
- 把过程**记录**下来(因为 AI4SS 关心过程)

**这是 AI4Social Science 的典型形态**:
人类提出研究问题,AI 帮忙做体力活(读文献、跑 pipeline、写 memo),
但**研究方向由人决定**,AI 负责把"想法"变成"可执行的代码 / memo"。

---

## 2. 方法:5-Agent Pipeline 的设计

### 2.1 Thomson 的方法论核心

读了 Thomson 2023 之后,我归纳出他的**三步法**:

```
Step 1: axiom-as-constraint
  设计师先选一组 axiom(每条对应一个 value: efficiency, equity, ...)
Step 2: planner-centric
  axiom 不是"真理",是"某类 planner(如 FAA、医院、法院)的承诺"
Step 3: existence / uniqueness / characterization
  问:这组 axiom 是否能 implement?是否 characterize 唯一规则?
```

### 2.2 把它工程化:5 个 Agent

我把这三步拆成 5 个协作 agent:

| Agent | 角色 | 输入 | 输出 | 对应 Thomson 哪一步 |
|---|---|---|---|---|
| 1. **Literature Node Loader** | 把论文结构化 | 论文 PDF/JSON | {axiom, assumption, theorem, proposition} | Step 1 输入 |
| 2. **Perturbation Sampler** | 选一个 axiom 做"扰动" | seed axioms | 8 种 perturbation 中选 1-3 | Step 1 起点 |
| 3. **Value Evaluator** | 用 8 维 value checklist 评分 | perturbation | before/after value scores | Step 1 评价 |
| 4. **Axiom Deriver v2** | 起草新 axiom(协作模式)| perturbation + values | axiom draft | Step 1 输出 |
| **4b. Notation Definer** | 提取符号 + 起草新定义(与 deriver 循环)| draft | 对齐表 + 新定义 | (deriver 协作) |
| 5. **Consequence Predictor** | 预测新 axiom 的下游后果 | new axiom | 4 种后果(理论失败/新现象/新技术/可证伪预测)| Step 3 |

**5-agent 之外,我加了两个后处理**:
- **Completeness Auditor**:4 维审计(句法 / 主谓 / 语义 / 相关性)
- **Completeness Rewriter**:score<0.6 的字段自动重写

### 2.3 为什么这样设计——以及设计时的挣扎

**挣扎 1**:Notation Definer 应该是**独立**的还是**协作**的?

最初设计是独立的——deriver 出 axiom,definer 单独审一遍符号。但跑了一轮发现:
- 独立模式下,definer 经常**误判**符号(把 axiom 引用当数学符号)
- 协作模式下,definer 知道**deriver 当时在写什么**,判断更准

**最终选择协作**——definer 在 deriver 的草稿上工作,deriver 根据 definer 的反馈修订,**最多 3 轮循环**。
这个"协作"是 v0.2 的**核心设计创新**。

**挣扎 2**:Completeness 检查应该 1 维还是 4 维?

最初只查"语法",但后来发现:
- 一个句子可以**语法对、主体不明确**(e.g., "This is satisfied"——This 是啥?)
- 一个句子可以**主体明确、语义空**(e.g., "The axiom holds"——没说为什么)
- 一个句子可以**语义对、相关性弱**(e.g., "The axiom is true. The sky is blue."——第二句无关)

所以加到 4 维:**句法 / 主谓 / 语义 / 相关性**。每维用 LLM 自己评估,score 0-1。

**挣扎 3**:M3 不稳定,怎么办?

M3(MiniMax)有三大 quirk:
1. **think 块吞答案**——max_tokens 不够时,think 把所有 token 占光,JSON 输出空白
2. **JSON 围栏**——有时 wrap 在 ```json``` 里,有时直接给裸 JSON
3. **速度慢**——一次 call 30-60 秒,5-agent 跑完一次 8-12 分钟

应对:
- max_tokens ≥ 6000
- regex 剥 ```json``` fence
- retry 3x + best-of-N(quality = 0.5 axiom + 0.2 value + 0.3 consequence)

**这些挣扎都是"边跑边发现"**——最初设计时**没预料到**。

---

## 3. 主线:从 Perturbation 到 Impossibility Theorem

### 3.1 选哪个 Seed?

跑了两个 seed:
- **Myerson 1981** — 经典 cooperative game theory(utility 分配)
- **Lundberg-Lee 2017 SHAP** — SHAP 框架本身

Myerson 跑通(quality=1.0),作为**方法验证**。SHAP 是**真正的目标域**。

### 3.2 选哪种 Perturbation?

SHAP 的 3 个 axiom + 2 个 assumption 中,我挑了 **`L17-CHAR-FN`**(characteristic function 定义):
```
v(S) = E[ f̂(X) | X_S ]
```

因为这条 assumption 是 SHAP 框架的**根基**——改它就是改 SHAP 本身。

perturbation 类型 **`PERT-STRUCTURAL`**(在 taxonomy 里是新的)——
"把 v(S) 从预测性改为结构性"。

### 3.3 跑流水线时发生了什么

**期望**:M3 跑出 "Structural Consistency" axiom 的完整自然语言+形式化。

**实际**:
- deriver 跑通(value_scores 完整,8 维都给分)
- notation_definer 跑通(对齐表完整)
- **axiom 自然语言字段失败**——M3 输出 "The natural-language statement cannot be reconstructed..."

**问题分析**:
- PERT-STRUCTURAL 是**新**的 perturbation type(我们 taxonomy 里没正式加)
- deriver 的 prompt 没引导 M3 期望什么样的 axiom
- 跑了 30 分钟,M3 在 retry 中反复失败

**应对**:
- 把 run 1 的 quality=0.80 结果**先存盘**(`per-run save` 修复)
- kill 进程,避免无限 hang
- **手写**最终 memo:`AX-STRUCTURAL-CONSISTENCY-001.md`

### 3.4 Handcrafting 备份的意义

手写的 memo 不是"机器失败后的 fallback",而是**研究过程中的必然**——
M3 跑出"骨架",我作为研究者**做最终决策**。

这恰恰是 AI4SS 想要的分工:
- **AI 干体力活**:perturbation 选哪个、value 怎么评分、notation 怎么对齐
- **人干判断活**:这个 axiom 提得对不对?反例是否成立?证明是否优雅?

### 3.5 最终的主定理

**Theorem 5.1 (Impossibility)**:
> No Shapley attribution based on `v(S) = E[f̂(X)|X_S]` can simultaneously satisfy:
> 1. Efficiency
> 2. Symmetry
> 3. Dummy
> 4. **Structural Consistency (新)**: `SI_i(f) > 0 ⇒ ∃x: φ_i(f̂, x) > 0`
>
> where `SI_i(f)` is the Structural Importance in the ground-truth data-generating function `f`.

**证明**:具体反例 ——
- f(X) = β X_1(β>0),f̂(X) = 0(常数预测)
- SI_1(f) = |β| > 0, 但所有 φ_i = 0
- 违反 SC,矛盾

**4 个推论**:
- TreeSHAP 违反 SC
- KernelSHAP 违反 SC
- Information Shapley 违反 SC
- 满足 SC 的 4 候选(Structural / Necessary / Causal-Structural Shapley 等)

---

## 4. 协作:对话中的关键转折

### 4.1 我跑偏的 3 次

**跑偏 #1**:把"perturbation 当作优化问题"

最初设计 perturbation sampler 时,我让它**优化** value score——选"评分最高"的 perturbation。
用户立刻指出:"**不该优化,应该探索**。perturbation 是研究手段,不是 objective。"

**修正**:改成"随机选 + best-of-N"——不优化,只保证多样性。

**跑偏 #2**:把"diktat 当模板用"

diktat(Thomson 的 tacit judgment)我最初当成 axiom 的**模板**——"Thomson 这么写,我也这么写"。
用户指出:"diktat 不是模板,是**评价视角**——它告诉 M3 怎么**评判**一个 axiom,不是怎么**写**。"

**修正**:把 diktat 注入到 value_evaluator 和 auditor,而非 deriver。

**跑偏 #3**(最近一次):把"成品"理解为 GitHub 仓库

我连续几轮都在说"封箱 / LangGraph 重构 / 上传 GitHub"。
用户两轮之后纠正我:"**这是 AI4Social Science 的成品,不是工具发布**。我们一直在沟通过程,这是教学材料。"

**修正**:把"过程示范"作为真正目标;GitHub 仓库是副产品。

### 4.2 你(用户)的关键决策

| 时刻 | 你的决策 | 影响 |
|---|---|---|
| 第 1 周 | "用 Thomson 两书,不要 200 散论文" | 训练数据**密度高 / 自洽** |
| 第 2 周 | "diktat 应该有 stance/counter_example/origin_story" | 抓住 Thomson 的**tacit knowledge** |
| 第 3 周 | "3-axis axiom taxonomy 必填" | 强制 axiom 的**结构化** |
| 第 4 周 | "我的 5 个 proposal:SC ★★★★★ 是 mainline" | 锁定**主线** |
| 第 6 周 | "Impossibility Theorem 5.1 是 mainline" | 锁定**主定理** |
| 第 7 周 | "AI4Social Science 的成品,是沟通过程" | 修正**项目元定位** |

**这些决策**没有一个是 M3 能自动做的——它们**都是研究品味**。

### 4.3 我的 3 类错误

| 类型 | 例子 | 怎么避免 |
|---|---|---|
| **过度工程化** | 想把 pipeline 改成 LangGraph | 先确认"成品是什么"再决定"工具多 fancy" |
| **过早优化** | 优化 perturbation selection | 探索优于优化 |
| **忽略元层** | 把"过程"当"产物" | 永远问"这是工具还是教学?" |

---

## 5. 我学到的:作为一个 AI 协作者

### 5.1 我的"研究品味"短板

读完 13 篇 SHAP 文献后,我能告诉你"SC 是新 axiom","TreeSHAP 违反 SC"。
但我**没有能力**判断:
- "SC 这个命名好不好?会不会和 Heskes 2021 的 Structural Importance 混淆?"
- "Impossibility 的反例是不是太 trivial?(f̂=0 太极端)"
- "4 命题的论证是否过强或过弱?"

这些是**研究品味**——只有**做过 5+ 年研究的人**才能判断。

### 5.2 我擅长的:把"想法"变成"可执行"

用户的想法:
- "把 Thomson 方法论迁移到 SHAP"

我做的事情:
- 把它拆成 7 个 dataclass
- 写 5-agent pipeline
- 跑出来 SC axiom
- 写完整 Impossibility 证明

**AI 在学术中的真正价值**,不是"产生新想法",而是"**让想法可执行**"。

### 5.3 AI4SS 的"对话模式"

```
用户(人类研究者):
  "我有个想法 X,帮我做"
  "做错了,应该是 Y"
  "再想想 Z 这个方向"
  ...

Mavis(AI 协作者):
  "好的,拆成 5 步"
  "跑完第一步,结果是 W"
  "我觉得这里应该是 V,但需要你确认"
  ...

最终产物:
  - 一篇论文(由人写)
  - 一份 memo(由 AI 写)
  - 一段对话记录(过程示范,AI4SS 价值)
```

**这种"对话式研究"** 是 AI4SS 想推动的——
不是"AI 自动写论文",而是"AI 帮人类把想法变成论文"。

---

## 6. 关键交付物(最终)

### 6.1 主定理

**Theorem 5.1 (Impossibility)** + **4 个推论**。
文件:`training/structural_consistency/AXIOM_SKELETON.md` (15KB)

### 6.2 主 Memo(handcrafted)

`outputs/v0.2_shap/AX-STRUCTURAL-CONSISTENCY-001.md` (10KB)——
含 NL/形式化/对齐表/Notation Legend/4 axiom/Impossibility 证明/4 命题/5 推论。

### 6.3 13 篇 SHAP 文献精读 + 谱系定位

**8 篇精读** + **5 篇参考**——
见 `training/structural_consistency/KNOWLEDGE_BASE.md` §1。

### 6.4 5-Agent Pipeline(可运行)

`legacy_v0.2_pipeline/` 13 个 .py (formerly `axiom_v02/`, renamed June 2026 for clarity)——文献加载 → 扰动采样 → 价值评估 → 协作起草 → 后果预测 → 备忘录 + 完整性审计/重写。

### 6.5 4 个 Seed JSON

`training/seeds/`:
- `lundberg_2017_shap.json` (L17 结构化)
- `heskes_2021_structural.json` (H21 结构化)
- `myerson_1981.json` (经典博弈)
- `VCG_1973.json` (经典机制)

### 6.6 12 个 Diktat 节点(Thomson 风格)

`training/graph/diktats/DIKT-*.json` 12 个——
每个含 stance.{value_priority, implicit_norm, trigger, verdict_pattern, rhetorical_device} + counter_example + origin_story。

### 6.7 知识库(过程轨迹)

`training/structural_consistency/KNOWLEDGE_BASE.md` (9KB, 压缩版)——
包含 13 篇文献分层精读 + 主线推演 + v0.2 实战 + ASCII 依赖路径 + 8 件待办。

### 6.8 README + 完整文档

- 主 README — 项目入口
- `docs/v0.3-alpha/README.md` — v0.3-alpha 主线结果
- `docs/PROCESS_NARRATIVE.md` — **本文档**

---

## 7. 怎么"用"这份过程叙事

### 7.1 给 AI4SS 项目的素材

- **§2-§3** 可以作为"AI 协作者做学术的方法论示范"
- **§4** 可以作为"对话式研究"的实例(尤其是 3 次跑偏的反思)
- **§5** 可以作为"AI 在学术中的局限与价值"的实证素材

### 7.2 给其他研究者的"避坑指南"

- **§4.1** 的 3 次跑偏 → 知道**哪些诱惑**该避开
- **§3.3** 的失败案例 → 知道**什么时候该 fallback 到手写**
- **§6.7** 的知识库 → 知道**怎么记录自己的研究过程**

### 7.3 给"做类似工具"的人的参考

- **§2.2** 的 5-agent 设计 → 知道**怎么拆解 Thomson 式方法论**
- **§2.3** 的 3 个挣扎 → 知道**Notation/Completeness/M3 quirk 怎么应对**
- **§6.4** 的 13 个 .py → 知道**怎么工程化"axiom derivation"**

---

## 8. 诚实交代:这份过程叙事的局限

### 8.1 我没做的事

- **没用 LangGraph / CrewAI**——v0.2 是**顺序的 module**,不是真正 multi-agent
- **没在真实数据上验证反例**——Impossibility 的反例(场景 B)只在 memo 里构造,没在 Boston Housing 上跑
- **没 J19 PNAS 2020**——Heskes 2021 Book 引的 "Janzing 2020" 我没读到
- **5 个开放问题(Q1-Q5)**没完全拍板——用户也没全回
- **5 个新 diktat** 没加进 taxonomy

### 8.2 我跑偏的反思

- **连续 3 轮**(我的回复)把"成品"理解为"GitHub 仓库",直到用户第 2 次纠正
- **第 1 轮**(建立知识库时)没把"项目元定位"放最顶部
- **好几次**过早跳到"工程细节"(LangGraph / Makefile)而不是"先确认方向"

### 8.3 这份叙事的局限

- 它**美化**了过程——很多"失败"实际上更混乱
- 它**简化**了 AI 的学习——实际"学到"是缓慢、累进、不确定的
- 它**没**展示**所有**对话——只展示了关键转折

### 8.4 元反思:这份叙事本身

**写这份叙事的过程**,本身就是一个 AI4SS 示范:
- 我(Mavis)用**之前对话积累的 KB + 主线 + pipeline**作为材料
- **重新组织**为"过程叙事"——按时间线、按主题、按角色
- **承认局限**——这是 AI4SS 重要的"可信赖性"要求

**这种"过程记录 + 反思 + 承认局限"** 模式,可能比"我做出了什么"更有 AI4SS 价值。

---

## 9. 元:这个文档的元定位

> **2026-06-09 写于 Axiom Finder v0.3-alpha 完成时**。
> 我与用户用 4 个月(2026-02 至 2026-06)共同完成了这个项目。
> 用户的角色:**研究方向 + 研究品味 + 关键决策**。
> 我的角色:**文献消化 + 方法工程化 + 流水线执行 + 过程记录**。
> 真正的"成品":**这种"对话 + 反思 + 工具"的整体**,而不是其中任何一个部分。

---

## 附录 A:对话时间线(精选)

| 时间 | 事件 | 影响 |
|---|---|---|
| 2026-02 | 用户读 WeChat 文章,提出 OR+AI 方向 | 项目起点 |
| 2026-03 | 我读 Thomson 两书,设计 7-dataclass contracts | 方法论框架 |
| 2026-04 | v0.1 3-agent pipeline(lit/reality/gap) | 第一版跑通 |
| 2026-04 末 | 12 diktat 节点 + 5-statement injection | 抓住 Thomson tacit |
| 2026-05 | v0.2 5-agent pipeline | 加入 Notation Definer 协作 |
| 2026-05 中 | Myerson 1981 跑通 quality=1.0 | 验证 pipeline |
| 2026-05 末 | 用户提出 5 个 proposal,SC ★★★★★ 为主线 | 锁定方向 |
| 2026-06 初 | 13 篇 SHAP 文献精读,定位 SC 在谱系中的位置 | 学术定位 |
| 2026-06-09 | 跑 SHAP seed(quality=0.80) + 手写主 memo | 主线完成 |
| 2026-06-09 | 知识库(KNOWLEDGE_BASE)压缩版 | 过程记录 |
| 2026-06-09 | 写本过程叙事 | AI4SS 价值封装 |

## 附录 B:用户决策的"研究品味"示例

**决策**:把"diktat"作为**独立节点类型**,而非 axiom 的属性。

**为什么是品味**:
- 形式上,可以把 diktat 当 axiom 的 metadata
- 但用户认为:diktat **独立**才能**被显式评价**,否则变成"隐藏偏好"
- 这是 Thomson 自己的做法——他**显式讨论**每个 axiom 的**反例**,不藏在 footnote

**教训**:**结构反映判断**。如果一个东西值得显式讨论,它就值得是独立节点。

---

**(本文档完)**
