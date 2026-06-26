# Git Workflow

Branching, commits, PRs, releases + iteration branches
Song Xihao (Alan), University of Glasgow  •  2026-06-23


# 1. Branching Model

Simplified GitHub Flow:
- main is the source of truth. It is always green and reflects the latest published version.
- Create a feature branch from main: `git checkout -b feat/lane-B-scale`
- Make commits with Conventional Commits messages
- Push the branch: `git push -u origin feat/lane-B-scale`
- Open a PR to main. Fill in the PR template. Wait for CI to pass.
- Self-review the diff. Squash-merge to main.
- Delete the feature branch.

For iteration PRs (lane-B-v2, lane-C-v2):
- Base branch is main (not feat/lane-B-scale)
- Must include link to lane_c_feedback.json triggering the revision
- PR description must state which dimensions improved and how


# 2. Branch Naming (updated)

| Branch                | Purpose |
|-----------------------|---------|
| feat/lane-B-scale     | Lane B baseline (v1 prompt) |
| feat/lane-B-scale-v2  | Lane B prompt refinement iteration 2 |
| feat/lane-B-scale-v3  | Lane B prompt refinement iteration 3 (last resort) |
| feat/lane-C-stats     | Lane C baseline |
| feat/lane-C-stats-v2  | Lane C re-run after prompt v2 |
| feat/expert-panel     | Expert validation panel review + paper update |
| feat/discovery-path   | gap_finder → candidate axiom generation |
| feat/lean-ci          | Add Lean 4 build to GitHub Actions |
| fix/<name>            | bug fix branches |


# 3. PR Template

```
## Type
- [ ] Bug fix
- [ ] New feature
- [ ] KB node contribution
- [ ] Reproduction result
- [ ] Documentation
- [ ] Refactor

## Description
<what changed + why>

## Testing
- [ ] Ran ./axiom-forge stats and KB unchanged (85 nodes, 63 relations, 8 types)
- [ ] Ran new commands / endpoints (if any)
- [ ] Ran M3 integration (if any)

## Lane-specific checklist (if applicable)
- [ ] Lane A: gold.json unchanged or annotations extended
- [ ] Lane B: predictions regenerated; report regenerated; lane_c_feedback.json updated
- [ ] Lane C: stats regenerated; convergence checked
- [ ] Lane D: paper draft updated
- [ ] Expert panel: scores added to Appendix A.3 (if applicable)

## Tool neutrality
- [ ] 3 anchors (empirical / philosophical / community) are equal
- [ ] No priority implied
- [ ] Process is reproducible
```


# 4. Merge Strategy

- Default: Squash and merge (one commit per PR).
- Big features with multiple logical commits: Rebase and merge (preserves history).
- Hot fixes: Squash and merge.
- Never force-push to main.
- Never commit directly to main; always go through a PR.


# 5. Tagging

Semantic versioning: MAJOR.MINOR.PATCH

| Tag                    | When                              | Example |
|------------------------|-----------------------------------|---------|
| v0.MINOR.PATCH-alpha   | Pre-release, may break without notice | v0.3-alpha (current) |
| v0.MINOR.PATCH-beta    | Feature-complete, testing         | v0.4-beta |
| v0.MINOR.PATCH         | Stable release                    | v0.4 |
| v1.0.0                 | First public stable release       | TBD |