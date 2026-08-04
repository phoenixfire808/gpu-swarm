# Laptop / no-NVIDIA quickstart

For friends on a **laptop without an NVIDIA GPU**. You can still use the pool.

**What this is for:** run jobs on friends’ GPUs (**Utilize**), optionally lend CPU (**Contribute** with VRAM=0), chat / suggest on the web hub. You do **not** need NVIDIA drivers. Workspace VMs (if you try them later) use shared CPU/RAM only — no GPU passthrough.

**Full login guide:** [`LOGIN.md`](LOGIN.md) (where to get invite / public URL, all three paths, troubleshooting).

## 1) Get on the network

**Preferred (no Tailscale):** ask the host for the **current public portal HTTPS link**.

Quick tunnels rotate when the host restarts `start-public-access.cmd` — do not reuse an old trycloudflare.com URL from chat. On the host PC the live link is also in `data/public_endpoints.share.txt`.

**Or Tailscale (automated):** from gpu-swarm run `scripts\install-prereqs.cmd` (or app wizard → **Network & Workspace** → **Install Tailscale only**). Approve UAC; finish the one browser login. Manual: [Tailscale download](https://tailscale.com/download).

## 2) Open the portal (full URL)

| Path | URL |
|------|-----|
| Public (when tunnel is up) | **Ask the host for current link** — example live now: `https://rational-delicious-bars-examination.trycloudflare.com/portal` |
| Tailscale | `http://100.85.165.84:8767/portal` |
| Host PC only | `http://127.0.0.1:8767/portal` |

Public links are `https://….trycloudflare.com/portal` (no `:8767`). Tailscale/LAN must include **`:8767`** and `/portal`.

## 3) Login

See [`LOGIN.md`](LOGIN.md) for the full form and paths.

- Invite: **`glitch-factor`** (from the host in Glitch Factor — not a public signup)
- Display name: your Discord name (e.g. `YourDiscordName`)
- Pool password: optional (only if a pool admin shares it)

## 4) What to do (no GPU)

1. **Utilize** (recommended) — submit `probe` / CUDA jobs; they run on online pool workers.
2. Optional **Contribute CPU** — register with VRAM=0; worker advertises CPU/RAM/disk with `gpu_available=false` and skips GPU jobs.

Banner on the portal: *No NVIDIA? You can still Utilize the pool or contribute CPU.*

## 5) Or use the Windows EXE (installer)

1. Download latest `GPUPool.exe` from [Releases](https://github.com/phoenixfire808/gpu-swarm/releases/latest)  
   (If SmartScreen appears → **More info** → **Run anyway** only if you trust this repo’s GitHub release.)
2. Run the wizard — you’ll see live progress (“Downloading Python…”, “Installing dependencies…”). It **auto-detects** the scheduler when `data/public_endpoints.json` is present on that machine (host writes it):
   - **First:** public `/pool-api` from `data/public_endpoints.json`
   - Then Tailscale `http://100.85.165.84:8766` if reachable
   - Then localhost
3. Friends joining remotely: open the **public portal** the host posts (or set `GPU_SWARM_SCHEDULER_URL` to the public `/pool-api`). No NVIDIA → wizard finishes on **Utilize-first**.

> **Note:** Until the host publishes EXE **v0.1.1+**, the GitHub Release EXE may be behind `master`. Browser portal + from-source `start-gpu-pool-app.cmd` have the newest Hub / Workspace features.

## 6) Coding agents (optional)

Only if you use CLI/SDK yourself. The installer does **not** require this for normal join.

```bat
set GPU_SWARM_SCHEDULER_URL=https://rational-delicious-bars-examination.trycloudflare.com/pool-api
```

(Replace with the **current** public `/pool-api` from the host if the tunnel restarted.)

Tailscale fallback:

```bat
set GPU_SWARM_SCHEDULER_URL=http://100.85.165.84:8766
```

Common mistake: bare `100.85.165.84` (missing **`:8766`**) or using the portal URL as the scheduler.

## Fixes

| Symptom | Fix |
|---------|-----|
| Black / blank portal | Hard refresh (Ctrl+F5). Ask the host for a **fresh** public link if the tunnel restarted. |
| Incorrect Scheduler URL Environment Variable | Use public `…/pool-api`, or Tailscale with port **8766**. Not the portal URL. |
| Can’t reach from public internet | Ask the host for the current public link, or use Tailscale. |
| No nvidia-smi | Expected on laptop — Utilize or Contribute CPU. |

See also: [`LOGIN.md`](LOGIN.md) · [`DOWNLOAD.md`](DOWNLOAD.md) · [`DISCORD_MEMBER_QUICKSTART.md`](DISCORD_MEMBER_QUICKSTART.md) · [`CONNECTING.md`](CONNECTING.md)
