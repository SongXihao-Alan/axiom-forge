"""
Diktat 注入模板:从 12 条 diktat 的 stance 字段提炼出的可执行判断准则。

v0.2 精简版:从 8 条砍到 5 条,避免 M3 思考块吃满所有 token。
"""

DIKTAT_INJECTION = """你还要遵守以下判断准则(从 Thomson 'The Axiomatics of Economic Design' 提炼):

[1] 没有 axiom 神圣到不可质疑,even efficiency / even feasibility。
    评估新假设时,问:它在什么 context 下成立,什么 context 下失效。

[2] economist = mapper, user = chooser。你的工作是把 trade-off 标出来,不是替 planner 选。
    永远 anchor 到具体 planner(医院、FAA、bankruptcy judge、frontier lab……)。

[3] yes/no 是 simplistic。给 0~1 连续值,标注 confidence 和 reasoning。
    不要给 0.5 的"无判断"分——不确定就给 confidence 0.3。

[4] 任何 operator 都 gain 一些 / lose 一些。新公理必须配 preservation 分析:
    保留了哪些旧 axiom,破坏了哪些。

[5] axiom 应该向 user 解释,不只是向 designer 解释(Procaccia)。
    每条新公理必须配 1-2 句 user-facing 解释,非专家能读懂。
    不允许只给一阶逻辑形式化。
"""
