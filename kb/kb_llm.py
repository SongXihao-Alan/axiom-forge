#!/usr/bin/env python3
"""
Axiom Forge KB-M3 Bridge (Phase 2.4)

让 CLI 通过 M3 API 真正能:
- ask: 读 KB + 问 M3 → 答
- explore-anchor: 探索锚
- validate: 用 M3 验证 KB 节点质量

注意:M3 API 是 必需的(export MINIMAX_API_KEY=xxx)
不调 M3 时 CLI 仍能跑(list/query/search/show),只是不能 ask/explore/validate
"""
import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

# 加载 .env(从项目根找)
try:
    from dotenv import load_dotenv
    _ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
    if _ENV_PATH.exists():
        load_dotenv(_ENV_PATH)
except ImportError:
    pass


# 复用现有 M3Client
KB_ROOT = Path(__file__).resolve().parent / "nodes"
AGENT_LLM_PATH = Path(__file__).resolve().parent.parent / "agents"
sys.path.insert(0, str(AGENT_LLM_PATH))
from llm import M3Client  # noqa: E402


def load_all_nodes():
    """加载所有节点。"""
    nodes = {}
    for type_dir in KB_ROOT.iterdir():
        if not type_dir.is_dir():
            continue
        for f in type_dir.glob("*.json"):
            try:
                n = json.loads(f.read_text(encoding="utf-8"))
                if "id" not in n or not n.get("id"):
                    n["id"] = n.get("name") or f.stem.upper()
                if "type" not in n or not n.get("type"):
                    n["type"] = type_dir.name.rstrip("s")
                nodes[n["id"]] = n
            except Exception:
                pass
    return nodes


def load_relations():
    """加载 relations.json。"""
    p = KB_ROOT / "relations.json"
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))["relations"]


# ============================================================
# M3 检索增强
# ============================================================


def retrieve_relevant_nodes(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Phase 2.2 简化版 RAG:加权关键词 + 跨字段评分"""
    nodes = load_all_nodes()
    query_words = set(re.findall(r'\w+', query.lower()))
    # 先检查 query 中是否包含完整节点 ID(直接命中)
    query_lower = query.lower()
    direct_match_ids = set()
    for n in nodes.values():
        if n.get("id", "").lower() in query_lower:
            direct_match_ids.add(n["id"])

    scored = []
    for n in nodes.values():
        score = 0
        # 直接 ID 命中: 极大加分
        if n["id"] in direct_match_ids:
            score += 1000
        fields_high = [n.get("title", ""), n.get("label_zh", ""), n.get("label_en", "")]
        fields_mid = [n.get("nl", ""), n.get("formal", ""), n.get("abstract_nl", ""), n.get("description", "")]
        fields_low = [" ".join(n.get("tags", [])), " ".join(n.get("aliases", []))]
        for f in fields_high:
            if f:
                for w in query_words:
                    if w in f.lower(): score += 5
        for f in fields_mid:
            if f:
                for w in query_words:
                    if w in f.lower(): score += 2
        for f in fields_low:
            if f:
                for w in query_words:
                    if w in f.lower(): score += 1
        for a in n.get("anchors", []):
            for w in query_words:
                if w in str(a).lower(): score += 0.5
        if score > 0:
            scored.append((score, n))
    scored.sort(key=lambda x: -x[0])
    return [n for _, n in scored[:top_k]]


def format_node_medium(node: Dict[str, Any]) -> str:
    """节点的中等粒度描述(给 M3 当 context)"""
    parts = [f"[{node.get('id', '?')}]({node.get('type', '?')})"]
    if node.get("title"):
        parts.append(f"  Title: {node['title']}")
    if node.get("label_zh"):
        parts.append(f"  Label: {node['label_zh']} / {node.get('label_en', '')}")
    if node.get("nl"):
        parts.append(f"  NL: {node['nl'][:300]}")
    elif node.get("description"):
        parts.append(f"  Description: {node['description'][:300]}")
    if node.get("formal"):
        parts.append(f"  Formal: {node['formal'][:200]}")
    if node.get("anchors"):
        parts.append(f"  Anchors ({len(node['anchors'])}):")
        for a in node["anchors"][:3]:
            t = a.get("type", "?")
            sub = a.get("subtype", "") or a.get("tradition", "")
            parts.append(f"    [{t}] {sub}")
    return "\n".join(parts)


def ask_m3(query: str, model: str = "MiniMax-M3", max_tokens: int = 4000) -> Optional[str]:
    """调 M3,带 KB context 答 query"""
    try:
        client = M3Client(model=model, temperature=0.3)
    except KeyError:
        return None  # 没设 API key
    # 检索 top-5 节点
    relevant = retrieve_relevant_nodes(query, top_k=5)
    if not relevant:
        return None
    # 拼 context
    context = "\n\n---\n\n".join(format_node_medium(n) for n in relevant)
    # 加入 REPRODUCTION README 摘要(让 M3 知道 T1/T2/T3 任务定义)
    repro_path = Path(__file__).resolve().parent / "REPRODUCTION" / "README.md"
    if repro_path.exists():
        try:
            repro_text = repro_path.read_text(encoding="utf-8")[:2500]  # limit
            context += f"\n\n=== REPRODUCTION README (摘要)===\n{repro_text}"
        except Exception:
            pass
    # 加入 KB 统计信息
    stats_path = None
    try:
        from kb_query import cmd_stats
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            cmd_stats([])
        stats_text = buf.getvalue()
        context += f"\n\n=== KB STATS ===\n{stats_text[:1500]}"
    except Exception:
        pass
    system = (
        "你是 Axiom Forge 的研究助手。Axiom Forge 是 1 个知识库 + CLI 工具,核心是 "
        "**Structural Consistency (SC)** 1 个新 axiom 和 **Impossibility Theorem 5.1** 1 个主定理。"
        "KB 里 85+ 节点覆盖: SHAP 文献(13 篇) / Thomson 风格 axiom 系统 / 价值观谱系(6 大类 33 锚) / 现实场景 / 经典权衡。"
        "**索引结构**: axiom (AX-*) / theorem (TH-*) / literature (LIT-*) / value_anchor (VA-*, value_class= moral/interest/...) / scenario (SC-*) / tradeoff (TR-*) / diktat (DIKT-*)"
        "**复现包** (kb/REPRODUCTION/): README.md 含 T1/T2/T3 任务定义, EVALUATION_RUBRIC.md 含评估标准"
        "**CLI 命令** (axiom-forge): list, query, search, show, stats, relations, graph, anchors, anchors-by-type, compressed, value-tree, ask, explore-anchor, validate"
        "你回答必须 **基于** 下面给的 KB context。如果 KB 没相关信息,直接说'KB 暂无相关信息'。"
        "回答尽量**具体引用节点 ID**(如 AX-SC-001, TH-IMP-501),不要泛泛而谈。"
    )
    user = (
        f"## KB Context (top-5 相关节点):\n\n{context}\n\n"
        f"## Question:\n{query}\n\n"
        f"## Answer(引用节点 ID):"
    )
    try:
        raw = client.chat(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            json_mode=False,
            max_tokens=max_tokens,
        )
        # 剥掉 M3 的 <think>...</think> 块(它会吞答案)
        return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    except Exception as e:
        return f"ERROR: {e}"


def explore_anchor_m3(anchor_type: str, max_tokens: int = 2000) -> Optional[str]:
    """用 M3 探索某一类锚, 给出哲学/经验/社群 3 维解读"""
    try:
        client = M3Client(model="MiniMax-M3", temperature=0.5)
    except KeyError:
        return None
    # 找所有带此锚的节点 + value_anchor 节点本身(value_class 匹配)
    nodes = load_all_nodes()
    matches = []
    for n in nodes.values():
        # 1. 节点带此锚
        for a in n.get("anchors", []):
            if a.get("type") == anchor_type:
                matches.append((n, a))
                break
        else:
            # 2. value_anchor 节点本身(value_class 匹配, 如 "philosophical")
            if n.get("value_class") == anchor_type:
                matches.append((n, {"type": anchor_type, "subtype": n.get("value_subclass", "")}))
    if not matches:
        return None
    # 拼 context
    context_lines = []
    for n, a in matches[:20]:  # limit 20
        context_lines.append(f"- {n['id']} ({n['type']}): {n.get('label_zh', n.get('nl', n.get('title', ''))[:60])}")
    context = "\n".join(context_lines)
    system = (
        f"你是 Axiom Forge 的研究助手。用户在探索 KB 中所有带 **{anchor_type}** 锚的节点。"
        f"请从 3 维解读(哲学 / 经验 / 社群), 给出这些节点的 **{anchor_type}** 解读和洞察。"
        "注意:3 锚**完全平等**, 不要给'哲学 > 经验'的暗示。"
    )
    user = (
        f"## 节点 (top-20 带 {anchor_type} 锚):\n\n{context}\n\n"
        f"## 任务:\n1. 这 {anchor_type} 锚在 KB 中覆盖了哪些 axiom / 文献 / scenario?\n"
        "2. 哪些节点最 surprising(应当带这锚但没带, 或带了但锚弱)?\n"
        "3. 整体看, {anchor_type} 锚揭示了什么 pattern?\n\n"
        "## 解读(中文):"
    )
    try:
        raw = client.chat(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            json_mode=False,
            max_tokens=max_tokens,
        )
        return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    except Exception as e:
        return f"ERROR: {e}"


def validate_node_m3(node_id: str, max_tokens: int = 2000) -> Optional[str]:
    """用 M3 验证 KB 节点质量"""
    nodes = load_all_nodes()
    n = nodes.get(node_id)
    if not n:
        return None
    try:
        client = M3Client(model="MiniMax-M3", temperature=0.2)
    except KeyError:
        return None
    # 节点完整 JSON
    node_text = json.dumps(n, ensure_ascii=False, indent=2)
    system = (
        "你是 Axiom Forge 的 KB 质量评估助手。"
        "请评估 1 个 KB 节点的 **质量**, 从 4 维:"
        "1. **形式正确性**: formal/nl 是否清晰, 是否自洽"
        "2. **锚合理性**: 3 锚 (empirical/philosophical/community) 是否合理, 是否过多/过少"
        "3. **引用准确性**: source.citations 是否段级精确, 有无错配"
        "4. **KB 一致性**: 跟其他节点的 depends_on / parent_child 关系是否合理"
        "给出 **5 档评分**: 优秀 (>=90) / 良好 (>=75) / 中等 (>=60) / 待改进 (>=40) / 失败 (<40)"
        "并具体指出改进建议。"
    )
    user = (
        f"## 节点 (id={node_id}):\n\n```json\n{node_text}\n```\n\n"
        f"## 评估:"
    )
    try:
        raw = client.chat(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            json_mode=False,
            max_tokens=max_tokens,
        )
        return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    except Exception as e:
        return f"ERROR: {e}"


def check_api_key() -> bool:
    """检查 MINIMAX_API_KEY 是否设置"""
    return bool(os.environ.get("MINIMAX_API_KEY"))


if __name__ == "__main__":
    # 测试
    print("MINIMAX_API_KEY set:", check_api_key())
    if check_api_key():
        print("\nTest ask: '什么是 Structural Consistency?'")
        ans = ask_m3("什么是 Structural Consistency?")
        print(ans[:500] if ans else "No answer")
