#!/usr/bin/env python3
"""
Axiom Forge Web API — FastAPI 封装

路由:
  POST /ask               M3 读 KB 回答
  POST /explore-anchor   M3 深度解读某类锚
  POST /validate         M3 评估节点质量
  GET  /list             列出所有节点
  GET  /show/:id         节点详情
  GET  /graph/:id        关系图
  GET  /stats            KB 统计
  GET  /value-tree       价值观谱系
"""
from __future__ import annotations
import sys
import json
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ── 路径 setup ────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
KB_ROOT = ROOT / "kb" / "nodes"
AGENT_LLM_PATH = ROOT / "agents"
KB_LLM_PATH = ROOT / "kb"
sys.path.insert(0, str(AGENT_LLM_PATH))
sys.path.insert(0, str(KB_LLM_PATH))

# ── .env 加载 ──────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    _ENV = ROOT / ".env"
    if _ENV.exists():
        load_dotenv(_ENV)
except ImportError:
    pass

# ── FastAPI app ────────────────────────────────────────────────
app = FastAPI(title="Axiom Forge Web API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ── 内部 helpers ───────────────────────────────────────────────
def load_all_nodes():
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
    p = KB_ROOT / "relations.json"
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))["relations"]


# ── Request / Response 模型 ────────────────────────────────────
class AskRequest(BaseModel):
    query: str
    top_k: int = 5


class ExploreAnchorRequest(BaseModel):
    type: str  # empirical | philosophical | community


class ValidateRequest(BaseModel):
    node_id: str


# ── GET /list ──────────────────────────────────────────────────
@app.get("/list")
def list_nodes():
    """列出所有节点（按 type 分组）"""
    nodes = load_all_nodes()
    by_type: dict[str, list[dict[str, Any]]] = {}
    for n in nodes.values():
        by_type.setdefault(n["type"], []).append({
            "id": n["id"],
            "type": n["type"],
            "label_zh": n.get("label_zh", ""),
            "label_en": n.get("label_en", ""),
            "title": n.get("title", ""),
            "nl": (n.get("nl") or "")[:100],
        })
    return {
        "total": len(nodes),
        "by_type": {t: sorted(ns, key=lambda x: x["id"]) for t, ns in by_type.items()},
    }


# ── GET /stats ─────────────────────────────────────────────────
@app.get("/stats")
def stats():
    """KB 统计"""
    nodes = load_all_nodes()
    rels = load_relations()
    by_type: dict[str, int] = {}
    anchor_types: dict[str, int] = {}
    domains: dict[str, int] = {}
    for n in nodes.values():
        by_type[n["type"]] = by_type.get(n["type"], 0) + 1
        d = n.get("domain", "(no domain)")
        domains[d] = domains.get(d, 0) + 1
        for a in n.get("anchors", []):
            t = a.get("type", "?")
            anchor_types[t] = anchor_types.get(t, 0) + 1
    rel_types: dict[str, int] = {}
    for r in rels:
        rel_types[r.get("type", "?")] = rel_types.get(r.get("type", "?"), 0) + 1
    return {
        "total_nodes": len(nodes),
        "total_relations": len(rels),
        "by_type": dict(sorted(by_type.items())),
        "anchor_types": dict(sorted(anchor_types.items())),
        "domains": dict(sorted(domains.items(), key=lambda x: -x[1])[:10]),
        "relation_types": dict(sorted(rel_types.items())),
    }


# ── GET /show/:id ──────────────────────────────────────────────
@app.get("/show/{node_id}")
def show_node(node_id: str):
    """节点完整 JSON"""
    nodes = load_all_nodes()
    n = nodes.get(node_id)
    if not n:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    return n


# ── GET /graph/:id ──────────────────────────────────────────────
@app.get("/graph/{node_id}")
def graph_node(node_id: str, depth: int = 2):
    """从节点出发 N 跳可达的所有节点"""
    nodes = load_all_nodes()
    rels = load_relations()
    if node_id not in nodes:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    visited = {node_id}
    frontier = {node_id}
    for _ in range(depth):
        new_frontier: set[str] = set()
        for r in rels:
            if r["from"] in frontier and r["to"] not in visited:
                new_frontier.add(r["to"])
                visited.add(r["to"])
        for r in rels:
            if r["to"] in frontier and r["from"] not in visited:
                new_frontier.add(r["from"])
                visited.add(r["from"])
        frontier = new_frontier
    return {
        "center": node_id,
        "depth": depth,
        "visited": sorted(visited),
        "count": len(visited),
    }


# ── GET /value-tree ─────────────────────────────────────────────
@app.get("/value-tree")
def value_tree():
    """价值观谱系（6 大类）"""
    nodes = load_all_nodes()
    tree = {
        "moral": ("道德", ["universal_kindness", "universal_prohibition", "general", "cultural_specific"]),
        "interest": ("利益", ["individual", "social", "power", "equality", "longterm"]),
        "aesthetic": ("美学", ["symmetry", "simplicity", "elegance", "unity"]),
        "epistemic": ("知识", ["truth", "consistency", "falsifiability", "interpretability", "universality"]),
        "practical": ("实践", ["efficiency", "scalability", "reproducibility", "maintainability", "teachability"]),
        "philosophical": ("哲学", ["kantian_ethics", "utilitarianism", "rawls", "libertarian", "phenomenology", "virtue_ethics", "pragmatism", "existentialism"]),
    }
    result = {}
    for vclass, (label, subclasses) in tree.items():
        result[vclass] = {"label": label, "subclasses": {}}
        for sub in subclasses:
            matches = [
                {"id": n["id"], "label_zh": n.get("label_zh", "")}
                for n in nodes.values()
                if n.get("value_class") == vclass and n.get("value_subclass") == sub
            ][:5]
            result[vclass]["subclasses"][sub] = matches
    return result


# ── POST /ask ──────────────────────────────────────────────────
@app.post("/ask")
def ask(req: AskRequest):
    """M3 读 KB 回答（需要 MINIMAX_API_KEY）"""
    try:
        from kb_llm import ask_m3, check_api_key
    except ImportError:
        raise HTTPException(status_code=500, detail="kb_llm not available; install httpx python-dotenv")
    if not check_api_key():
        raise HTTPException(status_code=500, detail="MINIMAX_API_KEY not set in .env")

    answer = ask_m3(req.query, max_tokens=4000)
    if answer is None:
        raise HTTPException(status_code=500, detail="M3 returned no answer")
    return {"query": req.query, "answer": answer}


# ── POST /explore-anchor ───────────────────────────────────────
@app.post("/explore-anchor")
def explore_anchor(req: ExploreAnchorRequest):
    """M3 深度解读某类锚"""
    try:
        from kb_llm import explore_anchor_m3, check_api_key
    except ImportError:
        raise HTTPException(status_code=500, detail="kb_llm not available")
    if not check_api_key():
        raise HTTPException(status_code=500, detail="MINIMAX_API_KEY not set in .env")

    result = explore_anchor_m3(req.type)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No nodes with '{req.type}' anchor found")
    return {"type": req.type, "analysis": result}


# ── POST /validate ──────────────────────────────────────────────
@app.post("/validate")
def validate(req: ValidateRequest):
    """M3 评估节点质量"""
    try:
        from kb_llm import validate_node_m3, check_api_key
    except ImportError:
        raise HTTPException(status_code=500, detail="kb_llm not available")
    if not check_api_key():
        raise HTTPException(status_code=500, detail="MINIMAX_API_KEY not set in .env")

    result = validate_node_m3(req.node_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Node '{req.node_id}' not found")
    return {"node_id": req.node_id, "evaluation": result}


# ── 健康检查 ───────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
