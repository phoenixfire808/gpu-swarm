# GPU Pool v0.1.0 — Windows EXE

One-click Windows joiner for the private Glitch Factor GPU pool.

## Download

**[GPUPool.exe](https://github.com/phoenixfire808/gpu-swarm/releases/download/v0.1.0/GPUPool.exe)**  
(~29 MB onefile; also via [latest](https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe))

## What’s included

- Contribute / Utilize / Connect home UX
- Setup wizard → Join pool worker (`GPUPool.exe --worker`)
- Portable Python bootstrap under `%LOCALAPPDATA%\GPUPool\` (isolated runtime)
- Diagnostics: Copy log / Submit diagnostics (portal `/api/diagnostics`)
- Default Tailscale scheduler/portal URLs; public tunnel URLs when the host runs `start-public-access.cmd`

## Not bundled

- Torch / CUDA wheels (optional; install via wizard / portable Python when needed)
- Discord bot token / `.env` secrets
- Scheduler / portal server processes (run on the host)

## Friend prerequisites

1. Invite code `glitch-factor`
2. Prefer the host’s public portal URL when posted (no Tailscale); else join Tailscale
3. NVIDIA drivers only if contributing a GPU (`nvidia-smi`); laptops can Utilize or contribute CPU-only
4. Windows SmartScreen may warn on unsigned builds → More info → Run anyway

## Rebuild (maintainers)

```powershell
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
gh release upload v0.1.0 dist/GPUPool.exe --clobber
```

See `RELEASE.md` and `DOWNLOAD.md`.
