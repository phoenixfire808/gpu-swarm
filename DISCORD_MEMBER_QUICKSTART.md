# Discord member quickstart (paste-ready)

Copy everything inside the fence below into Discord.

**URL note:** Cloudflare quick-tunnel hostnames **change** when Drew restarts `start-public-access.cmd`. Prefer “ask Drew for the current public link,” or (on host) read `data/public_endpoints.share.txt`. The URL below is the one live at last doc update — verify before pasting if unsure.

```text
**GPU Pool** — contribute GPUs/CPUs or utilize the pool

Primary Discord: **Glitch Factor**
Bot: **GPU Pool**
Commands: `/pool` `/workers` `/contribute` `/submit_probe` `/submit_compute` `/job_status`
Repo: https://github.com/phoenixfire808/gpu-swarm
EXE: https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe

**Easiest — public portal (no Tailscale)**
1. Open (current public link — ask Drew if this 404s):
   https://rational-delicious-bars-examination.trycloudflare.com/portal
2. Sign in: invite **glitch-factor** + your Discord display name
3. **Utilize** allowlisted jobs — or **Contribute** (GPU or CPU-only / VRAM=0)
4. Optional SDK/CLI: GPU_SWARM_SCHEDULER_URL=
   https://rational-delicious-bars-examination.trycloudflare.com/pool-api
   (same host; /pool-api proxies the scheduler)
Full notes: DOWNLOAD.md · FRIEND_LAPTOP.md

**Windows EXE**
1. Download GPUPool.exe:
   https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe
2. Run wizard → invite **glitch-factor** → set caps (VRAM=0 OK for no-GPU)
3. Prefer public pool-api URL if Drew shared one; Tailscale optional
4. If install fails: wizard → Copy log / Submit diagnostics
5. Discord: `/pool` `/workers`

**Tailscale (optional private path)**
Portal: http://100.85.165.84:8767/portal
Scheduler: http://100.85.165.84:8766

**Laptop / no NVIDIA?** Still useful — Utilize on the public portal, or Contribute CPU only.

Leave anytime. Invite required. Allowlisted jobs only. Never share .env / bot tokens.
```

## Laptop / no NVIDIA (friends)

| Point | Detail |
|-------|--------|
| Public first | Ask Drew for current `…trycloudflare.com/portal` — **no Tailscale needed** while the tunnel is up |
| Utilize | Login → **Utilize** → jobs run on pool GPUs (e.g. Drew’s) |
| Optional Contribute | CPU/RAM/disk only; VRAM=0. CUDA probes need an NVIDIA worker online |
| Tailscale | Optional fallback: `http://100.85.165.84:8767/portal` |

Invite: **`glitch-factor`**. See also [`DOWNLOAD.md`](DOWNLOAD.md).

## Host (Drew) — publish a public link

```bat
cd C:\Users\Drew\Projects\gpu-swarm
start-scheduler-lan.cmd
start-portal.cmd
start-public-access.cmd
```

DM friends the portal line from `data\public_endpoints.share.txt` (gitignored; URL rotates on tunnel restart).
