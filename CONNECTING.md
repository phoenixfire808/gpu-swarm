# Connecting to GPU Pool

One page: **Contribute** vs **Utilize** vs **Connect from code**.

After portal login (`/portal`), the **Home** view shows the same three paths as big sections — Contribute · Utilize · Connect (how-to with URLs, Discord commands, CLI/SDK).

Primary Discord: **Glitch Factor** · Bot: **GPU Pool**

| Service | Local (host) | Tailscale (members) |
|---------|--------------|---------------------|
| Scheduler | `http://127.0.0.1:8766` | `http://100.85.165.84:8766` |
| Portal | `http://127.0.0.1:8767/portal` | `http://100.85.165.84:8767/portal` |

---

## 1) Contribute (plug in your PC)

You advertise GPU/CPU/RAM/disk and run allowlisted jobs for the pool.

| Path | How |
|------|-----|
| **Portal** (easiest) | Open `/portal` → invite code + display name → set caps → start worker |
| **Desktop app** | `start-gpu-pool-app.cmd` → wizard → **Save + Join** |
| **CLI** | `python -m gpu_swarm worker --name YourName --discord-user YourName` |
| **Discord** | `/contribute` for instructions; `/workers` to confirm you’re online |

Leave anytime (portal/app Leave, or stop the worker). Caps are soft ads for scheduling — not a shared NAS.

---

## 2) Utilize (run a job on the pool)

You submit an **allowlisted** job; a worker leases it and returns JSON.

| Path | How |
|------|-----|
| **Discord** | `/submit_probe` · `/submit_compute` · `/job_status <id>` |
| **Portal** | Utilize panel (same allowlist) |
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
| **HTTP** | `POST /jobs` · `GET /jobs/{id}` · `GET /status` (also `/v1/pool/*` wrappers when scheduler restarted) |
| **Local models** | Keep Ollama/LM Studio local; pool for probe/CUDA — [`examples/ollama_or_local_offload.md`](examples/ollama_or_local_offload.md) |
| **Hermes notes** | [`examples/hermes_pool_skill.md`](examples/hermes_pool_skill.md) |

**Under 5 lines of Python**

```python
from gpu_swarm.client import GPUPool
pool = GPUPool()  # or GPUPool("http://127.0.0.1:8766")
print(pool.status()["workers_online"])
print(pool.submit_probe(wait=True)["status"])
```

Env: `GPU_SWARM_SCHEDULER_URL` — local host scripts often use `http://127.0.0.1:8766`; SDK default for remote utilizers is `http://100.85.165.84:8766`.
---

## Discord (status + submit)

`/pool` `/workers` `/contribute` `/submit_probe` `/submit_compute` `/job_status`

Paste-ready member blurb: [`DISCORD_MEMBER_QUICKSTART.md`](DISCORD_MEMBER_QUICKSTART.md).

---

## How friends connect

1. Install Tailscale — https://tailscale.com/download  
2. Ask Drew for an invite to the Glitch Factor tailnet (login + join)  
3. Open portal `http://100.85.165.84:8767/portal` or run the GPU Pool EXE / desktop app  
4. Sign in with invite code `glitch-factor` + your display name  
5. Contribute (join as worker) or Utilize (run allowlisted jobs)

---

## Rules of the road

- Private Tailscale/LAN pool — not exposed to the open internet. Friends join via Tailscale, then use the URLs above (do not put `:8766` / `:8767` on the open WAN without an auth gateway).
- Allowlisted jobs only — no remote shell on contributors.
- Never share `.env` or Discord bot tokens.
- No Docker for this stack (VirtualBox/Vagrant elsewhere; workers are bare metal / host Python).
