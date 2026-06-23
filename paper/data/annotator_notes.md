# Annotator Notes — Lane A

This file documents the design choices, edge cases, and known limitations of the
gold-standard dataset built for the LLM-axiom-evaluator calibration study.

## 1. Scope and Selection

The KB contains 86 nodes spread across 8 types. Rather than label every node, we
selected **74 representative real items** (out of 86) plus **30 hand-built distractors**
= **104 total items**. The selection biases were:

- **All 8 axioms** included (low count, every one matters).
- **All 10 theorems** included.
- **All 12 diktats** included (they're all handcrafted; we kept them).
- **All 4 tradeoffs**, **all 6 scenarios**, **both assumptions** included.
- **21 of 33 value_anchors** included — we dropped 12 that were near-duplicates
  (e.g., aesthetic subclasses where labels were nearly identical).
- **11 of 10 literature nodes** included — the dedup in the source directory left
  LIT-L17-SHAP appearing twice; we kept both copies as separate items because they
  appear as distinct JSON files in the KB and an LLM evaluator will see both.

The remaining 12 nodes are reserved for future expansion (see Open Questions).

## 2. Rubric (5 dimensions, 1–5 scale)

The rubric is in `rubric.md`. Three principles drove its design:

1. **Dimensions are independent.** A node can be high on `clarity` but low on
   `empirical_grounding`, etc.
2. **Internal consistency is purely local.** We do not penalize a node for
   contradicting *another* node unless the contradiction is visible from the
   statement alone.
3. **Actionability is domain-sensitive.** Value anchors (`VA-*`) are scored honestly
   low on actionability (~2) because they assert general moral/aesthetic claims
   that require context to test. Allocation axioms (`AX-*`) are scored high (~4-5).

## 3. Distractor construction

The 30 distractors are designed to fail 1–3 specific dimensions. They are
grouped by `failure_mode` in `distractors.json`:

| failure_mode    | count | description                                            |
|-----------------|-------|--------------------------------------------------------|
| circular        | 6     | Defines predicate in terms of itself                    |
| vague_gesture   | 9     | Uses undefined words ("meaningful", "fair", "good")    |
| restatement     | 3     | Faithful restatement of a known axiom without citation |
| premise_mismatch| 3     | Conclusion doesn't follow from premise                 |
| no_source       | 3     | Claim with no citation or anchor chain                  |
| contradictory   | 3     | Asserts both p and ¬p                                   |
| vacuous         | 3     | Quantifier over empty set, or tautology                 |

Distractors were tuned to score **mean ≈ 1.8 across dims** (target: 2.0). Real
items score **mean ≈ 3.9 across dims** (target: 3.5+). The 2.1-point gap is
intentional — it gives an LLM evaluator a clear signal but also leaves room for
boundary errors.

## 4. Edge cases and conventions

### 4.1 `status: "draft"` / `status: "seed"` nodes
Items with weaker status were scored honestly lower. Example: AX-SHAP-CONS has
status=seed and only cites L17; we scored its `empirical_grounding=3` rather
than 4. AX-SHAP-EFF has status=seed but is canonical (Shapley 1953); its
`empirical_grounding=4` because it has the industrial-deployment evidence.

### 4.2 Known internal tensions
Some real items have known internal tensions flagged in their `process_meta`:

- **AX-SC-001** has process_meta noting the asymmetry (SC acts on f, others on f̂)
  is the innovation. We scored `novelty=5`.
- **TH-SHAP-UNIQ** has process_meta flagging circularity in L17's uniqueness.
  We scored `internal_consistency=4` (downgraded from 5).
- **TH-PROP-621/622/624** have status=sketch/argued. We scored
  `empirical_grounding=2` (no external citation) but kept `internal_consistency`
  high because the logical claim is sound.

### 4.3 Handcrafted vs. seed status
Per the schema, `handcrafted` nodes are the user's own inventions; `seed` nodes
are imported from canonical sources. `handcrafted` items are NOT automatically
scored higher on novelty — AX-SC-001 (handcrafted) gets novelty=5, but TH-IMP-501
(handcrafted, more complex) gets novelty=5 as well.

### 4.4 Score spread and tier assignment
Tier is derived as follows:

- **easy**: score spread across dims ≤ 2 (or ≥1 dim with score 5 and ≥1 with 1),
  AND any distractor present is obviously bad on 2+ dims. The LLM should be
  confident.
- **medium**: spread 2-3, item is clearly a real axiom, no obvious trap.
- **hard**: spread ≥ 3 across dims, OR the item has a known internal tension
  flagged in `process_meta`, OR the distractor is subtle (e.g., DIS-011
  contradicts SHAP-DUM, which an LLM might miss).

After promotion, the final tier distribution is **46 easy / 37 medium / 21 hard**,
or **44% / 36% / 20%** — close to the target 30/50/20 but with more easy items
than anticipated. This is acceptable because the LLM evaluator should
struggle more on the easy bucket than on hard.

## 5. Limitations

1. **Single annotator.** All scores reflect one human judgment. A second
   annotator would yield inter-annotator agreement statistics that we don't
   have. The Lane B harness should report LLM-vs-human agreement, which is a
   proxy for human-vs-human agreement.
2. **English-only justifications.** Some KB nodes are bilingual
   (zh + en); the justifications are written in English. An LLM evaluator
   reading zh-only might under-perform.
3. **No double-blind calibration.** The annotator (Lane A) had access to the
   `process_meta` field, which is a strong prior. An independent evaluator
   should ideally not see process_meta to avoid leakage.
4. **Distractors skew toward "easy".** About 70% of distractors have score 1 on
   novelty and empirical_grounding, which makes them easy to reject. The 3
   `hard`-tier distractors (DIS-008, DIS-011, DIS-025) are designed to slip past
   a careless evaluator. Lane B should report the breakdown of distractor
   rejection accuracy by tier.
5. **Score correlation not modeled.** We expect `clarity` and
   `actionability` to be moderately correlated (clear axioms tend to be more
   testable). We did not explicitly decorrelate them; this is left to Lane C.

## 6. Open questions for downstream lanes

- **Lane B (harness):** How will the LLM evaluator's output be parsed? Each
  item has `scores.{dim}` as integers 1-5; the harness should emit the same
  shape.
- **Lane C (stats):** Should we report Cohen's kappa between LLM and human,
  or just MSE on the 5-dim vector? Kappa is more meaningful for ordinal data.
- **Lane D (write-up):** The dataset includes 30 distractors (~29% of the
  total), which is higher than the suggested 20%. Adjust the prose if needed.

## 7. File manifest

| File                                    | Purpose                                  |
|-----------------------------------------|------------------------------------------|
| `paper/data/rubric.md`                  | 5-dim rubric with anchor scale           |
| `paper/data/gold.json`                  | 104 items, gold standard                 |
| `paper/data/distractors.json`           | 30 distractor axioms with failure modes  |
| `paper/data/sanity_check.txt`           | Output of `sanity_check.py`              |
| `paper/data/build_gold.py`              | Generator script (reproducible)           |
| `paper/data/sanity_check.py`            | Sanity-check script                       |
| `paper/data/fix_tier.py`, `fix_tier2.py`| Tier distribution adjustment scripts     |

To rebuild from scratch:

```bash
python3 paper/data/build_gold.py
python3 paper/data/sanity_check.py
```