# CURRENT_PROGRESS — GPU Pool (gpu-swarm)

Living scorecard for Drew’s private Discord GPU/CPU co-op.  
**Updated:** 2026-08-04 ~12:05 CDT · Desktop Home UX — Contribute / Utilize / Connect first-class.

**GitHub:** https://github.com/phoenixfire808/gpu-swarm (public)

| Service | Local | Tailscale |
|---------|-------|-----------|
| Scheduler | `http://127.0.0.1:8766` | `http://100.85.165.84:8766` |
| Portal | `http://127.0.0.1:8767/portal` | `http://100.85.165.84:8767/portal` |
| Robinhood CC | `127.0.0.1:8765` | **do not steal** |

**Discord:** App **GPU Pool** · Primary guild **Glitch Factor** · Invite code `glitch-factor`  
**v1 jobs only:** `probe`, `pytorch_cuda_probe` · Auth MVP: invite/password (OAuth later)  
**Rules:** No Docker · No mock GPU/host data · Never commit `.env` / token paste files

---

## Live scorecard (fresh LIVE probe 2026-08-04 ~12:05 CDT)

| # | Check | Result |
|---|--------|--------|
| 1 | Scheduler `:8766` `/status` + workers + resource fields | **PASS** — `workers_online=1` |
| 2 | Worker online with real GPUs | **PASS** — Drew-Home; RTX 5060 Ti + 2070 SUPER |
| 3 | Utilize e2e `probe` + `pytorch_cuda_probe` (app_backend path) | **PASS** — probe + CUDA completed; `cuda:0` 5060 Ti |
| 4 | Desktop Home UX — 3 big modes | **PASS** — Home cards + tabs Contribute / Utilize / Connect; Run Probe / Run CUDA Job |
| 5 | Portal Tailscale + invite | **PASS** (prior) — invite `glitch-factor` |
| 6 | Discord GPU Pool bot | **PASS** (prior) — slash cmds synced |
| 7 | GitHub `phoenixfire808/gpu-swarm` | **PASS** — push this UX commit |
| 8 | GPUPool.exe Release | **NEEDS REBUILD** — packaging Worker must rebuild from this source |

**Demo verdict:** MOSTLY — Home makes Utilize + Connect obvious; live jobs complete. EXE Release (if any) needs rebuild to pick up UI.

---

## Done (with dates)

### Desktop UX — Utilize + Connect first-class (2026-08-04)
- [x] Home screen with three large mode cards (Contribute / Utilize / Connect)
- [x] Mode tabs: Home · 1 Contribute · 2 Utilize · 3 Connect
- [x] Utilize: live pool status, scheduler Local/Tailscale, **Run Probe** / **Run CUDA Job**, status+result panel, allowlist help
- [x] Connect: scheduler + portal copy (default Tailscale), Discord tips, Python/CLI snippets, CONNECTING.md + examples/
- [x] README **Using the app** section updated
- [x] `RELEASE.md` notes packaging Worker must rebuild EXE from this source
- [x] Live verify: probe + CUDA jobs completed against `http://127.0.0.1:8766`

### Core pool / portal / Discord / connect surface (2026-08-04)
- [x] Scheduler, workers, allowlisted jobs, CLI `utilize`, portal, Discord bot, SDK, CONNECTING.md, examples
- [x] Public repo https://github.com/phoenixfire808/gpu-swarm
- [x] DOWNLOAD.md / member quickstart (EXE placeholder until packaging publishes)

---

## In progress

- [ ] Packaging Worker: rebuild + publish Windows EXE to GitHub Releases (source now has Home/Utilize/Connect UX)
- [ ] Confirm Discord `/pool` smoke in Glitch Factor (manual; optional)
- [ ] Keep scorecard/TODO in sync

---

## Next (prioritized)

1. **Packaging Worker** — rebuild EXE from current master; publish Release (old EXE lacks Home three-mode UX).
2. **Member onboarding paste** — post `DISCORD_MEMBER_QUICKSTART.md` in Glitch Factor.
3. **Stream-friendly verify** — Home → Utilize Run Probe → Connect copy URL → Discord `/pool`.
4. **Future job types** — Whisper / bounded LLM (allowlisted only).
5. **Discord OAuth** for portal (later).

### Next 5 Drew should care about right now

1. Packaging Worker rebuild of GPUPool.exe from this commit.
2. Post member quickstart (EXE-first) + repo URL in Glitch Factor.
3. Quick live smoke: Home → Utilize Run Probe / Run CUDA Job.
4. Plan Whisper/LLM allowlisted runners (post-publish).
5. Keep `.env` / tokens local — never commit.

---

## Blocked

| Blocker | Why | Unblock |
|---------|-----|---------|
| **Whisper / LLM jobs** | No runners in `jobs.py` | Design narrow contract → runners + UI |
| **Portal OAuth** | MVP invite/password only | Implement when auth story ready |
| **Public internet expose** | LAN/Tailscale only by design | Keep private |

---

## How to relaunch host services

```bat
cd C:\Users\Drew\Projects\gpu-swarm
start-scheduler-lan.cmd
start-portal.cmd
start-bot.cmd
start-gpu-pool-app.cmd
```

Coding smoke:

```bat
set GPU_SWARM_SCHEDULER_URL=http://127.0.0.1:8766
python -m gpu_swarm utilize status
python -m gpu_swarm utilize probe --wait
python -m gpu_swarm utilize cuda --wait
```

---

## Do not

- Commit `.env`, `DISCORD_BOT_TOKEN_PASTE.txt`, tokens, or `data/`
- Use Docker for this stack
- Steal port `8765` (Robinhood)
- Wipe Hermes durable memory / reuse Jarvis bot token
- Invent green checks — re-probe `/status` + portal when updating this file
