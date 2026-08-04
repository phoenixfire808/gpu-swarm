# Download GPU Pool (Windows EXE)

Get the Windows desktop joiner from GitHub Releases — no Python install required for the common path.

**Repo:** https://github.com/phoenixfire808/gpu-swarm  
**Releases:** https://github.com/phoenixfire808/gpu-swarm/releases  

### Download GPU Pool for Windows

| | URL |
|--|-----|
| **Latest EXE** | https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe |
| **v0.1.0 (pinned)** | https://github.com/phoenixfire808/gpu-swarm/releases/download/v0.1.0/GPUPool.exe |
| **Release page** | https://github.com/phoenixfire808/gpu-swarm/releases/tag/v0.1.0 |

Asset name: **`GPUPool.exe`** (~29 MB onefile). Includes Contribute / Utilize / Connect, portable Python bootstrap, and Copy log / Submit diagnostics.

---

## Friend path (pick one)

| Path | Tailscale? | How |
|------|------------|-----|
| **Public portal URL** (preferred) | **No** | Open Drew’s current `https://….trycloudflare.com/portal` → invite **`glitch-factor`** + display name → Utilize (or Contribute CPU) |
| **Installer / EXE** | Optional | Download EXE → wizard auto-detects `data/public_endpoints.json` → public `/pool-api` when present; else Tailscale |
| **Tailscale** (optional private path) | Yes | Join Drew’s tailnet → `http://100.85.165.84:8767/portal` |

Drew starts public access on the host with `start-public-access.cmd` (Cloudflare quick tunnel → portal `:8767`; `/pool-api` proxies the scheduler so **one** public URL works). Invite-code auth stays on.

**URL rotates** when the tunnel restarts — ask Drew for the current public link, or (on Drew’s PC) read `data/public_endpoints.share.txt`. Do not rely on an old trycloudflare.com hostname from chat history.

---

## Prerequisites

1. **Access** — either Drew’s **public portal URL** (no Tailscale) **or** Tailscale on Drew’s private network (ask in Discord).
2. **Invite code** — `glitch-factor` (Glitch Factor Discord). Use it with your display name at portal login / app join.
3. **NVIDIA drivers** — only if you want to **Contribute a GPU**. Install current Game Ready / Studio drivers so `nvidia-smi` works. **No GPU?** Skip this — use Utilize (and optional CPU contribute) below.

---

## Laptop / no NVIDIA GPU

Friends on MacBooks, Intel/AMD laptops, or any PC without NVIDIA are still welcome.

| Do this | Details |
|---------|---------|
| Open the link Drew DMs | Prefer the **current** public `…trycloudflare.com/portal` URL — **no Tailscale needed** while the tunnel is up |
| Or Tailscale (optional) | Portal: `http://100.85.165.84:8767/portal` · Scheduler: `http://100.85.165.84:8766` |
| Utilize the pool | Browser → invite **`glitch-factor`** + display name → **Utilize** → allowlisted jobs (`probe`, etc.). Jobs run on whoever has GPUs online |
| Optional: Contribute CPU | Register machine with CPU/RAM/disk caps; leave GPU/VRAM at **0**. Helps non-CUDA work when the job allows it. CUDA probes still need an NVIDIA worker |
| Discord | `/pool` · `/submit_probe` · `/job_status` (Glitch Factor · bot **GPU Pool**) |

### Common mistakes

| Symptom | Fix |
|---------|-----|
| Page won’t load | Try Drew’s **public** portal URL first; or confirm Tailscale is up and use full `:8767` / `:8766` URLs |
| CLI / script can’t connect | Public: `GPU_SWARM_SCHEDULER_URL=https://….trycloudflare.com/pool-api` · Tailscale: `http://100.85.165.84:8766` |
| Black / blank portal screen | Hard refresh (**Ctrl+F5**), reopen the latest portal URL Drew posted |
| Tunnel URL expired | Quick tunnels rotate when Drew restarts `start-public-access.cmd` — ask for a fresh link |

Paste-ready Discord blurb (includes no-GPU path): [`DISCORD_MEMBER_QUICKSTART.md`](DISCORD_MEMBER_QUICKSTART.md).

---

## Install & join (EXE)

1. Open [Releases](https://github.com/phoenixfire808/gpu-swarm/releases) → download the Windows EXE from the latest release.
2. Run the EXE (Windows SmartScreen may warn on unsigned builds — “More info” → Run anyway if you trust Drew’s release).
3. Prefer the **public portal / pool-api** URLs Drew shared. Tailscale is optional.
4. In the wizard:
   - **Python & Deps** — if system Python is missing/broken, click **Bootstrap portable Python** (isolated under `%LOCALAPPDATA%\GPUPool\`, never global site-packages). GPUPool.exe also bootstraps in the background on first run when needed.
   - Scheduler defaults: public `/pool-api` when available, else Tailscale host (`100.85.165.84`).
   - Sign in with invite code **`glitch-factor`** + your Discord display name.
   - Set caps for GPU VRAM, CPU, RAM, and disk (**VRAM=0** is fine for CPU-only).
   - **Save + Join** so the worker heartbeats into the pool.
5. In Discord (**Glitch Factor**): `/pool` and `/workers` — your machine should appear.

Leave anytime from the app (**Leave**) or by quitting the EXE.

### If install / join fails — report to Drew

1. Wizard → **Copy log** or **Submit diagnostics** (Python & Deps or Join step).
2. **Submit** POSTs a redacted log to portal `/api/diagnostics` (invite session or invite code).
3. If portal is down, **Copy log** → paste to Drew in Discord.
4. On disk: `%LOCALAPPDATA%\GPUPool\logs\error-*.log`

Tokens/passwords are redacted before copy/submit.

---

## URLs (Drew host)

| What | URL |
|------|-----|
| **Public portal** (live example — may change) | `https://rational-delicious-bars-examination.trycloudflare.com/portal` |
| **Public pool API** | `https://rational-delicious-bars-examination.trycloudflare.com/pool-api` (proxies scheduler) |
| **Canonical source** | Ask Drew, or read `data/public_endpoints.share.txt` / `data/public_endpoints.json` on the host (gitignored) |
| Contributor portal (Tailscale) | `http://100.85.165.84:8767/portal` |
| Scheduler API (Tailscale) | `http://100.85.165.84:8766` |

Shape reference (no live URL): [`public_endpoints.example.json`](public_endpoints.example.json).

### Drew: start public access

```bat
cd C:\Users\Drew\Projects\gpu-swarm
start-scheduler-lan.cmd
start-portal.cmd
start-public-access.cmd
```

Share the printed portal URL + invite `glitch-factor`. Files (gitignored): `data/public_endpoints.json`, `data/public_endpoints.share.txt`.

**Fallback if cloudflared fails:** [ngrok](https://ngrok.com/download) `ngrok http 8767`, then write the https URL into `data/public_endpoints.json` (`portal_public_url`) or re-run after fixing cloudflared.

---

## Fallbacks (power users)

| Path | How |
|------|-----|
| **Browser portal** | Public URL or Tailscale → invite + name → Utilize / register machine |
| **From source** | Clone repo → `start-gpu-pool-app.cmd` (needs Python) |
| **CLI** | `python -m gpu_swarm worker --name YourName --discord-user YourName` |

Paste-ready Discord blurb: [`DISCORD_MEMBER_QUICKSTART.md`](DISCORD_MEMBER_QUICKSTART.md).  
Contribute / Utilize / code: [`CONNECTING.md`](CONNECTING.md).

---

## Supported install matrix (Windows)

| Component | Supported | Notes |
|-----------|-----------|-------|
| OS | Windows 10/11 x64 | No Docker |
| **GPUPool.exe** | Any supported Windows | No Python required for Contribute/Utilize UI + worker |
| **From source / wizard pip** | CPython **3.10 – 3.12** (prefer **3.12**) | Isolated venv: `%LOCALAPPDATA%\GPUPool\venv` |
| Portable bootstrap | CPython **3.12.x** (NuGet) | `%LOCALAPPDATA%\GPUPool\python` when system Python is missing/broken |
| Python **3.13** | Optional / fragile | Not selected by default; torch/CUDA wheels often lag |
| Joiner deps | `requirements-joiner.txt` | No torch, no Discord — Contribute/Utilize |
| Full host stack | `requirements.txt` | Scheduler + portal + Discord bot |
| Optional CUDA torch | `requirements-cuda.txt` | `scripts/install_joiner_deps.ps1 -WithTorchCuda` (cu128 index) |

**Friend install (recommended):** EXE → wizard → Bootstrap portable Python if prompted → invite `glitch-factor`.

**From source:**

```bat
scripts\install_joiner_deps.cmd
"%LOCALAPPDATA%\GPUPool\venv\Scripts\python.exe" -m gpu_swarm.app
```

Optional GPU contributor torch (large):

```bat
scripts\install_joiner_deps.cmd --with-torch-cuda
```

---

## Rules

- Invite code required on the portal (public or Tailscale). Do not disable auth for public mode.
- Allowlisted jobs only (`probe`, `pytorch_cuda_probe` in v1).
- Never share `.env` or Discord bot tokens — invite code in Discord is fine; tokens are not.
- No Docker for this stack.
