# CURRENT_PROGRESS — GPU Pool (gpu-swarm)

Living scorecard for Drew’s private Discord GPU/CPU co-op.  
**Updated:** 2026-08-04 · Scheduler restarted; `/v1/pool/*` live on `:8766`.

| Service | Local | Tailscale |
|---------|-------|-----------|
| Scheduler | `http://127.0.0.1:8766` | `http://100.85.165.84:8766` |
| Portal | `http://127.0.0.1:8767/portal` | `http://100.85.165.84:8767/portal` |
| Robinhood CC | `127.0.0.1:8765` | **do not steal** |

**Discord:** App **GPU Pool** · Primary guild **Glitch Factor** · Invite code `glitch-factor`  
**v1 jobs only:** `probe`, `pytorch_cuda_probe` · Auth MVP: invite/password (OAuth later)  
**Rules:** No Docker · No mock GPU/host data · Never commit `.env` / token paste files

---

## Live scorecard (spot-check 2026-08-04)

### Scheduler restart (2026-08-04, post-SDK `/v1/pool`)
- Restarted **only** `python -m gpu_swarm scheduler --host 0.0.0.0 --port 8766`; did **not** touch Robinhood `:8765` or Discord bot
- **PASS** scheduler: listening `0.0.0.0:8766`
- **PASS** classic: `GET /status` 200; `POST /jobs` + `GET /jobs/{id}` 200
- **PASS** `/v1/pool`: `GET /v1/pool/status` 200; `POST /v1/pool/jobs` + `GET /v1/pool/jobs/{id}` 200
- **PASS** worker: `Drew-Home` stayed online (no worker restart)



| # | Check | Result |
|---|--------|--------|
| 1 | Scheduler `:8766` `/status` + workers + GPU/CPU/RAM/disk | **PASS** (live JSON; bind `0.0.0.0`) |
| 2 | Worker online with real GPUs | **PASS** (`Drew-Home`: 5060 Ti + 2070 SUPER) |
| 3 | Job e2e `probe` + `pytorch_cuda_probe` | **PASS** (completed earlier today; jobs.completed ≥ 17) |
| 4 | Portal `:8767` Contribute/Utilize + Tailscale | **PASS** (HTTP 200 localhost + Tailscale) |
| 5 | Desktop wizard / prereqs / join helpers | **PASS** (code + prior smoke) |
| 6 | Discord GPU Pool bot + guild slash cmds | **PASS** (6 cmds; process left running in prior session) |
| 7 | Coding client / `CONNECTING.md` / examples | **PASS** — `GPUPool` + `utilize` CLI + examples e2e |
| 8 | GitHub remote + push | **FAIL** — no `origin`; `gh` not logged in; dirty tree |

Honest v1: GPU/CPU run jobs; RAM/SSD are **capacity ads** for scheduling, not pooled memory/DFS.

---

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
- [ ] Remote + push — see **Blocked**

---

## In progress

- [ ] Working tree has **uncommitted** safe product work (client, CONNECTING, examples, portal/desktop/CLI/docs). Needs a clean commit before publish — prefer GitHub worker to commit; this progress pass only stages docs.
- [ ] Confirm Discord `/pool` smoke in a Glitch Factor channel (manual; optional but good for stream).
- [ ] Keep scorecard/TODO in sync as features land (this file + `TODO.md`).

---

## Next (prioritized)

1. **Stage/commit safe tree** — include product + docs; **exclude** `.env`, `DISCORD_BOT_TOKEN_PASTE.txt`, `data/`, `logs/`. Coordinate with GitHub worker.
2. **`gh auth login`** on Drew’s machine (currently: *not logged into any GitHub hosts*).
3. **`gh repo create` + `git remote add origin` + push** — first public/private share URL.
4. **Stream-friendly verify** — wizard Join → portal Contribute/Utilize → Discord `/pool` → `coding_agent_pool.py --job probe`.
5. **Member onboarding paste** — ship `DISCORD_MEMBER_QUICKSTART.md` blurb in Glitch Factor once repo URL exists.
6. **Future job types** — design then implement `whisper_transcribe` / bounded `llm_generate` (see `examples/ollama_or_local_offload.md`); no shell jobs.
7. **Discord OAuth** for portal (replace invite/password MVP).
8. Optional: DFS / pooled memory — out of v1 scope (VISION.md).

### Next 5 Drew should care about right now

1. Commit the dirty safe files (no secrets).
2. Authenticate GitHub CLI (`gh auth login`).
3. Create remote + push (`gh repo create` / `git push -u origin master`).
4. Quick live smoke: portal Utilize + Discord `/pool`.
5. Only after publish: plan Whisper/LLM allowlisted runners (do not rush into OAuth/DFS).

---

## Blocked

| Blocker | Why | Unblock |
|---------|-----|---------|
| **GitHub publish** | No `git remote`; `gh auth status` → not logged in | `gh auth login` → `gh repo create` → push |
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
