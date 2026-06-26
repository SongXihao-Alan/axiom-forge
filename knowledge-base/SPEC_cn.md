# axiom-forge v0.3 — 第二步 & 第三步 技术文档

**主题**：D ⇄ F 交替流水线：发现 → 形式化 → 回译验证 → Z3 一致性检验

**来源**：原始 docx 文件 `第二步/axiom_forge_step2_cn.docx`(第二步) + `第三步/axiom_forge_step3_cn.docx`(第三步);已迁移,docx 文件归档于 git history。

---




1. 整体概述
axiom-forge 是一个从社会科学文献中自动发现并形式化规范性公理的流水线。第二步负责提取、形式化候选公理并通过回译闸门进行质量过滤；第三步使用 Z3 SMT 求解器对形式化结果进行一致性验证。

核心设计原则：  LLM 的语义能力在自然语言层面远强于形式语言层面。正确的做法是先让 LLM 在自然语言中自由搜索（call_1），再压缩为形式表达（call_2），最后用回译检验压缩是否保真（call_3）。强迫 LLM 先在形式语言中工作会浪费其最强的能力。

1.1  完整流水线一览
文本块
|
v  call_1_discover()      --> AxiomCandidateNL      (自然语言候选)
|
v  call_2_formalize()     --> AxiomCandidateFormal  (结构化 JSON + SMT-LIB2)
|
v  call_3_backtranslate() --> BackTranslationResult (相似度闸门)
|
v  z3_verify()            --> AxiomVerificationResult
|
v  AxiomRecord --> 写入 JSONL 知识库

三次独立 LLM 调用，一次 Z3 验证。三次调用严格隔离：call_3 不能看到原始自然语言声明，只能看到形式化表达。这种隔离使回译成为真正有意义的保真度检验，而不是同义反复。


2. 第二步 — D ⇄ F 交替提取
第二步由四个文件组成：discover.py（call_1）、formalize.py（call_2）、backtranslate.py（call_3）、pipeline.py（调度器）。

2.1  discover.py — call_1_discover()
作用：从原始文本块中提取规范性声明，不使用任何预定义 schema 锚定。模型可以自由地发现任何断言代理人、机制或分配应当或必须如何运作的主张。

为什么不先给 schema？  Schema 锚定会导致 LLM 只找符合模板结构的公理，漏掉其他所有类型。给了对称性模板，它就只找对称性公理，效率公理会被完全忽略。自由发现最大化召回率。

输入：DiscoverInput
字段名
类型
说明
chunk_id
str
文本块的唯一 ID
text
str
原始文本：摘要、段落或章节（最多 4000 字符）
source_paper
str
论文标题或 DOI，用于来源追溯
domain
str
取值之一：game_theory | mechanism_design | social_choice | welfare_economics | credit_systems | political_philosophy | ml_fairness | history | math | other

输出：list[AxiomCandidateNL]（每块 0–5 个）
字段名
类型
说明
candidate_id
str
提取时分配的 UUID4
claim_nl
str
用一句清晰的英文表述的规范性声明
claim_type
str
axiom | principle | constraint | impossibility | characterization
entities
list
关键变量：agent, coalition, allocation, value function 等
normative_strength
str
must | should | may | must_not
confidence
float
LLM 自报：该声明是规范性的可信度（0–1）
raw_quote
str
来源文本中的原文引用，作为证据锚点
low_confidence
bool
confidence < 0.5 时为 True，标记但不丢弃

关键设计选择
instructor 结构化输出：Pydantic schema RawCandidateList 强制 JSON 格式，防止 LLM 输出自由文本。
规范性 vs 描述性区分：系统提示明确列举两类示例。定义、实证发现和文献综述不属于规范性声明，会被排除。
低置信度候选保留：confidence < 0.5 设置 low_confidence=True，但候选保留在知识库中。边界案例通常最有价值。
文本长度保护：短于 100 字符的块跳过；文本截断至 4000 字符防止 token 超限。

2.2  formalize.py — call_2_formalize()
作用：接收 AxiomCandidateNL，生成结构化形式表达，包括供 Z3 使用的 SMT-LIB2 片段。最关键的要求：模型必须命名它选择了哪种解释，并列出备选解释。这是强制要求，不是可选项。

静默失真问题：  许多社会科学术语有多种非等价的技术定义。「对称代理人应获得相同份额」至少可以映射到四个不同的形式公理：anonymity（置换不变性）、symmetry（边际贡献相等）、equal treatment（等价代理人）、interchangeability（最强版本）。如果不强制模型声明它的选择，形式化结果就无法审计。

输出：AxiomCandidateFormal
字段名
类型
说明
quantifier
str
forall | exists | forall_exists | none
bound_variables
list
使用的变量名，如 ['i', 'j', 'S', 'v']
condition
str
前件（IF 部分）的符号表达，无前件时为空字符串
conclusion
str
后件（THEN 部分）的符号表达
formal_type
str
equality | inequality | implication | iff | negation | ...
smt_fragment
str
有效的 SMT-LIB2 字符串（declare-const + assert），或 CANNOT_FORMALIZE
interpretation_chosen
str
强制：所选解释的名称，不能为空
alternative_interpretations
list
未选择的其他有效形式化，若存在则至少列出 1 个
formalization_confidence
float
0–1，声明越模糊置信度越低
shap_variables
dict
仅 ml_fairness 域：phi_i、f、S、v 到 SHAP 含义的映射

各领域专属词汇提示
每个 domain 向 prompt 注入专属词汇提示块，防止模型使用通用变量名：

game_theory：v: 2^N → ℝ，边际贡献 v(S∪{i})−v(S)，对 symmetry / anonymity / equal_treatment 的歧义提示
mechanism_design：IC dominant vs Bayes vs ex-post；IR ex-ante vs interim vs ex-post 的区分
social_choice：IIA 弱版本 vs 强版本；Pareto 弱 vs 强；non-dictatorship vs anonymity
ml_fairness：φ_i（Shapley 值），v(S) = E[f(x)|x_S]，conditional vs interventional vs marginal SHAP 的歧义

SMT-LIB2 规则（在 prompt 中强制执行）
所有自由变量用 (declare-const name Type) 声明
类型只能是 Real、Int 或 Bool
只能有一个 (assert ...) 语句，不能有 check-sat 或 get-model
不能使用 lambda 或二阶量词
若无法用一阶 SMT-LIB2 表达，输出 CANNOT_FORMALIZE

后处理
LLM 调用返回后，formalize.py 会剥除 Markdown 代码块标记，并运行结构校验（括号平衡 + 至少一个 assert）。校验失败时 smt_fragment 被强制设为 CANNOT_FORMALIZE，而不是把有问题的字符串传给 Z3。

2.3  backtranslate.py — call_3_backtranslate()
作用：仅从形式化表达重建自然语言含义，不允许看到原始 claim_nl。然后计算重建结果与原始声明的相似度。若两者差异过大，说明形式化步骤改变了语义，候选被标记为需要人工审查。

为什么要隔离？  如果 call_3 能看到原始 claim_nl，模型会直接改写它，检验就成了同义反复，毫无意义。隔离之后，相似度分数才能真实衡量形式化步骤中损失了多少语义信息。

两阶段相似度检验
第一阶段 — voyage-3 嵌入余弦相似度（快速，约 50ms）：计算 claim_nl_original 和 claim_reconstructed 的嵌入向量余弦相似度。默认阈值 0.75。
第二阶段 — LLM-as-judge（可选）：仅在第一阶段分数落在边界区间 [0.65, 0.75) 时触发。加权平均：60% 嵌入 + 40% judge。避免对明显通过/失败的案例发出额外 API 调用。

输出：BackTranslationResult
字段名
类型
说明
claim_reconstructed
str
仅从形式表达生成的自然语言句子
similarity_score
float
与原始 claim_nl 的余弦相似度（0–1）
similarity_method
str
embedding | embedding+judge | skipped | failed
passed
bool
score >= 阈值（默认 0.75）时为 True
failure_reason
str
passed=False 时的人类可读原因
ambiguity_preserved
bool
重建结果是否明确提及了 interpretation_chosen
judge_score
float
LLM judge 分数（触发时），否则为 None

失败处理策略
失败不等于丢弃。passed=False 的候选以 status=needs_human_review 写入知识库。这些案例最有价值：claim_nl 与 claim_reconstructed 的差异本身就是一个发现，说明该公理在形式化时存在真实的语义歧义，值得在论文中报告。

CANNOT_FORMALIZE 的处理
若 smt_fragment == CANNOT_FORMALIZE，直接跳过回译，候选以 SKIPPED 状态进入 Z3 步骤，不会被丢弃。

2.4  pipeline.py — 调度器
将四个步骤串联为单一可调用函数。处理 DiscoverInput 块列表，将 AxiomRecord 对象写入 JSONL 文件，并生成配套的 PipelineReport JSON。

AxiomRecord — 知识库最终条目（35 个字段）
每条记录包含完整的来源链：原始自然语言声明、形式化表达、回译结果和 Z3 验证结果。status 字段汇总流水线结果：

status 值
含义
后续动作
verified
回译通过 + Z3 sat
纳入 gold set
z3_unsat
回译通过 + Z3 unsat
潜在不可能性定理 — 重点审查
needs_human_review
回译失败或 Z3 unknown/timeout
送交专家评审
cannot_formalize
SMT 片段 = CANNOT_FORMALIZE
保留用于定性分析
formalization_failed
call_2 API 调用失败
重试或丢弃

PipelineReport — Lane C 收敛指标
mean_backtranslation_similarity  — 整体形式化保真度信号
backtranslation_pass_rate  — 通过回译闸门的比例（目标 ≥ 0.80 视为收敛）
impossibility_count  — Z3 unsat 结果数量（这些是真正的发现）
cannot_formalize_rate  — 一阶 SMT-LIB2 无法表达的比例
z3_tier_distribution  — Tier A / B / C 使用分布

命令行用法
# 结构演示（无需 API key）
python pipeline.py --demo

# 快速运行（跳过 Z3，用于原型验证）
python pipeline.py --input chunks.jsonl --output records.jsonl --skip-z3

# 完整运行
python pipeline.py --input chunks.jsonl --output records.jsonl

# 带参数
python pipeline.py --input chunks.jsonl --output records.jsonl \
--bt-threshold 0.75 --z3-timeout 5000 --model claude-sonnet-4-6




已知局限
Z3 仅支持一阶逻辑。需要二阶量词的社会科学公理（如「对所有可能机制」）无法在 SMT-LIB2 中表达，将被标记为 CANNOT_FORMALIZE。这是结构性限制，应在论文中作为局限性诚实陈述。

回译阈值是经验值。默认阈值 0.75 基于 voyage-3 测试示例确定，应在 gold set（Lane A）上重新校准后再作为最终收敛标准。

Tier C 重新形式化具有不确定性。相同声明在不同运行中可能产生不同的 SMT 片段。如需可复现性，应在 Tier C prompt 中设置 temperature=0。

速率限制。默认 parallel_workers=1 为顺序执行。处理 5000 篇论文耗时较长。S2 API key 在沙盒中限速 100 次/7 天，但 pipeline.py 使用 Anthropic API，不受此限制。

嵌入模型可用性。voyage-3 不可用时，backtranslate.py 降级为 TF-IDF 余弦相似度，质量显著下降，会产生更多假阴性。确认 EMBEDDING_MODEL 环境变量已正确设置。

3. 第三步 — Z3 一致性验证（z3_verify.py）
第三步接收形式化后的公理候选，运行三层验证流程。层级根据 SMT 片段质量自动选择。

3.1  层级路由逻辑
smt_fragment == CANNOT_FORMALIZE  -->  直接返回，不进 Z3
backtranslation_passed == False   -->  SKIPPED（回译闸门未通过）
Tier A: 正则表达式检测到平凡结构  -->  即时返回结果
Tier B: Z3 可以直接解析片段      -->  毫秒级验证
Tier C: Tier B 失败              -->  LLM 重新形式化 --> Z3

3.2  Tier A — 模式匹配检测
Tier A 在调用 Z3 之前运行，用正则表达式检测三类平凡情况：

恒真（Tautology）：(assert (or p (not p))) — 永远为真，无信息量
矛盾（Contradiction）：(assert false) 或 (assert (and p (not p))) — 永远为假
平凡满足（Vacuous）：(assert (= x x)) 或 (assert true) — 无条件成立

这三类情况以置信度 0.95 直接返回，不调用 Z3。它们通常是 LLM 形式化错误，而非真正的公理。

3.3  Tier B — 直接 Z3 验证
将 SMT-LIB2 片段直接传入 z3.Solver().from_string()。三种结果：

sat：存在满足赋值。公理一致。Z3 返回具体变量值作为模型。置信度 0.90。
unsat：不存在满足赋值。这是不可能性结果：没有任何代理人配置、分配或机制能同时满足所述条件。Z3 返回 unsat core。置信度 0.95。这是最有价值的发现类型。
unknown：Z3 超时或问题在该片段中不可判定。送交人工审查。置信度 0.30。

SHAP 专项支持（Tier B）
Tier B 识别标准 SHAP 变量名，并为四个核心 SHAP 公理提供预置 SMT-LIB2 模板：
效率公理（Efficiency）：(assert (= phi_sum f_x))
对称公理（Symmetry）：(assert (=> (= marginal_i marginal_j) (= phi_i phi_j)))
哑变量公理（Dummy）：(assert (=> (= marginal_i 0.0) (= phi_i 0.0)))
线性公理（Linearity）：(assert (= phi_combined (+ phi_f phi_g)))

3.4  Tier C — LLM 重新形式化
当 Tier B 无法解析 SMT 片段时，Tier C 向 LLM 发出重新形式化请求：要求它将原始 claim_nl 直接翻译为有效的 SMT-LIB2 字符串。生成结果再次交给 Tier B。若仍失败，状态设为 parse_error。

SHAP 模板捷径：  在发起 LLM 调用之前，Tier C 先检查 claim_nl 是否提到了已知的 SHAP 公理名称（efficiency、symmetry、dummy、linearity）。若匹配，直接使用预置模板，节省一次 API 调用。

置信度惩罚：Tier C 结果的置信度在 Tier B 基础上乘以 0.85，反映重新形式化引入的额外不确定性。

3.5  输出：AxiomVerificationResult
字段名
类型
说明
tier_used
str
A | B | C | SKIPPED | CANNOT
z3_status
str
sat | unsat | unknown | vacuous | tautology | contradiction | cannot_formalize | skipped_backtranslation_fail | parse_error | timeout
z3_model
dict
满足赋值（sat 时）
unsat_core
list
导致不可满足的约束集合（unsat 时）
verification_confidence
float
0–1，Tier C 惩罚后的置信度
smt_used
str
实际传入 Z3 的 SMT-LIB2 字符串（用于调试）

3.6  置信度映射
z3_status
置信度
含义
sat
0.90
公理一致
unsat
0.95
不可能性 — 最强结果，重点关注
tautology
0.95
恒真 — 形式化产生的假象
contradiction
0.95
恒假 — 形式化错误
vacuous
0.80
平凡满足
unknown
0.30
超时或不可判定
parse_error
0.10
SMT 语法错误
timeout
0.20
Z3 超时（增大 --z3-timeout）


4. 与 Lane B / Lane C 的集成
4.1  lane_b_evaluator.py 的改造
将原来的单次调用结构替换为每个条目三次顺序调用：
# 旧结构
score = llm_evaluate(item)

# 新结构
nl_result     = call_1_discover(item.text)
formal_result = call_2_formalize(nl_result)
bt_result     = call_3_backtranslate(formal_result)
z3_result     = z3_verify(formal_result, bt_result)

backtranslation_similarity 作为新列写入 lane_b_predictions.json，与现有评分维度并列。

4.2  lane_c_feedback.json 新增收敛维度
mean_backtranslation_similarity  — 整体形式化保真度
backtranslation_pass_rate  — 通过回译闸门的比例（目标 ≥ 0.80 视为 converged_formalization=True）
formalization_fidelity_score  — 新增的 Lane C QWK 计算维度
converged_formalization  — 仅当 pass_rate ≥ 0.80 时为 True

收敛规则：  lane_c_feedback.json 中的整体 converged 标志，只有在「现有维度 QWK >= 0.6」AND「converged_formalization == True」同时满足时才为 True。内容维度分数高但形式化保真度低的流水线不视为收敛。


5. 依赖与环境配置
5.1  Python 包
z3-solver>=4.12.0      # SMT 求解器
anthropic>=0.25.0      # LLM API
instructor>=1.0.0      # 基于 Pydantic 的结构化输出
pydantic>=2.0.0        # 数据验证
numpy>=1.24.0          # 数值计算
scikit-learn>=1.3.0    # cosine_similarity（TF-IDF 兜底）

5.2  环境变量
字段名
类型
说明
ANTHROPIC_API_KEY
str
必填。Anthropic API 密钥
S2_API_KEY
str
语料库摄取必填（Semantic Scholar）
BACKTRANSLATION_THRESHOLD
float
相似度阈值（默认 0.75）
BACKTRANSLATION_JUDGE_THRESHOLD
float
LLM judge 触发下界（默认 0.65）
Z3_TIMEOUT_MS
int
Z3 求解器超时，毫秒（默认 5000）
EMBEDDING_MODEL
str
嵌入模型（默认 voyage-3）
DISCOVER_LOW_CONF_THRESHOLD
float
低置信度标记阈值（默认 0.5）
DISCOVER_MIN_TEXT_LENGTH
int
最小块长度，字符数（默认 100）


6. 已知局限
Z3 仅支持一阶逻辑。需要二阶量词的社会科学公理（如「对所有可能机制」）无法在 SMT-LIB2 中表达，将被标记为 CANNOT_FORMALIZE。这是结构性限制，应在论文中作为局限性诚实陈述。

回译阈值是经验值。默认阈值 0.75 基于 voyage-3 测试示例确定，应在 gold set（Lane A）上重新校准后再作为最终收敛标准。

Tier C 重新形式化具有不确定性。相同声明在不同运行中可能产生不同的 SMT 片段。如需可复现性，应在 Tier C prompt 中设置 temperature=0。

速率限制。默认 parallel_workers=1 为顺序执行。处理 5000 篇论文耗时较长。S2 API key 在沙盒中限速 100 次/7 天，但 pipeline.py 使用 Anthropic API，不受此限制。

嵌入模型可用性。voyage-3 不可用时，backtranslate.py 降级为 TF-IDF 余弦相似度，质量显著下降，会产生更多假阴性。确认 EMBEDDING_MODEL 环境变量已正确设置。