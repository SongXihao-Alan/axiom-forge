# dev_notes — developer references (not user-facing)

> These scripts and notes are kept for developer reference. They are **not** part of the user-facing v0.3-alpha skill.

## Contents

- `ALT_SHIP_WITHOUT_REVOKE.sh` — **DO NOT USE**. A backup push script that swaps your real MINIMAX_API_KEY with a dummy before pushing. This was a one-time emergency workaround for when the platform didn't let the author revoke an exposed key. If your key is exposed, **revoke it properly** — see `SHIP_TO_GITHUB.sh` Step 1 in the project root, or `docs/QUICKSTART_API.md` for the proper workflow.

## Active scripts

- `../SHIP_TO_GITHUB.sh` — the only push-to-GitHub script you should use
- `../axiom-forge` — the CLI shim

See `../CONTRIBUTING.md` for the contribution workflow.