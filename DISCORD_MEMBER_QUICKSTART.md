# Discord member quickstart (paste-ready)

Copy everything inside the fence below into Discord.

```text
**GPU Pool** — plug your PC into our private co-op (Tailscale)

Primary Discord: **Glitch Factor**
Bot: **GPU Pool**
Commands: `/pool` `/workers` `/contribute` `/submit_probe` `/submit_compute` `/job_status`
Repo: https://github.com/phoenixfire808/gpu-swarm

**Easiest path — Windows EXE (recommended)**
1. Join Tailscale with the crew (ask Drew)
2. Download the latest Windows EXE from GitHub Releases:
   https://github.com/phoenixfire808/gpu-swarm/releases/latest
   Direct asset (placeholder until release publishes):
   https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe
3. Install current NVIDIA drivers (so nvidia-smi works)
4. Run the EXE → wizard → invite code **glitch-factor** + your display name
5. Set caps (GPU VRAM / CPU / RAM / disk) → Save + Join
6. In Discord: `/pool` and `/workers` — you should appear in the pool
Full download notes: DOWNLOAD.md

**Browser portal (no EXE)**
1. Join Tailscale with the crew (ask Drew)
2. Open the contributor portal:
   http://100.85.165.84:8767/portal
   (local on Drew’s PC: http://127.0.0.1:8767/portal)
3. Sign in with invite code **glitch-factor** + your display name
4. Register this machine — set caps for GPU VRAM, CPU, RAM, and disk
5. Follow the on-page “start worker” steps so your PC stays connected
6. In Discord: `/pool` and `/workers` — you should appear in the pool

**Native app from source (power users)**
1. Get the gpu-swarm folder (GitHub or zip from Drew)
2. Double-click `start-gpu-pool-app.cmd`  (or: `python -m gpu_swarm.app`)
3. Wizard → set scheduler URL → set VRAM/CPU/RAM/disk caps → Join Pool

**CLI fallback**
  set GPU_SWARM_SCHEDULER_URL=http://100.85.165.84:8766
  python -m gpu_swarm worker --name YourDiscordName --discord-user YourDiscordName

**Coding / local-model users**
v1 does **not** proxy Ollama or chat APIs. Allowlisted jobs only:
`probe` + `pytorch_cuda_probe`. Keep your local model on your PC; use the
pool to discover capacity / prove CUDA. From the repo:
  python examples\coding_agent_pool.py --job probe
  python examples\coding_agent_pool.py --job pytorch_cuda_probe
Docs: CONNECTING.md · examples/ollama_or_local_offload.md

**Laptop / no NVIDIA GPU? (still useful)**
You do **not** need a GPU to join the crew.
1. Join Tailscale (ask Drew) — private Tailscale/LAN pool, not exposed to
   the open internet. “Can’t reach it from Chrome without Tailscale” is normal.
2. Open the portal with the **full URL including port**:
   http://100.85.165.84:8767/portal
   Scheduler API (CLI / env): http://100.85.165.84:8766
3. Sign in: invite **glitch-factor** + your Discord display name
4. Use **Utilize** — submit allowlisted jobs (`probe`, etc.) onto the pool’s
   GPUs. Optional: **Contribute** CPU/RAM/disk only (skip GPU caps / leave
   VRAM at 0). CUDA jobs need someone else’s NVIDIA box online.
5. Discord: `/pool` `/submit_probe` `/job_status`

**Common mistakes (fix these first)**
- Missing port → `…84/portal` fails; must be `:8767/portal` and `:8766` for API
- Wrong env → CLI needs `GPU_SWARM_SCHEDULER_URL=http://100.85.165.84:8766`
  (not the portal URL, not bare host without port)
- Black / blank portal → hard refresh (Ctrl+F5) or reopen latest portal URL
  after Drew updates; confirm Tailscale is connected
- Expecting open-internet URL → won’t work; install/login Tailscale + join Drew’s tailnet

**How friends connect**
1. Install Tailscale
2. Get invited to Drew’s Glitch Factor tailnet
3. Open portal http://100.85.165.84:8767/portal or run the EXE
4. Contribute or Utilize (invite: glitch-factor)

**Honest v1 limits**
Jobs actually run on GPU/CPU. RAM + SSD numbers are capacity you advertise
for scheduling — not a magic shared hard drive or pooled RAM across PCs yet.

Leave anytime (EXE Leave / portal Leave / app Leave / Ctrl+C on CLI).
Private Tailscale/LAN pool — not exposed to the open internet (by design).
Never share `.env` or bot tokens.
```

## Laptop / no NVIDIA (friends)

You can still use the pool without a GPU.

| Point | Detail |
|-------|--------|
| Private by design | Private Tailscale/LAN pool — not exposed to the open internet. Friends join via Tailscale, then use these URLs. |
| Full URLs + ports | Portal `http://100.85.165.84:8767/portal` · Scheduler `http://100.85.165.84:8766` |
| Utilize first | Login → **Utilize** → submit jobs; pool GPUs (e.g. Drew’s) run them |
| Optional Contribute | Advertise CPU/RAM/disk only; leave GPU/VRAM at 0. CUDA probes need an NVIDIA worker online |
| Fixes | Missing `:8767`/`:8766`; wrong env (`GPU_SWARM_SCHEDULER_URL` = scheduler, not portal); black screen → Ctrl+F5 / latest portal + Tailscale up |

Invite: **`glitch-factor`**. See also [`DOWNLOAD.md`](DOWNLOAD.md) → “Laptop / no NVIDIA”.

## URLs (Drew host)

| What | URL |
|------|-----|
| Contributor portal (primary) | `http://100.85.165.84:8767/portal` |
| Scheduler API | `http://100.85.165.84:8766` |
| Local portal (host only) | `http://127.0.0.1:8767/portal` |
| Local scheduler | `http://127.0.0.1:8766` |
| Windows EXE (Releases) | https://github.com/phoenixfire808/gpu-swarm/releases/latest |
| Download guide | [`DOWNLOAD.md`](DOWNLOAD.md) |

Primary Discord: **Glitch Factor** (`1532614467974856724`).  
Invite code: **`glitch-factor`**.  
If Tailscale IP changes: Drew runs `tailscale ip -4` and posts the new URLs.

See also `DOWNLOAD.md` (EXE), `CONNECTING.md` (Contribute / Utilize / code), `VISION.md`, `ADVANCED_VM.md` (optional agent-vms — no GPU passthrough), and `examples/ollama_or_local_offload.md` for local-model users.

## Secrets

`.env` holds `DISCORD_BOT_TOKEN` and is gitignored — **never commit it**. Share the portal invite code in Discord DMs/voice, not tokens.
