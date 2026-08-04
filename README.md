# gpu-swarm — Private GPU Pool Co-op

Members of a **private Discord** (and friends on Tailscale) plug home PCs into a shared compute pool. Workers advertise GPU / CPU / RAM / disk capacity, pull allowlisted jobs from a central scheduler, and return real results.

This is a co-op pool — **not** a public marketplace.

## Product vision (v1)

**Browser-first:** anyone Drew invites can log into a web portal, register a machine, set resource caps, and keep a worker online so the pool grows dynamically.

| Resource | What v1 actually does |
|----------|------------------------|
| **GPU (VRAM)** | Real jobs run here (`nvidia-smi` inventory; CUDA probes) |
| **CPU** | Soft percent/core caps; used by allowlisted compute |
| **RAM** | Advertised capacity + soft cap for **scheduling** — not pooled shared memory yet |
| **SSD / disk** | Advertised free space + soft cap for **scheduling** — not a magic shared hard drive yet |

Jobs execute on a worker’s own GPU/CPU. RAM/SSD numbers help the scheduler pick a machine; they do **not** turn everyone’s drives into one NAS.

## Ways to join (pick one)

| Path | Who it’s for | Entry |
|------|--------------|--------|
| **0. Windows EXE** (easiest) | Friends on Windows | [Releases](https://github.com/phoenixfire808/gpu-swarm/releases/latest) · [`DOWNLOAD.md`](DOWNLOAD.md) |
| **1. Web portal** | Friends / Twitch collab | `http://<host>:8767/portal` |
| **2. Desktop app** (from source) | Power users on Windows | `start-gpu-pool-app.cmd` → `python -m gpu_swarm.app` |
| **3. CLI worker** | Scripts / Hermes | `python -m gpu_swarm worker …` |
| **Discord bot** | Status + submit jobs | `/pool`, `/workers`, … in **Glitch Factor** |
| **Connect from code** | Coders / local models / agents | `GPUPool` SDK · `utilize` CLI · [`CONNECTING.md`](CONNECTING.md) |

Product one-pager: [`VISION.md`](VISION.md).  
**Windows EXE download:** [`DOWNLOAD.md`](DOWNLOAD.md) · [GitHub Releases](https://github.com/phoenixfire808/gpu-swarm/releases/latest).  
Connect paths (Contribute / Utilize / code): [`CONNECTING.md`](CONNECTING.md).  
Paste-ready blurb for Discord: [`DISCORD_MEMBER_QUICKSTART.md`](DISCORD_MEMBER_QUICKSTART.md).  
Local models / coding agents: [`examples/ollama_or_local_offload.md`](examples/ollama_or_local_offload.md) · [`examples/coding_agent_pool.py`](examples/coding_agent_pool.py) · [`examples/use_pool_from_script.py`](examples/use_pool_from_script.py).  
Optional VM workspaces (not GPU passthrough): [`ADVANCED_VM.md`](ADVANCED_VM.md).

## What's included

| Piece | Role |
|-------|------|
| **Web portal** | Browser login + “plug in this PC” caps (GPU/CPU/RAM/disk) — port **8767** `/portal` |
| **Desktop app** | Native Windows joiner — wizard, caps, Join/Leave (`start-gpu-pool-app.cmd`) |
| **Scheduler** | FastAPI + SQLite queue on **8766** (`/workers/*`, `/jobs/*`, `/status`) |
| **Worker** | Real `nvidia-smi` + host metrics, heartbeats, leases + runs jobs |
| **CLI** | Hermes-friendly `python -m gpu_swarm …` + coder `utilize status|probe|cuda` |
| **Python SDK** | `from gpu_swarm.client import GPUPool` — `status` / `submit` / `wait` / probes |
| **Discord bot** | `/pool` `/workers` `/contribute` `/submit_probe` `/submit_compute` `/job_status` |

### Job types (allowlisted only)

- `probe` — live `nvidia-smi` GPU inventory JSON (proves network + worker)
- `pytorch_cuda_probe` — real CUDA matmul via PyTorch when available

No arbitrary shell from Discord. Results are size-capped.

---

## 1) Web portal contributor flow (primary for friends)

Default URLs on Drew’s host (Tailscale):

| Service | URL |
|---------|-----|
| Portal | `http://100.85.165.84:8767/portal` |
| Scheduler API | `http://100.85.165.84:8766` |
| Local portal | `http://127.0.0.1:8767/portal` |

**Friend flow**

1. Install Tailscale and join Drew’s private network (ask Drew). Private Tailscale/LAN pool — not exposed to the open internet.
2. Open the portal URL → sign in with **invite code / pool password** + display name (OAuth comes later).
3. **Home** shows three big paths: **Contribute** · **Utilize** · **Connect** (URLs, Discord commands, CLI/SDK — [`CONNECTING.md`](CONNECTING.md)).
4. **Contribute — register this machine** — set dedication caps:
   - GPU VRAM (MiB)
   - CPU (% or cores)
   - RAM (MiB advertised / capped)
   - Disk / SSD (MiB free for job scratch — scheduling hint)
5. Start the worker from the portal instructions (or keep the downloadable agent running) so the machine heartbeats into the pool.
6. Confirm in Discord: `/pool` and `/workers` show the new machine.

Leave anytime from the portal (or stop the worker). Caps persist for the next session.

> Portal launcher: `start-portal.cmd` or `python -m gpu_swarm portal` → **8767**/portal. Scheduler stays on **8766**.

---

## 2) GPU Pool desktop app (native)

### Using the app

Windows one-stop app. After the setup wizard, **Home** shows three large modes — Contribute, Utilize, and Connect are first-class (not buried).

```bat
cd C:\Users\Drew\Projects\gpu-swarm
REM deps already on this machine; only install if missing:
REM python -m pip install --user -r requirements.txt

start-gpu-pool-app.cmd
REM equivalent: python -m gpu_swarm.app
REM EXE rebuild (packaging Worker): rebuild from this source so Home / Utilize / Connect ship in GPUPool.exe
```

| Mode | What it does |
|------|----------------|
| **1 · Contribute** | Install/join as a worker — wizard, caps, **Join / Leave** |
| **2 · Utilize** | Use the pool **now** — live workers/GPUs, **Run Probe**, **Run CUDA Job**, status + result panel |
| **3 · Connect** | Plug in from code/tools — scheduler/portal copy, `GPUPool` snippet, `python -m gpu_swarm utilize …`, Discord tips |

**Contribute**

1. Setup wizard — Python/deps, NVIDIA, optional CUDA torch (consent), scheduler URL (default Tailscale `:8766`).
2. Identity + **VRAM / CPU / RAM / disk** soft caps.
3. Portal awareness (Tailscale `http://100.85.165.84:8767/portal`, invite `glitch-factor`).
4. **Join Pool** / **Leave Pool**.

**Utilize**

1. Home → **Utilize** (or tab **2 · Utilize**).
2. Pick scheduler: Local `http://127.0.0.1:8766` or Tailscale `http://100.85.165.84:8766`.
3. Refresh live pool (workers / GPUs / VRAM).
4. **Run Probe** or **Run CUDA Job** → wait for completed JSON in the result panel.
5. Allowlisted only: `probe`, `pytorch_cuda_probe` (see “What can I run?”). Discord: `/pool` · `/submit_probe` · `/submit_compute`.

**Connect**

1. Home → **Connect**.
2. Copy **Scheduler URL** (env `GPU_SWARM_SCHEDULER_URL`, default Tailscale `:8766`).
3. Copy **Portal URL** `http://100.85.165.84:8767/portal` (invite `glitch-factor`).
4. Open [`CONNECTING.md`](CONNECTING.md) / `examples/` · paste Python `GPUPool` or CLI:

```bat
set GPU_SWARM_SCHEDULER_URL=http://100.85.165.84:8766
python -m gpu_swarm utilize status
python -m gpu_swarm utilize probe --wait
python examples\coding_agent_pool.py --job probe
```

Full map: [`CONNECTING.md`](CONNECTING.md). Settings under `data/joiner_settings.json` (gitignored).

---

## 3) Discord GPU Pool bot commands

Primary guild: **Glitch Factor**. Bot app name: **GPU Pool** (`GPU pool#1686`).

| Command | Purpose |
|---------|---------|
| `/pool` | Pool overview (workers + VRAM / capacity) |
| `/workers` | List online workers |
| `/contribute` | How to join + soft caps |
| `/submit_probe` | Live GPU probe job |
| `/submit_compute` | CUDA matmul probe |
| `/job_status` | Check a job by id |

Host setup (Drew): dedicated Discord Application **GPU Pool** — do **not** reuse Hermes **Jarvis** (same token fights the gateway).

1. https://discord.com/developers/applications → **GPU Pool** → **Bot**
2. **Message Content Intent** ON
3. Token → `set-discord-token.cmd <token>` or `.env` as `DISCORD_BOT_TOKEN=` (**never commit**)
4. Invite: scopes `bot` + `applications.commands`, permissions `84992`
5. Guild slash sync: `DISCORD_GUILD_ID=1532614467974856724` (Glitch Factor)
6. `start-bot.cmd` (scheduler on `:8766`)

```bat
make-invite-url.cmd 1534226262510403654
```

Invite template:

```
https://discord.com/oauth2/authorize?client_id=1534226262510403654&permissions=84992&scope=bot%20applications.commands
```

---

## Twitch / friend demo (browser dashboard)

Stream-friendly talking points:

1. **Open the portal** (`:8767/portal`) — “This is the control room. Friends log in and plug a PC into the pool.”
2. **Show the pool** — machines online with GPU / CPU / RAM / disk numbers. Say clearly: *GPU and CPU run jobs; RAM and SSD are capacity we advertise for scheduling, not a shared drive yet.*
3. **Discord side-by-side** — `/pool` then `/submit_probe` (or `/submit_compute`) so chat sees a real job land on a home GPU.
4. **Friend join beat** — they open the same portal on Tailscale, set caps, start worker → `/workers` shows two names.
5. **Optional** — flash the desktop app (`start-gpu-pool-app.cmd`) as the native power-user path; keep the hero demo on the **browser**.

**One sentence for chat:**  
“We’re building a private co-op cloud — log into the portal, dedicate spare GPU/CPU (and advertise RAM/disk), and jobs farm across whoever’s online.”

**Do not show on stream:** `.env`, bot tokens, invite codes in chat overlays, public-internet binds.

---

## Quickstart (Windows — Drew home host)

```bat
cd C:\Users\Drew\Projects\gpu-swarm
REM python -m pip install --user -r requirements.txt   # only if missing
```

| Script | What it does |
|--------|----------------|
| `start-scheduler.cmd` | Scheduler on `127.0.0.1:8766` (local only) |
| `start-scheduler-lan.cmd` | Scheduler on `0.0.0.0:8766` (Tailscale/LAN) |
| `start-portal.cmd` | Contributor web portal on `:8767/portal` |
| `start-gpu-pool-app.cmd` | Desktop joiner UI *(when present)* |
| `start-worker.cmd` | Worker `Drew-Home` → localhost scheduler |
| `start-bot.cmd` | Discord bot (`DISCORD_BOT_TOKEN` in `.env`) |
| `start-all-local.cmd` | Scheduler + worker + bot windows |

**Ports:** Robinhood Command Center uses **8765** — do not steal it. Scheduler **8766**, portal **8767**.

### CLI equivalents

```bash
python -m gpu_swarm scheduler --host 0.0.0.0 --port 8766
python -m gpu_swarm worker --name Drew-Home
python -m gpu_swarm status
python -m gpu_swarm submit probe --wait
python -m gpu_swarm submit pytorch_cuda_probe --matrix-size 1024 --wait
python -m gpu_swarm bot --check
python -m gpu_swarm bot
python -m gpu_swarm.app
```

### Member CLI fallback

```text
1) NVIDIA drivers; nvidia-smi works
2) Python 3.10+ + gpu-swarm folder
3) pip install -r requirements.txt
4) set GPU_SWARM_SCHEDULER_URL=http://100.85.165.84:8766
5) python -m gpu_swarm worker --name YourDiscordName --discord-user YourDiscordName
6) Discord: /pool  /workers  /contribute  /submit_probe  /submit_compute  /job_status
```

*(Tailscale IP re-checked 2026-08-04: `100.85.165.84`.)*

## Safety / networking / secrets

- Local demo: scheduler `127.0.0.1:8766`, portal `127.0.0.1:8767/portal`
- Multi-house: Tailscale URLs above — **no public bind without auth**
- Workers only run allowlisted job types
- **Never commit `.env`** — listed in `.gitignore` with `data/`, tokens paste files, venvs, DBs
- Copy `.env.example` → `.env` locally; share invite codes in private channels, never bot tokens

## Connect from a coding session (Cursor / Hermes)

```python
from gpu_swarm.client import GPUPool
pool = GPUPool()  # GPU_SWARM_SCHEDULER_URL or http://100.85.165.84:8766
print(pool.status()["workers_online"])
print(pool.submit_probe(wait=True)["status"])
```

```bash
set GPU_SWARM_SCHEDULER_URL=http://127.0.0.1:8766
python -m gpu_swarm utilize status
python -m gpu_swarm utilize probe --wait
python -m gpu_swarm utilize cuda --wait
python examples/coding_agent_pool.py --job probe
python examples/use_pool_from_script.py --cuda
```

HTTP (same as the agent script): `GET /status`, `POST /jobs`, `GET /jobs/{id}`.  
Details: [`CONNECTING.md`](CONNECTING.md) · Hermes notes: [`examples/hermes_pool_skill.md`](examples/hermes_pool_skill.md).

## Hermes (host ops)

```bash
python -m gpu_swarm scheduler --host 0.0.0.0 --port 8766
python -m gpu_swarm worker --name Drew-Home
python -m gpu_swarm utilize probe --wait
python -m gpu_swarm status
```

Skill stub: `shared-skills/gpu-swarm/SKILL.md`.

## Project layout

```
gpu_swarm/
  client.py         # GPUPool utilizer SDK (POST /jobs, GET /status)
  scheduler.py      # FastAPI scheduler (:8766)
  worker.py         # contribution worker
  jobs.py           # allowlisted runners
  gpu.py            # nvidia-smi inventory
  bot.py            # discord.py hybrid commands
  cli.py            # entry CLI (+ utilize)
  db.py             # SQLite store
  config.py         # env config
  app_backend.py    # desktop/portal backend API
  joiner_settings.py
  app/              # desktop joiner (customtkinter)
CONNECTING.md       # Contribute / Utilize / Connect map
examples/           # coding_agent_pool.py, use_pool_from_script.py, …
ADVANCED_VM.md      # optional agent-vms note (no fake GPU passthrough)
DISCORD_MEMBER_QUICKSTART.md
```
