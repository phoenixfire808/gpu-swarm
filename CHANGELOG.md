# Changelog

All notable changes to **GPU Pool** (`gpu-swarm`) are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/) for releases.

## [Unreleased]

### Fixed

- **Console window spam (Windows)** — root cause: subprocess spawns (`powershell`, `cmd`, `python`) without `CREATE_NO_WINDOW`, plus Connect tab polling `workspace_status()` every 4s (Hermes `agent-vm` each tick). Added `gpu_swarm/win_subprocess.py`; applied to worker/local-endpoint/pip/prereqs/agent-vm paths; stopped auto workspace refresh on poll; host `start-*.cmd` now use `scripts/run-hidden.cmd` (pythonw + hidden window).
- **Duplicate stack processes** — trimmed extra nohup-wrapped bot/portal instances when prior run-stack left duplicates.

### Changed

- **Grandma-friendly onboarding** — Welcome wizard, `START_HERE.md`, portal hub hero/login/home copy: numbered “just do this” steps, plain-English tool explanations (Tailscale = private network), big buttons only; Invite / Share / Use / Grow path preserved.

### Added

- **`START_HERE.md`** — 5-minute friend path + paste-ready Discord growth blurb.
- **Portal newcomer UX** — clearer hero/login; three huge post-login actions (Share / Use / Invite); How it works (3 steps); Chat/Suggest demoted to secondary nav; mobile-friendly action buttons.
- **Share / Invite others** — `gpu_swarm/share_invite.py`; portal Hub **Invite others** view + desktop **4 · Invite others** with one-click copy (friend message, full blurb, portal URL, invite code, GitHub download). Primary actions: Join / Share my PC / Use the pool / Invite others.
- **Automated friend prereqs** — `scripts/install-prereqs.ps1` (+ `.cmd`): detect-or-install **Tailscale**, **VirtualBox** (+ Extension Pack best-effort), **Vagrant**; verbose step labels; skips if present; optional `GPU_SWARM_TAILSCALE_AUTHKEY` / `TS_AUTHKEY` (never committed); UAC + Tailscale login remain one clear click.
- **Wizard step Network & Workspace** — Detect / Install & connect / Tailscale-only; wired via `app_backend.install_prereqs`.
- **`SHARED_AGENT_DEV.md`** — ready-to-go shared agent-development space (hub → Workspace → harness endpoint).
- **Verbose install / bootstrap progress** — step labels (“Downloading Python runtime…”, “Installing dependencies (1/5)…”), download percent, pip package streaming, PowerShell `Write-Progress`, wizard progress bar + visible logs, first-run log at `%LOCALAPPDATA%\GPUPool\logs\first-run-bootstrap.log`.
- **Plain-language friend UX** — Welcome/Home copy for Join / Share my PC / Use the pool / Invite others; SmartScreen + invite + rotating public URL; honest no-NVIDIA / host_protect / no passthrough notes in `DOWNLOAD.md` / `LOGIN.md` / `NO_GPU_LAPTOP.md` / `RELEASE.md`.
- Draft **`RELEASE_NOTES_v0.1.1.md`** + publish commands (EXE rebuild still required to ship asset).
- **All-in-One Network Hub portal** — brand-first peer-mesh `/portal` (`portal_hub.html`); live workers from `/status` (no mocks); Contribute / Utilize / Connect / Workspace / Diagnostics in one place.
- **Pool chat** — authenticated shared room; SQLite in `portal.db`; 2.5s poll; empty state when quiet (`GET/POST /api/chat`, `/api/presence`).
- **Suggestions & review inbox** — submit suggestion/bug/review; host marks open/read/done (`/api/suggestions`).
- Workers advertise **`llm_ready`** on register/heartbeat for hub display.
- **Workspace VM integration (MVP)** — desktop Home/Connect → Hermes `agent-vm` with Contribute/`host_protect` CPU+RAM caps; `gpu_swarm/agent_vm_bridge.py`; honest no-NVIDIA-passthrough docs (`ADVANCED_VM.md`); portal Connect note.
- **Host GPU safety ceiling (`host_protect`)** — default ON; offer ≤55% VRAM; pause lease at ≥65% util / low free VRAM; Contribute checkbox + env tunables; light unit tests.
- **Living project memory** — `ROADMAP.md`, this `CHANGELOG.md`, `DESIGN.md` (idea → ship pipeline), Cursor rule to keep docs current.
- Local Pool Endpoint (`local-endpoint` / Connect Start–Stop) — OpenAI-compatible `http://127.0.0.1:8080/v1`.
- Allowlisted job **`llm_chat`** — worker-local Ollama / OpenAI-compatible runtime; lease only when `llm_ready`.
- Contributor **offer ownership** — only the machine owner changes VRAM/CPU/RAM/disk caps; cross-user PATCH 403; scheduler ignores force-cap payloads.
- Friend laptop path — diagnostics collect/submit, portable Python bootstrap, joiner venv isolation.
- Public tunnel helpers (`start-public-access` / cloudflared) + installer preference for public endpoints when present.
- Desktop Home three-mode UX: Contribute / Utilize / Connect.
- Windows EXE packaging path (`build_exe.ps1`, `GPUPool.exe`, Release docs).

### Fixed

- **Desktop app Tk threading** — worker threads no longer call `self.after()` directly (fixes `RuntimeError: main thread is not in main loop` on Workspace refresh and all background UI updates). Uses `GpuPoolApp.post_ui()` + main-loop queue drain.

### Changed

- Welcome / invite blurbs emphasize automatic install + **Invite friends** growth (“add your machine, grow the pool”).
- Packaging spec bundles `scripts/install-prereqs.*`, joiner/check prereq scripts, and `SHARED_AGENT_DEV.md` for next EXE.
- `check_prereqs.ps1` reports Tailscale / VirtualBox / Vagrant (optional for share path).
- Docs: `START_HERE.md`, `LOGIN.md`, `DOWNLOAD.md`, `NO_GPU_LAPTOP.md` (was `FRIEND_LAPTOP.md`), `ROADMAP.md` for automated join + shared agent-dev; v0.1.1 EXE links.
- **Personal-name scrub** — friend-facing copy uses host / friend / pool member / pool admin; removed sample friend display names and personal laptop anecdotes.
- `install_joiner_deps.ps1` / `build_exe.ps1` print numbered human steps instead of quiet pip.

### Fixed

- Friend-install / portable Python path issues and progress-doc typos around joiner venv.
- Distinct `install_joiner_deps` progress bullets; CPython 3.10–3.12 preference for joiners.

## [0.1.0] — 2026-08-04

### Added

- Public GitHub repo + first Windows Release asset docs for `GPUPool.exe`.
- Scheduler, workers, heartbeats (GPU/CPU/RAM/disk), portal, Discord GPU Pool bot.
- Jobs: `probe`, `pytorch_cuda_probe`.
- Tailscale/LAN private pool messaging and Contribute/Utilize portal cards.

## [0.1.1] — 2026-08-04

### Added
- Windows EXE release with Network Hub, Invite friends, host_protect, Workspace bridge, verbose install, Tk UI fix.
- `START_HERE.md` + punchy Discord growth blurbs; portal newcomer UX (three huge actions).

[Unreleased]: https://github.com/phoenixfire808/gpu-swarm/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/phoenixfire808/gpu-swarm/releases/tag/v0.1.1
[0.1.0]: https://github.com/phoenixfire808/gpu-swarm/releases/tag/v0.1.0
