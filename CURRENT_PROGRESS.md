# CURRENT_PROGRESS — gpu-swarm

Private Discord GPU/CPU co-op swarm for Drew's Discord members.

Updated: 2026-08-04 (desktop Contribute + Utilize + Connect)

## Desktop Contribute + Utilize + Connect (2026-08-04)

- [x] Main panel modes: **Contribute** · **Utilize** · **Connect from code**
- [x] Contribute: wizard + Join/Leave + caps (`install_joiner_deps` / prereqs / NVIDIA / optional torch)
- [x] Utilize: live `pool_status`, submit `probe` + `pytorch_cuda_probe`, wait/poll JSON, Discord slash copy
- [x] Connect panel → **`CONNECTING.md`** + **`examples/coding_agent_pool.py`** (+ `ollama_or_local_offload.md`)
- [x] Backend APIs: `submit_job` / `get_job` / `wait_for_job` / `pool_status` / `get_connect_from_code_text` / `open_repo_doc`
- [x] README: Contribute vs Utilize vs Connect table
- [x] **E2E (live scheduler)** PASS — probe `4980a624-…` completed; cuda `66fd3853-…` on `cuda:0`; `coding_agent_pool.py` probe `3d13845f-…` completed; UI import OK
- [x] Portal Tailscale already verified separately (`0.0.0.0:8767`); Discord bot untouched; no Docker; no secrets committed

### How users Contribute vs Utilize (desktop app)

| Mode | Action |
|------|--------|
| **Contribute** | Wizard → caps → **Join pool** / **Leave** |
| **Utilize** | Utilize tab → Refresh → **Submit probe** / **Submit CUDA matmul** → results |
| **Connect** | Open CONNECTING.md / coding_agent_pool.py · copy `GPU_SWARM_SCHEDULER_URL` · Tailscale portal |

```bat
start-gpu-pool-app.cmd
set GPU_SWARM_SCHEDULER_URL=http://100.85.165.84:8766
python examples\coding_agent_pool.py --job probe
```

## Portal Utilize panel (2026-08-04)

- [x] Portal bind `0.0.0.0:8767` — Tailscale `http://100.85.165.84:8767/portal` works
- [x] After login: **Dashboard** (scheduler `/status` capacity) · **Utilize** · **Contribute**
- [x] Utilize: submit allowlisted `probe` / `pytorch_cuda_probe` via `POST /api/jobs` → scheduler; poll `GET /api/jobs/{id}`
- [x] Honest copy: v1 allowlisted jobs only (shell rejected with 400)
- [x] Contribute/register machine flow kept
- [x] Verified over Tailscale: login `glitch-factor` → probe completed → cuda probe completed on `cuda:0` (5060 Ti)
- [x] Discord bot left running (PID 5972); no Docker; no secret leaks

**HTTP smoke (Tailscale):**
```bat
curl http://100.85.165.84:8767/health
REM login with invite, then:
curl -b cookies -c cookies -X POST http://100.85.165.84:8767/api/jobs -H "Content-Type: application/json" -d "{\"job_type\":\"probe\"}"
curl -b cookies http://100.85.165.84:8767/api/jobs/<id>
```

## Local-model / coding-agent bridge (2026-08-04)

- [x] `CONNECTING.md` — Contribute vs Utilize vs Connect from code/Discord/portal/app
- [x] `examples/ollama_or_local_offload.md` — honest v1 (no Ollama proxy); path to whisper/LLM job types; how to add allowlisted runners
- [x] `examples/coding_agent_pool.py` — stdlib script: submit probe / pytorch_cuda_probe → print JSON
- [x] `DISCORD_MEMBER_QUICKSTART.md` — coding / local-model users blurb
- [x] README links to CONNECTING + examples
- [x] Verified live vs `http://127.0.0.1:8766`: status OK; probe completed; pytorch_cuda_probe completed on `cuda:0` (5060 Ti)
- [x] Did **not** add shell/pip_list/echo jobs; no Whisper runner yet (no hooks in repo — documented for later)
- [x] Did **not** touch Discord token / Docker / restart scheduler/bot

**Agent invoke:**
```bat
python examples\coding_agent_pool.py --job probe
python examples\coding_agent_pool.py --job pytorch_cuda_probe --matrix-size 1024
```

## Live verification scorecard (2026-08-04 (live stream verify))

| # | Check | Result |
|---|--------|--------|
| 1 | Scheduler :8766 `/status` workers + GPU/CPU/RAM/disk | **PASS** (bind `0.0.0.0`) |
| 2 | Worker online real GPUs | **PASS** (`Drew-Home`: 5060 Ti + 2070 SUPER) |
| 3 | Job e2e probe + pytorch_cuda_probe | **PASS** (completed on cuda:0) |
| 4 | Portal :8767 login `glitch-factor` + dashboard workers | **PASS** localhost + Tailscale (`0.0.0.0:8767`) |
| 5 | Desktop app import / smoke / prereqs | **PASS** |
| 6 | Discord bot GPU Pool process + guild slash cmds | **PASS** (token last4 `...NsrI`; 6 cmds in Glitch Factor) |
| 7 | agent-vms `agent-vm status` | **PASS** (`agent-ubuntu` running; Hermes intact) |
| 8 | GitHub remote/push ready | **FAIL/GAP** — local commits exist; **no remote**; **gh not authed**; dirty working tree |

### Honest gaps vs vision
- RAM/SSD = capacity ads for scheduling, **not** DFS / pooled memory (see `capacity_note` + VISION.md)
- Portal now binds `0.0.0.0:8767` (same pattern as scheduler); Tailscale `:8767` and `:8766` OK
- Invite/password MVP auth — Discord OAuth later
- `gh auth login` + add `origin` still needed to publish

## One-stop install helpers (Support Worker — 2026-08-04)

- [x] `scripts/check_prereqs.ps1` (+ `.cmd`) — real probes: Python, nvidia-smi, scheduler `/status`, disk free; JSON (default) or `-Text`
- [x] `scripts/install_joiner_deps.ps1` (+ `.cmd`) — idempotent `requirements.txt` install; optional `-WithTorchCuda` (skips if CUDA torch already present)
- [x] `app_backend.script_paths()` / `check_prereqs()` / `install_joiner_deps()` wired to those scripts
- [x] Verified live on Drew-Home: prereqs OK (2 GPUs, scheduler :8766, ~28 GiB free); deps skip when satisfied; torch CUDA skip when present
- [x] Did **not** touch Discord token / Docker / restart scheduler

**Invoke from wizard/backend:**
- `be.check_prereqs()` → `scripts/check_prereqs.ps1`
- `be.install_joiner_deps(with_torch_cuda=False|True)` → `scripts/install_joiner_deps.ps1`
- CLI: `scripts\check_prereqs.cmd --text` · `scripts\install_joiner_deps.cmd [--with-torch-cuda]`


## Checklist

- [x] Create project at `C:\Users\Drew\Projects\gpu-swarm`
- [x] Scheduler API (FastAPI + SQLite): register, heartbeat, lease, complete/fail, submit, status
- [x] Worker: real `nvidia-smi` GPU detect, heartbeat, lease/run/report
- [x] Job `probe` — live GPU inventory
- [x] Job `pytorch_cuda_probe` — real CUDA matmul via existing torch
- [x] CLI: `scheduler`, `worker`, `submit`, `status`, `bot`, `job`
- [x] Discord bot wired (hybrid + guild slash sync via `DISCORD_GUILD_ID`)
- [x] `.env` / `.env.example`, README, `.gitignore` (secrets never committed)
- [x] Windows start scripts + `set-discord-token.cmd` + `make-invite-url.cmd`
- [x] End-to-end verify on Drew's machine (probe + CUDA)
- [x] Hermes skill stub at `shared-skills/gpu-swarm/SKILL.md`
- [x] Scheduler LAN/Tailscale bind prepared (`0.0.0.0:8766`); Tailscale IP documented
- [x] **Discord Application = GPU Pool** (existing app; not a new "GPU Swarm" app; not Jarvis)
- [x] Bot token in `.env` as `DISCORD_BOT_TOKEN` (paste file scrubbed after write)
- [x] Message Content Intent enabled on GPU Pool (verified ON in Developer Portal)
- [x] Bot invited / present in **Glitch Factor** (primary) and Jarvis HQ
- [x] Bot online as `GPU pool#1686`; guild slash sync OK to Glitch Factor
- [x] Docs updated: primary server is Glitch Factor (README / QUICKSTART / CURRENT_PROGRESS)
- [x] **Host metrics advertise** — worker register/heartbeat include real CPU/RAM/disk + GPU
- [x] Scheduler DB migration + `/status` aggregates for `cpu_cores`, `ram_*`, `disk_free_mb`
- [x] Soft caps honored: `max_vram_mb`, `max_cpu_percent`, `max_ram_mb`, `max_disk_mb` (+ portal `dedicated_*` aliases)
- [x] Smoke: restarted scheduler+worker; `/status` shows non-zero live RAM/CPU/disk/GPU (no mocks)
- [x] Discord bot left running (PID preserved); `/pool` + `/workers` show new fields when next invoked
- [x] **Web portal LIVE** at `http://127.0.0.1:8767/portal` (auth: pool password from `.env` **or** invite `glitch-factor`)
- [x] **Desktop one-stop** — wizard + modes **Contribute** / **Utilize** / **Connect from code** (CONNECTING.md + coding_agent_pool.py)
- [x] `start-gpu-pool-app.cmd` Explorer-safe (cd to repo, `py`/`python` discovery, auto-deps if missing)
- [ ] Optional: smoke `/pool` in Glitch Factor Discord channel (manual)
- [x] Portal bound to `0.0.0.0:8767` so Tailscale `http://100.85.165.84:8767/portal` works remotely
- [ ] Optional Whisper job later (reuse DrewLocalVoice/faster-whisper without breaking it) — see `examples/ollama_or_local_offload.md` checklist

## One-stop desktop joiner (2026-08-04)

### What was broken

- Wizard finished without **Save + Join** (Join lived only on the main panel)
- No Python detect / missing-Python guidance in-wizard or in the `.cmd`
- Deps step skipped `psutil` in the check list; no optional **CUDA PyTorch** consent button
- Failures were often silent / without a concrete FIX line
- Portal deep-link preferred Tailscale `100.85.165.84:8767` even when that port refused (portal was only live on `127.0.0.1:8767`)
- Invite code not surfaced in UI; Open Portal could open a dead URL
- `start-gpu-pool-app.cmd` hardcoded `C:\Python313\python.exe` (broke double-click for other layouts)

### What was fixed

- 7-step wizard: Welcome → Python & Deps → Hardware → Identity → Connect → Caps → **Save + Join**
- Progress/log panels on deps, connect test, and join with exact FIX text on failure
- Live host + scheduler metrics in UI (`cpu_cores`, `ram_*`, `disk_*`, `dedicated_*`, VRAM)
- Caps persist to `data/joiner_settings.json` + safe `.env` keys; worker CLI gets `--max-vram/cpu/ram/disk`
- Portal resolve prefers live URL; shows invite **`glitch-factor`** (never prints pool password)
- Join waits for scheduler registration; Leave stops the joiner-managed worker cleanly
- Launcher: `cd /d %~dp0`, `py -3` → `python` → common paths, installs requirements if UI deps missing

### Verified on Drew's machine

- Portal `http://127.0.0.1:8767/portal` → 200; Tailscale `http://100.85.165.84:8767/portal` → 200 (bind `0.0.0.0`)
- Scheduler `http://127.0.0.1:8766/status` → OK
- Join as `Wizard-OneStop` → online with caps `vram=2048`, `cpu=30%`, `ram=8192`, `disk=20480 MiB`
- Leave → process stopped
- Deps already satisfied → install skipped (no redundant full reinstall)
- Torch CUDA present (`2.11.0+cu128`)

## How Drew launches the one-stop app

Double-click or run:

```bat
C:\Users\Drew\Projects\gpu-swarm\start-gpu-pool-app.cmd
```

Or:

```bat
cd C:\Users\Drew\Projects\gpu-swarm
py -3 -m gpu_swarm.app
```

Wizard opens when `wizard_completed` is false (currently reset to false so next launch walks the full flow). Use **Re-run wizard** from the main panel anytime.

Browser portal (easiest remote path):

- Local: http://127.0.0.1:8767/portal
- Tailscale (when portal bound for LAN): http://100.85.165.84:8767/portal
- Invite: `glitch-factor` (pool password stays in `.env`)

## Host metrics — stable JSON field names (portal / desktop / Discord)

Measured (from `nvidia-smi` + `psutil` via `gpu_swarm/host.py`):

| Field | Meaning |
|-------|---------|
| `cpu_cores` | Logical CPU cores |
| `ram_total_mb` | Total system RAM (MiB) |
| `ram_available_mb` | Available RAM after soft cap |
| `disk_free_mb` | Free space on work-dir drive after soft cap |
| `disk_total_mb` | Drive capacity (MiB) |
| `disk_path` | Path used for disk measurement |
| `gpus` / `free_vram_mb` / `total_vram_mb` | Existing GPU inventory |

Caps / portal aliases:

| Field | Meaning |
|-------|---------|
| `max_vram_mb` | Soft VRAM advertise cap (`0` = uncapped free VRAM) |
| `max_cpu_percent` | CPU % contribution cap |
| `max_ram_mb` / `dedicated_ram_mb` | RAM soft cap / dedication ad |
| `max_disk_mb` / `dedicated_disk_mb` | Disk soft cap / dedication ad |
| `dedicated_cpu_cores` | Core-equivalent ad (`cpu_cores * max_cpu_percent/100` if unset) |

Env: `GPU_SWARM_MAX_VRAM_MB`, `GPU_SWARM_MAX_CPU_PERCENT`, `GPU_SWARM_MAX_RAM_MB`, `GPU_SWARM_MAX_DISK_MB` (or `GPU_SWARM_MAX_DISK_GB` / `GPU_SWARM_DEDICATED_*`).

## Port / networking (important)

| Service | Address | Notes |
|---------|---------|--------|
| Robinhood Command Center | `127.0.0.1:8765` | **Do not steal** — already bound |
| gpu-swarm scheduler | `:8766` (running) | Local: `http://127.0.0.1:8766` |
| Tailscale (Drew host) | `100.85.165.84` | Members: `http://100.85.165.84:8766` |
| Web portal | `:8767` | **Live on `0.0.0.0`** — localhost + Tailscale |

## Discord bot — GPU Pool (2026-08-04)

| Item | Value |
|------|-------|
| App name | **GPU Pool** (Developer Portal; username `GPU pool#1686`) |
| Client ID | `1534226262510403654` |
| **Primary guild** | **Glitch Factor** `1532614467974856724` |
| Also in | Jarvis HQ `1532553474577924156` (not primary for slash sync) |
| Bot online | **yes** — left running during metrics smoke (not restarted) |
| Slash sync | **yes** — synced **6** guild slash command(s) to Glitch Factor |
| Token source | Opera Developer Portal (Copy after MFA); paste file was empty then scrubbed |
| Token last4 | *(redacted for public repo)* |
| Message Content Intent | **ON** |
| Invite URL | `https://discord.com/oauth2/authorize?client_id=1534226262510403654&permissions=84992&scope=bot%20applications.commands` |
| Jarvis reused? | **no** |
| Hermes wiped? | **no** |

### Next step for Drew (smoke test)

1. Double-click `start-gpu-pool-app.cmd`
2. Walk wizard → **Save + Join pool**
3. Confirm status shows connected + live CPU/RAM/disk/VRAM
4. Optional: Open portal → invite `glitch-factor`
5. In Discord Glitch Factor: `/pool`

## How Drew starts host services next time

```bat
cd C:\Users\Drew\Projects\gpu-swarm
start-scheduler-lan.cmd
start-portal.cmd
start-bot.cmd
REM members / Drew: start-gpu-pool-app.cmd  (one-stop joiner)
```

## Notes

- Discord application name is **GPU Pool** (project folder/package remains `gpu-swarm`)
- Primary co-op Discord = **Glitch Factor** (not Jarvis HQ)
- No Docker / no mock GPU or host data
- Did not wipe Hermes durable MEMORY/USER/SOUL/credentials/vault
- Did not stop Robinhood on 8765
- Did **not** use Jarvis bot token
- Did **not** commit `.env`
- Pool password never shown in desktop UI (invite code `glitch-factor` is OK to show)


## Worker 4 — GitHub publish readiness (2026-08-04)

- [x] Audited `.gitignore`: blocks `.env`, `DISCORD_BOT_TOKEN_PASTE.txt` / `*TOKEN*PASTE*`, `data/`, `logs/`, `smoke_results/`, `venv/` / `.venv/`, `__pycache__/`, `*.pyc` / `*.py[cod]`, `tokens/`, `*.pem` / `*.key`
- [x] Scrubbed token last4 from this progress file for public-safe commit
- [x] Confirmed `.env` and paste file are not staged
- [x] Local commit of safe project files (desktop app, backend, docs, bot/scheduler/worker)
- [ ] `gh repo create` + push — requires GitHub CLI install/auth on Drew's machine if not present
- GitHub URL: *(pending `gh repo create`)*

## Portal LAN bind fix (2026-08-04)
- Changed defaults: `start-portal.cmd`, `PortalConfig` / `GPU_SWARM_PORTAL_HOST`, CLI help → `0.0.0.0:8767`
- Restarted portal cleanly; listen confirmed `0.0.0.0:8767`
- Verified HTTP 200: `http://127.0.0.1:8767/portal` and `http://100.85.165.84:8767/portal`
- Scheduler `:8766` and Discord bot left running (untouched)
