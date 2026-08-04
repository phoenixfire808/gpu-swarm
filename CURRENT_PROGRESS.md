# CURRENT_PROGRESS — gpu-swarm

Private Discord GPU/CPU co-op swarm for Drew's Discord members.

Updated: 2026-08-04 — **Workers advertise real RAM/CPU/disk/GPU**; `/status` shows live host metrics

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
- [ ] Optional: smoke `/pool` in Glitch Factor Discord channel (manual)
- [ ] Optional Whisper job later (reuse DrewLocalVoice/faster-whisper without breaking it)

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
| Web portal (when used) | `:8767` | Browser join path |

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

In **Glitch Factor** Discord: type `/pool` — should now also show CPU cores, RAM, and disk free.

## Live pool status (scheduler) — host metrics smoke

- Scheduler `:8766` healthy (restarted with DB migration)
- Worker `Drew-Home` re-registered with live host metrics
- Example `/status` (no secrets): see snippet below / `artifacts/status_host_metrics.json`

```json
{
  "workers_online": 1,
  "cpu_cores": 16,
  "ram_available_mb": 8219,
  "ram_total_mb": 32693,
  "disk_free_mb": 28901,
  "free_vram_mb": 1024,
  "total_vram_mb": 24503,
  "dedicated_cpu_cores": 4.0,
  "gpus": [
    "Drew-Home: NVIDIA GeForce RTX 5060 Ti",
    "Drew-Home: NVIDIA GeForce RTX 2070 SUPER"
  ]
}
```

Note: `free_vram_mb=1024` reflects soft cap `max_vram_mb=1024` from current worker env (not mock data).

## How Drew starts next time

```bat
cd C:\Users\Drew\Projects\gpu-swarm
start-scheduler-lan.cmd
start-worker.cmd
start-bot.cmd
```

## Notes

- Discord application name is **GPU Pool** (project folder/package remains `gpu-swarm`)
- Primary co-op Discord = **Glitch Factor** (not Jarvis HQ)
- No Docker / no mock GPU or host data
- Did not wipe Hermes durable MEMORY/USER/SOUL/credentials/vault
- Did not stop Robinhood on 8765
- Did **not** use Jarvis bot token
- Did **not** commit `.env`


## Worker 4 — GitHub publish readiness (2026-08-04)

- [x] Audited `.gitignore`: blocks `.env`, `DISCORD_BOT_TOKEN_PASTE.txt` / `*TOKEN*PASTE*`, `data/`, `logs/`, `smoke_results/`, `venv/` / `.venv/`, `__pycache__/`, `*.pyc` / `*.py[cod]`, `tokens/`, `*.pem` / `*.key`
- [x] Scrubbed token last4 from this progress file for public-safe commit
- [x] Confirmed `.env` and paste file are not staged
- [x] Local commit of safe project files (desktop app, backend, docs, bot/scheduler/worker)
- [ ] `gh repo create` + push — requires GitHub CLI install/auth on Drew's machine if not present
- GitHub URL: *(pending `gh repo create`)*
