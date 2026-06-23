#!/usr/bin/env python3
"""Sanity check for gold.json — prints summary statistics and flags potential errors."""
import json
import statistics
from pathlib import Path
from collections import Counter

DATA = Path("/Users/alan/Downloads/axiom-finder/paper/data")
gold = json.loads((DATA / "gold.json").read_text())
items = gold["items"]

# Header
print("=" * 70)
print("GOLD JSON SANITY CHECK")
print("=" * 70)
print(f"Rubric version : {gold['rubric_version']}")
print(f"Created        : {gold['created']}")
print(f"Total items    : {len(items)}")
print(f"  Real         : {gold['n_real']}")
print(f"  Distractors  : {gold['n_distractor']}")
print(f"  Actual real  : {sum(1 for it in items if not it['is_distractor'])}")
print(f"  Actual distr : {sum(1 for it in items if it['is_distractor'])}")
print()

# Score distribution per dim
dims = ["clarity", "novelty", "internal_consistency", "empirical_grounding", "actionability"]
print("Score distribution per dimension (across ALL items):")
print("-" * 70)
for d in dims:
    vals = [it["scores"][d] for it in items]
    print(f"  {d:25s}  mean={statistics.mean(vals):.2f}  std={statistics.stdev(vals):.2f}  "
          f"min={min(vals)}  max={max(vals)}")
print()

# Real-only vs distractor-only breakdown
print("Score distribution per dimension (REAL items only):")
print("-" * 70)
real = [it for it in items if not it["is_distractor"]]
for d in dims:
    vals = [it["scores"][d] for it in real]
    print(f"  {d:25s}  mean={statistics.mean(vals):.2f}  std={statistics.stdev(vals):.2f}  "
          f"min={min(vals)}  max={max(vals)}")
print()

print("Score distribution per dimension (DISTRACTOR items only):")
print("-" * 70)
distr = [it for it in items if it["is_distractor"]]
for d in dims:
    vals = [it["scores"][d] for it in distr]
    print(f"  {d:25s}  mean={statistics.mean(vals):.2f}  std={statistics.stdev(vals):.2f}  "
          f"min={min(vals)}  max={max(vals)}")
print()

# Flag: items with all 5s or all 1s
print("Items with all-5 or all-1 (potential errors):")
print("-" * 70)
flagged = []
for it in items:
    sv = list(it["scores"].values())
    if all(s == 5 for s in sv):
        flagged.append((it["id"], "all-5", sv))
    elif all(s == 1 for s in sv):
        flagged.append((it["id"], "all-1", sv))
if not flagged:
    print("  (none)")
else:
    for fid, kind, sv in flagged:
        print(f"  [{kind}] {fid}  scores={sv}")
print()

# Tier distribution
print("Tier distribution:")
print("-" * 70)
tier_counts = Counter(it["tier"] for it in items)
for tier in ("easy", "medium", "hard"):
    n = tier_counts.get(tier, 0)
    pct = 100.0 * n / len(items) if items else 0.0
    print(f"  {tier:10s}  n={n:3d}  ({pct:.1f}%)")
print()

# Type breakdown
print("Type breakdown:")
print("-" * 70)
type_counts = Counter(it["type"] for it in items)
for t, n in sorted(type_counts.items(), key=lambda x: -x[1]):
    print(f"  {t:15s}  n={n}")
print()

# Overall distribution
print("Overall score distribution (mean across dims):")
print("-" * 70)
overalls = [it["overall"] for it in items]
print(f"  mean={statistics.mean(overalls):.2f}  std={statistics.stdev(overalls):.2f}  "
      f"min={min(overalls):.2f}  max={max(overalls):.2f}")
print(f"  median={statistics.median(overalls):.2f}")
real_overalls = [it["overall"] for it in real]
distr_overalls = [it["overall"] for it in distr]
print(f"  Real mean overall   = {statistics.mean(real_overalls):.2f}")
print(f"  Distractor mean     = {statistics.mean(distr_overalls):.2f}")
print(f"  Difference          = {statistics.mean(real_overalls) - statistics.mean(distr_overalls):.2f}")
print()

# Save summary
output_lines = []
def p(*args):
    s = " ".join(str(a) for a in args)
    output_lines.append(s)

p("=" * 70)
p("GOLD JSON SANITY CHECK (saved)")
p("=" * 70)
p(f"Rubric version : {gold['rubric_version']}")
p(f"Created        : {gold['created']}")
p(f"Total items    : {len(items)}")
p(f"  Real         : {gold['n_real']}  (actual: {sum(1 for it in items if not it['is_distractor'])})")
p(f"  Distractors  : {gold['n_distractor']}  (actual: {sum(1 for it in items if it['is_distractor'])})")
p()
p("Score distribution per dimension (across ALL items):")
for d in dims:
    vals = [it["scores"][d] for it in items]
    p(f"  {d:25s}  mean={statistics.mean(vals):.2f}  std={statistics.stdev(vals):.2f}  min={min(vals)}  max={max(vals)}")
p()
p("Score distribution per dimension (REAL items only):")
for d in dims:
    vals = [it["scores"][d] for it in real]
    p(f"  {d:25s}  mean={statistics.mean(vals):.2f}  std={statistics.stdev(vals):.2f}  min={min(vals)}  max={max(vals)}")
p()
p("Score distribution per dimension (DISTRACTOR items only):")
for d in dims:
    vals = [it["scores"][d] for it in distr]
    p(f"  {d:25s}  mean={statistics.mean(vals):.2f}  std={statistics.stdev(vals):.2f}  min={min(vals)}  max={max(vals)}")
p()
p("Flagged items (all-5 / all-1):")
if not flagged:
    p("  (none)")
else:
    for fid, kind, sv in flagged:
        p(f"  [{kind}] {fid}  scores={sv}")
p()
p("Tier distribution:")
for tier in ("easy", "medium", "hard"):
    n = tier_counts.get(tier, 0)
    pct = 100.0 * n / len(items) if items else 0.0
    p(f"  {tier:10s}  n={n:3d}  ({pct:.1f}%)")
p()
p("Type breakdown:")
for t, n in sorted(type_counts.items(), key=lambda x: -x[1]):
    p(f"  {t:15s}  n={n}")
p()
p("Overall score distribution (mean across dims):")
p(f"  mean={statistics.mean(overalls):.2f}  std={statistics.stdev(overalls):.2f}  min={min(overalls):.2f}  max={max(overalls):.2f}")
p(f"  median={statistics.median(overalls):.2f}")
p(f"  Real mean overall   = {statistics.mean(real_overalls):.2f}")
p(f"  Distractor mean     = {statistics.mean(distr_overalls):.2f}")
p(f"  Difference          = {statistics.mean(real_overalls) - statistics.mean(distr_overalls):.2f}")
p()

(DATA / "sanity_check.txt").write_text("\n".join(output_lines))
print(f"Saved summary to {DATA / 'sanity_check.txt'}")