# Building & publishing GPUPool.exe

Reproducible Windows release for the GPU Pool desktop joiner.

## Build (maintainer)

**Packaging Worker:** rebuild from current `master` after UI changes (Home + three big modes Contribute / Utilize / Connect). Any existing `GPUPool.exe` Release is stale until you rebuild + re-publish.

```powershell
cd C:\Users\Drew\Projects\gpu-swarm
# Install PyInstaller only if missing (build_exe.ps1 does this):
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
| Contribute wizard + Utilize + Connect UI | Discord bot token / `.env` |
| Worker start path (`GPUPool.exe --worker`) | Full torch / CUDA wheels (too large) |
| Portable Python bootstrap hooks (`portable_python`, first-run) | Pre-downloaded CPython zip (fetched on demand) |
| Diagnostics collect/submit (Copy log / Submit) | Scheduler / portal server processes |
| Default Tailscale scheduler/portal URLs | Discord.py |
| httpx, customtkinter, psutil, etc. | |

Settings / logs / portable Python / venv write to `%LOCALAPPDATA%\GPUPool\` (not into the EXE):

| Path | Purpose |
|------|---------|
| `%LOCALAPPDATA%\GPUPool\python\` | Portable CPython 3.12 (NuGet) when system Python is bad |
| `%LOCALAPPDATA%\GPUPool\venv\` | Isolated deps (never global site-packages) |
| `%LOCALAPPDATA%\GPUPool\logs\error-*.log` | Submitable friend diagnostics |

Packaging Worker: rebuild from this source so EXE includes `gpu_swarm.portable_python` + `gpu_swarm.diagnostics` (see `gpu_pool.spec` hiddenimports).

## Publish GitHub Release

```powershell
# After a good local smoke (EXE opens wizard):
gh release create v0.1.0 dist/GPUPool.exe `
  --repo phoenixfire808/gpu-swarm `
  --title "GPU Pool v0.1.0 — Windows EXE" `
  --notes-file RELEASE_NOTES_v0.1.0.md
```

Public asset URL pattern:

`https://github.com/phoenixfire808/gpu-swarm/releases/download/v0.1.0/GPUPool.exe`

Latest alias:

`https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe`

## User prerequisites

1. Tailscale on Drew’s private network  
2. Invite code `glitch-factor`  
3. NVIDIA drivers (`nvidia-smi`) for GPU contribution  
4. Windows SmartScreen may warn on unsigned builds — More info → Run anyway  

See [`DOWNLOAD.md`](DOWNLOAD.md).
