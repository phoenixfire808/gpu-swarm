# Download GPU Pool (Windows EXE)

Get the Windows desktop joiner from GitHub Releases — no Python install required for the common path.

**Repo:** https://github.com/phoenixfire808/gpu-swarm  
**Releases:** https://github.com/phoenixfire808/gpu-swarm/releases  
**Latest EXE (placeholder until Worker publishes):**  
https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe  
*(Asset name may be `GPUPool.exe` or `gpu_pool.exe` — use whatever the release lists. Packaging Worker will fill the exact URL.)*

---

## Prerequisites

1. **Tailscale** — join Drew’s private network first (ask in Discord). The scheduler and portal are Tailscale/LAN only — not on the public internet. That is intentional; friends on laptops will not reach the pool from the open internet.
2. **Invite code** — `glitch-factor` (Glitch Factor Discord). Use it with your display name at portal login / app join.
3. **NVIDIA drivers** — only if you want to **Contribute a GPU**. Install current Game Ready / Studio drivers so `nvidia-smi` works. **No GPU?** Skip this — use Utilize (and optional CPU contribute) below.

---

## Laptop / no NVIDIA GPU

Friends on MacBooks, Intel/AMD laptops, or any PC without NVIDIA are still welcome.

| Do this | Details |
|---------|---------|
| Stay on Tailscale | Pool is **private** — not public internet. If the URL fails without Tailscale connected, that is expected. |
| Use full URLs with ports | Portal: `http://100.85.165.84:8767/portal` · Scheduler API: `http://100.85.165.84:8766` |
| Utilize the pool | Browser portal → invite **`glitch-factor`** + display name → **Utilize** → submit allowlisted jobs (`probe`, etc.). Jobs run on whoever has GPUs online. |
| Optional: Contribute CPU | Register machine with CPU/RAM/disk caps; leave GPU/VRAM at **0**. You help with non-CUDA work when the job allows it. CUDA probes still need an NVIDIA worker. |
| Discord | `/pool` · `/submit_probe` · `/job_status` (Glitch Factor · bot **GPU Pool**) |

### Common mistakes

| Symptom | Fix |
|---------|-----|
| Page won’t load / “can’t reach” | Confirm Tailscale is up; use the **full** Tailscale URL with **`:8767`** (portal) or **`:8766`** (scheduler). Bare host or missing port fails. |
| CLI / script can’t connect | Set `GPU_SWARM_SCHEDULER_URL=http://100.85.165.84:8766` — scheduler port **8766**, not the portal URL. |
| Black / blank portal screen | Hard refresh (**Ctrl+F5**), reopen `http://100.85.165.84:8767/portal`, or ask Drew if the portal was just updated. |
| Expected public link | There isn’t one. Tailscale-private is normal for v1. |

Paste-ready Discord blurb (includes no-GPU path): [`DISCORD_MEMBER_QUICKSTART.md`](DISCORD_MEMBER_QUICKSTART.md).

---

## Install & join (EXE)

1. Open [Releases](https://github.com/phoenixfire808/gpu-swarm/releases) → download the Windows EXE from the latest release.
2. Run the EXE (Windows SmartScreen may warn on unsigned builds — “More info” → Run anyway if you trust Drew’s release).
3. Confirm you are on Tailscale (`tailscale status` or the Tailscale tray icon).
4. In the wizard:
   - Scheduler / portal defaults should point at Drew’s Tailscale host (`100.85.165.84`).
   - Sign in with invite code **`glitch-factor`** + your Discord display name.
   - Set caps for GPU VRAM, CPU, RAM, and disk.
   - **Save + Join** so the worker heartbeats into the pool.
5. In Discord (**Glitch Factor**): `/pool` and `/workers` — your machine should appear.

Leave anytime from the app (**Leave**) or by quitting the EXE.

---

## URLs (Drew host)

| What | URL |
|------|-----|
| Contributor portal | `http://100.85.165.84:8767/portal` |
| Scheduler API | `http://100.85.165.84:8766` |

If Tailscale IP changes, Drew posts the new URLs in Discord.

---

## Fallbacks (no EXE yet / power users)

| Path | How |
|------|-----|
| **Browser portal** | Tailscale → open portal URL → invite + name → register machine |
| **From source** | Clone repo → `start-gpu-pool-app.cmd` (needs Python) |
| **CLI** | `python -m gpu_swarm worker --name YourName --discord-user YourName` |

Paste-ready Discord blurb: [`DISCORD_MEMBER_QUICKSTART.md`](DISCORD_MEMBER_QUICKSTART.md).  
Contribute / Utilize / code: [`CONNECTING.md`](CONNECTING.md).

---

## Rules

- Private Tailscale/LAN only — do **not** expose `:8766` / `:8767` to the public internet.
- Allowlisted jobs only (`probe`, `pytorch_cuda_probe` in v1).
- Never share `.env` or Discord bot tokens — invite code in Discord is fine; tokens are not.
