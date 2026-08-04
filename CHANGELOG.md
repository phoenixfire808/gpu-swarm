# Changelog

All notable changes to **GPU Pool** (`gpu-swarm`) are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/) for releases.

## [Unreleased]

### Added

- **Host GPU safety ceiling (`host_protect`)** — default ON; offer ≤55% VRAM; pause lease at ≥65% util / low free VRAM; Contribute checkbox + env tunables; light unit tests.
- **Living project memory** — `ROADMAP.md`, this `CHANGELOG.md`, `DESIGN.md` (idea → ship pipeline), Cursor rule to keep docs current.
- Local Pool Endpoint (`local-endpoint` / Connect Start–Stop) — OpenAI-compatible `http://127.0.0.1:8080/v1`.
- Allowlisted job **`llm_chat`** — worker-local Ollama / OpenAI-compatible runtime; lease only when `llm_ready`.
- Contributor **offer ownership** — only the machine owner changes VRAM/CPU/RAM/disk caps; cross-user PATCH 403; scheduler ignores force-cap payloads.
- Friend laptop path — diagnostics collect/submit, portable Python bootstrap, joiner venv isolation.
- Public tunnel helpers (`start-public-access` / cloudflared) + installer preference for public endpoints when present.
- Desktop Home three-mode UX: Contribute / Utilize / Connect.
- Windows EXE packaging path (`build_exe.ps1`, `GPUPool.exe`, Release docs).

### Changed

- Packaging spec keeps fastapi/uvicorn/starlette + `host_protect` / `local_endpoint` for frozen Connect Start/Stop.
- Docs: `LOGIN.md`, `CONNECTING.md`, `LOCAL_MODEL.md`, `FRIEND_LAPTOP.md`, `DOWNLOAD.md` for friend onboarding.

### Fixed

- Friend-install / portable Python path issues and progress-doc typos around joiner venv.
- Distinct `install_joiner_deps` progress bullets; CPython 3.10–3.12 preference for joiners.

## [0.1.0] — 2026-08-04

### Added

- Public GitHub repo + first Windows Release asset docs for `GPUPool.exe`.
- Scheduler, workers, heartbeats (GPU/CPU/RAM/disk), portal, Discord GPU Pool bot.
- Jobs: `probe`, `pytorch_cuda_probe`.
- Tailscale/LAN private pool messaging and Contribute/Utilize portal cards.

[Unreleased]: https://github.com/phoenixfire808/gpu-swarm/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/phoenixfire808/gpu-swarm/releases/tag/v0.1.0
