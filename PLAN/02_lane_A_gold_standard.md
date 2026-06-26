# Lane A — Gold Standard

Building the 104-item hand-annotated gold standard + inter-rater reliability
Song Xihao (Alan), University of Glasgow  •  2026-06-23


# 1. Purpose

Lane A produces the gold standard: a hand-annotated dataset that defines 'ground truth' quality for each axiom item. The LLM evaluator (Lane B) is calibrated against this gold standard. Lane A also produces a dual-annotator subset for inter-rater reliability measurement — a methodological requirement for any publishable calibration study.


# 2. Gold Standard Size and Composition

Total: 104 items
- 74 real axioms from kb/nodes/ (axioms/, theorems/, assumptions/)
- 30 hand-built distractors from paper/data/distractors.json

Each item has:
- id: unique identifier
- natural_language: the axiom statement in English
- formal (optional): the formal version in mathematical notation
- domain: feature_attribution | mechanism_design | social_choice | fair_division | moral | philosophical
- tier: easy | medium | hard (based on annotator confidence)
- is_distractor: true/false
- failure_mode: circular | vague_gesture | restatement | premise_mismatch | no_source | contradictory | vacuous (distractors only)
- scores: {clarity, novelty, internal_consistency, empirical_grounding, actionability} ∈ [1, 5]
- anchors: {empirical, philosophical, community} (at least one required)


# 3. The 5-Dimension Rubric

Each dimension is scored 1–5:
- clarity (1=ungrammatical/meaningless, 5=crystal clear to any expert)
- novelty (1=restates existing axiom, 5=genuinely new insight not in literature)
- internal_consistency (1=logically self-contradictory, 5=formally airtight)
- empirical_grounding (1=no evidence, 5=strong empirical or theoretical backing)
- actionability (1=principle only, 5=directly implementable by practitioners)

Full rubric with anchor examples: paper/data/rubric.md


# 3a. Second Annotator Requirement (NEW — addresses R5)

CRITICAL: A single-annotator gold standard is insufficient for a publishable calibration study. Cohen's kappa requires two independent raters.

Requirement: Recruit one additional annotator to independently score a 30-item subset of gold.json (10 easy + 10 medium + 10 hard).

Rules:
1. The 30-item subset MUST be selected BEFORE annotation begins to avoid bias.
2. The two annotators MUST NOT discuss their scores until both are submitted.
3. The subset spans all 3 tiers (easy/medium/hard) proportionally.
4. Both annotators score independently using rubric.md.

Target: ≥ 0.6 QWK agreement on the 30-item dual-annotated subset.

If QWK < 0.6: revisit the rubric definition; retrain on rubric.md; re-annotate.

Output: paper/data/gold_dual_annotator.json — 30 items with fields:
- annotator_1_scores, annotator_2_scores, qwk_inter_rater

If time/methodological constraints prevent a second annotator, the paper MUST acknowledge this as a primary limitation in Lane D §5.


# 4. Annotation Process

1. Select 30-item dual-annotator subset (random stratified by tier)
2. Annotator 1 scores all 104 items using rubric.md
3. Annotator 2 independently scores the 30-item subset only
4. Compute inter-rater QWK on the 30-item overlap
5. If QWK ≥ 0.6, gold.json is final; if not, resolve discrepancies and re-annotate
6. Lock gold.json (no further changes after this)


# 5. Quality Assurance

Sanity checks (paper/data/sanity_check.py):
- All scores ∈ [1, 5]
- Distractors have mean_score < 2.5
- Real axioms have mean_score ≥ 3.0
- All items have at least 1 anchor
- Tier distribution: easy ≥ 20, medium ≥ 30, hard ≥ 20

Annotator notes: paper/data/annotator_notes.md (decision log, edge cases)


# 6. Lane A Deliverables

- paper/data/gold.json — 104 items, 5-dim scores, tier labels
- paper/data/gold_dual_annotator.json — 30-item subset, dual annotator QWK (NEW)
- paper/data/rubric.md — 5-dim scoring rubric with examples
- paper/data/annotator_notes.md — decision log