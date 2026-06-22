# Deploy directory

This directory holds deployment artifacts for hosting the Axiom Forge Web API.

## Contents

- `axiomfinder.pem` — Tencent Cloud SSH key (deployment-only; NEVER committed to git, see root `.gitignore`)
- `.gitkeep` — keeps the directory in git after `.pem` is excluded

## Setup

1. Verify your local SSH config points at this key (or symlink to `~/.ssh/`):
   ```bash
   chmod 600 deploy/axiomfinder.pem
   ssh-add deploy/axiomfinder.pem    # optional, if using ssh-agent
   ```

2. To deploy, follow the steps in `docs/QUICKSTART_API.md` (Step 7 onward).

## Security

- The `.pem` file is **excluded by `.gitignore`** (`/deploy/*.pem`). Confirm with:
  ```bash
  git check-ignore -v deploy/axiomfinder.pem
  # Should print: .gitignore:<line>:/deploy/*.pem deploy/axiomfinder.pem
  ```
- If you accidentally `git add` this file, **rotate the Tencent Cloud key immediately** — it may already be exposed in any earlier push you made.
- Never share this key in chat, screenshots, or issues.