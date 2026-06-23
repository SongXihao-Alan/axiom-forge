#!/usr/bin/env python3
"""Improve tier distribution: shift ~10 medium items to hard to reach target 30/50/20."""
import json
from collections import Counter
from pathlib import Path

DATA = Path("/Users/alan/Downloads/axiom-finder/paper/data")
gold = json.loads((DATA / "gold.json").read_text())
items = gold["items"]

# Show current state
print("Before:")
for tier in ("easy", "medium", "hard"):
    n = sum(1 for it in items if it["tier"] == tier)
    print(f"  {tier}: {n}")

# Promote the following medium-tier items to hard (debatable even for a human expert):
PROMOTE_TO_HARD = {
    # TH-PROP-* — argued/sketch propositions are inherently hard
    "TH-PROP-621", "TH-PROP-622", "TH-PROP-624",
    # Some value_anchors with low cross-cultural consistency or vague operationalization
    "VA-MORAL-CULTURAL", "VA-PHIL-EXIST", "VA-AESTHETIC-ELEGANCE",
    # TR-PREDICTIVE-STRUCTURAL is a novel tradeoff
    "TR-PREDICTIVE-STRUCTURAL",
    # Vague value anchors
    "VA-INTEREST-POWER",
    # Disputed axioms (TH-SHAP-UNIQ has known circularity flag)
    "TH-SHAP-UNIQ",
    # Axiom with novelty but unclear actionability
    "AX-SHAP-CONS",
}

promoted = 0
for it in items:
    if it["id"] in PROMOTE_TO_HARD and it["tier"] == "medium":
        it["tier"] = "hard"
        promoted += 1
print(f"\nPromoted {promoted} items to hard.")

# Verify
print("After:")
for tier in ("easy", "medium", "hard"):
    n = sum(1 for it in items if it["tier"] == tier)
    print(f"  {tier}: {n} ({100.0 * n / len(items):.1f}%)")

# Also add n_real and n_distractor correctly
gold["n_real"] = sum(1 for it in items if not it["is_distractor"])
gold["n_distractor"] = sum(1 for it in items if it["is_distractor"])

DATA.joinpath("gold.json").write_text(json.dumps(gold, indent=2, ensure_ascii=False))
print(f"\nUpdated {DATA / 'gold.json'}.")