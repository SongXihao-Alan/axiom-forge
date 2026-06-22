"""
[1/5] Literature Node Loader
从 JSON 加载手工结构化的种子文献节点。
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def load_seed(seed_id: str) -> Dict:
    """加载种子文献节点(从 training/seeds/ 或 seeds/ 目录)。"""
    candidates = [
        ROOT / "training" / "seeds" / f"{seed_id}.json",
        ROOT / "seeds" / f"{seed_id}.json",
    ]
    for p in candidates:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"seed not found: {seed_id}")


def list_available_seeds() -> List[str]:
    """列出所有可用种子文献 id。"""
    out = []
    for d in [ROOT / "training" / "seeds", ROOT / "seeds"]:
        if d.exists():
            for p in d.glob("*.json"):
                out.append(p.stem)
    return sorted(set(out))


def format_seed_for_prompt(seed: Dict) -> str:
    """把种子节点格式化成 LLM 友好的文本。"""
    meta = seed.get("meta", {})
    lines = [
        f"# {meta.get('title', 'Unknown')}",
        f"Authors: {', '.join(meta.get('authors', []))}",
        f"Year: {meta.get('year')}, Venue: {meta.get('venue')}",
        f"ID: {meta.get('id')}",
    ]
    linage = meta.get("linage", {})
    if linage:
        lines.append(f"Linage: in={linage.get('in', [])}, out={linage.get('out', [])}, branch={linage.get('branch')}")
    lines.append("")
    lines.append("## Axioms")
    for a in seed.get("axioms", []):
        lines.append(f"- **{a['id']}** ({a.get('type', '?')}): {a['statement']}")
    lines.append("")
    lines.append("## Assumptions")
    for a in seed.get("assumptions", []):
        lines.append(f"- **{a['id']}** ({a.get('type', '?')}): {a['statement']}")
    lines.append("")
    lines.append("## Theorems")
    for t in seed.get("theorems", []):
        lines.append(f"- **{t['id']}**: {t['statement']}")
        if t.get("depends_on"):
            lines.append(f"  depends on: {', '.join(t['depends_on'])}")
    lines.append("")
    lines.append("## Propositions")
    for p in seed.get("propositions", []):
        lines.append(f"- **{p['id']}** ({p.get('proof_status', '?')}): {p['claim']}")
    return "\n".join(lines)
