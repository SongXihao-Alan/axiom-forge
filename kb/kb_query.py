#!/usr/bin/env python3
"""
Axiom Forge CLI v2.0 (Phase 1.4 + 1.5 + 2.2 + 2.3 完整版)

命令:
  list                              列出所有节点
  query <keyword>                   关键词查询(基础)
  search <query>                    语义搜索 (RAG 简化版,加权匹配)
  show <NODE_ID>                    显示节点完整 JSON
  stats                             知识库统计
  relations <NODE_ID>               显示节点关系
  graph <NODE_ID> [--depth N]       关系图(从某节点出发 N 跳)
  anchors <NODE_ID>                 显示节点的所有锚
  anchors-by-type <type>            按锚类型列节点
  compressed <NODE_ID> [粒度]       多粒度压缩 (full/medium/tiny)
  value-tree                        价值观谱系图
  explore [--anchor TYPE]           按锚探索节点
  help                              帮助
"""
import sys
import json
import re
from pathlib import Path

KB_ROOT = Path(__file__).resolve().parent / "nodes"


def load_all_nodes():
    """加载所有节点。返回 dict[id -> node] + list。"""
    nodes = {}
    for type_dir in KB_ROOT.iterdir():
        if not type_dir.is_dir():
            continue
        for f in type_dir.glob("*.json"):
            try:
                n = json.loads(f.read_text(encoding="utf-8"))
                # Fallback: 优先用 'id' 字段,否则用 'name',否则用文件名
                if "id" not in n or not n.get("id"):
                    n["id"] = n.get("name") or f.stem.upper()
                if "type" not in n or not n.get("type"):
                    n["type"] = type_dir.name.rstrip("s")  # diktats -> diktat
                nodes[n["id"]] = n
            except Exception as e:
                pass
    return nodes


def load_relations():
    """加载 relations.json。"""
    p = KB_ROOT / "relations.json"
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))["relations"]


def cmd_list(args):
    nodes = load_all_nodes()
    by_type = {}
    for n in nodes.values():
        by_type.setdefault(n["type"], []).append(n)
    print("=" * 60)
    print(f"Axiom Forge KB — {len(nodes)} 节点 / {len(by_type)} 类型")
    print("=" * 60)
    for t in sorted(by_type.keys()):
        ns = sorted(by_type[t], key=lambda x: x["id"])
        print(f"\n[{t}] ({len(ns)} 个)")
        for n in ns:
            label = n.get("label_zh") or (n.get("nl") or n.get("title") or n.get("description", ""))[:60]
            print(f"  {n['id']:<28} | {label}")
    return 0


def cmd_query(args):
    if not args:
        print("用法: axiom-forge query <关键词>")
        return 1
    keyword = " ".join(args).lower()
    nodes = load_all_nodes()
    matches = []
    for n in nodes.values():
        haystack = " ".join([
            n.get("nl", ""), n.get("formal", ""), n.get("title", ""),
            n.get("label_zh", ""), n.get("label_en", ""), n.get("description", ""),
            n.get("abstract_nl", ""), " ".join(n.get("tags", [])),
            " ".join(n.get("aliases", [])),
        ]).lower()
        if keyword in haystack:
            matches.append(n)
    if not matches:
        print(f"未找到匹配 '{keyword}' 的节点。")
        return 1
    print(f"找到 {len(matches)} 个匹配节点:")
    for n in matches:
        print(f"\n📌 {n['id']} ({n['type']})")
        if n.get("title"):
            print(f"   Title: {n['title']}")
        if n.get("label_zh"):
            print(f"   Label: {n['label_zh']} / {n.get('label_en', '')}")
        if n.get("nl"):
            nl = n["nl"]
            print(f"   NL: {nl[:120]}{'...' if len(nl) > 120 else ''}")
        if n.get("anchors"):
            print(f"   Anchors: {len(n['anchors'])} 个")
    return 0


def cmd_search(args):
    """Phase 2.2 RAG 简化版:加权关键词 + 跨字段评分"""
    if not args:
        print("用法: axiom-forge search <自然语言 query>")
        return 1
    query = " ".join(args).lower()
    query_words = set(re.findall(r'\w+', query))
    nodes = load_all_nodes()
    scored = []
    for n in nodes.values():
        score = 0
        # 加权:title 最高,其次 nl/formal/abstract,最后 tags/aliases
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
        # 锚加权
        for a in n.get("anchors", []):
            for w in query_words:
                if w in str(a).lower(): score += 0.5
        if score > 0:
            scored.append((score, n))
    scored.sort(key=lambda x: -x[0])
    if not scored:
        print(f"未找到与 '{query}' 相关的节点。")
        return 1
    print(f"🔍 语义搜索 '{query}' (top 10):")
    print("=" * 60)
    for score, n in scored[:10]:
        print(f"\n📌 {n['id']} ({n['type']}) — score: {score:.1f}")
        if n.get("title"):
            print(f"   {n['title']}")
        if n.get("label_zh"):
            print(f"   {n['label_zh']} / {n.get('label_en', '')}")
        if n.get("nl"):
            print(f"   {n['nl'][:100]}...")
    return 0


def cmd_show(args):
    if not args:
        print("用法: axiom-forge show <NODE_ID>")
        return 1
    target_id = args[0]
    nodes = load_all_nodes()
    n = nodes.get(target_id)
    if not n:
        print(f"未找到节点 '{target_id}'。")
        return 1
    print(json.dumps(n, ensure_ascii=False, indent=2))
    return 0


def cmd_stats(args):
    nodes = load_all_nodes()
    rels = load_relations()
    print("=" * 60)
    print("Axiom Forge KB 统计")
    print("=" * 60)
    print(f"\n总节点数: {len(nodes)}")
    print(f"关系数: {len(rels)}")
    by_type = {}
    for n in nodes.values():
        by_type[n["type"]] = by_type.get(n["type"], 0) + 1
    print(f"\n类型分布:")
    for t in sorted(by_type.keys()):
        print(f"  {t:<20} {by_type[t]:>4} 个")
    domains = {}
    for n in nodes.values():
        d = n.get("domain", "(no domain)")
        domains[d] = domains.get(d, 0) + 1
    print(f"\n域分布 (top 10):")
    for d, c in sorted(domains.items(), key=lambda x: -x[1])[:10]:
        print(f"  {d:<30} {c:>4} 个")
    anchor_types = {}
    for n in nodes.values():
        for a in n.get("anchors", []):
            t = a.get("type", "(no type)")
            anchor_types[t] = anchor_types.get(t, 0) + 1
    print(f"\n锚类型分布 (3 锚完全平等):")
    for t in sorted(anchor_types.keys()):
        print(f"  {t:<20} {anchor_types[t]:>4} 个")
    rel_types = {}
    for r in rels:
        rt = r.get("type", "(no type)")
        rel_types[rt] = rel_types.get(rt, 0) + 1
    print(f"\n关系类型分布:")
    for t in sorted(rel_types.keys()):
        print(f"  {t:<25} {rel_types[t]:>4} 条")
    return 0


def cmd_relations(args):
    if not args:
        print("用法: axiom-forge relations <NODE_ID>")
        return 1
    target_id = args[0]
    nodes = load_all_nodes()
    rels = load_relations()
    n = nodes.get(target_id)
    if not n:
        print(f"未找到节点 '{target_id}'。")
        return 1
    print(f"节点 {target_id} 的关系:")
    print("=" * 60)
    # 出向(in node fields)
    for field, label, arrow in [("depends_on", "📥 depends_on", "→"),
                                  ("linage_in", "📚 linage_in", "↑"),
                                  ("linage_out", "📤 linage_out", "↓")]:
        if field in n:
            print(f"\n{label} ({len(n[field])}):")
            for d in n[field]:
                print(f"  {arrow} {d}")
    if "aliases" in n:
        print(f"\n🔤 aliases ({len(n['aliases'])}):")
        for a in n["aliases"]:
            print(f"  = {a}")
    # 入向/出向 (from relations.json)
    out_rels = [r for r in rels if r["from"] == target_id]
    in_rels = [r for r in rels if r["to"] == target_id]
    if out_rels:
        print(f"\n🔗 explicit outgoing ({len(out_rels)}):")
        for r in out_rels:
            print(f"  → {r['to']} ({r['type']}, strength={r.get('strength', '?')})")
    if in_rels:
        print(f"\n🔙 explicit incoming ({len(in_rels)}):")
        for r in in_rels:
            print(f"  ← {r['from']} ({r['type']}, strength={r.get('strength', '?')})")
    if "anchors" in n:
        print(f"\n⚓ anchors ({len(n['anchors'])}):")
        for a in n["anchors"]:
            t = a.get("type", "?")
            sub = a.get("subtype", "") or a.get("tradition", "") or a.get("concept", "")
            ev = a.get("evidence", "") or a.get("supporters", "")
            print(f"  [{t}] {sub}: {str(ev)[:60]}")
    return 0


def cmd_graph(args):
    """从某节点出发,沿关系遍历 N 跳。"""
    if not args:
        print("用法: axiom-forge graph <NODE_ID> [--depth N]")
        return 1
    target_id = args[0]
    depth = 2
    if "--depth" in args:
        i = args.index("--depth")
        depth = int(args[i + 1]) if i + 1 < len(args) else 2
    nodes = load_all_nodes()
    rels = load_relations()
    n = nodes.get(target_id)
    if not n:
        print(f"未找到节点 '{target_id}'。")
        return 1
    # 双向遍历
    visited = {target_id}
    frontier = {target_id}
    print(f"🌐 关系图: {target_id} (depth={depth})")
    print("=" * 60)
    print(f"\n[center] {target_id} ({n['type']})")
    if n.get("title"):
        print(f"           {n['title']}")
    elif n.get("nl"):
        print(f"           {n['nl'][:80]}")
    for d in range(1, depth + 1):
        new_frontier = set()
        # 出向
        for r in rels:
            if r["from"] in frontier and r["to"] not in visited:
                new_frontier.add(r["to"])
                visited.add(r["to"])
        for r in rels:
            if r["to"] in frontier and r["from"] not in visited:
                new_frontier.add(r["from"])
                visited.add(r["from"])
        if not new_frontier:
            print(f"\n  [depth {d}] (无新节点)")
            break
        print(f"\n[depth {d}] ({len(new_frontier)} 个新节点):")
        for nid in sorted(new_frontier)[:15]:
            nn = nodes.get(nid, {})
            label = nn.get("label_zh") or (nn.get("nl") or nn.get("title", ""))[:50]
            t = nn.get("type", "?")
            print(f"  - {nid} ({t}): {label}")
        if len(new_frontier) > 15:
            print(f"  ... 还有 {len(new_frontier) - 15} 个")
        frontier = new_frontier
    print(f"\n总计: {len(visited)} 个节点在 {depth} 跳内可达")
    return 0


def cmd_anchors(args):
    """显示某节点的所有锚。"""
    if not args:
        print("用法: axiom-forge anchors <NODE_ID>")
        return 1
    target_id = args[0]
    nodes = load_all_nodes()
    n = nodes.get(target_id)
    if not n:
        print(f"未找到节点 '{target_id}'。")
        return 1
    anchors = n.get("anchors", [])
    if not anchors:
        print(f"节点 {target_id} 没有锚。")
        return 0
    print(f"节点 {target_id} 的锚 ({len(anchors)} 个):")
    print("=" * 60)
    for i, a in enumerate(anchors, 1):
        t = a.get("type", "?")
        sub = a.get("subtype", "") or a.get("tradition", "") or a.get("concept", "")
        ev = a.get("evidence", "") or a.get("supporters", "")
        print(f"\n  [锚 {i}] type={t}")
        if sub:
            print(f"    {sub}")
        if ev:
            print(f"    evidence: {str(ev)[:120]}")
    return 0


def cmd_anchors_by_type(args):
    """按锚类型列节点。"""
    if not args:
        print("用法: axiom-forge anchors-by-type <type>")
        print("  type: empirical | philosophical | community")
        return 1
    target_type = args[0]
    nodes = load_all_nodes()
    matches = []
    for n in nodes.values():
        for a in n.get("anchors", []):
            if a.get("type") == target_type:
                matches.append((n, a))
                break
    if not matches:
        print(f"无节点带 '{target_type}' 锚。")
        return 1
    print(f"带 '{target_type}' 锚的节点 ({len(matches)} 个):")
    print("=" * 60)
    for n, a in matches:
        sub = a.get("subtype", "") or a.get("tradition", "") or a.get("concept", "")
        ev = a.get("evidence", "") or a.get("supporters", "")
        print(f"\n  📌 {n['id']} ({n['type']})")
        if sub:
            print(f"     {sub}")
        if ev:
            print(f"     {str(ev)[:80]}")
    return 0


def cmd_compressed(args):
    """多粒度压缩视图。"""
    if not args:
        print("用法: axiom-forge compressed <NODE_ID> [粒度: full/medium/tiny]")
        return 1
    target_id = args[0]
    granularity = args[1] if len(args) > 1 else "medium"
    nodes = load_all_nodes()
    n = nodes.get(target_id)
    if not n:
        print(f"未找到节点 '{target_id}'。")
        return 1
    if granularity == "full":
        print(json.dumps(n, ensure_ascii=False, indent=2))
    elif granularity == "medium":
        # Medium: ID + type + 关键字段 + 1-2 句
        print(f"📦 {n['id']} (medium 粒度):")
        print("=" * 60)
        print(f"Type: {n['type']}")
        if n.get("title"):
            print(f"Title: {n['title']}")
        if n.get("label_zh"):
            print(f"Label: {n['label_zh']} / {n.get('label_en', '')}")
        if n.get("nl"):
            print(f"NL: {n['nl'][:300]}")
        elif n.get("description"):
            print(f"Description: {n['description'][:300]}")
        if n.get("formal"):
            print(f"Formal: {n['formal'][:200]}")
        if n.get("anchors"):
            print(f"\nAnchors ({len(n['anchors'])}):")
            for a in n["anchors"][:3]:
                t = a.get("type", "?")
                sub = a.get("subtype", "") or a.get("tradition", "")
                print(f"  [{t}] {sub}")
    elif granularity == "tiny":
        # Tiny: 1 句话
        print(f"🔖 {n['id']}: ", end="")
        if n.get("label_zh"):
            print(f"{n['label_zh']} ({n.get('label_en', '')})")
        elif n.get("title"):
            print(n["title"])
        elif n.get("nl"):
            print(n["nl"][:120])
        else:
            print(n.get("description", "")[:120])
    else:
        print(f"未知粒度 '{granularity}'。可选: full / medium / tiny")
        return 1
    return 0


def cmd_value_tree(args):
    """显示价值观谱系。"""
    print("🌳 价值观谱系 (6 大类,3 锚完全平等)")
    print("=" * 60)
    tree = {
        "moral": ("道德", ["universal_kindness", "universal_prohibition", "general", "cultural_specific"]),
        "interest": ("利益", ["individual", "social", "power", "equality", "longterm"]),
        "aesthetic": ("美学", ["symmetry", "simplicity", "elegance", "unity"]),
        "epistemic": ("知识", ["truth", "consistency", "falsifiability", "interpretability", "universality"]),
        "practical": ("实践", ["efficiency", "scalability", "reproducibility", "maintainability", "teachability"]),
        "philosophical": ("哲学", ["kantian_ethics", "utilitarianism", "rawls", "libertarian", "phenomenology", "virtue_ethics", "pragmatism", "existentialism"]),
    }
    nodes = load_all_nodes()
    for vclass, (label, subclasses) in tree.items():
        print(f"\n📁 {vclass} ({label})")
        for sub in subclasses:
            matches = [n for n in nodes.values()
                       if n.get("value_class") == vclass and n.get("value_subclass") == sub]
            if matches:
                names = " / ".join(m.get("label_zh", m["id"]) for m in matches[:3])
                print(f"  └─ {sub}: {names}")
            else:
                print(f"  └─ {sub}: (无节点)")
    return 0


def cmd_explore(args):
    """按锚类型探索所有节点。"""
    if not args or "--anchor" not in args:
        print("用法: axiom-forge explore --anchor <type>")
        print("  type: empirical | philosophical | community")
        return 1
    i = args.index("--anchor")
    if i + 1 >= len(args):
        print("需要指定锚类型")
        return 1
    target = args[i + 1]
    return cmd_anchors_by_type([target])


def cmd_ask(args):
    """用 M3 读 KB 回答问题(RAG 模式)"""
    if not args:
        print("用法: axiom-forge ask <问题>")
        return 1
    # lazy import 避免强依赖
    try:
        from kb_llm import ask_m3, check_api_key
    except ImportError as e:
        print(f"ERROR: 需要 httpx + dotenv. 运行: pip install httpx python-dotenv")
        return 1
    if not check_api_key():
        print("ERROR: MINIMAX_API_KEY 未设置. export MINIMAX_API_KEY=xxx")
        return 1
    question = " ".join(args)
    print(f"💬 问 M3: {question}")
    print("=" * 60)
    answer = ask_m3(question)
    if answer:
        print(answer)
    else:
        print("M3 未返回答案")
    return 0


def cmd_explore_anchor(args):
    """M3 深度解读某类锚"""
    if not args:
        print("用法: axiom-forge explore-anchor <empirical|philosophical|community>")
        return 1
    try:
        from kb_llm import explore_anchor_m3, check_api_key
    except ImportError:
        print("ERROR: 需要 httpx + dotenv")
        return 1
    if not check_api_key():
        print("ERROR: MINIMAX_API_KEY 未设置")
        return 1
    anchor_type = args[0]
    print(f"🔍 M3 探索 {anchor_type} 锚 ...")
    print("=" * 60)
    answer = explore_anchor_m3(anchor_type)
    if answer:
        print(answer)
    else:
        print(f"无 {anchor_type} 锚节点, 或 M3 未返回")
    return 0


def cmd_validate(args):
    """M3 评估节点质量"""
    if not args:
        print("用法: axiom-forge validate <NODE_ID>")
        return 1
    try:
        from kb_llm import validate_node_m3, check_api_key
    except ImportError:
        print("ERROR: 需要 httpx + dotenv")
        return 1
    if not check_api_key():
        print("ERROR: MINIMAX_API_KEY 未设置")
        return 1
    target = args[0]
    print(f"✅ M3 验证 {target} ...")
    print("=" * 60)
    answer = validate_node_m3(target)
    if answer:
        print(answer)
    else:
        print(f"未找到节点 {target}, 或 M3 未返回")
    return 0


def cmd_check(args):
    """Lean 4 proof-checker: verify a KB node's `formal` field compiles."""
    if not args:
        print("用法: axiom-forge check <NODE_ID>")
        print("  或: axiom-forge check-all")
        return 1
    import subprocess
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        ["python3", str(root / "kb" / "ingest" / "proof_checker.py"), "check", args[0]],
        capture_output=True, text=True, timeout=300,
    )
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    return proc.returncode


def cmd_check_all(args):
    """Lean 4 proof-checker: verify ALL axiom/theorem/assumption nodes."""
    import subprocess
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        ["python3", str(root / "kb" / "ingest" / "proof_checker.py"), "check-all"],
        capture_output=True, text=True, timeout=1800,
    )
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    return proc.returncode


def cmd_lane_b(args):
    """Lane B LLM evaluator: 5-dim rubric (clarity/novelty/consistency/grounding/actionability)."""
    import subprocess
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    cmd = ["python3", str(root / "kb" / "ingest" / "lane_b_evaluator.py")]
    cmd.extend(args)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    return proc.returncode


def cmd_proof_status(args):
    """Show Lean proof-checker status for all KB nodes with `formal` field."""
    import subprocess
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        ["python3", str(root / "kb" / "ingest" / "proof_checker.py"), "status"],
        capture_output=True, text=True, timeout=30,
    )
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    return proc.returncode


def cmd_help(args):
    print("Axiom Forge CLI v2.0 (Phase 1.4 + 1.5 + 2.2 + 2.3)")
    print("=" * 60)
    print("用法: axiom-forge <command> [args]")
    print("")
    print("命令:")
    print("  list                              列出所有节点")
    print("  query <keyword>                   关键词查询")
    print("  search <query>                    加权语义搜索 (RAG 简化版)")
    print("  show <NODE_ID>                    显示节点完整 JSON")
    print("  stats                             知识库统计")
    print("  relations <NODE_ID>               显示节点关系")
    print("  graph <NODE_ID> [--depth N]       关系图(N 跳)")
    print("  anchors <NODE_ID>                 显示节点的所有锚")
    print("  anchors-by-type <type>            按锚类型列节点")
    print("  compressed <NODE_ID> [粒度]       多粒度 (full/medium/tiny)")
    print("  value-tree                        价值观谱系图")
    print("  explore --anchor <type>           按锚探索 (无 M3)")
    print("  check <NODE_ID>                   Lean 4 证明验证 (Phase C)")
    print("  check-all                         验证所有 axiom/theorem 节点")
    print("  proof-status                      Lean 4 证明状态报告")
    print("  lane-b <sub>                      Lane B LLM 评估 (5 维 + Cohen's kappa)")
    print("")
    print("  ── 需要 M3 API key ──")
    print("  ask <question>                    用 M3 读 KB 回答 (RAG)")
    print("  explore-anchor <type>             M3 深度解读某类锚")
    print("  validate <NODE_ID>                M3 评估节点质量")
    print("")
    print("  help                              显示此帮助")
    print("")
    print("示例:")
    print('  axiom-forge list')
    print('  axiom-forge search "Shapley attribution"')
    print('  axiom-forge graph AX-SC-001 --depth 2')
    print('  axiom-forge anchors AX-SC-001')
    print('  axiom-forge compressed AX-SC-001 tiny')
    print('  axiom-forge value-tree')
    return 0


def main():
    if len(sys.argv) < 2:
        return cmd_help([])
    cmd = sys.argv[1]
    args = sys.argv[2:]
    cmds = {
        "list": cmd_list, "query": cmd_query, "search": cmd_search,
        "show": cmd_show, "stats": cmd_stats, "relations": cmd_relations,
        "graph": cmd_graph, "anchors": cmd_anchors,
        "anchors-by-type": cmd_anchors_by_type, "compressed": cmd_compressed,
        "value-tree": cmd_value_tree, "explore": cmd_explore,
        "ask": cmd_ask, "explore-anchor": cmd_explore_anchor, "validate": cmd_validate,
        "check": cmd_check, "check-all": cmd_check_all, "proof-status": cmd_proof_status,
        "lane-b": cmd_lane_b,
        "help": cmd_help, "-h": cmd_help, "--help": cmd_help,
    }
    fn = cmds.get(cmd)
    if not fn:
        print(f"未知命令: {cmd}")
        return cmd_help([])
    return fn(args)


if __name__ == "__main__":
    sys.exit(main())
