#!/usr/bin/env python3
"""
Axiom Forge — Lane B LLM Evaluator (replaces validate_node_m3)

Inputs:  KB nodes (axiom/theorem/value_anchor/...) OR distractor items
Output: 5-dim scores (clarity / novelty / internal_consistency /
         empirical_grounding / actionability) on 1-5 integer scale
LLM:     MINIMAX_API_KEY (MiniMax-M3)

Modes:
  evaluate <node_id>          — score a single KB node
  evaluate-file <path>        — score a single JSON file (gold.json or distractor)
  evaluate-all                — score all KB nodes
  evaluate-gold               — score all 104 items in paper/data/gold.json
  evaluate-distractors        — score all 30 items in paper/data/distractors.json
  scale <target>              — generate + evaluate N items (target=2000+)
  report <predictions.json>   — compute Cohen's kappa vs gold
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent.parent
KB_NODES = ROOT / "kb" / "nodes"
GOLD = ROOT / "paper" / "data" / "gold.json"
DISTRACTORS = ROOT / "paper" / "data" / "distractors.json"
PREDICTIONS = ROOT / "paper" / "results" / "lane_b_predictions.json"
DIMS = ["clarity", "novelty", "internal_consistency",
        "empirical_grounding", "actionability"]

# ── M3 client (replaces kb_llm.py:validate_node_m3) ──────────────
def _m3_call(system: str, user: str, max_tokens: int = 1500) -> Optional[str]:
    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        return None
    base_url = os.environ.get("MINIMAX_BASE_URL", "https://api.minimaxi.com/v1")
    model = os.environ.get("MINIMAX_MODEL", "MiniMax-M3")
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode("utf-8"))
        raw = data["choices"][0]["message"]["content"]
        # Strip M3's <think>...</think>
        return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    except urllib.error.HTTPError as e:
        return f"ERROR: HTTP {e.code}: {e.read().decode('utf-8')[:200]}"
    except Exception as e:
        return f"ERROR: {e}"


# ── Rubric prompt ─────────────────────────────────────────────────
RUBRIC_PROMPT = """You are an axiom-quality evaluator. Given a candidate axiom (natural-language + formal statement + source/anchors if provided), score it on these 5 dimensions, each an integer 1-5:

1. **clarity** — Is the NL statement unambiguous? Can a domain expert tell what it asserts without further clarification?
2. **novelty** — Is this a new claim, or a restatement of a known result? (low = canonical restatement; high = genuinely new)
3. **internal_consistency** — Is the formal statement self-consistent (no p ∧ ¬p, no scope errors, no vacuous content)?
4. **empirical_grounding** — Is there a traceable citation/anchor/evidence chain?
5. **actionability** — Can a competent engineer write a test case for this axiom in <1 day?

Anchor scale (use strictly):
- 5 = top tier; clear winner
- 4 = solid, minor issues
- 3 = average; identifiable but hand-wavy
- 2 = weak; experts would flag
- 1 = failure (circular, vacuous, or no source)

Output a JSON object with this exact shape (and nothing else):
{
  "scores": {"clarity": N, "novelty": N, "internal_consistency": N,
             "empirical_grounding": N, "actionability": N},
  "justifications": {"clarity": "...", "novelty": "...", ...},
  "tier": "easy|medium|hard"
}

Tier rule: easy if score spread ≤ 2; hard if spread ≥ 3 OR contains a subtle distractor; else medium.
"""


# ── Item construction ────────────────────────────────────────────
def item_from_kb(node: dict) -> dict:
    """Convert a KB node dict into a Lane B evaluation item."""
    return {
        "id": node.get("id"),
        "type": node.get("type"),
        "source": f"kb/nodes/{node.get('type')}s/{node.get('id')}.json",
        "is_distractor": False,
        "nl": node.get("nl") or node.get("description") or node.get("title") or "",
        "formal": node.get("formal") or "",
        "domain": node.get("domain", ""),
        "anchors": node.get("anchors", []),
        "process_meta": node.get("process_meta", {}),
    }


def item_from_distractor(d: dict) -> dict:
    """Convert a distractors.json entry into a Lane B item."""
    return {
        "id": d.get("id"),
        "type": "distractor",
        "source": "paper/data/distractors.json",
        "is_distractor": True,
        "nl": d.get("nl", ""),
        "formal": d.get("formal", ""),
        "failure_mode": d.get("failure_mode", ""),
    }


def item_from_gold(g: dict) -> dict:
    """Convert a gold.json item (which may reference KB or be a distractor)."""
    return {
        "id": g.get("id"),
        "type": g.get("type"),
        "source": g.get("source", ""),
        "is_distractor": g.get("is_distractor", False),
        "nl": "",  # loaded from KB if available
        "formal": "",
    }


def load_item_nl_formal(item: dict) -> dict:
    """Augment item with nl/formal from KB if not already set."""
    if item.get("nl") and item.get("formal"):
        return item
    if item.get("is_distractor") and item.get("id", "").startswith("DIS-"):
        # Look up in distractors.json
        d_data = json.loads(DISTRACTORS.read_text(encoding="utf-8"))
        for d in d_data.get("distractors", []):
            if d.get("id") == item["id"]:
                item["nl"] = item.get("nl") or d.get("nl", "")
                item["formal"] = item.get("formal") or d.get("formal", "")
                return item
        return item
    # Look up in KB
    kb_path = item.get("source", "")
    if kb_path and not kb_path.startswith("kb/"):
        # Try relative
        kb_path = "kb/" + kb_path
    p = ROOT / kb_path
    if p.exists():
        try:
            n = json.loads(p.read_text(encoding="utf-8"))
            item["nl"] = item.get("nl") or n.get("nl") or n.get("description") or n.get("title", "")
            item["formal"] = item.get("formal") or n.get("formal", "")
            item["anchors"] = item.get("anchors") or n.get("anchors", [])
            item["process_meta"] = item.get("process_meta") or n.get("process_meta", {})
        except Exception:
            pass
    return item


# ── Evaluation ───────────────────────────────────────────────────
def evaluate_item(item: dict) -> dict:
    """Run M3 on a single item, return scores + justifications."""
    item = load_item_nl_formal(item)
    nl = item.get("nl", "")
    formal = item.get("formal", "")
    anchors = item.get("anchors", [])
    if not nl and not formal:
        return {
            "id": item.get("id"),
            "scores": {d: 1 for d in DIMS},
            "justifications": {d: "no NL or formal statement" for d in DIMS},
            "tier": "easy",
            "error": "empty item",
        }
    user = (
        f"## Candidate axiom\n\n"
        f"NL: {nl[:600]}\n\n"
        f"Formal: {formal[:400]}\n\n"
        f"Anchors: {json.dumps(anchors, ensure_ascii=False)[:200] if anchors else '(none)'}\n\n"
        f"## Output (JSON only):"
    )
    raw = _m3_call(RUBRIC_PROMPT, user, max_tokens=1500)
    if not raw:
        return {
            "id": item.get("id"),
            "scores": {d: None for d in DIMS},
            "justifications": {},
            "tier": None,
            "error": "MINIMAX_API_KEY not set or call failed",
        }
    if raw.startswith("ERROR"):
        return {
            "id": item.get("id"),
            "scores": {d: None for d in DIMS},
            "justifications": {},
            "tier": None,
            "error": raw,
        }
    try:
        # Strip ```json fences if present
        m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL)
        if m:
            raw = m.group(1)
        result = json.loads(raw)
        # Coerce scores to ints, validate range
        for d in DIMS:
            v = result.get("scores", {}).get(d)
            if v is not None:
                v = int(v)
                if v < 1: v = 1
                if v > 5: v = 5
                result["scores"][d] = v
        result["id"] = item.get("id")
        return result
    except Exception as e:
        return {
            "id": item.get("id"),
            "scores": {d: None for d in DIMS},
            "justifications": {},
            "tier": None,
            "error": f"parse failed: {e}; raw={raw[:200]}",
        }


# ── Bulk evaluation with rate limit + retry ─────────────────────
def evaluate_all(items: list[dict], output_path: Path,
                 rate_limit_s: float = 1.0) -> list[dict]:
    """Evaluate all items; save predictions to output_path; resume from existing."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    predictions = []
    if output_path.exists():
        try:
            predictions = json.loads(output_path.read_text(encoding="utf-8"))
            print(f"Resuming: {len(predictions)} predictions already on file")
        except Exception:
            predictions = []
    done_ids = {p.get("id") for p in predictions if p.get("id")}

    import time
    for i, item in enumerate(items):
        if item.get("id") in done_ids:
            continue
        print(f"[{i+1}/{len(items)}] {item.get('id')}", end=" ", flush=True)
        pred = evaluate_item(item)
        if "scores" in pred and pred["scores"]:
            scores = pred["scores"]
            score_str = " ".join(f"{d[:3]}={scores[d]}" for d in DIMS if scores.get(d) is not None)
            print(f"-> {score_str} tier={pred.get('tier','?')}")
        else:
            print(f"-> ERROR: {pred.get('error','?')[:60]}")
        predictions.append(pred)
        # Save after each item (resume-safe)
        output_path.write_text(json.dumps(predictions, ensure_ascii=False, indent=2),
                              encoding="utf-8")
        time.sleep(rate_limit_s)
    return predictions


# ── Cohen's kappa vs gold ───────────────────────────────────────
def cohens_kappa(predictions: list[dict], gold: list[dict], dim: str) -> Optional[float]:
    """Quadratic-weighted Cohen's kappa for one dimension."""
    pred_map = {p["id"]: p for p in predictions if p.get("id")}
    gold_map = {g["id"]: g for g in gold if g.get("id")}
    common = set(pred_map) & set(gold_map)
    if not common:
        return None
    pred_scores = [pred_map[i]["scores"].get(dim) for i in common]
    gold_scores = [gold_map[i]["scores"].get(dim) for i in common]
    pairs = [(p, g) for p, g in zip(pred_scores, gold_scores) if p is not None and g is not None]
    if not pairs:
        return None
    # Quadratic-weighted kappa
    k = 5
    weights = [[(i - j) ** 2 / (k - 1) ** 2 for j in range(1, k + 1)] for i in range(1, k + 1)]
    n = len(pairs)
    observed = sum(weights[p - 1][g - 1] for p, g in pairs) / n
    pred_counts = Counter(p for p, _ in pairs)
    gold_counts = Counter(g for _, g in pairs)
    expected = sum(
        (pred_counts[i] / n) * (gold_counts[j] / n) * weights[i - 1][j - 1]
        for i in range(1, k + 1) for j in range(1, k + 1)
    )
    if expected >= 1.0:
        return 1.0
    return 1 - observed / expected


def report(predictions_path: Path, gold_path: Path) -> int:
    if not predictions_path.exists():
        print(f"ERROR: {predictions_path} not found")
        return 1
    predictions = json.loads(predictions_path.read_text(encoding="utf-8"))
    gold_data = json.loads(gold_path.read_text(encoding="utf-8"))
    gold = gold_data.get("items", [])
    print(f"Predictions: {len(predictions)}, Gold: {len(gold)}")
    print()
    print("=" * 60)
    print(f"{'Dimension':<28} {'QWK':<8} {'n':<6} {'coverage'}")
    print("=" * 60)
    for dim in DIMS:
        k = cohens_kappa(predictions, gold, dim)
        pred_map = {p["id"]: p for p in predictions if p.get("id")}
        gold_map = {g["id"]: g for g in gold if g.get("id")}
        common = set(pred_map) & set(gold_map)
        non_null = sum(1 for i in common
                       if pred_map[i]["scores"].get(dim) is not None
                       and gold_map[i]["scores"].get(dim) is not None)
        cov = f"{non_null}/{len(common)}" if common else "0/0"
        print(f"{dim:<28} {k if k is not None else 'N/A':<8} {len(common):<6} {cov}")
    # Mean absolute error
    print()
    print("Mean absolute error per dim:")
    for dim in DIMS:
        pred_map = {p["id"]: p for p in predictions if p.get("id")}
        gold_map = {g["id"]: g for g in gold if g.get("id")}
        common = set(pred_map) & set(gold_map)
        errs = [
            abs(pred_map[i]["scores"][dim] - gold_map[i]["scores"][dim])
            for i in common
            if pred_map[i]["scores"].get(dim) is not None
            and gold_map[i]["scores"].get(dim) is not None
        ]
        mae = sum(errs) / len(errs) if errs else None
        print(f"  {dim:<28} {mae if mae is not None else 'N/A'}")
    return 0


# ── Scaling to 2000+ items ──────────────────────────────────────
def scale_to(target: int, predictions_path: Path) -> int:
    """Generate + evaluate items until we hit `target` total predictions."""
    # Start with gold + distractors + KB nodes as the base set
    base_items = []
    if GOLD.exists():
        gold_data = json.loads(GOLD.read_text(encoding="utf-8"))
        for g in gold_data.get("items", []):
            base_items.append(item_from_gold(g))
    if DISTRACTORS.exists():
        d_data = json.loads(DISTRACTORS.read_text(encoding="utf-8"))
        for d in d_data.get("distractors", []):
            base_items.append(item_from_distractor(d))
    # All KB nodes
    for type_dir in KB_NODES.iterdir():
        if not type_dir.is_dir():
            continue
        for f in type_dir.glob("*.json"):
            try:
                n = json.loads(f.read_text(encoding="utf-8"))
                base_items.append(item_from_kb(n))
            except Exception:
                continue
    # Dedup by id
    seen = set()
    unique = []
    for it in base_items:
        if it.get("id") and it["id"] not in seen:
            seen.add(it["id"])
            unique.append(it)
    base_items = unique
    print(f"Base set: {len(base_items)} unique items")
    # If under target, auto-generate distractors from KB nodes
    if len(base_items) < target:
        needed = target - len(base_items)
        print(f"Need {needed} more items; auto-generating distractors from KB nodes")
        # Distractor construction: pick a KB node, perturb a dimension
        candidates = [it for it in base_items if not it.get("is_distractor") and it.get("nl")]
        for i in range(needed):
            src = candidates[i % len(candidates)]
            new_id = f"AUTO-DIS-{i+1:04d}"
            perturb_mode = ["circular", "vague_gesture", "restatement",
                            "premise_mismatch", "no_source", "contradictory",
                            "vacuous"][i % 7]
            nl, formal = _generate_distractor(src, perturb_mode)
            base_items.append({
                "id": new_id,
                "type": "auto_distractor",
                "source": f"lane_b_evaluator.py auto-generation mode={perturb_mode}",
                "is_distractor": True,
                "nl": nl,
                "formal": formal,
                "failure_mode": perturb_mode,
                "perturb_source": src.get("id"),
            })
    print(f"Final item count: {len(base_items)}")
    return evaluate_all(base_items, predictions_path)


def _generate_distractor(src: dict, mode: str) -> tuple[str, str]:
    """Generate a perturbed distractor item from a source axiom."""
    nl = src.get("nl", "")
    formal = src.get("formal", "")
    if mode == "circular":
        return (f"{nl.split(' ')[0] if nl.split() else 'X'} is true if and only if "
                f"{nl.split(' ')[0] if nl.split() else 'X'} is true.",
                f"True ↔ True")
    if mode == "vague_gesture":
        return (f"{nl} in a meaningful, appropriate, and reasonable way.",
                f"∀x: Reasonable({formal[:50]}) [no definition]")
    if mode == "restatement":
        return (f"Restating: {nl} (this is just a restatement).",
                formal or "True")
    if mode == "premise_mismatch":
        return (f"If the axiom is vacuous, then {nl}",
                f"Vacuous ⇒ ({formal})")
    if mode == "no_source":
        return (nl, formal)
    if mode == "contradictory":
        return (f"NOT ({nl})",
                f"¬({formal})")
    if mode == "vacuous":
        return (f"For all x in the empty set, {nl}",
                f"∀x ∈ ∅: ({formal})")
    return (nl, formal)


# ── CLI ─────────────────────────────────────────────────────────
def cmd_evaluate_one(node_id: str) -> int:
    for type_dir in KB_NODES.iterdir():
        if not type_dir.is_dir():
            continue
        for f in type_dir.glob("*.json"):
            try:
                n = json.loads(f.read_text(encoding="utf-8"))
                if n.get("id") == node_id:
                    item = item_from_kb(n)
                    pred = evaluate_item(item)
                    print(json.dumps(pred, ensure_ascii=False, indent=2))
                    return 0
            except Exception:
                continue
    print(f"ERROR: node '{node_id}' not found in KB", file=sys.stderr)
    return 1


def cmd_evaluate_gold() -> int:
    if not GOLD.exists():
        print(f"ERROR: {GOLD} not found")
        return 1
    data = json.loads(GOLD.read_text(encoding="utf-8"))
    items = [item_from_gold(g) for g in data.get("items", [])]
    return evaluate_all(items, PREDICTIONS)


def cmd_evaluate_distractors() -> int:
    if not DISTRACTORS.exists():
        print(f"ERROR: {DISTRACTORS} not found")
        return 1
    data = json.loads(DISTRACTORS.read_text(encoding="utf-8"))
    items = [item_from_distractor(d) for d in data.get("distractors", [])]
    return evaluate_all(items, PREDICTIONS)


def cmd_evaluate_all() -> int:
    items = []
    for type_dir in KB_NODES.iterdir():
        if not type_dir.is_dir():
            continue
        for f in type_dir.glob("*.json"):
            try:
                n = json.loads(f.read_text(encoding="utf-8"))
                items.append(item_from_kb(n))
            except Exception:
                continue
    return evaluate_all(items, PREDICTIONS)


def cmd_scale(target: int) -> int:
    return scale_to(target, PREDICTIONS)


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("evaluate", help="Score a single KB node")
    sp.add_argument("node_id")

    sub.add_parser("evaluate-all", help="Score every KB node")
    sub.add_parser("evaluate-gold", help="Score all 104 gold items")
    sub.add_parser("evaluate-distractors", help="Score all 30 distractor items")

    sp = sub.add_parser("scale", help="Scale to N items (auto-generate distractors)")
    sp.add_argument("target", type=int)

    sp = sub.add_parser("report", help="Compute Cohen's kappa vs gold")
    sp.add_argument("--gold", default=str(GOLD))

    args = p.parse_args()
    if args.cmd == "evaluate":
        return cmd_evaluate_one(args.node_id)
    elif args.cmd == "evaluate-all":
        return cmd_evaluate_all()
    elif args.cmd == "evaluate-gold":
        return cmd_evaluate_gold()
    elif args.cmd == "evaluate-distractors":
        return cmd_evaluate_distractors()
    elif args.cmd == "scale":
        return cmd_scale(args.target)
    elif args.cmd == "report":
        return report(PREDICTIONS, Path(args.gold))
    return 1


if __name__ == "__main__":
    sys.exit(main())
