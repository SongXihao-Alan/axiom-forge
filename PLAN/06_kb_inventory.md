# Knowledge Base Inventory

85 nodes, 8 types, 6 relations, 33 value anchors + update mechanism
Song Xihao (Alan), University of Glasgow  •  2026-06-23


# 1. Overview

The KB is the substrate of the entire project: 85 hand-curated nodes across 8 types, 63 explicit relations, 3 anchor types (empirical / philosophical / community) with full equality between them, and a 6-class value hierarchy (moral / interest / aesthetic / epistemic / practical / philosophical) with 33 subclasses.


# 2. Node Type Distribution

| Type             | Count | Description                                              | Example IDs |
|------------------|-------|----------------------------------------------------------|-------------|
| axiom            | 8     | First-class axioms (Efficiency, Symmetry, Dummy, SC, Thomson's 3, +1 demo) | AX-SC-001, AX-SHAP-EFF, AX-THOMSON-STRPRO |
| assumption       | 2     | Working assumptions (e.g., v(S) = E[f\|X_S])             | AS-SHAP-CHARFN, AS-SHAP-DISTINCT |
| theorem          | 10    | Main theorem + 4 corollaries + 4 propositions + L17 uniqueness | TH-IMP-501, TH-COR-501-1, TH-PROP-621 |
| literature       | 10    | SHAP literature + Thomson 2 books                        | LIT-L17-SHAP, LIT-THOMSON-2023 |
| value_anchor     | 33    | 6 classes × 5-8 subclasses (33 total)                    | VA-MORAL-HELP-WEAK, VA-PHIL-RAWLS |
| diktat           | 14    | Thomson-style tacit evaluation perspectives              | DIKT-PROCACCIA-EXPLAIN-SOLUTIONS |
| scenario         | 6     | Real-world scenarios (medical, voting, etc.)             | SC-ML-ATTR-SHAP, SC-COURT-DIVORCE |
| tradeoff         | 4     | Classical tradeoffs (Hurwicz 1972, etc.)                 | TR-HURWICZ-1972 |


# 3. Relation Types

6 explicit relation types in kb/nodes/relations.json (63 relations total):

| Type               | Count | Semantics |
|--------------------|-------|-----------|
| parent_child       | many  | Derivation: A is a parent/child of B in a derivation lineage |
| generalization     | many  | A is a generalization of B (or vice versa) |
| contradicts        | 1     | A and B are mutually exclusive (used sparingly) |
| same_intuition     | many  | A and B share the same underlying intuition but differ in formalization |
| critiques          | 1     | A is a critical response to B |
| extends            | many  | A extends B (adds assumptions, drops requirements, etc.) |


# 4. The 3 Anchors (Tool Neutrality)

Each axiom node can carry any subset of 3 anchor types:
- empirical: experimental / data-driven / observation-based evidence
- philosophical: tradition / concept-based / normative argument
- community: supporters / consensus / literature-following

Tool neutrality principle: 1 anchor is enough; no priority implied; anchors are not exclusive.


# 5. Value Hierarchy (6 classes, 33 anchors)

| Class        | Subclasses |
|--------------|------------|
| moral        | universal_kindness / universal_prohibition / general / cultural_specific |
| interest     | individual / social / power / equality / longterm |
| aesthetic    | symmetry / simplicity / elegance / unity |
| epistemic    | truth / understanding / explanation / predictive_accuracy |
| practical    | feasibility / implementability / cost / scalability |
| philosophical | autonomy / dignity / rights / fairness / justice |


# 6. KB Update Mechanism (NEW — KB is not static)

The KB is the foundation of axiom discovery. It MUST stay current. The following mechanisms keep it alive:

## Literature Fetcher (automated, monthly cron)

Trigger: literature_fetcher.py runs automatically on a monthly cron, or on-demand via: `axiom-forge kb refresh`

Process:
1. literature_fetcher.py queries arXiv / Semantic Scholar for new papers citing LIT-L17-SHAP, LIT-H20-CAUSAL-SHAP, or LIT-J19-CAUSAL
2. extract_nodes.py generates LIT-* draft nodes for papers with new axioms, theorems, or value anchors
3. PR created in kb/nodes/literature/ for human review
4. Human reviewer approves/rejects within 1 week
5. If approved: node merged to main; if not acted on in 2 weeks: auto-close

## Expert Review Trigger (NEW)

After Lane C converges, the gap_finder.py output is reviewed by the domain expert panel.
Their annotations (what's missing, what's wrong, what's overlooked) are added as DIKT-* nodes and VALUE-* sub-anchors.
This human feedback loop continuously enriches the KB.

## KB Health Metrics (monitored in CI)

- nodes/ must have valid JSON (all fields present)
- No LIT-* node older than 12 months without a 'needs_review' flag
- relations.json must be consistent (no orphan nodes)