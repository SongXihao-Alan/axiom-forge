"""
v0.2 完整流水线(beta 版):带 retry + 评分 + 选最优。
literature_loader → perturbation_sampler → value_evaluator → axiom_deriver → consequence_predictor → memo_writer

retry 策略:每个 agent 失败时最多重试 N 次,返回第一个非空结果
最优选择:对多次运行打分(axiom 有非空内容 / value 有评分 / consequence 有内容),取最高分
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.llm import M3Client
from .literature_node_loader import load_seed, format_seed_for_prompt
from .perturbation_sampler import sample_perturbation
from .value_evaluator import evaluate_perturbation
from .axiom_deriver import derive_axiom
from .axiom_deriver_v2 import derive_axiom_v2
from .consequence_predictor import predict_consequences
from .memo_writer import render_memo


@dataclass
class PerturbationMemo:
    seed_id: str
    perturbation: Dict
    value_scores: List[Dict]
    new_axiom: Dict
    consequences: List[Dict]
    memo_md: str
    quality_score: float = 0.0  # 综合质量分
    run_id: int = 0  # 第几次 retry

    def to_dict(self):
        return {
            "seed_id": self.seed_id,
            "perturbation": self.perturbation,
            "value_scores": self.value_scores,
            "new_axiom": self.new_axiom,
            "consequences": self.consequences,
            "quality_score": self.quality_score,
            "run_id": self.run_id,
        }


# ============================================================
# 评分函数
# ============================================================

def score_axiom(axiom: Dict) -> float:
    """给 axiom 字段填充度打分。0 = 全空,1 = 全部填满。"""
    required = ["statement_nl", "formalization", "justification", "user_facing_explanation"]
    optional = ["preserves", "breaks", "falsifiable_predictions", "invariance_class"]

    score = 0.0
    for f in required:
        v = axiom.get(f, "")
        if v and len(str(v).strip()) > 5:
            score += 0.20  # 4 个 required 各占 0.20,合计 0.80
    for f in optional:
        v = axiom.get(f, None)
        if v:
            if isinstance(v, str) and len(v.strip()) > 0:
                score += 0.05
            elif isinstance(v, list) and len(v) > 0:
                score += 0.05
            elif isinstance(v, str) and v.strip():
                score += 0.05
    return min(score, 1.0)


def score_value_evaluation(scores: List[Dict]) -> float:
    """给 value evaluation 打分:有评分 + 有 reasoning + 有 confidence。"""
    if not scores:
        return 0.0
    n_useful = sum(1 for s in scores if s.get("reasoning") and s.get("reasoning") != "")
    return min(n_useful / 6.0, 1.0)  # 6 个有 reasoning 的 score = 满分


def score_consequences(cons: List[Dict]) -> float:
    """给 consequences 打分:有内容 + 有 scenario_anchor + 类型多样。"""
    if not cons:
        return 0.0
    n_useful = sum(1 for c in cons if c.get("statement") and len(c["statement"]) > 20)
    n_anchored = sum(1 for c in cons if c.get("scenario_anchor") and c.get("scenario_anchor") != "none")
    types = set(c.get("type", "") for c in cons)
    return min(
        0.5 * (n_useful / 4.0) + 0.3 * (n_anchored / 4.0) + 0.2 * (len(types) / 4.0),
        1.0
    )


def score_memo(memo: Dict) -> float:
    """综合分:axiom 0.5 + value 0.2 + consequence 0.3。"""
    return (
        0.5 * score_axiom(memo.get("new_axiom", {}))
        + 0.2 * score_value_evaluation(memo.get("value_scores", []))
        + 0.3 * score_consequences(memo.get("consequences", []))
    )


# ============================================================
# Retry 包装器
# ============================================================

def with_retry(fn, max_retries: int = 3, label: str = "agent"):
    """调用 fn(),失败(返回空 / 异常)时重试,直到拿到非空结果或用完重试次数。"""
    last_err = None
    for i in range(max_retries):
        try:
            result = fn()
            if result and (not isinstance(result, list) or len(result) > 0):
                if i > 0:
                    print(f"      [retry success on attempt {i+1}]")
                return result
        except Exception as e:
            last_err = e
            print(f"      [retry {i+1}/{max_retries}] {label} err: {e}")
        time.sleep(1.0)
    print(f"      [retry exhausted] {label}: {last_err}")
    return [] if "list" in str(type(fn())) else None


# ============================================================
# 单次完整运行
# ============================================================

def run_one(
    seed_id: str,
    perturbation: Dict,
    client: M3Client,
    seed_text: str,
    run_id: int = 0,
    n_consequences: int = 4,
    max_value_criteria: int = 8,
    use_v2: bool = True,
) -> Optional[PerturbationMemo]:
    """单次跑完整 pipeline(除 sampler 外)。"""
    # value evaluator (retry)
    scores = with_retry(
        lambda: evaluate_perturbation(client, seed_text, perturbation, max_criteria=max_value_criteria),
        max_retries=3,
        label="value_evaluator",
    )
    if not scores:
        scores = []
    scores_dict = [s.model_dump() for s in scores]

    # axiom deriver v2 (协作式:deriver + notation_definer)
    if use_v2:
        new_axiom = with_retry(
            lambda: derive_axiom_v2(client, seed_text, perturbation, scores_dict, max_cycles=3),
            max_retries=3,
            label="axiom_deriver_v2",
        )
    else:
        new_axiom = with_retry(
            lambda: derive_axiom(client, seed_text, perturbation, scores_dict),
            max_retries=3,
            label="axiom_deriver",
        )
    if not new_axiom:
        from axiom_v02.axiom_deriver import CandidateAxiom
        new_axiom = CandidateAxiom(
            id="AX-FAIL", statement_nl="(axiom deriver failed)",
            formalization="", justification="", user_facing_explanation=""
        )
    new_axiom_dict = new_axiom.model_dump() if hasattr(new_axiom, "model_dump") else new_axiom

    # consequence predictor (retry)
    cons = with_retry(
        lambda: predict_consequences(client, seed_text, perturbation, new_axiom_dict, n_consequences=n_consequences),
        max_retries=3,
        label="consequence_predictor",
    )
    if not cons:
        cons = []
    cons_dict = [c.model_dump() for c in cons]

    # memo
    memo_md = render_memo(
        seed_id=seed_id,
        seed_text=seed_text,
        perturbation=perturbation,
        value_scores=scores_dict,
        new_axiom=new_axiom_dict,
        consequences=cons_dict,
    )

    memo_dict = {
        "perturbation": perturbation,
        "value_scores": scores_dict,
        "new_axiom": new_axiom_dict,
        "consequences": cons_dict,
    }
    q = score_memo(memo_dict)

    return PerturbationMemo(
        seed_id=seed_id,
        perturbation=perturbation,
        value_scores=scores_dict,
        new_axiom=new_axiom_dict,
        consequences=cons_dict,
        memo_md=memo_md,
        quality_score=q,
        run_id=run_id,
    )


# ============================================================
# 完整 v0.2 入口(带 retry + 选最优)
# ============================================================

def run_v02_pipeline(
    seed_id: str,
    perturbation: Optional[Dict] = None,
    n_pipeline_runs: int = 3,
    n_proposals: int = 3,
    output_dir: Optional[str] = None,
) -> List[PerturbationMemo]:
    """
    对给定 seed 跑完整 v0.2 pipeline。
    - 如果 perturbation=None:让 sampler 选 n_proposals 个扰动,各跑一次
    - 如果 perturbation=Dict:用这个扰动跑 n_pipeline_runs 次,取质量最高的
    """
    client = M3Client()
    seed = load_seed(seed_id)
    seed_text = format_seed_for_prompt(seed)

    print(f"\n========= [v0.2 PIPELINE beta: {seed_id}] =========")
    print(f"\n[1/5] 📚 Literature Node Loader — {seed_id} loaded")

    if perturbation is None:
        # 让 sampler 选扰动
        print(f"\n[2/5] 🎯 Perturbation Sampler — sampling {n_proposals} proposals")
        proposals = with_retry(
            lambda: sample_perturbation(client, seed_text, n_proposals=n_proposals),
            max_retries=3,
            label="sampler",
        )
        if not proposals:
            print("      [fatal] sampler failed, abort")
            return []
        print(f"      → {len(proposals)} proposals")
        perturbations = [p.model_dump() for p in proposals]
    else:
        print(f"\n[2/5] 🎯 Perturbation Sampler — MANUAL: {perturbation.get('target_id')} ({perturbation.get('perturbation_type_id')})")
        perturbations = [perturbation]

    out_dir = Path(output_dir) if output_dir else (ROOT / "outputs" / "v0.2")
    out_dir.mkdir(parents=True, exist_ok=True)

    all_best_memos: List[PerturbationMemo] = []

    for idx, pert in enumerate(perturbations, 1):
        print(f"\n--- Perturbation {idx}/{len(perturbations)}: {pert.get('target_id')} ({pert.get('perturbation_type_id')}) ---")
        # 跑 n_pipeline_runs 次,取质量最高
        candidates: List[PerturbationMemo] = []
        for r in range(n_pipeline_runs):
            print(f"\n      [run {r+1}/{n_pipeline_runs}]")
            memo = run_one(seed_id, pert, client, seed_text, run_id=r+1)
            if memo:
                print(f"      [run {r+1}] quality = {memo.quality_score:.3f}")
                candidates.append(memo)
                # ★ 每 run 立即保存(防止慢/中断丢失)
                slug = f"{seed_id}_{pert.get('perturbation_type_id')}_{pert.get('target_id')}_run{r+1}".replace("/", "_")
                try:
                    (out_dir / f"{slug}.md").write_text(memo.memo_md)
                    (out_dir / f"{slug}.json").write_text(json.dumps(memo.to_dict(), ensure_ascii=False, indent=2))
                    print(f"      [run {r+1}] saved {slug}.md")
                except Exception as e:
                    print(f"      [run {r+1}] save err: {e}")

        if not candidates:
            print(f"      [warn] all {n_pipeline_runs} runs failed for this perturbation")
            continue

        # 选最优
        best = max(candidates, key=lambda m: m.quality_score)
        print(f"\n      ★ BEST: run {best.run_id} with quality={best.quality_score:.3f}")
        print(f"      ★ axiom: {best.new_axiom.get('statement_nl', '')[:80]}")
        all_best_memos.append(best)

        # 写文件(只写最佳)
        slug = f"{seed_id}_{pert.get('perturbation_type_id')}_{pert.get('target_id')}".replace("/", "_")
        md_path = out_dir / f"{slug}.md"
        json_path = out_dir / f"{slug}.json"
        md_path.write_text(best.memo_md)
        json_path.write_text(json.dumps(best.to_dict(), ensure_ascii=False, indent=2))
        print(f"      ✅ Saved: {md_path.name} (best of {len(candidates)})")

    return all_best_memos


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default="myerson_1981")
    parser.add_argument("--n-pipeline-runs", type=int, default=3)
    parser.add_argument("--n-proposals", type=int, default=2)
    args = parser.parse_args()
    memos = run_v02_pipeline(
        args.seed,
        n_pipeline_runs=args.n_pipeline_runs,
        n_proposals=args.n_proposals,
    )
    print(f"\n✅ Total: {len(memos)} best-of-N PerturbationMemos generated.")
