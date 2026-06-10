# Contributing to Axiom Forge

> **欢迎贡献!** Axiom Forge 是 **AI4SS 前身**——一个扩散性价值观探索 program。
> 我们**不只是**接受代码贡献——**KB 节点贡献**和**复现任务结果**都欢迎。

---

## 1. 谁能贡献

| 角色 | 怎么贡献 |
|---|---|
| **任何用 CLI 的人** | `axiom-forge list` → 发现缺什么 → 加节点 (见 §3) |
| **博弈论 / XAI / 哲学研究生** | 完成 `kb/REPRODUCTION/` 里的 T1/T2/T3 任务 |
| **开发者** | 提 issue / PR (CLI 新功能,新命令) |
| **研究者** | 给 KB 加新文献节点,加新 theorem 节点 |

**前置条件**:
- 知道 cooperative game theory / feature attribution 至少一种
- 不需要懂 LLM / Python 内部
- 工具中立性反馈表(5 个问题)必填

---

## 2. 3 种贡献方式(从轻到重)

### 2.1 轻:提 issue

- 报 bug / 提问题
- **不需要写代码**

### 2.2 中:加 KB 节点(纯数据)

- 加 1 个 axiom / theorem / literature / value_anchor 节点
- 格式:参考 `kb/SCHEMA.md` + 已有节点
- 提 PR,把 JSON 放 `kb/nodes/<type>/<ID>.json`
- **需要 review** (因为 3 锚要"完全平等",不能暗示优先级)

### 2.3 重:加 CLI 命令 / 加 M3 prompt

- 提 PR 到 `kb/kb_query.py` 或 `kb/kb_llm.py`
- 跑通后必须 `axiom-forge help` 看新命令
- 写 1 个 demo 在 PR description

---

## 3. KB 节点贡献详细步骤

### 3.1 选 type

| Type | 什么时候加 |
|---|---|
| `axiom` | KB 没有的公理(你想加的) |
| `theorem` | KB 没有的定理(你自己的结果) |
| `literature` | KB 没有的论文(13 篇 SHAP 之外) |
| `value_anchor` | 6 大类中没有的子类(eg 儒家仁) |
| `diktat` | Thomson 风格评价视角(没覆盖) |
| `scenario` | 现实场景(eg 教育 / 医疗 / 招聘) |
| `tradeoff` | 经典权衡(eg 隐私 vs 透明) |
| `assumption` | 新假设(eg f 是 sparse linear) |

### 3.2 JSON 模板

参考 `kb/SCHEMA.md` + 已有节点。**最简模板**(以 value_anchor 为例):

```json
{
  "id": "VA-PHIL-CONFUCIAN-REN",
  "type": "value_anchor",
  "version": "1.0",
  "created": "2026-06-10",
  "status": "seed",
  "value_class": "philosophical",
  "value_subclass": "confucian_ren",
  "label_zh": "仁",
  "label_en": "Confucian benevolence (Ren)",
  "description": "Confucian virtue: caring for others, especially through reciprocity",
  "cross_cultural_consistency": "medium",
  "domain": "philosophical",
  "tags": ["philosophical", "confucian", "east_asian"],
  "anchors_self": [
    {"type": "empirical", "subtype": "moral_consensus", "evidence": "East Asian philosophical tradition"}
  ],
  "source": {
    "primary": "Analects 12:22",
    "user_provided": true
  }
}
```

### 3.3 必填字段(9 个)

1. `id`(唯一,前缀匹配 type:`AX-` / `AS-` / `TH-` / `LIT-` / `VA-` / `SC-` / `TR-` / `DIKT-`)
2. `type`(从 8 类选 1)
3. `version`,`created`,`status`
4. 核心字段(`nl` / `formal` / `title` / `value_class` / `name` 至少 1)
5. `domain`
6. `tags`
7. `anchors`(3 锚**完全平等** — 经验/哲学/社群任选 1+,**不暗示优先级**)
8. `source`(`primary` 必填)
9. `process_meta`(`[HUNCH]` / `[AH-HA]` / `[TODO]` 等)

### 3.4 自动验证(可选)

```bash
./axiom-forge stats        # 看节点数 +1
./axiom-forge show <NEW_ID>  # 看节点
./axiom-forge relations <NEW_ID>  # 看关系
./axiom-forge anchors <NEW_ID>  # 看锚
```

---

## 4. 复现任务贡献

`kb/REPRODUCTION/` 里有 **3 个任务** (T1/T2/T3) + 评估标准。

任何想跑复现的人:
1. 选 1 个任务
2. 按 README.md 步骤做
3. 提交:任务输出(JSON 或 MD)+ 反思 (200-500 字) + 工具中立性反馈表(5 问题)
4. 提 PR 到 `kb/REPRODUCTION/contributions/<your-name>/`
5. 我们**评估** (不评判对错,只评过程质量)

**详见**:`kb/REPRODUCTION/EVALUATION_RUBRIC.md`

---

## 5. 开发工作流(开发者向)

### 5.1 本地设置

```bash
git clone <repo>
cd axiom-forge
pip install -r requirements.txt
cp .env.example .env  # 填 MINIMAX_API_KEY
chmod +x axiom-forge
./axiom-forge list  # 验证能跑
```

### 5.2 加新 CLI 命令

1. 在 `kb/kb_query.py` 加 1 个 `cmd_xxx()` 函数
2. 在 `cmds` dict 注册
3. 在 `cmd_help()` 加 help 文本
4. 跑 `./axiom-forge <新命令>` 验证
5. 提 PR

### 5.3 加新 M3 桥接

1. 在 `kb/kb_llm.py` 加 1 个 `xxx_m3()` 函数
2. 在 `kb/kb_query.py` 加对应 `cmd_xxx()` 调用它
3. 跑 `./axiom-forge <新命令> "test query"` 验证
4. 提 PR

---

## 6. 工具中立性原则(必读)

> 这是项目的**元层价值**。任何贡献必须遵守。

1. **3 锚完全平等** —— empirical / philosophical / community, **1 个就够**
2. **不暗示优先级** —— 不要加 `✓✓` 或 "主导"
3. **工具中立** —— CLI 不预设"哪个 axiom 正确"
4. **先探索后深挖** —— 不是对立,是顺序
5. **过程可追溯** —— 任何结论能回溯到 KB / 文献 / CLI 输出

**违反这些原则的 PR 会被拒**。

---

## 7. Code Style

- Python 3.11+ (用 `dict` / `list` typing hints)
- 文件用 `pathlib` 不混 `os.path`
- 错误用 `try/except` + print 友好信息
- CLI 命令 30 秒内能跑(测试)
- KB 节点 JSON 用 2 空格 indent

---

## 8. Commit 规范

- `feat: <新功能>`
- `fix: <bug 修复>`
- `docs: <文档>`
- `kb: <新节点 / 新关系>`
- `refactor: <重构,无新功能>`
- `test: <测试>`

例:`kb: add VA-PHIL-CONFUCIAN-REN value anchor`

---

## 9. PR 模板

```markdown
## 类型
- [ ] Bug 修复
- [ ] 新功能
- [ ] KB 节点贡献
- [ ] 复现任务结果
- [ ] 文档
- [ ] 重构

## 描述
<什么改了 + 为什么>

## 测试
- [ ] 跑了 `./axiom-forge list / show / relations`
- [ ] 跑了新命令(如果加)
- [ ] 跑了 M3 集成(如果加)

## 工具中立性
- [ ] 3 锚无优先级暗示
- [ ] 探索 / 深挖是顺序,不是对立
- [ ] 过程可追溯
```

---

## 10. 紧急联系

- 提 issue (首选)
- 邮件(看 `package.json` / `pyproject.toml`)
- 任何问题先看 `docs/PROCESS_NARRATIVE.md` 理解项目元层

---

**任何贡献都感谢!** Axiom Forge 是开源 / 工具中立 / 价值多元的。
