# GPU Pool v0.1.1 — Windows EXE

One-click Windows joiner for the private Glitch Factor GPU pool.

## Download

**[GPUPool.exe](https://github.com/phoenixfire808/gpu-swarm/releases/download/v0.1.1/GPUPool.exe)**  
(~29 MB onefile; also via [latest](https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe))

## What’s new since v0.1.0

- **Host GPU safety** (`host_protect`) — default ON so Contribute won’t freeze Windows
- **Workspace** — optional Hermes agent-vms Linux desktop (CPU/RAM share only; no NVIDIA passthrough)
- **Network Hub** — Contribute / Utilize / Connect / Workspace home; web hub has pool **Chat** + **Suggest**
- **Local model endpoint** + `llm_chat` job path (needs a contributor running Ollama)
- **Verbose install progress** — step labels, percent / package names, logs stay visible

## What’s included

- Contribute / Utilize / Connect / Workspace home UX
- Setup wizard → Join pool worker (`GPUPool.exe --worker`)
- Portable Python bootstrap under `%LOCALAPPDATA%\GPUPool\` (isolated runtime)
- Diagnostics: Copy log / Submit diagnostics (portal `/api/diagnostics`)
- Default Tailscale scheduler/portal URLs; public tunnel URLs when the host runs `start-public-access.cmd`

## Not bundled

- Torch / CUDA wheels (optional; install via wizard / portable Python when needed)
- Discord bot token / `.env` secrets
- Scheduler / portal server processes (run on the host)

## Friend prerequisites

1. Invite code `glitch-factor` + Discord display name
2. Prefer the host’s **current** public portal URL (no Tailscale); else join Tailscale
3. NVIDIA drivers only if contributing a GPU; laptops can Utilize or contribute CPU-only
4. Windows SmartScreen may warn on unsigned builds → More info → Run anyway

## Honest limits

- Public trycloudflare URLs **rotate** when the tunnel restarts — ask the host for a fresh link
- Workspace VM does **not** get NVIDIA passthrough; GPU stays on the host pool worker
- Full chat e2e needs a contributor with Ollama running (`llm_ready`)

See `DOWNLOAD.md` and `LOGIN.md`.
