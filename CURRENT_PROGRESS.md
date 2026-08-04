# CURRENT_PROGRESS — GPU Pool (gpu-swarm)

Living scorecard for Drew’s private Discord GPU/CPU co-op.  
**Updated:** 2026-08-04 ~11:57 CDT · Portal Home = Contribute / Utilize / Connect polish.

**GitHub:** https://github.com/phoenixfire808/gpu-swarm (public)

| Service | Local | Tailscale |
|---------|-------|-----------|
| Scheduler | `http://127.0.0.1:8766` | `http://100.85.165.84:8766` |
| Portal | `http://127.0.0.1:8767/portal` | `http://100.85.165.84:8767/portal` |
| Robinhood CC | `127.0.0.1:8765` | **do not steal** |

**Discord:** App **GPU Pool** · Primary guild **Glitch Factor** · Invite code `glitch-factor`  
**v1 jobs only:** `probe`, `pytorch_cuda_probe` · Auth MVP: invite/password (OAuth later)  
**Rules:** No Docker · No mock GPU/host data · Never commit `.env` / token paste files

---

## Portal Home polish (2026-08-04)

- [x] After login: big **Contribute** · **Utilize** · **Connect** chooser cards on Home
- [x] Connect panel: Tailscale + local scheduler/portal URLs, Discord cmds, CLI/SDK/HTTP snippets (no secrets)
- [x] `/api/config` exposes `connect` block + invite hint `glitch-factor`
- [x] `CONNECTING.md` notes portal Home mirrors the three paths
- [x] Tailscale portal kept on `0.0.0.0:8767`; bot/scheduler not touched for this polish

---

## Live scorecard (fresh LIVE probe 2026-08-04 ~11:50 CDT)

| # | Check | Result |
|---|--------|--------|
| 1 | Scheduler `:8766` `/status` + workers + resource fields | **PASS** — `workers_online=1`, CPU/RAM/disk/VRAM fields present; `/v1/pool/status` mirrors |
| 2 | Worker online with real GPUs | **PASS** — `Drew-Home` online; RTX 5060 Ti + 2070 SUPER via nvidia-smi |
| 3 | Job e2e `probe` + `pytorch_cuda_probe` via `/jobs` + `/v1/pool` | **PASS** — probe `cf64269b…` completed; CUDA `49c6ddfa…` `cuda_available=true` on `cuda:0` 5060 Ti |
| 4 | Portal Tailscale `http://100.85.165.84:8767/portal` + invite login | **PASS** — HTTP 200; invite `glitch-factor` → `auth_method=invite_code` |
| 5 | Portal Utilize submit (quick probe) | **PASS** — `POST /api/jobs` probe completes through worker |
| 6 | Desktop app import / `start-gpu-pool-app` | **PASS** — `GPUPool`+`desktop_app` import OK; `start-gpu-pool-app.cmd` present; process `-m gpu_swarm.app` running |
| 7 | Discord GPU Pool bot + guild commands | **PASS** — PID running `-m gpu_swarm bot`; earlier sync 6 guild cmds (`pool/workers/contribute/submit_probe/submit_compute/job_status`) |
| 8 | GitHub `phoenixfire808/gpu-swarm` local=remote | **PASS** — public repo; `master` = `origin/master` @ `5cc347f` |
| 9 | agent-vms quick status | **PASS (cheap)** — `agent-ubuntu` running SSH/RDP; `demo-a` poweroff |

**Demo verdict:** MOSTLY — safe Twitch show: scheduler status, real GPUs, probe/CUDA jobs, Tailscale portal invite+Utilize, Discord slash cmds, GitHub. Gaps vs vision: RAM/SSD ads not DFS; OAuth later; no Whisper/LLM jobs yet; only allowlisted job types.



## Done (with dates)

### Core pool (2026-08-04)
- [x] Project scaffold at `C:\Users\Drew\Projects\gpu-swarm`
- [x] **Scheduler** (FastAPI + SQLite): register, heartbeat, lease, complete/fail, submit, `/status`, `/v1/pool/*` wrappers
- [x] **Workers**: real `nvidia-smi`, lease/run/report, soft caps (`max_vram/cpu/ram/disk`)
- [x] **Resource heartbeats**: CPU/RAM/disk + GPU on register/heartbeat; `/status` aggregates
- [x] Job runners: `probe`, `pytorch_cuda_probe` (allowlisted only)
- [x] CLI: `scheduler`, `worker`, `submit`, `status`, `bot`, `job`, `utilize …`
- [x] Start scripts: `start-scheduler-lan.cmd`, `start-portal.cmd`, `start-bot.cmd`, `start-gpu-pool-app.cmd`, etc.
- [x] `.env.example`, `.gitignore` (blocks `.env`, `*TOKEN*PASTE*`, `data/`, `logs/`, keys)

### Discord GPU Pool bot (2026-08-04)
- [x] Bot wired as **GPU Pool** (not Jarvis); token in local `.env` only
- [x] Hybrid + guild slash sync → Glitch Factor: `/pool` `/workers` `/contribute` `/submit_probe` `/submit_compute` `/job_status`
- [x] Message Content Intent ON; invited to Glitch Factor (+ Jarvis HQ non-primary)
- [x] Docs: primary server = Glitch Factor

### Portal Contribute / Utilize (2026-08-04)
- [x] Web portal at `/portal` — Contribute (register/caps/join) + Utilize (allowlisted submit)
- [x] MVP auth: pool password **or** invite `glitch-factor` + display name
- [x] Bound `0.0.0.0:8767` — Tailscale portal works remotely
- [x] Proxy submit to scheduler; OAuth explicitly deferred (`oauth: later`)

### Desktop one-stop wizard (2026-08-04)
- [x] 7-step wizard → **Save + Join**; Leave; Re-run wizard
- [x] Main panel modes: Contribute · Utilize · Connect-from-code helpers
- [x] Caps → `data/joiner_settings.json` + safe `.env` keys
- [x] `scripts/check_prereqs.ps1` + `install_joiner_deps.ps1` (+ `.cmd`); backend wired
- [x] Explorer-safe `start-gpu-pool-app.cmd` (`py`/`python` discovery)

### Coding / connect surface (2026-08-04)
- [x] `CONNECTING.md` — Contribute vs Utilize vs Connect from code (links SDK + examples)
- [x] `gpu_swarm/client.py` — `GPUPool` SDK (`status` / `submit` / `wait` / probe helpers) → `POST /jobs` + `GET /status` (aligned with `coding_agent_pool.py`)
- [x] CLI `python -m gpu_swarm utilize status|probe|cuda`
- [x] Examples: `coding_agent_pool.py`, `use_pool_from_script.py`, `ollama_or_local_offload.md`, `hermes_pool_skill.md`
- [x] Hermes skill stub `shared-skills/gpu-swarm/SKILL.md`
- [x] Local-model honesty doc: no Ollama proxy in v1; path sketched for Whisper/LLM later
- [x] **E2E (this pass):** SDK probe+cuda (`cuda:0`); CLI utilize probe+cuda; `use_pool_from_script.py` probe — all completed on live scheduler
- [x] Scheduler process restart applied — `/v1/pool/status`, `POST/GET /v1/pool/jobs` live; classic `/status`+`/jobs` still OK; Drew-Home stayed online (no worker restart)

### Git hygiene (partial, 2026-08-04)
- [x] Local commits exist on `master` (public-ready baseline + publish checklist commits)
- [x] Secrets scrubbed from docs for public-safe share (token last4 removed)
- [x] Remote + push — https://github.com/phoenixfire808/gpu-swarm (`origin`/`master`, public)

---

### GitHub (2026-08-04)
- [x] **GitHub publish** — public repo https://github.com/phoenixfire808/gpu-swarm (`gh auth` as phoenixfire808; `origin` pushed)

### EXE download UX docs (2026-08-04)
- [x] `DOWNLOAD.md` — Releases URL placeholder, Tailscale, invite `glitch-factor`, NVIDIA drivers, join steps
- [x] `DISCORD_MEMBER_QUICKSTART.md` — leads with Windows EXE download (placeholder asset URL until packaging Worker publishes)
- [x] README links Releases + `DOWNLOAD.md` as easiest path
- [x] `.gitignore` — `dist/` `build/` `*.spec` with `!gpu_pool.spec` (track PyInstaller spec when packaging Worker adds it)
- [ ] GitHub Release + EXE asset — **owned by packaging Worker** (docs use `/releases/latest` placeholder)

## In progress

- [x] Public repo published — remaining work is Discord smoke + member quickstart, not git publish.
- [x] Download / member docs prepared for EXE Releases UX (placeholder URL until release exists).
- [ ] Packaging Worker: build + publish Windows EXE to GitHub Releases; fill exact asset URL in docs if name differs.
- [ ] Confirm Discord `/pool` smoke in a Glitch Factor channel (manual; optional but good for stream).
- [ ] Keep scorecard/TODO in sync as features land (this file + `TODO.md`).

---

## Next (prioritized)

1. **Packaging Worker** — publish Windows EXE to GitHub Releases; swap placeholder asset name/URL if needed.
2. **Member onboarding paste** — post `DISCORD_MEMBER_QUICKSTART.md` in Glitch Factor (EXE + repo URL).
3. **Stream-friendly verify** — EXE/wizard Join → portal Contribute/Utilize → Discord `/pool` → `coding_agent_pool.py --job probe`.
4. **Discord `/pool` channel smoke** (optional, stream).
5. **Future job types** — design then implement `whisper_transcribe` / bounded `llm_generate` (see `examples/ollama_or_local_offload.md`); no shell jobs.
6. **Discord OAuth** for portal (replace invite/password MVP).
7. Optional: DFS / pooled memory — out of v1 scope (VISION.md).

### Next 5 Drew should care about right now

1. Wait for / verify packaging Worker Release + EXE asset.
2. Post member quickstart (EXE-first) + repo URL in Glitch Factor.
3. Quick live smoke: portal Utilize + Discord `/pool`.
4. Plan Whisper/LLM allowlisted runners (post-publish).
5. Keep `.env` / tokens local — never commit.

---

## Blocked

| Blocker | Why | Unblock |
|---------|-----|---------|
| **Whisper / LLM jobs** | No runners in `jobs.py`; only sketches in docs | Design narrow contract → `ALLOWED_JOB_TYPES` + runner + UI surfaces |
| **Portal OAuth** | MVP invite/password only by design | Implement OAuth when publish + auth story is ready |
| **Public internet expose** | Intentionally LAN/Tailscale only | Keep private; do not open `:8766`/`:8767` to WAN |

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
python -m gpu_swarm utilize cuda --wait
python examples\coding_agent_pool.py --job probe
python examples\use_pool_from_script.py --cuda
```

---

## Do not

- Commit `.env`, `DISCORD_BOT_TOKEN_PASTE.txt`, tokens, or `data/`
- Use Docker for this stack
- Steal port `8765` (Robinhood)
- Wipe Hermes durable memory / reuse Jarvis bot token
- Invent green checks — re-probe `/status` + portal when updating this file
