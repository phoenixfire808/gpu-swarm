# CURRENT_PROGRESS — GPU Pool (gpu-swarm)

Living scorecard for Drew private Discord GPU/CPU co-op.  
**Updated:** 2026-08-04 ~12:20 CDT · Local model endpoint + Connect Start/Stop UI.

**GitHub:** https://github.com/phoenixfire808/gpu-swarm (public)

| Service | Local | Public (live now) | Tailscale (optional) |
|---------|-------|-------------------|----------------------|
| Portal | `http://127.0.0.1:8767/portal` | `https://rational-delicious-bars-examination.trycloudflare.com/portal` | `http://100.85.165.84:8767/portal` |
| Scheduler / pool API | `http://127.0.0.1:8766` | `https://rational-delicious-bars-examination.trycloudflare.com/pool-api` | `http://100.85.165.84:8766` |
| Robinhood CC | `127.0.0.1:8765` | — | **do not steal** |

**DM aariff01 NOW:**  
`https://rational-delicious-bars-examination.trycloudflare.com/portal`  
Invite: `glitch-factor` · cloudflared pid `41552` · files in `data/public_endpoints.*` (gitignored)

**Discord:** App **GPU Pool** · Primary guild **Glitch Factor** · Invite code `glitch-factor`  
**v1 jobs only:** `probe`, `pytorch_cuda_probe` · Auth MVP: invite/password (kept on for public)  
**Rules:** No Docker · No mock GPU/host data · Never commit `.env` / token paste files  
**Network model:** Public Cloudflare quick tunnel ON; Tailscale optional

---

## Friend laptop / no-NVIDIA path (2026-08-04)

- [x] Portal black screen: removed Google Fonts @import; system fonts; laptop banner
- [x] CPU-only worker: gpu_available=false without nvidia-smi
- [x] Utilize-without-GPU probe path; scheduler URL validation; public_endpoints auto-detect
- [x] Docs: FRIEND_LAPTOP.md / DOWNLOAD.md / DISCORD_MEMBER_QUICKSTART (current public URL + rotate note)
- [x] **Public access LIVE** — cloudflared quick tunnel; portal+`/pool-api` HTTPS 200
- [x] **Fix:** `endpoints.load_public_endpoints` maps tunnel keys (`pool_api_public_url` / `portal_path`) so installer prefers public `/pool-api` when file present (verified probe source=`public_endpoints.json`)

---

## Live scorecard (2026-08-04 ~12:15 CDT)

| # | Check | Result |
|---|--------|--------|
| 1 | Public portal HTTPS `/portal` | **PASS 200** — `https://rational-delicious-bars-examination.trycloudflare.com/portal` |
| 2 | Public `/pool-api/status` | **PASS 200** — proxies scheduler; allowlisted jobs only |
| 3 | Invite auth still on | **PASS** — `auth: pool_password_or_invite` on public `/health` |
| 4 | `data/public_endpoints.json` | **PASS** — written; share.txt ready to DM |
| 5 | GPUPool.exe Release | **PASS** — [v0.1.0](https://github.com/phoenixfire808/gpu-swarm/releases/tag/v0.1.0) · [GPUPool.exe](https://github.com/phoenixfire808/gpu-swarm/releases/download/v0.1.0/GPUPool.exe) (~29 MB); launch smoke OK (wizard title) |

**Demo verdict:** aariff01 can open the public portal **without Tailscale**. Friends can download GPUPool.exe. Invite `glitch-factor` required.

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


### Windows EXE Release v0.1.0 (2026-08-04)
- [x] Built from master `469c30a` via `build_exe.ps1` → `dist/GPUPool.exe` (~29 MB onefile)
- [x] Launch smoke: wizard window **GPU Pool — Contribute · Utilize · Connect**
- [x] GitHub Release https://github.com/phoenixfire808/gpu-swarm/releases/tag/v0.1.0
- [x] Asset https://github.com/phoenixfire808/gpu-swarm/releases/download/v0.1.0/GPUPool.exe
- [x] DOWNLOAD.md / README / DISCORD_MEMBER_QUICKSTART real URLs (no placeholder)

### Friend diagnostics + portable Python (2026-08-04)
- [x] `gpu_swarm/diagnostics.py` — OS/python/pip freeze/nvidia-smi/scheduler test/traceback/wizard step; redact secrets
- [x] Writes `%LOCALAPPDATA%\GPUPool\logs\error-*.log` (+ json sibling)
- [x] Wizard UI: **Copy log** + **Submit diagnostics** (Python & Deps + Join); clipboard fallback if portal down
- [x] Portal `POST /api/diagnostics` (invite or session) → `data/diagnostics/` size-capped; `GET` list for logged-in admin
- [x] `gpu_swarm/portable_python.py` — NuGet CPython 3.12 → `%LOCALAPPDATA%\GPUPool\python\` + venv at `\venv`
- [x] Wizard **Bootstrap portable Python**; EXE first-run background bootstrap when no usable Python
- [x] pip installs prefer isolated venv (never fight global site-packages)
- [x] `scripts/install_joiner_deps.ps1` restored → GPUPool venv + `requirements-joiner.txt`
- [x] Docs: DOWNLOAD / RELEASE / CURRENT_PROGRESS / TODO; `gpu_pool.spec` hiddenimports + req datas

### Tailscale/LAN UX + Desktop three-mode (2026-08-04)
- [x] Private-network messaging, Utilize/Connect first-class, portal friends cards
- [x] Public repo + CONNECTING / DOWNLOAD / member quickstart

### Local model endpoint (2026-08-04)
- [x] `gpu_swarm/local_endpoint.py` — localhost OpenAI-compatible API → allowlisted `llm_chat`
- [x] CLI `python -m gpu_swarm local-endpoint` + `start-local-endpoint.cmd`
- [x] Desktop **Connect**: Start/Stop, status, copy OpenAI base URL, link `LOCAL_MODEL.md`
- [x] Honest copy: local AI API for apps — **not** a physical GPU device
- [x] Port pick: prefer 8080, fall back to 11434 when busy (Windows connect+bind check)
- [x] Verified: start → `/health` + `/v1/models` → stop (bound `127.0.0.1:11434` while :8080 occupied)

---

## In progress

- [x] Packaging Worker: published **v0.1.0** GPUPool.exe (portable_python + diagnostics + Home UX)
- [ ] Rebuild EXE so Connect local-endpoint UI ships in GPUPool.exe
- [ ] Confirm Discord `/pool` smoke in Glitch Factor (manual; optional)
- [ ] Post member quickstart + EXE download link in Glitch Factor

---

## Next (prioritized)

1. **Member onboarding** — post EXE link + “if join fails → Submit diagnostics”.
2. Stream smoke: friend downloads EXE → wizard → Join / Utilize; Connect → Start local endpoint.
3. Contributor workers with Ollama for real `llm_chat` completions.
4. Whisper / more bounded LLM (allowlisted).
5. Portal Discord OAuth (later).

### Next 5 Drew should care about right now

1. DM friends: https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe
2. Tell friends: Connect → **Start local endpoint** → paste `OPENAI_BASE_URL` (see LOCAL_MODEL.md).
3. Run Ollama (or compatible) on a GPU worker so `llm_chat` jobs complete.
4. Rebuild/publish EXE after this commit for Connect UI.
5. Keep `.env` / tokens local — never commit.

---

## Blocked

| Blocker | Why | Unblock |
|---------|-----|---------|
| **LLM chat quality** | Needs Ollama (or compat) on at least one worker | Install runtime on Drew-Home / friend GPU |
| **Whisper** | No runners yet | Narrow contract → runners + UI |
| **Portal OAuth** | MVP invite/password only | Implement when auth story ready |
| **EXE includes Connect local-endpoint** | v0.1.0 predates this UI | Packaging rebuild |

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
