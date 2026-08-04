# CURRENT_PROGRESS — GPU Pool (gpu-swarm)

Living scorecard for the private Discord GPU/CPU co-op.  
**Updated:** 2026-08-04 ~16:30 CDT · use cases + availability timers + portal restart.

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

## Done (this turn — after `c45ffc8`)

- [x] **Portal restarted** — `start-portal.cmd` (hidden via `run-hidden.cmd`); hub serves updated HTML (use cases + schedule UI)
- [x] **Use cases** — `gpu_swarm/use_cases.py`; portal hub Home, desktop Welcome/Home, `START_HERE.md` ("What can you use this for?")
- [x] **Availability timers MVP** — `gpu_swarm/availability_schedule.py`
  - Presets: Always · Nights & weekends · Next 2 hours · Custom daily window
  - Persisted in `joiner_settings.json` + env (`GPU_SWARM_AVAILABILITY_*`)
  - Worker pauses new leases outside window; heartbeat status `paused_schedule`
  - UI: "Sharing now" / "Paused — resumes at …" (desktop Contribute + portal Share my PC)
- [x] Unit tests — `tests/test_availability_schedule.py` (18 tests with host_protect, all pass)
- [x] One healthy stack — scheduler :8766 + portal :8767 (no console spam)

## How availability timers work

1. **Share my PC → When should we use your PC?** — pick a preset (or custom HH:MM window).
2. Settings save to **`data/joiner_settings.json`** (desktop) or portal machine notes/env (browser token path).
3. On each heartbeat/lease the worker re-reads settings and evaluates the window (like `host_protect`).
4. **Inside window:** status `online`, jobs lease normally.
5. **Outside window:** status `paused_schedule`, worker skips lease (still heartbeats so peers see you).

## How a non-tech person starts now

**Browser (easiest):** ask for web link → invite `glitch-factor` + Discord name → Join → Share / Use / Invite.

**Windows app:** download GPUPool.exe → follow numbered wizard → same three big buttons.

**Host background services:** double-click `start-all-local.cmd` once — no extra console windows; logs in `%LOCALAPPDATA%\GPUPool\logs\`.

## Next

- Rebuild GPUPool.exe when ready to ship frozen path with availability + use_cases bundled
- Post Discord invite blurb + local-model tip

---

## Ready-to-go checklist

| # | Check | Result |
|---|--------|--------|
| 1 | One app window; background hidden | **PASS** (`c45ffc8`) |
| 2 | Portal + EXE grandma copy | **PASS** |
| 3 | Use cases + availability timers | **SHIPPED** this turn |
| 4 | Share / Use / Invite path | **PASS** |
| 5 | Workers + scheduler | **PASS** (portal restarted) |
