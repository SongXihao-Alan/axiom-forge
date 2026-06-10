"""
[2/5] Perturbation Sampler
从 Thomson 8 维扰动分类中选 1 个,生成具体扰动提案。
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Dict, List
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.llm import M3Client
from training.diktat_injection import DIKTAT_INJECTION


class PerturbationProposal(BaseModel):
    target_id: str
    target_kind: str  # "axiom" | "assumption"
    original: str
    modified: str
    rationale: str
    magnitude: str  # "micro" | "meso" | "macro"
    perturbation_type_id: str  # PERT-* 之一


PERTURBATION_SYSTEM = """你是机制设计公理学的专家。**不要输出任何思考过程**,直接以 JSON 形式回答。
任务:从 Thomson 8 维扰动分类中为一个给定的种子文献节点选**最有学术价值**的 axiom/assumption 进行扰动。
Thomson 8 维: PERT-UNIV-MODEL, PERT-PUNCT-REL, PERT-PRE-POST, PERT-IND-GRP, PERT-SELF-OTHER, PERT-FIX-VAR, PERT-MONO-INV, PERT-CONTENT。
要求: 修改要可操作; rationale 回答"为什么有趣/重要"; magnitude ∈ micro/meso/macro。
输出严格 JSON,无额外文字。"""


def load_perturbation_taxonomy() -> List[Dict]:
    p = ROOT / "training" / "graph" / "perturbations" / "perturbation_taxonomy.json"
    return json.loads(p.read_text(encoding="utf-8"))["perturbation_types"]


def format_taxonomy_for_prompt() -> str:
    types = load_perturbation_taxonomy()
    out = []
    for t in types:
        out.append(f"- **{t['id']}** ({t['dimension']}): {t['description']}")
        out.append(f"  - from: {t['from']} → to: {t['to']}")
        out.append(f"  - rationale: {t['rationale']}")
    return "\n".join(out)


def sample_perturbation(
    client: M3Client,
    seed_text: str,
    n_proposals: int = 3,
) -> List[PerturbationProposal]:
    """让 M3 提出 n 个扰动提案。"""
    taxonomy = format_taxonomy_for_prompt()
    user = f"""
种子文献节点:

{seed_text}

可用扰动分类(Thomson 8 维):

{taxonomy}

请提出 **{n_proposals} 个**扰动提案(每个必须**不同**的 perturbation_type_id)。
按以下 JSON 返回:
{{
  "proposals": [
    {{
      "target_id": "<被修改的 axiom/assumption id>",
      "target_kind": "axiom|assumption",
      "original": "<原文>",
      "modified": "<修改后>",
      "rationale": "<为什么这个扰动有趣/重要>",
      "magnitude": "micro|meso|macro",
      "perturbation_type_id": "PERT-*"
    }}
  ]
}}
"""
    system = PERTURBATION_SYSTEM + "\n\n" + DIKTAT_INJECTION
    raw = client.chat_json(system, user, max_tokens=6000)
    proposals = raw.get("proposals", []) if isinstance(raw, dict) else []
    out = []
    for p in proposals:
        try:
            out.append(PerturbationProposal(**p))
        except Exception as e:
            print(f"      [warn] proposal parse err: {e}")
    return out
