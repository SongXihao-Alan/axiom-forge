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
import math
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel

# ── 路径 setup ────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
KB_ROOT = ROOT / "knowledge-base" / "nodes"
AGENT_LLM_PATH = ROOT / "agents"
KB_LLM_PATH = ROOT / "knowledge-base"
PAPER_DATA = ROOT / "paper" / "data"
PAPER_RESULTS = ROOT / "paper" / "results"
sys.path.insert(0, str(AGENT_LLM_PATH))
sys.path.insert(0, str(KB_LLM_PATH))
sys.path.insert(0, str(PAPER_DATA))

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


# ── POST /verify — Lean 4 proof-checker (Phase C) ───────────────
class VerifyRequest(BaseModel):
    node_id: Optional[str] = None  # check a KB node
    lean_code: Optional[str] = None  # or check a free-form Lean snippet


@app.post("/verify")
def verify(req: VerifyRequest):
    """Run proof-checker on a KB node or free-form Lean code.
    Delegates to knowledge-base/ingest/proof_checker.py. Requires Lean 4 + lake installed."""
    if not req.node_id and not req.lean_code:
        raise HTTPException(status_code=400, detail="Provide `node_id` or `lean_code`")
    if req.node_id:
        try:
            import subprocess
            proc = subprocess.run(
                ["python3", str(ROOT / "knowledge-base" / "ingest" / "proof_checker.py"), "check", req.node_id],
                capture_output=True, text=True, timeout=300,
            )
            return {
                "node_id": req.node_id,
                "exit_code": proc.returncode,
                "stdout": proc.stdout[-2000:],
                "stderr": proc.stderr[-2000:],
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"proof_checker failed: {e}")
    else:
        # Free-form Lean code: write to temp file, run lake env lean --check
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".lean", delete=False) as f:
                f.write(req.lean_code)
                tmp_path = f.name
            import subprocess
            proc = subprocess.run(
                ["lake", "env", "lean", "--root", str(FORMAL_DIR), tmp_path],
                capture_output=True, text=True, timeout=120,
            )
            return {
                "lean_code_preview": req.lean_code[:200],
                "exit_code": proc.returncode,
                "stdout": proc.stdout[-1000:],
                "stderr": proc.stderr[-1000:],
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Lean check failed: {e}")


# ── GET /proof-status — proof-checker status report ─────────────
@app.get("/proof-status")
def proof_status():
    """Show Lean proof status for all KB nodes with a `formal` field."""
    try:
        import subprocess
        proc = subprocess.run(
            ["python3", str(ROOT / "knowledge-base" / "ingest" / "proof_checker.py"), "status"],
            capture_output=True, text=True, timeout=30,
        )
        return {"report": proc.stdout, "stderr": proc.stderr[-500:]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"status failed: {e}")


# ── Global ROOT for /verify ─────────────────────────────────────
FORMAL_DIR = ROOT / "formal"


# =============================================================================
# Lane C — Statistics (imported from paper.data.lane_c_stats)
# =============================================================================
DIMS = ["clarity", "novelty", "internal_consistency",
        "empirical_grounding", "actionability"]

FEEDBACK_PATH = PAPER_RESULTS / "lane_c_feedback.json"
REPORT_PATH = PAPER_RESULTS / "lane_c_report.md"
STATS_PATH = PAPER_RESULTS / "lane_c_stats.json"


def _quad_weighted_kappa(pred, gold, k=5):
    from collections import Counter
    if not pred or not gold or len(pred) != len(gold):
        return None
    weights = [[(i - j) ** 2 / (k - 1) ** 2 for j in range(1, k + 1)]
               for i in range(1, k + 1)]
    n = len(pred)
    observed = sum(weights[p - 1][g - 1] for p, g in zip(pred, gold)) / n
    pred_counts = Counter(pred)
    gold_counts = Counter(gold)
    expected = sum(
        (pred_counts[i] / n) * (gold_counts[j] / n) * weights[i - 1][j - 1]
        for i in range(1, k + 1)
        for j in range(1, k + 1)
    )
    if expected >= 1.0:
        return 1.0
    return 1 - observed / expected


def _pearson(pred, gold):
    if len(pred) != len(gold) or len(pred) < 2:
        return None
    n = len(pred)
    mean_p = sum(pred) / n
    mean_g = sum(gold) / n
    cov = sum((p - mean_p) * (g - mean_g) for p, g in zip(pred, gold))
    var_p = sum((p - mean_p) ** 2 for p in pred)
    var_g = sum((g - mean_g) ** 2 for g in gold)
    if var_p == 0 or var_g == 0:
        return None
    return cov / math.sqrt(var_p * var_g)


def _stats_per_dim(predictions, gold):
    pred_map = {p["id"]: p for p in predictions if p.get("id")}
    gold_map = {g["id"]: g for g in gold if g.get("id")}
    common = sorted(set(pred_map) & set(gold_map))
    out = {}
    for dim in DIMS:
        pairs = []
        for cid in common:
            p_score = pred_map[cid].get("scores", {}).get(dim)
            g_score = gold_map[cid].get("scores", {}).get(dim)
            if p_score is not None and g_score is not None:
                pairs.append((p_score, g_score))
        if not pairs:
            out[dim] = {"n": 0, "qwk": None, "mae": None, "pearson": None,
                        "bias": None, "pred_mean": None, "gold_mean": None}
            continue
        pred = [p for p, _ in pairs]
        gold_ = [g for _, g in pairs]
        qwk = _quad_weighted_kappa(pred, gold_)
        mae = sum(abs(p - g) for p, g in pairs) / len(pairs)
        pear = _pearson(pred, gold_)
        bias = sum(p - g for p, g in pairs) / len(pairs)
        out[dim] = {
            "n": len(pairs),
            "qwk": round(qwk, 4) if qwk is not None else None,
            "mae": round(mae, 4),
            "pearson": round(pear, 4) if pear is not None else None,
            "bias": round(bias, 4),
            "pred_mean": round(sum(pred) / len(pred), 2),
            "gold_mean": round(sum(gold_) / len(gold_), 2),
        }
    qwks = [out[d]["qwk"] for d in DIMS if out[d]["qwk"] is not None]
    out["__macro_qwk"] = round(sum(qwks) / len(qwks), 4) if qwks else None
    return out


def _tier_accuracy(predictions, gold):
    from collections import Counter
    pred_map = {p["id"]: p for p in predictions if p.get("id")}
    gold_map = {g["id"]: g for g in gold if g.get("id")}
    common = set(pred_map) & set(gold_map)
    if not common:
        return {}
    correct = 0
    total = 0
    confusion = Counter()
    for cid in common:
        p_tier = pred_map[cid].get("tier")
        g_tier = gold_map[cid].get("tier")
        if p_tier and g_tier:
            confusion[(g_tier, p_tier)] += 1
            if p_tier == g_tier:
                correct += 1
            total += 1
    acc = correct / total if total else None
    return {
        "accuracy": round(acc, 4) if acc is not None else None,
        "n": total,
        "confusion_matrix": {f"{g}->{p}": c for (g, p), c in confusion.items()},
    }


def _distractor_rejection(predictions, gold):
    pred_map = {p["id"]: p for p in predictions if p.get("id")}
    gold_map = {g["id"]: g for g in gold if g.get("id")}
    distractors = [g for g in gold if g.get("is_distractor")]
    out = {"by_failure_mode": {}, "by_tier": {}}
    for d in distractors:
        p = pred_map.get(d["id"])
        if not p:
            continue
        scores = p.get("scores", {})
        valid = [scores[k] for k in DIMS if scores.get(k) is not None]
        if not valid:
            continue
        llm_mean = sum(valid) / len(valid)
        rejected = llm_mean < 2.5
        fm = d.get("failure_mode", "unknown")
        out["by_failure_mode"].setdefault(fm, {"n": 0, "rejected": 0, "llm_mean": []})
        out["by_failure_mode"][fm]["n"] += 1
        if rejected:
            out["by_failure_mode"][fm]["rejected"] += 1
        out["by_failure_mode"][fm]["llm_mean"].append(llm_mean)
        tier = d.get("tier", "unknown")
        out["by_tier"].setdefault(tier, {"n": 0, "rejected": 0, "llm_mean": []})
        out["by_tier"][tier]["n"] += 1
        if rejected:
            out["by_tier"][tier]["rejected"] += 1
        out["by_tier"][tier]["llm_mean"].append(llm_mean)
    for k in out["by_failure_mode"]:
        d = out["by_failure_mode"][k]
        d["rejection_rate"] = round(d["rejected"] / d["n"], 4) if d["n"] else None
        d["llm_mean"] = round(sum(d["llm_mean"]) / len(d["llm_mean"]), 2) if d["llm_mean"] else None
        del d["llm_mean"]
    for k in out["by_tier"]:
        d = out["by_tier"][k]
        d["rejection_rate"] = round(d["rejected"] / d["n"], 4) if d["n"] else None
        d["llm_mean"] = round(sum(d["llm_mean"]) / len(d["llm_mean"]), 2) if d["llm_mean"] else None
    return out


def _per_anchor_breakdown(predictions, gold):
    pred_map = {p["id"]: p for p in predictions if p.get("id")}
    gold_map = {g["id"]: g for g in gold if g.get("id")}
    real_items = [g for g in gold if not g.get("is_distractor")]
    out = {}
    for g_item in real_items:
        if g_item["id"] not in pred_map:
            continue
        kb_path = ROOT / "knowledge-base" / g_item.get("source", "")
        if not kb_path.exists():
            continue
        try:
            n = json.loads(kb_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        anchors = n.get("anchors", [])
        for a in anchors:
            atype = a.get("type", "unknown")
            out.setdefault(atype, []).append(g_item["id"])
    by_anchor = {}
    for atype, ids in out.items():
        by_anchor[atype] = {"n": len(ids), "per_dim_qwk": {}}
        for dim in DIMS:
            pred_scores, gold_scores = [], []
            for cid in ids:
                p = pred_map.get(cid, {}).get("scores", {}).get(dim)
                g = gold_map.get(cid, {}).get("scores", {}).get(dim)
                if p is not None and g is not None:
                    pred_scores.append(p)
                    gold_scores.append(g)
            qwk = _quad_weighted_kappa(pred_scores, gold_scores) if pred_scores else None
            by_anchor[atype]["per_dim_qwk"][dim] = round(qwk, 4) if qwk is not None else None
    return by_anchor


def _per_domain_breakdown(predictions, gold):
    from collections import defaultdict
    pred_map = {p["id"]: p for p in predictions if p.get("id")}
    gold_map = {g["id"]: g for g in gold if g.get("id")}
    real_items = [g for g in gold if not g.get("is_distractor")]
    by_domain = defaultdict(list)
    for g_item in real_items:
        if g_item["id"] not in pred_map:
            continue
        kb_path = ROOT / "knowledge-base" / g_item.get("source", "")
        if not kb_path.exists():
            continue
        try:
            n = json.loads(kb_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        domain = n.get("domain", "unknown")
        by_domain[domain].append(g_item["id"])
    out = {}
    for domain, ids in by_domain.items():
        out[domain] = {"n": len(ids), "per_dim_qwk": {}}
        for dim in DIMS:
            pred_scores, gold_scores = [], []
            for cid in ids:
                p = pred_map.get(cid, {}).get("scores", {}).get(dim)
                g = gold_map.get(cid, {}).get("scores", {}).get(dim)
                if p is not None and g is not None:
                    pred_scores.append(p)
                    gold_scores.append(g)
            qwk = _quad_weighted_kappa(pred_scores, gold_scores) if pred_scores else None
            out[domain]["per_dim_qwk"][dim] = round(qwk, 4) if qwk is not None else None
    return dict(out)


def _bland_altman(predictions, gold):
    pred_map = {p["id"]: p for p in predictions if p.get("id")}
    gold_map = {g["id"]: g for g in gold if g.get("id")}
    common = sorted(set(pred_map) & set(gold_map))
    out = {}
    for dim in DIMS:
        diffs = []
        for cid in common:
            p = pred_map[cid].get("scores", {}).get(dim)
            g = gold_map[cid].get("scores", {}).get(dim)
            if p is not None and g is not None:
                diffs.append(p - g)
        if not diffs:
            out[dim] = None
            continue
        n = len(diffs)
        mean = sum(diffs) / n
        var = sum((d - mean) ** 2 for d in diffs) / n
        sd = math.sqrt(var)
        out[dim] = {
            "n": n,
            "mean_diff": round(mean, 4),
            "sd_diff": round(sd, 4),
            "loa_lower": round(mean - 1.96 * sd, 4),
            "loa_upper": round(mean + 1.96 * sd, 4),
        }
    return out


def _compute_lane_c(predictions_file: Path, gold_file: Path,
                   prompt_version: str = "v1") -> dict:
    """Run Lane C stats pipeline; write feedback + report + stats JSON files."""
    predictions = json.loads(predictions_file.read_text(encoding="utf-8"))
    gold_data = json.loads(gold_file.read_text(encoding="utf-8"))
    gold = gold_data.get("items", [])

    results = {
        "per_dim_stats": _stats_per_dim(predictions, gold),
        "tier_accuracy": _tier_accuracy(predictions, gold),
        "distractor_rejection": _distractor_rejection(predictions, gold),
        "per_anchor_type": _per_anchor_breakdown(predictions, gold),
        "per_domain": _per_domain_breakdown(predictions, gold),
        "bland_altman": _bland_altman(predictions, gold),
    }

    per_dim_stats = results["per_dim_stats"]
    tier_acc = results["tier_accuracy"].get("accuracy", 0.0) or 0.0
    per_dim_feedback = {}
    dims_needing_revision = []
    all_qwk = []
    for dim in DIMS:
        s = per_dim_stats[dim]
        qwk = s.get("qwk")
        mae = s.get("mae", 0.0) or 0.0
        bias = s.get("bias", 0.0) or 0.0
        per_dim_feedback[dim] = {"qwk": qwk, "mae": mae, "bias": bias}
        if qwk is not None:
            all_qwk.append(qwk)
            if qwk < 0.6 or mae > 1.0:
                dims_needing_revision.append(dim)

    converged = all(qwk >= 0.6 for qwk in all_qwk) and tier_acc >= 0.75

    distractor_weaknesses = {
        fm: data["rejection_rate"]
        for fm, data in results["distractor_rejection"]["by_failure_mode"].items()
        if data.get("rejection_rate") is not None
    }

    feedback = {
        "prompt_version": prompt_version,
        "converged": converged,
        "dims_needing_revision": dims_needing_revision,
        "per_dim": per_dim_feedback,
        "distractor_weaknesses": distractor_weaknesses,
        "tier_accuracy": tier_acc,
    }

    PAPER_RESULTS.mkdir(parents=True, exist_ok=True)
    FEEDBACK_PATH.write_text(json.dumps(feedback, ensure_ascii=False, indent=2), encoding="utf-8")
    STATS_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    md = []
    md.append("# Lane C Calibration Report\n")
    md.append(f"Predictions: **{len(predictions)}** | Gold: **{len(gold)}**\n")
    md.append("\n## Per-dimension statistics\n")
    md.append("| Dim | n | QWK | MAE | Pearson | Bias | LLM mean | Gold mean |")
    md.append("|-----|---|-----|-----|---------|------|----------|-----------|")
    for dim in DIMS:
        s = results["per_dim_stats"][dim]
        md.append(f"| {dim} | {s['n']} | {s['qwk']} | {s['mae']} | "
                  f"{s['pearson']} | {s['bias']} | {s['pred_mean']} | {s['gold_mean']} |")
    md.append(f"\n**Macro QWK:** {results['per_dim_stats'].get('__macro_qwk')}\n")
    md.append("\n## Tier accuracy\n")
    t = results["tier_accuracy"]
    md.append(f"Accuracy: **{t.get('accuracy')}** ({t.get('n')} items)\n")
    md.append("Confusion (gold -> predicted):\n")
    for k, v in sorted(t.get("confusion_matrix", {}).items()):
        md.append(f"- {k}: {v}")
    md.append("\n## Distractor rejection rate\n")
    dr = results["distractor_rejection"]
    md.append("By failure_mode:\n")
    for fm, d in sorted(dr["by_failure_mode"].items()):
        md.append(f"- {fm}: {d['rejection_rate']} ({d['rejected']}/{d['n']}, mean={d.get('llm_mean')})")
    md.append("\nBy tier:\n")
    for tier, d in sorted(dr["by_tier"].items()):
        md.append(f"- {tier}: {d['rejection_rate']} ({d['rejected']}/{d['n']}, mean={d.get('llm_mean')})")
    md.append("\n## Per-anchor-type (real items only)\n")
    md.append("| Anchor | n | clarity | novelty | consistency | grounding | actionability |")
    md.append("|--------|---|---------|---------|-------------|-----------|---------------|")
    for atype, d in sorted(results["per_anchor_type"].items()):
        qwks = d["per_dim_qwk"]
        md.append(f"| {atype} | {d['n']} | {qwks.get('clarity')} | {qwks.get('novelty')} | "
                  f"{qwks.get('internal_consistency')} | {qwks.get('empirical_grounding')} | "
                  f"{qwks.get('actionability')} |")
    md.append("\n## Per-domain (real items only)\n")
    md.append("| Domain | n | clarity | novelty | consistency | grounding | actionability |")
    md.append("|--------|---|---------|---------|-------------|-----------|---------------|")
    for domain, d in sorted(results["per_domain"].items()):
        qwks = d["per_dim_qwk"]
        md.append(f"| {domain} | {d['n']} | {qwks.get('clarity')} | {qwks.get('novelty')} | "
                  f"{qwks.get('internal_consistency')} | {qwks.get('empirical_grounding')} | "
                  f"{qwks.get('actionability')} |")
    md.append("\n## Bland-Altman (95% Limits of Agreement)\n")
    md.append("| Dim | n | Mean diff | SD diff | LoA lower | LoA upper |")
    md.append("|-----|---|-----------|---------|-----------|-----------|")
    for dim in DIMS:
        b = results["bland_altman"][dim]
        if b:
            md.append(f"| {dim} | {b['n']} | {b['mean_diff']} | {b['sd_diff']} | "
                      f"{b['loa_lower']} | {b['loa_upper']} |")

    REPORT_PATH.write_text("\n".join(md), encoding="utf-8")
    return {"results": results, "feedback": feedback, "converged": converged}


# =============================================================================
# Lane B — single-item evaluation wrapper
# =============================================================================
class LaneBEvaluateRequest(BaseModel):
    item: dict
    prompt_version: str = "v1"


# =============================================================================
# Lane C — Request model
# =============================================================================
class LaneCRequest(BaseModel):
    predictions_file: str = "paper/results/lane_b_predictions.json"
    gold_file: str = "paper/data/gold.json"
    prompt_version: str = "v1"


# =============================================================================
# Lane C Endpoints
# =============================================================================
@app.post("/lane-c")
def lane_c(req: LaneCRequest):
    """Run Lane C stats pipeline (predictions vs gold); returns report + feedback + convergence."""
    pred_path = ROOT / req.predictions_file
    gold_path = ROOT / req.gold_file
    if not pred_path.exists():
        raise HTTPException(status_code=404, detail=f"Predictions file not found: {pred_path}")
    if not gold_path.exists():
        raise HTTPException(status_code=404, detail=f"Gold file not found: {gold_path}")

    out = _compute_lane_c(pred_path, gold_path, req.prompt_version)
    return {
        "converged": out["converged"],
        "report_md": REPORT_PATH.read_text(encoding="utf-8") if REPORT_PATH.exists() else "",
        "feedback": out["feedback"],
    }


@app.get("/lane-c/feedback")
def lane_c_feedback():
    """Return the current lane_c_feedback.json as JSON."""
    if not FEEDBACK_PATH.exists():
        raise HTTPException(status_code=404, detail="lane_c_feedback.json not found")
    return json.loads(FEEDBACK_PATH.read_text(encoding="utf-8"))


@app.get("/lane-c/report")
def lane_c_report():
    """Return the current lane_c_report.md content as markdown."""
    if not REPORT_PATH.exists():
        raise HTTPException(status_code=404, detail="lane_c_report.md not found")
    return PlainTextResponse(REPORT_PATH.read_text(encoding="utf-8"), media_type="text/markdown")


@app.get("/lane-c/stats")
def lane_c_stats():
    """Return the current lane_c_stats.json as JSON."""
    if not STATS_PATH.exists():
        raise HTTPException(status_code=404, detail="lane_c_stats.json not found")
    return json.loads(STATS_PATH.read_text(encoding="utf-8"))


# =============================================================================
# Lane B Endpoints
# =============================================================================
@app.post("/lane-b/evaluate")
def lane_b_evaluate(req: LaneBEvaluateRequest):
    """Evaluate a single item using Lane B evaluator; returns prediction JSON."""
    try:
        from kb_ingest.lane_b_evaluator import evaluate_item as _eval_item
    except ImportError:
        raise HTTPException(status_code=500, detail="lane_b_evaluator not available")
    result = _eval_item(req.item, req.prompt_version)
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
