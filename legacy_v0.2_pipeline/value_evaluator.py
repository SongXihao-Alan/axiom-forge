"""
[3/5] Value Evaluator
按 8 个 value_root 的 instance 评分(0~1 参数化),输出 trade-off matrix。
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


class ValueScore(BaseModel):
    criterion: str
    instance_id: str
    score_before: float = Field(..., ge=0.0, le=1.0, description="扰动前的满足度 0~1")
    score_after: float = Field(..., ge=0.0, le=1.0, description="扰动后的满足度 0~1")
    delta: float
    reasoning: str
    confidence: float = Field(0.5, ge=0.0, le=1.0)


def load_value_roots() -> List[Dict]:
    p = ROOT / "training" / "value_roots_draft.json"
    return json.loads(p.read_text(encoding="utf-8"))["value_roots"]


def format_roots_for_prompt() -> str:
    roots = load_value_roots()
    out = []
    for r in roots:
        out.append(f"## {r['root_id']} ({r['name']})")
        for inst in r["instances"]:
            out.append(f"- {inst['instance_id']}: {inst['name']}")
            out.append(f"  formal: {inst.get('formal_form', '')}")
    return "\n".join(out)


VALUE_EVAL_SYSTEM = """你是经济学公理学 + 价值哲学的专家。**不要输出思考过程**,直接以 JSON 形式回答。
任务:给定一个公理扰动方案,对一组 planner-centric criterion 评分(0~1 连续值)。
核心要求:
- 0~1 连续值,不要 yes/no
- 每个评分配 reasoning(1-2 句)
- anchor 到具体 planner(医院、FAA、bankruptcy judge、frontier lab)
- delta = score_after - score_before
- 不确定就给 confidence 0.3,不要假装平衡给 0.5
- 不能 anchor 到 planner 的 criterion 标 confidence=0.2
输出严格 JSON,无额外文字。"""


def evaluate_perturbation(
    client: M3Client,
    seed_text: str,
    perturbation: Dict,
    max_criteria: int = 8,
) -> List[ValueScore]:
    """对扰动方案做 value evaluation。"""
    roots_text = format_roots_for_prompt()
    user = f"""
种子文献:

{seed_text}

扰动方案:
- target: {perturbation.get('target_id')}
- type: {perturbation.get('perturbation_type_id')}
- magnitude: {perturbation.get('magnitude')}
- original: {perturbation.get('original')}
- modified: {perturbation.get('modified')}
- rationale: {perturbation.get('rationale')}

可用 value criteria:

{roots_text}

请选**最多 {max_criteria} 个**最相关的 criterion 评分。
按以下 JSON 返回:
{{
  "scores": [
    {{
      "criterion": "<criterion 名字,如 efficiency / strategy-proofness / envy-freeness>",
      "instance_id": "<如 V-PARETO / V-DSIC / V-NO-ENVOY 等>",
      "score_before": 0.0,
      "score_after": 0.0,
      "delta": 0.0,
      "reasoning": "<1-2 句,anchor 到具体 planner>",
      "confidence": 0.5
    }}
  ]
}}
"""
    system = VALUE_EVAL_SYSTEM + "\n\n" + DIKTAT_INJECTION
    raw = client.chat_json(system, user, max_tokens=6000)
    scores = raw.get("scores", []) if isinstance(raw, dict) else []
    out = []
    for s in scores:
        try:
            sc = ValueScore(
                criterion=s["criterion"],
                instance_id=s["instance_id"],
                score_before=float(s.get("score_before", 0.5)),
                score_after=float(s.get("score_after", 0.5)),
                delta=float(s.get("score_after", 0.5)) - float(s.get("score_before", 0.5)),
                reasoning=s.get("reasoning", ""),
                confidence=float(s.get("confidence", 0.5)),
            )
            out.append(sc)
        except Exception as e:
            print(f"      [warn] value score parse err: {e}")
    return out
