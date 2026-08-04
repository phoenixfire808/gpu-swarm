# CURRENT_PROGRESS — GPU Pool (gpu-swarm)

Living scorecard. **Updated:** 2026-08-04 ~16:25 CDT · use cases + availability timers + console fix.

**GitHub:** https://github.com/phoenixfire808/gpu-swarm

---

## Done (this turn)

- [x] **Console spam fix** (prior commit `c45ffc8`) — `CREATE_NO_WINDOW`, hidden `start-*.cmd`, no workspace poll loop
- [x] **Use-case copy** — portal hub, desktop Welcome/Home, `START_HERE.md`, `gpu_swarm/use_cases.py`
- [x] **Availability timers MVP** — Always / Nights & weekends / Next 2h / Custom; worker lease pause + `paused_schedule` heartbeat; Contribute UI + portal Share form; `tests/test_availability_schedule.py` (9 tests pass)
- [x] Grandma-friendly onboarding preserved — Join → Share / Use / Invite big buttons

## How timers work

| Preset | Behavior |
|--------|----------|
| **Always on** | Worker accepts jobs anytime (default) |
| **Nights & weekends** | Daily 10pm–8am local time |
| **Next 2 hours** | Sharing until timer ends, then paused |
| **Custom** | Your daily start/end times (supports overnight e.g. 22:00–08:00) |

Outside the window: worker **stays registered**, heartbeats `paused_schedule`, **won't lease new jobs**. Status panel shows e.g. "Paused — resumes at 10pm".

Settings: `joiner_settings.json` + `GPU_SWARM_AVAILABILITY_*` env (synced on Join).

## How a non-tech person starts

1. **Browser:** web link → invite `glitch-factor` + name → Join → Share / Use / Invite  
2. **App:** GPUPool.exe → numbered wizard → same three buttons  
3. **Share schedule:** Share my PC → pick "When should we use your PC?" → Join pool  

## Next

- Restart portal for updated hub HTML
- Rebuild GPUPool.exe when shipping frozen build with schedule module
- Post Discord invite blurb
