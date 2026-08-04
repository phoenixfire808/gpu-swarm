# Discord member quickstart

**5-minute start:** [`START_HERE.md`](START_HERE.md) · **Full guide:** [`LOGIN.md`](LOGIN.md)

Short version below is paste-ready for Discord. **Share it — every new machine makes the pool stronger.**

**URL note:** Cloudflare quick-tunnel hostnames **change** when the host restarts `start-public-access.cmd`. Prefer “ask the host for the current public link,” or (on host) read `data/public_endpoints.share.txt`.

```text
**GPU Pool** — add your machine, grow the pool, everyone gets more compute.

Download (Windows): https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe
Start here: https://github.com/phoenixfire808/gpu-swarm/blob/master/START_HERE.md
Repo: https://github.com/phoenixfire808/gpu-swarm

Primary Discord: **Glitch Factor** · Bot: **GPU Pool**
Commands: `/pool` `/workers` `/contribute` `/submit_probe` `/submit_compute` `/job_status`

**Login (invite from a pool member — not public signup)**
• Invite: **glitch-factor** (+ your Discord display name)

**Easiest — public portal (no Tailscale)**
1. Open the **current** public link (ask the host if an old one 404s):
   https://rational-delicious-bars-examination.trycloudflare.com/portal
2. Sign in → Home shows three big buttons:
   • **Share my PC** — offer spare GPU/CPU (VRAM=0 OK)
   • **Use the pool** — run jobs (no NVIDIA needed)
   • **Invite friends** — copy this blurb and grow the network
3. Optional SDK: GPU_SWARM_SCHEDULER_URL=
   https://rational-delicious-bars-examination.trycloudflare.com/pool-api

**Windows EXE** — download → SmartScreen → More info → Run anyway → wizard installs what you need → invite → Share / Use / Invite
**Tailscale (optional):** http://100.85.165.84:8767/portal
**Laptop / no NVIDIA?** Use the pool or Share CPU only.

Leave anytime. Invite required. Never share .env / bot tokens.
```

## Laptop / no NVIDIA (friends)

| Point | Detail |
|-------|--------|
| Public first | Ask the host for current `…trycloudflare.com/portal` — **no Tailscale needed** while the tunnel is up |
| Use the pool | Login → **Use the pool** → jobs run on pool GPUs (online contributors) |
| Optional Share | CPU/RAM/disk only; VRAM=0. CUDA probes need an NVIDIA worker online |
| Tailscale | Optional fallback: `http://100.85.165.84:8767/portal` |

Invite: **`glitch-factor`**. See [`START_HERE.md`](START_HERE.md) · [`LOGIN.md`](LOGIN.md) · [`DOWNLOAD.md`](DOWNLOAD.md).

## Host (operator) — publish a public link

```bat
cd C:\Users\Drew\Projects\gpu-swarm
start-scheduler-lan.cmd
start-portal.cmd
start-public-access.cmd
```

DM friends the portal line from `data\public_endpoints.share.txt` (gitignored; URL rotates on tunnel restart).  
Auth keys (names only — see `.env.example`): `GPU_SWARM_INVITE_CODES`, `GPU_SWARM_POOL_PASSWORD`.
