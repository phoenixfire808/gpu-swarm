# Building & publishing GPUPool.exe

Reproducible Windows release for the GPU Pool desktop joiner.

## Build (maintainer)

**Packaging Worker:** rebuild from current `master` after UI / hub / workspace / host_protect changes. Published **v0.1.0** is **stale** vs tip until you rebuild + publish **v0.1.1+**.

```powershell
cd C:\Users\Drew\Projects\gpu-swarm
# Verbose step labels + Write-Progress (build_exe.ps1):
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

Output (gitignored): `dist\GPUPool.exe`

Optional clean rebuild:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1 -Clean
```

## What is / isn’t in the EXE

| Included | Not included |
|----------|--------------|
| Contribute / Utilize / Connect / Workspace UI | Discord bot token / `.env` |
| Worker start path (`GPUPool.exe --worker`) | Full torch / CUDA wheels (too large) |
| Portable Python bootstrap (verbose progress + first-run log) | Pre-downloaded CPython zip (fetched on demand) |
| Diagnostics collect/submit (Copy log / Submit) | Scheduler / portal server processes |
| host_protect + local_endpoint + hub assets (when built from tip) | Discord.py |
| httpx, customtkinter, psutil, etc. | |

Settings / logs / portable Python / venv write to `%LOCALAPPDATA%\GPUPool\` (not into the EXE):

| Path | Purpose |
|------|---------|
| `%LOCALAPPDATA%\GPUPool\python\` | Portable CPython 3.12 (NuGet) when system Python is bad |
| `%LOCALAPPDATA%\GPUPool\venv\` | Isolated deps (never global site-packages) |
| `%LOCALAPPDATA%\GPUPool\logs\error-*.log` | Submitable friend diagnostics |
| `%LOCALAPPDATA%\GPUPool\logs\first-run-bootstrap.log` | Background first-run download/install progress |

Packaging Worker: rebuild from this source so EXE includes `gpu_swarm.portable_python`, `host_protect`, `agent_vm_bridge`, `portal_hub.html`, diagnostics (see `gpu_pool.spec` hiddenimports / datas).

## Publish GitHub Release (v0.1.1+)

```powershell
# After a good local smoke (EXE opens wizard; progress bar on Bootstrap):
gh release create v0.1.1 dist/GPUPool.exe `
  --repo phoenixfire808/gpu-swarm `
  --title "GPU Pool v0.1.1 — Windows EXE" `
  --notes-file RELEASE_NOTES_v0.1.1.md
```

If `RELEASE_NOTES_v0.1.1.md` is missing, write short notes covering: host_protect, Workspace, Network Hub/chat, verbose install progress, SmartScreen caveat.

Public asset URL pattern:

`https://github.com/phoenixfire808/gpu-swarm/releases/download/v0.1.1/GPUPool.exe`

Latest alias:

`https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe`

### Exact next commands (when ready to publish)

```powershell
cd C:\Users\Drew\Projects\gpu-swarm
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1 -Clean
# Smoke: .\dist\GPUPool.exe  → Welcome → Python & Deps → Bootstrap (watch %)
gh release create v0.1.1 dist/GPUPool.exe --repo phoenixfire808/gpu-swarm --title "GPU Pool v0.1.1 — Windows EXE" --notes-file RELEASE_NOTES_v0.1.1.md
```

## User prerequisites

1. Invite code `glitch-factor` (+ display name)
2. Prefer the host’s **current** public portal URL when posted (no Tailscale); else join Tailscale
3. NVIDIA drivers (`nvidia-smi`) **only** for GPU contribution — Utilize needs no NVIDIA
4. Windows SmartScreen may warn on unsigned builds — More info → Run anyway  

See [`DOWNLOAD.md`](DOWNLOAD.md) · [`LOGIN.md`](LOGIN.md).
