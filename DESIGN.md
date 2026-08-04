# Design pipeline — GPU Pool

Short practical loop. Full vision: [`VISION.md`](VISION.md). Status: [`CURRENT_PROGRESS.md`](CURRENT_PROGRESS.md).

## Flow

```
idea → design note → build → light verify → ship → docs
```

| Stage | What to do | Where it lands |
|-------|------------|----------------|
| **Idea** | One sentence: who benefits + what breaks if wrong | Chat / Discord; optional bullet in `ROADMAP.md` |
| **Design** | Constraints, defaults, non-goals (esp. desktop safety, no Docker, no fake GPU passthrough) | Thin note here or in PR body; link ADVANCED_VM when VMs involved |
| **Build** | Scaffold off existing modules (`worker`, `portal`, `app_backend`, joiner settings) | Code + light tests only |
| **Verify** | Smoke the happy path; **no** heavy CUDA / PyInstaller stress on Drew’s PC | Scorecard row in `CURRENT_PROGRESS.md` |
| **Ship** | Commit + push (never `.env` / tokens / `data/public_endpoints*`) | GitHub `master` + optional Release |
| **Docs** | Update TODO · ROADMAP · CHANGELOG · CURRENT_PROGRESS same turn | Living docs |

## Defaults that stick

- **Host protect ON** — pool must not freeze the desktop.
- **Hermes owns agent-vms** — GPU Pool may *detect* / link workspaces; it does not become the VM control plane.
- **Allowlisted jobs only** — no arbitrary shell from Discord.
- **Honest capacity** — RAM/disk are scheduling ads until a real shared fabric exists.

## When to write more design

Write a short subsection (or a `docs/` note) only if the change spans multiple services or changes the trust model. Prefer updating ROADMAP + CHANGELOG over new long docs.
