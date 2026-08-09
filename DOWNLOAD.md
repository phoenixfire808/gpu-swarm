# Download GPU Pool (Windows EXE)

**Start in 5 minutes:** [`START_HERE.md`](START_HERE.md) · **Login walkthrough:** [`LOGIN.md`](LOGIN.md)

Get the Windows desktop joiner from GitHub Releases — **no Python install required**. The wizard installs what you need automatically (progress stays on screen).

**Repo:** https://github.com/phoenixfire808/gpu-swarm  
**Releases:** https://github.com/phoenixfire808/gpu-swarm/releases  

### What GPU Pool is for (why join)

A **private co-op** for friends — share spare GPU/CPU, run jobs on whoever is online, chat, suggest improvements, and **invite friends so everyone gets more compute**. Not a public marketplace. Not Docker.

| Mode | What it does | Who it’s for |
|------|--------------|--------------|
| **Join** | Sign in with invite + display name | Everyone |
| **Share my PC** | Contribute spare GPU/CPU with **your** caps; host GPU safety ON by default | Anyone with spare compute (VRAM=0 = CPU-only) |
| **Use the pool** | Utilize jobs on online workers | Everyone — **no NVIDIA required** on your laptop |
| **Invite friends** | Copy portal URL + invite blurb + GitHub download → paste in Discord | **Everyone — grow the network** |
| **Connect / Workspace** | URLs, local model endpoint, optional Linux VM | Coders / power users — **CPU/RAM only** in VMs |
| **Chat / Suggest** | Pool chat + improvement inbox | Everyone (web Network Hub) |

### Download GPU Pool for Windows

| | URL |
|--|-----|
| **Latest EXE (v0.1.1+)** | https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe |
| **v0.1.1 (pinned)** | https://github.com/phoenixfire808/gpu-swarm/releases/download/v0.1.1/GPUPool.exe |
| **Release page** | https://github.com/phoenixfire808/gpu-swarm/releases |

Asset name: **`GPUPool.exe`** (~29 MB onefile). Includes hub, Invite friends, host_protect, Workspace bridge, verbose install, Tk UI fix.

---

## Friend path (pick one)

| Path | Tailscale? | How |
|------|------------|-----|
| **Public portal URL** (preferred) | **No** | Open the host’s current `https://….trycloudflare.com/portal` → invite **`glitch-factor`** + display name → Utilize (or Contribute CPU) |
| **From source (ready-to-go tip)** | Optional | `start-gpu-pool-app.cmd` → wizard **Python & Deps** → invite → Contribute/Utilize; optional network tools are separate |
| **Installer / EXE** | Optional | Download EXE → wizard (v0.1.1+ includes prereqs step; **v0.1.0 stale**) → public `/pool-api` when present; else Tailscale |
| **Tailscale** (optional private path) | Yes | Auto via `install-prereqs` or manual install → `http://100.85.165.84:8767/portal` |

**Shared agent development space** (hub + Workspace VM + pool endpoint): [`SHARED_AGENT_DEV.md`](SHARED_AGENT_DEV.md).

the host starts public access on the host with `start-public-access.cmd` (Cloudflare quick tunnel → portal `:8767`; `/pool-api` proxies the scheduler so **one** public URL works). Invite-code auth stays on.

**URL rotates** when the tunnel restarts — ask the host for the current public link, or (on the host PC) read `data/public_endpoints.share.txt`. Do not rely on an old trycloudflare.com hostname from chat history.

---

## Prerequisites

1. **Access** — public portal URL is enough. Tailscale is an optional private-network fallback; `scripts\install-prereqs.cmd` only installs it when you explicitly choose that path. Already-installed tools are skipped.
2. **Invite code** — `glitch-factor` (Glitch Factor Discord). Use it with your display name at portal login / app join.
3. **NVIDIA drivers** — only if you want to **Contribute a GPU**. **No GPU?** Skip — Utilize / CPU contribute still work.
4. **Workspace (optional)** — VirtualBox + Vagrant only when you explicitly run `scripts\install-prereqs.cmd -WorkspaceTools`; UAC once; then Home → Workspace.

---

## What you’ll see during install

Installers and the desktop wizard print **plain step labels** and keep logs on screen (failures are not hidden):

1. **Creating GPUPool folder…** — `%LOCALAPPDATA%\GPUPool\`
2. **Downloading Python runtime…** — percent progress when a portable CPython is needed
3. **Creating isolated Python environment…** — private venv (never global site-packages)
4. **Installing dependencies (1/5)…** — package names stream as pip works
5. **Checking GPU…** — optional; Utilize works without NVIDIA
6. **Setup ready.** / **Connecting to pool…** — after you Save + Join

Install progress stays in the wizard. The EXE does not start downloads before the wizard is ready; portable Python and package installation begin only after you choose Bootstrap.

---

## Laptop / no NVIDIA GPU

Friends on MacBooks, Intel/AMD laptops, or any PC without NVIDIA are still welcome.

| Do this | Details |
|---------|---------|
| Open the link a pool admin shares | Prefer the **current** public `…trycloudflare.com/portal` URL — **no Tailscale needed** while the tunnel is up |
| Or Tailscale (optional) | Portal: `http://100.85.165.84:8767/portal` · Scheduler: `http://100.85.165.84:8766` |
| Utilize the pool | Browser → invite **`glitch-factor`** + display name → **Utilize** → allowlisted jobs (`probe`, etc.). Jobs run on whoever has GPUs online |
| Optional: Contribute CPU | Register machine with CPU/RAM/disk caps; leave GPU/VRAM at **0**. Helps non-CUDA work when the job allows it. CUDA probes still need an NVIDIA worker |
| Discord | `/pool` · `/submit_probe` · `/job_status` (Glitch Factor · bot **GPU Pool**) |

### Common mistakes

| Symptom | Fix |
|---------|-----|
| Page won’t load | Try the host’s **public** portal URL first; or confirm Tailscale is up and use full `:8767` / `:8766` URLs |
| CLI / script can’t connect | Public: `GPU_SWARM_SCHEDULER_URL=https://….trycloudflare.com/pool-api` · Tailscale: `http://100.85.165.84:8766` |
| Black / blank portal screen | Hard refresh (**Ctrl+F5**), reopen the latest portal URL the host posted |
| Tunnel URL expired | Quick tunnels rotate when the host restarts `start-public-access.cmd` — ask for a fresh link |
| SmartScreen blocks EXE | **More info** → **Run anyway** (only if you trust [this repo’s Releases](https://github.com/phoenixfire808/gpu-swarm/releases)) |

Login walkthrough: [`LOGIN.md`](LOGIN.md).  
Paste-ready Discord blurb (includes no-GPU path): [`DISCORD_MEMBER_QUICKSTART.md`](DISCORD_MEMBER_QUICKSTART.md).

---

## Getting started (EXE) — automatic install

1. Download **[GPUPool.exe](https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe)** (or open [Releases](https://github.com/phoenixfire808/gpu-swarm/releases)).
2. Run it. Windows SmartScreen may warn on **unsigned** builds → **More info** → **Run anyway** if you trust this repo’s release.
3. **Choose setup.** The normal friend path needs no Tailscale, VirtualBox, or Vagrant. If the wizard reports missing runtime support, click **Bootstrap portable Python** and leave that one install running. Live step labels and package progress stay on screen
4. Prefer the **public portal / pool-api** URL a pool member shared. Tailscale is optional.
5. Wizard path:
   - **Welcome** — plain-language overview; three big destinations after join
   - **Network & Workspace** — Detect / Install & connect (optional tools)
   - **Python & Deps** — Bootstrap if needed (progress bar + live log)
   - Invite **`glitch-factor`** + Discord display name
   - Caps for GPU VRAM, CPU, RAM, disk (**VRAM=0** = CPU-only). **Host GPU safety** ON by default
   - **Save + Join**
6. Home → **Share my PC** · **Use the pool** · **Invite friends** (grow the network — paste Discord blurb)
7. In Discord (**Glitch Factor**): `/pool` and `/workers` — your machine should appear when contributing

Leave anytime from the app (**Leave**) or by quitting the EXE.

### If install / join fails — report to the host

1. Wizard → **Copy log** or **Submit diagnostics** (Python & Deps or Join step). Keep the log visible — don’t close the window until you’ve copied it.
2. **Submit** POSTs a redacted log to portal `/api/diagnostics` (invite session or invite code).
3. If portal is down, **Copy log** → paste to the host in Discord.
4. On disk: `%LOCALAPPDATA%\GPUPool\logs\error-*.log` · first-run: `first-run-bootstrap.log`

Tokens/passwords are redacted before copy/submit.

---

## URLs (host)

| What | URL |
|------|-----|
| **Public portal** (live example — may change) | `https://rational-delicious-bars-examination.trycloudflare.com/portal` |
| **Public pool API** | `https://rational-delicious-bars-examination.trycloudflare.com/pool-api` (proxies scheduler) |
| **Canonical source** | Ask the host, or read `data/public_endpoints.share.txt` / `data/public_endpoints.json` on the host (gitignored) |
| Contributor portal (Tailscale) | `http://100.85.165.84:8767/portal` |
| Scheduler API (Tailscale) | `http://100.85.165.84:8766` |

Shape reference (no live URL): [`public_endpoints.example.json`](public_endpoints.example.json).

### Host: start public access

```bat
cd C:\Users\Drew\Projects\gpu-swarm
start-scheduler-lan.cmd
start-portal.cmd
start-public-access.cmd
```

Share the printed portal URL + invite `glitch-factor` (or use **Invite others** in the portal / desktop app for a one-click copy blurb). Files (gitignored): `data/public_endpoints.json`, `data/public_endpoints.share.txt`.

**Fallback if cloudflared fails:** [ngrok](https://ngrok.com/download) `ngrok http 8767`, then write the https URL into `data/public_endpoints.json` (`portal_public_url`) or re-run after fixing cloudflared.

---

## Fallbacks (power users)

| Path | How |
|------|-----|
| **Browser portal** | Public URL or Tailscale → invite + name → Utilize / register machine |
| **From source** | Clone repo → `scripts\install_joiner_deps.cmd` (verbose) → `start-gpu-pool-app.cmd` |
| **CLI** | `python -m gpu_swarm worker --name YourName --discord-user YourName` |

Login: [`LOGIN.md`](LOGIN.md).  
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

Optional GPU contributor torch (large — verbose pip output):

```bat
scripts\install_joiner_deps.cmd --with-torch-cuda
```

---

## Rules

- Invite code required on the portal (public or Tailscale). Do not disable auth for public mode.
- Allowlisted jobs only (`probe`, `pytorch_cuda_probe`, `llm_chat` in current tip).
- Never share `.env` or Discord bot tokens — invite code in Discord is fine; tokens are not.
- No Docker for this stack.
- Honest limits: host GPU safety protects contributors; Utilize needs no NVIDIA; Workspace VM has **no** NVIDIA passthrough.
