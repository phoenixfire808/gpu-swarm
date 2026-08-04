# CURRENT_PROGRESS — GPU Pool (gpu-swarm)

Living scorecard for Drew private Discord GPU/CPU co-op.  
**Updated:** 2026-08-04 ~12:20 CDT · Friend diagnostics + portable Python (3.10-3.12) + laptop path.

**GitHub:** https://github.com/phoenixfire808/gpu-swarm (public)

| Service | Local | Tailscale |
|---------|-------|-----------|
| Scheduler | `http://127.0.0.1:8766` | `http://100.85.165.84:8766` |
| Portal | `http://127.0.0.1:8767/portal` | `http://100.85.165.84:8767/portal` |
| Robinhood CC | `127.0.0.1:8765` | **do not steal** |

**Discord:** App **GPU Pool** · Primary guild **Glitch Factor** · Invite code `glitch-factor`  
**v1 jobs only:** `probe`, `pytorch_cuda_probe` · Auth MVP: invite/password (OAuth later)  
**Rules:** No Docker · No mock GPU/host data · Never commit `.env` / token paste files  
**Network model:** Private Tailscale/LAN (+ optional public tunnel when Drew runs `start-public-access.cmd`)

---

## Friend laptop / no-NVIDIA path (2026-08-04)

- [x] Portal black screen: removed Google Fonts @import; system fonts; laptop banner
- [x] CPU-only worker: gpu_available=false without nvidia-smi
- [x] Utilize-without-GPU probe path; scheduler URL validation; public_endpoints auto-detect
- [x] Docs: FRIEND_LAPTOP.md

---

## Live scorecard (2026-08-04 ~12:15 CDT)

| # | Check | Result |
|---|--------|--------|
| 1 | Scheduler Tailscale `/status` | **PASS** (prior probe) @ `http://100.85.165.84:8766/status` |
| 2 | Portal `/api/diagnostics` | **NEW** — POST upload + GET list (invite/session); store `data/diagnostics/` |
| 3 | Portable Python dry-run | **VERIFY this commit** — `ensure_portable_python(dry_run=True)` |
| 4 | Purpose-failed error log | **VERIFY this commit** — `write_error_log` → `%LOCALAPPDATA%\GPUPool\logs\error-*.log` |
| 5 | GPUPool.exe Release | **NEEDS REBUILD** — must include `portable_python` + `diagnostics` |

**Demo verdict:** Friends can bootstrap isolated Python + submit redacted logs when join fails. Packaging Worker must rebuild EXE.

---

## Done (with dates)

### Friend laptop / no-NVIDIA path (2026-08-04)
- [x] Portal black screen: removed Google Fonts `@import` (root cause on locked-down laptops); system fonts; laptop banner
- [x] Portal restarted on `0.0.0.0:8767`; Tailscale + localhost HTML 200; `/pool-api` proxy OK
- [x] CPU-only worker: `gpu_available=false`, no hard fail without nvidia-smi; check_prereqs NVIDIA optional
- [x] Utilize-without-GPU: probe from “no gpu” client → Drew workers completes
- [x] Scheduler URL validation: “Incorrect Scheduler URL Environment Variable” for bare IP; accepts `:8766` + public `/pool-api`
- [x] Installer auto-detect: public_endpoints.json → Tailscale → localhost; wizard Utilize-first when no NVIDIA
- [x] Docs: `FRIEND_LAPTOP.md`

### Install harden — multi-machine (2026-08-04)
- [x] Pin requirements.txt / requirements-app.txt for Win CPython 3.10-3.12
- [x] Add requirements-joiner.txt (no torch) + requirements-cuda.txt (optional cu128)
- [x] scripts/install_joiner_deps.ps1 -> %LOCALAPPDATA%\GPUPool\venv (coord w/ diagnostics portable Python)
- [x] Prefer 3.12 > 3.11 > 3.10; do not auto-select 3.13
- [x] Document supported matrix in DOWNLOAD.md


### Friend diagnostics + portable Python (2026-08-04)
- [x] `gpu_swarm/diagnostics.py` — OS/python/pip freeze/nvidia-smi/scheduler test/traceback/wizard step; redact secrets
- [x] Writes `%LOCALAPPDATA%\GPUPool\logs\error-*.log` (+ json sibling)
- [x] Wizard UI: **Copy log** + **Submit diagnostics** (Python & Deps + Join); clipboard fallback if portal down
- [x] Portal `POST /api/diagnostics` (invite or session) → `data/diagnostics/` size-capped; `GET` list for logged-in admin
- [x] `gpu_swarm/portable_python.py` — NuGet CPython 3.12 → `%LOCALAPPDATA%\GPUPool\python\` + venv at `\venv`
- [x] Wizard **Bootstrap portable Python**; EXE first-run background bootstrap when no usable Python
- [x] pip installs prefer isolated venv (never fight global site-packages)
- [x] scripts/install_joiner_deps.ps1 -> %LOCALAPPDATA%\GPUPool\venv (coord w/ diagnostics portable Python)
- [x] Docs: DOWNLOAD / RELEASE / CURRENT_PROGRESS / TODO; `gpu_pool.spec` hiddenimports + req datas

### Tailscale/LAN UX + Desktop three-mode (2026-08-04)
- [x] Private-network messaging, Utilize/Connect first-class, portal friends cards
- [x] Public repo + CONNECTING / DOWNLOAD / member quickstart

---

## In progress

- [ ] Packaging Worker: rebuild + publish Windows EXE (must ship portable_python + diagnostics)
- [ ] Confirm Discord `/pool` smoke in Glitch Factor (manual; optional)
- [ ] Keep scorecard/TODO in sync

---

## Next (prioritized)

1. **Packaging Worker** — rebuild EXE from this commit; publish Release.
2. **Member onboarding** — post quickstart + “if join fails → Submit diagnostics”.
3. Stream smoke: Home → Utilize probe → friend join with portable Python path.
4. Whisper / bounded LLM (allowlisted).
5. Portal Discord OAuth (later).

### Next 5 Drew should care about right now

1. Packaging Worker rebuild of GPUPool.exe (diagnostics + portable Python).
2. Tell friends: on failure use **Submit diagnostics** / **Copy log**.
3. Live smoke portal `POST /api/diagnostics` after portal restart.
4. Plan Whisper/LLM runners.
5. Keep `.env` / tokens local — never commit.

---

## Blocked

| Blocker | Why | Unblock |
|---------|-----|---------|
| **Whisper / LLM jobs** | No runners in `jobs.py` | Design narrow contract → runners + UI |
| **Portal OAuth** | MVP invite/password only | Implement when auth story ready |
| **EXE asset** | Needs packaging rebuild | Worker publishes Release |

---

## How friends report errors

1. Wizard → **Copy log** or **Submit diagnostics**
2. Submit → portal `/api/diagnostics` (Drew reads `data/diagnostics/`)
3. Fallback: clipboard paste in Discord; files in `%LOCALAPPDATA%\GPUPool\logs\`

## How Python is isolated per machine

| Path | Role |
|------|------|
| `%LOCALAPPDATA%\GPUPool\python\` | Portable CPython 3.12 (NuGet) when system Python is bad |
| `%LOCALAPPDATA%\GPUPool\venv\` | Isolated deps (`requirements-joiner.txt`) — no global site-packages |
| GPUPool.exe | Bundled UI/worker; pip/torch uses portable/venv |

---

## How to relaunch host services

```bat
cd C:\Users\Drew\Projects\gpu-swarm
start-scheduler-lan.cmd
start-portal.cmd
start-bot.cmd
start-gpu-pool-app.cmd
```

Coding smoke:

```bat
set GPU_SWARM_SCHEDULER_URL=http://127.0.0.1:8766
python -m gpu_swarm utilize status
python -m gpu_swarm utilize probe --wait
```

Diagnostics / portable dry-run:

```bat
python -c "from gpu_swarm.portable_python import ensure_portable_python; print(ensure_portable_python(dry_run=True))"
python -c "from gpu_swarm.diagnostics import write_error_log; print(write_error_log(wizard_step='Join', reason='test-fail', include_traceback='purpose-failed test'))"
```

---

## Do not

- Commit `.env`, `DISCORD_BOT_TOKEN_PASTE.txt`, tokens, or `data/`
- Use Docker for this stack
- Steal port `8765` (Robinhood)
- Wipe Hermes durable memory / reuse Jarvis bot token
- Invent green checks — re-probe `/status` + portal when updating this file
