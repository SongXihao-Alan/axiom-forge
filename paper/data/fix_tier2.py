#!/usr/bin/env python3
"""Promote more medium items to hard — pick ones with score spread >= 2 across dims."""
import json
from pathlib import Path

DATA = Path("/Users/alan/Downloads/axiom-finder/paper/data")
gold = json.loads((DATA / "gold.json").read_text())
items = gold["items"]

# Find medium items with score spread (max - min) >= 3 — these are legitimately hard
print("Medium items with large score spread (>= 3 across dims):")
candidates = []
for it in items:
    if it["tier"] == "medium":
        sv = list(it["scores"].values())
        spread = max(sv) - min(sv)
        if spread >= 3:
            candidates.append((it["id"], it["type"], spread, it["scores"]))
            print(f"  {it['id']:30s} ({it['type']:15s}) spread={spread} scores={it['scores']}")

# Promote up to 8 more to reach ~20% hard
n_current_hard = sum(1 for it in items if it["tier"] == "hard")
target_hard = round(0.20 * len(items))
to_promote = max(0, target_hard - n_current_hard)
print(f"\nCurrently hard: {n_current_hard}; target: {target_hard}; need to promote: {to_promote}")

promoted = 0
for cid, ctype, spread, scores in candidates:
    if promoted >= to_promote:
        break
    for it in items:
        if it["id"] == cid and it["tier"] == "medium":
            it["tier"] = "hard"
            promoted += 1
            print(f"  Promoted: {cid}")
            break

# Final counts
from collections import Counter
print("\nAfter promotion:")
tier_counts = Counter(it["tier"] for it in items)
for tier in ("easy", "medium", "hard"):
    n = tier_counts.get(tier, 0)
    pct = 100.0 * n / len(items)
    print(f"  {tier}: {n} ({pct:.1f}%)")

gold["n_real"] = sum(1 for it in items if not it["is_distractor"])
gold["n_distractor"] = sum(1 for it in items if it["is_distractor"])
DATA.joinpath("gold.json").write_text(json.dumps(gold, indent=2, ensure_ascii=False))
print(f"\nUpdated {DATA / 'gold.json'}.")