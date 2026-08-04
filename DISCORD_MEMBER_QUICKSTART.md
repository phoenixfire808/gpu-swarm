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

**Honest v1 limits**
Jobs actually run on GPU/CPU. RAM + SSD numbers are capacity you advertise
for scheduling — not a magic shared hard drive or pooled RAM across PCs yet.

Leave anytime (EXE Leave / portal Leave / app Leave / Ctrl+C on CLI).
Do **not** expose the scheduler or portal to the public internet.
Never share `.env` or bot tokens.
```

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
