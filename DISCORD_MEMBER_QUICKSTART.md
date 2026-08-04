# Discord member quickstart

**Full login guide (step-by-step, troubleshooting, host notes):** [`LOGIN.md`](LOGIN.md)

Short version below is paste-ready for Discord.

**URL note:** Cloudflare quick-tunnel hostnames **change** when the host restarts `start-public-access.cmd`. Prefer “ask the host for the current public link,” or (on host) read `data/public_endpoints.share.txt`. The URL below is the one live at last doc update — verify before pasting if unsure.

```text
**GPU Pool** — Join · Share my PC · Use the pool · Invite others

Login guide: https://github.com/phoenixfire808/gpu-swarm/blob/master/LOGIN.md
Download: https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe
Repo: https://github.com/phoenixfire808/gpu-swarm

Primary Discord: **Glitch Factor** · Bot: **GPU Pool**
Commands: `/pool` `/workers` `/contribute` `/submit_probe` `/submit_compute` `/job_status`

**Login (invite from a pool member — not public signup)**
• Invite: **glitch-factor** (+ your Discord display name)
• Pool password: optional (only if a pool admin shares it)

**Easiest — public portal (no Tailscale)**
1. Open (current public link — ask the host if this 404s):
   https://rational-delicious-bars-examination.trycloudflare.com/portal
2. Sign in: invite **glitch-factor** + your Discord display name
3. Pick: **Use the pool** · **Share my PC** (VRAM=0 OK) · **Invite others** (copy blurb)
4. Optional SDK: GPU_SWARM_SCHEDULER_URL=
   https://rational-delicious-bars-examination.trycloudflare.com/pool-api

**Windows EXE** — download → wizard → invite → Share / Use / Invite
**Tailscale (optional):** http://100.85.165.84:8767/portal
**Laptop / no NVIDIA?** Use the pool or Contribute CPU only.

Leave anytime. Invite required. Never share .env / bot tokens.
```

## Laptop / no NVIDIA (friends)

| Point | Detail |
|-------|--------|
| Public first | Ask the host for current `…trycloudflare.com/portal` — **no Tailscale needed** while the tunnel is up |
| Utilize | Login → **Utilize** → jobs run on pool GPUs (online contributors) |
| Optional Contribute | CPU/RAM/disk only; VRAM=0. CUDA probes need an NVIDIA worker online |
| Tailscale | Optional fallback: `http://100.85.165.84:8767/portal` |

Invite: **`glitch-factor`**. See [`LOGIN.md`](LOGIN.md) · [`DOWNLOAD.md`](DOWNLOAD.md).

## Host (operator) — publish a public link

```bat
cd C:\Users\Drew\Projects\gpu-swarm
start-scheduler-lan.cmd
start-portal.cmd
start-public-access.cmd
```

DM friends the portal line from `data\public_endpoints.share.txt` (gitignored; URL rotates on tunnel restart).  
Auth keys (names only — see `.env.example`): `GPU_SWARM_INVITE_CODES`, `GPU_SWARM_POOL_PASSWORD`.
