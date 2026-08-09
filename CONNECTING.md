# Connecting to GPU Pool

One page: **Contribute** vs **Utilize** vs **Connect from code**.

After portal login (`/portal`), the **Home** view shows the same three paths as big sections — Contribute · Utilize · Connect (how-to with URLs, Discord commands, CLI/SDK).

Primary Discord: **Glitch Factor** · Bot: **GPU Pool**

| Service | Local (host) | Public (when tunnel on) | Tailscale (optional) |
|---------|--------------|-------------------------|----------------------|
| Portal | `http://127.0.0.1:8767/portal` | `https://….trycloudflare.com/portal` | `http://100.85.165.84:8767/portal` |
| Scheduler / pool API | `http://127.0.0.1:8766` | `https://….trycloudflare.com/pool-api` | `http://100.85.165.84:8766` |

The host enables public URLs with `start-public-access.cmd` or the installer wizard's **Publish temporary HTTPS link** button. This uses a Cloudflare Quick Tunnel with no account. For a stable hostname, the host can use `scripts\setup_cloudflare_named.cmd -Hostname gpu-pool.example.com -TunnelName gpu-pool -Launch` after selecting a Cloudflare-managed domain. One public hostname serves the portal; `/pool-api` proxies the scheduler.

---

## 1) Contribute (plug in your PC)

You advertise GPU/CPU/RAM/disk and run allowlisted jobs for the pool.

| Path | How |
|------|-----|
| **Portal** (easiest) | Open public or Tailscale `/portal` → invite + display name → set **your** caps → start worker |
| **Desktop app** | `start-gpu-pool-app.cmd` → wizard → set caps → **Save + Join** (saved in `data/joiner_settings.json`) |
| **CLI** | `python -m gpu_swarm worker --name YourName --discord-user YourName` (+ env/CLI caps) |
| **Discord** | `/contribute` for instructions; `/workers` to confirm you’re online |
| **CPU-only / no NVIDIA** | Leave VRAM at 0; advertise CPU/RAM/disk. Still useful for non-CUDA work |

Leave anytime (portal/app Leave, or stop the worker). Caps are soft ads for scheduling — not a shared NAS.

**Personal offer control:** Only **you** control how much of your PC is offered (VRAM/CPU/RAM/disk). Change anytime on your machine or in your Contribute settings. The worker process is the source of truth; the scheduler stores what your worker heartbeats. Pool admins cannot remotely raise another contributor’s offer via Discord or an admin API.

**Host GPU safety (default ON):** The worker clamps advertised VRAM to ~55% of total, pauses new leases when live `nvidia-smi` util is ≥65% or free VRAM is below ~1.5 GiB, and caps heavy CUDA probe matrix sizes. You can raise your offer sliders; the safety ceiling still protects the desktop. Toggle in Contribute UI / `joiner_settings.json` (`host_protect`) or env `GPU_SWARM_HOST_PROTECT=0` (not recommended on a gaming PC).

---

## 2) Utilize (run a job on the pool)

You submit an **allowlisted** job; a worker leases it and returns JSON.

| Path | How |
|------|-----|
| **Discord** | `/submit_probe` · `/submit_compute` · `/job_status <id>` |
| **Portal** | Utilize panel (same allowlist) — works on the **public** URL with no Tailscale |
| **Desktop app** | Utilize / job catalog |
| **CLI (coders)** | `python -m gpu_swarm utilize status` · `utilize probe --wait` · `utilize cuda --wait` |
| **CLI (generic)** | `python -m gpu_swarm submit probe --wait` |

**v1 jobs:** `probe`, `pytorch_cuda_probe` only. No arbitrary shell.

---

## 3) Connect from code / coding agents / local models

| Path | How |
|------|-----|
| **Python SDK** | `from gpu_swarm.client import GPUPool` → `status()` / `submit()` / `wait()` (POST `/jobs`, GET `/status`) |
| **Agent script** | [`examples/coding_agent_pool.py`](examples/coding_agent_pool.py) — stdlib HTTP, same scheduler paths |
| **SDK example** | [`examples/use_pool_from_script.py`](examples/use_pool_from_script.py) |
| **HTTP** | `POST /jobs` · `GET /jobs/{id}` · `GET /status` (public: prefix with `/pool-api`) |
| **Local models** | Keep Ollama/LM Studio local; pool for probe/CUDA — [`examples/ollama_or_local_offload.md`](examples/ollama_or_local_offload.md) |
| **Hermes notes** | [`examples/hermes_pool_skill.md`](examples/hermes_pool_skill.md) |

**Under 5 lines of Python**

```python
from gpu_swarm.client import GPUPool
pool = GPUPool()  # or GPUPool("https://….trycloudflare.com/pool-api")
print(pool.status()["workers_online"])
print(pool.submit_probe(wait=True)["status"])
```

Env: `GPU_SWARM_SCHEDULER_URL` — public friends use `…/pool-api`; host scripts often use `http://127.0.0.1:8766`; Tailscale default `http://100.85.165.84:8766`.

### Workspace VM (host — one product)

Desktop app **Home → Workspace** (or Connect → Workspace card) opens the Hermes agent Ubuntu VM with **CPU/RAM clamped to your Contribute share** (+ `host_protect`). Real GPU/VRAM stays on the **host worker** — VirtualBox does not pass through NVIDIA. Details: [`ADVANCED_VM.md`](ADVANCED_VM.md).

---

## Discord (status + submit)

`/pool` `/workers` `/contribute` `/submit_probe` `/submit_compute` `/job_status`

Login walkthrough: [`LOGIN.md`](LOGIN.md).  
Paste-ready member blurb: [`DISCORD_MEMBER_QUICKSTART.md`](DISCORD_MEMBER_QUICKSTART.md).

---

## How friends connect

1. **Preferred:** open the public portal URL a pool admin shares (`https://….trycloudflare.com/portal`) — **no Tailscale needed**
2. Or install Tailscale and join the Glitch Factor tailnet
3. Sign in with invite code `glitch-factor` + your display name
4. Contribute (GPU or CPU-only) or Utilize (allowlisted jobs)
5. Optional: Windows EXE from GitHub Releases ([`DOWNLOAD.md`](DOWNLOAD.md))

---

## Rules of the road

- Invite code required on the portal (public tunnel does **not** disable auth).
- Allowlisted jobs only — no remote shell on contributors.
- Never share `.env` or Discord bot tokens.
- No Docker for this stack (VirtualBox/Vagrant elsewhere; workers are bare metal / host Python).
- Quick-tunnel URLs change when the host restarts `start-public-access.cmd`.
