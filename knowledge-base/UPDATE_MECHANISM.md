# KB Update Mechanism

## Overview
The KB is the foundation of axiom discovery. This document describes how it stays current.

## Literature Fetcher (Automated, Monthly Cron)

### Trigger
- Automated: Monthly cron job
- Manual: `axiom-forge kb refresh`

### Process
1. Query arXiv / Semantic Scholar for papers citing LIT-L17-SHAP, LIT-H20-CAUSAL-SHAP, LIT-J19-CAUSAL
2. Generate LIT-* draft nodes for papers with new axioms or theorems
3. Create PR in `kb/nodes/literature/` for human review
4. Human reviewer approves/rejects within 1 week
5. If not acted on in 2 weeks: auto-close PR

## Expert Review Trigger
After Lane C converges, gap_finder.py output is reviewed by the domain expert panel.
Annotations become DIKT-* nodes and VALUE-* sub-anchors.

## KB Health Metrics (CI-monitored)
- All nodes/ JSON must be valid
- No LIT-* node older than 12 months without `needs_review: true`
- relations.json must have no orphan nodes

## Literature Fetcher CLI
axiom-forge kb refresh [--limit N] [--source arxiv|semantic]
