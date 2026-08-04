# Friend laptop quickstart (aariff01 & crew)

For friends on a **laptop without an NVIDIA GPU**. You can still use the pool.

## 1) Get on the network

**Preferred (no Tailscale):** ask Drew for the **public portal HTTPS link** (when he runs `start-public-access.cmd`).

**Or Tailscale:** install [Tailscale](https://tailscale.com/download), join Drew’s Glitch Factor tailnet.

## 2) Open the portal (full URL with port)

| Path | URL |
|------|-----|
| Public (when tunnel is up) | `https://….trycloudflare.com/portal` (Drew DMs the real link) |
| Tailscale | `http://100.85.165.84:8767/portal` |
| Drew’s PC only | `http://127.0.0.1:8767/portal` |

Must include **`:8767`** and `/portal`. Bare IP without port fails.

## 3) Login

- Invite: **`glitch-factor`**
- Display name: your Discord name (e.g. `aariff01`)

## 4) What to do (no GPU)

1. **Utilize** (recommended) — submit `probe` / CUDA jobs; they run on Drew’s workers.
2. Optional **Contribute CPU** — register with VRAM=0; worker advertises CPU/RAM/disk with `gpu_available=false` and skips GPU jobs.

Banner on the portal: *No NVIDIA? You can still Utilize the pool or contribute CPU.*

## 5) Or use the Windows EXE (installer)

1. Download latest `GPUPool.exe` from [Releases](https://github.com/phoenixfire808/gpu-swarm/releases/latest)
2. Run wizard — it **auto-detects** the scheduler:
   - `data/public_endpoints.json` / public `/pool-api` if present
   - Tailscale `http://100.85.165.84:8766` if reachable
   - localhost
3. No NVIDIA → wizard finishes on **Utilize-first** (you do **not** need to hand-edit env vars)

## 6) Coding agents (optional)

Only if you use CLI/SDK yourself. The installer does **not** require this for normal join.

```bat
set GPU_SWARM_SCHEDULER_URL=http://100.85.165.84:8766
```

Public tunnel friends (when live):

```bat
set GPU_SWARM_SCHEDULER_URL=https://YOUR-TUNNEL.trycloudflare.com/pool-api
```

Common mistake: bare `100.85.165.84` (missing **`:8766`**) or using the portal URL (`:8767`) as the scheduler.

## Fixes

| Symptom | Fix |
|---------|-----|
| Black / blank portal | Hard refresh (Ctrl+F5). Latest portal has no Google Fonts `@import`. Use full `:8767/portal` URL. |
| Incorrect Scheduler URL Environment Variable | Include port **8766**, or use public `…/pool-api`. Not the portal URL. |
| Can’t reach from public internet | Normal unless Drew’s public tunnel is on — use that link or Tailscale. |
| No nvidia-smi | Expected on laptop — Utilize or Contribute CPU. |

See also: [`DOWNLOAD.md`](DOWNLOAD.md) · [`DISCORD_MEMBER_QUICKSTART.md`](DISCORD_MEMBER_QUICKSTART.md) · [`CONNECTING.md`](CONNECTING.md)
