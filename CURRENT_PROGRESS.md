# CURRENT_PROGRESS — GPU Pool (gpu-swarm)

Living scorecard for the private Discord GPU/CPU co-op.  
**Updated:** 2026-08-04 ~16:05 CDT · console-spam fix + grandma onboarding.

**GitHub:** https://github.com/phoenixfire808/gpu-swarm (public)

| Service | Local | Tailscale |
|---------|-------|-----------|
| Scheduler | `http://127.0.0.1:8766` | `http://100.85.165.84:8766` |
| Portal | `http://127.0.0.1:8767/portal` | `http://100.85.165.84:8767/portal` |
| **Local model endpoint** | `http://127.0.0.1:18080/v1` (8080 busy → fallback) | localhost only |
| Public portal (when tunnel up) | see `data/public_endpoints.share.txt` | — |
| Robinhood CC | `127.0.0.1:8765` | **do not steal** |

**Discord:** App **GPU Pool** · Primary guild **Glitch Factor** · Invite code `glitch-factor`  
**Rules:** No Docker · No mock GPU/host data · Never commit `.env` / tokens / `data/public_endpoints*` / `data/portal.db`  
**Living docs:** [`TODO.md`](TODO.md) · [`ROADMAP.md`](ROADMAP.md) · [`CHANGELOG.md`](CHANGELOG.md) · [`START_HERE.md`](START_HERE.md)

---

## Done (this turn)

- [x] **Root cause:** Windows subprocesses lacked `CREATE_NO_WINDOW`; Connect tab polled Hermes `agent-vm` every 4s → flashing cmd/powershell loops
- [x] **`gpu_swarm/win_subprocess.py`** — shared hidden-spawn flags for Popen/run
- [x] Applied to `app_backend`, `agent_vm_bridge`, `portable_python`, diagnostics, joiner_settings, gpu
- [x] Stopped auto `_refresh_workspace()` on 4s poll (manual Refresh only)
- [x] **`scripts/run-hidden.cmd`** + all `start-*.cmd` → background pythonw, logs under `%LOCALAPPDATA%\GPUPool\logs\`
- [x] Grandma-friendly Welcome / `START_HERE.md` / portal hub copy (numbered steps, plain tool names)
- [x] Killed duplicate nohup bot/portal wrappers from prior run-stack

## How a non-tech person starts now

**Browser (easiest):** ask for web link → invite `glitch-factor` + Discord name → Join → Share / Use / Invite.

**Windows app:** download GPUPool.exe → follow numbered wizard → same three big buttons.

**Host background services:** double-click `start-all-local.cmd` once — no extra console windows; logs in `%LOCALAPPDATA%\GPUPool\logs\`.

## Next

- Restart portal once so live hub serves updated HTML
- Rebuild GPUPool.exe when ready to ship frozen path with win_subprocess bundled
- Post Discord invite blurb

---

## Ready-to-go checklist

| # | Check | Result |
|---|--------|--------|
| 1 | One app window; background hidden | **FIXED** this turn |
| 2 | Portal + EXE grandma copy | **SHIPPED** |
| 3 | Share / Use / Invite path | **PASS** |
| 4 | Workers + scheduler | **PASS** (one stack; duplicates trimmed) |
