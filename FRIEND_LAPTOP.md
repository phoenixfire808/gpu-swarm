# Friend laptop quickstart (aariff01 & crew)

For friends on a **laptop without an NVIDIA GPU**. You can still use the pool.

## 1) Get on the network

**Preferred (no Tailscale):** ask Drew for the **current public portal HTTPS link**.

Quick tunnels rotate when Drew restarts `start-public-access.cmd` — do not reuse an old trycloudflare.com URL from chat. On Drew’s PC the live link is also in `data/public_endpoints.share.txt`.

**Or Tailscale:** install [Tailscale](https://tailscale.com/download), join Drew’s Glitch Factor tailnet.

## 2) Open the portal (full URL)

| Path | URL |
|------|-----|
| Public (when tunnel is up) | **Ask Drew for current link** — example live now: `https://rational-delicious-bars-examination.trycloudflare.com/portal` |
| Tailscale | `http://100.85.165.84:8767/portal` |
| Drew’s PC only | `http://127.0.0.1:8767/portal` |

Public links are `https://….trycloudflare.com/portal` (no `:8767`). Tailscale/LAN must include **`:8767`** and `/portal`.

## 3) Login

- Invite: **`glitch-factor`**
- Display name: your Discord name (e.g. `aariff01`)

## 4) What to do (no GPU)

1. **Utilize** (recommended) — submit `probe` / CUDA jobs; they run on Drew’s workers.
2. Optional **Contribute CPU** — register with VRAM=0; worker advertises CPU/RAM/disk with `gpu_available=false` and skips GPU jobs.

Banner on the portal: *No NVIDIA? You can still Utilize the pool or contribute CPU.*

## 5) Or use the Windows EXE (installer)

1. Download latest `GPUPool.exe` from [Releases](https://github.com/phoenixfire808/gpu-swarm/releases/latest)
2. Run wizard — it **auto-detects** the scheduler when `data/public_endpoints.json` is present on that machine (host writes it):
   - **First:** public `/pool-api` from `data/public_endpoints.json`
   - Then Tailscale `http://100.85.165.84:8766` if reachable
   - Then localhost
3. Friends joining remotely: open the **public portal** Drew posts (or set `GPU_SWARM_SCHEDULER_URL` to the public `/pool-api`). No NVIDIA → wizard finishes on **Utilize-first**.

## 6) Coding agents (optional)

Only if you use CLI/SDK yourself. The installer does **not** require this for normal join.

```bat
set GPU_SWARM_SCHEDULER_URL=https://rational-delicious-bars-examination.trycloudflare.com/pool-api
```

(Replace with the **current** public `/pool-api` from Drew if the tunnel restarted.)

Tailscale fallback:

```bat
set GPU_SWARM_SCHEDULER_URL=http://100.85.165.84:8766
```

Common mistake: bare `100.85.165.84` (missing **`:8766`**) or using the portal URL as the scheduler.

## Fixes

| Symptom | Fix |
|---------|-----|
| Black / blank portal | Hard refresh (Ctrl+F5). Ask Drew for a **fresh** public link if the tunnel restarted. |
| Incorrect Scheduler URL Environment Variable | Use public `…/pool-api`, or Tailscale with port **8766**. Not the portal URL. |
| Can’t reach from public internet | Ask Drew for the current public link, or use Tailscale. |
| No nvidia-smi | Expected on laptop — Utilize or Contribute CPU. |

See also: [`DOWNLOAD.md`](DOWNLOAD.md) · [`DISCORD_MEMBER_QUICKSTART.md`](DISCORD_MEMBER_QUICKSTART.md) · [`CONNECTING.md`](CONNECTING.md)
