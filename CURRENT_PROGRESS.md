# CURRENT_PROGRESS — GPU Pool (gpu-swarm)

Living scorecard for Drew’s private Discord GPU/CPU co-op.  
**Updated:** 2026-08-04 ~12:10 CDT · Clarified Tailscale/LAN “not on public internet” UX (actionable, not broken).

**GitHub:** https://github.com/phoenixfire808/gpu-swarm (public)

| Service | Local | Tailscale |
|---------|-------|-----------|
| Scheduler | `http://127.0.0.1:8766` | `http://100.85.165.84:8766` |
| Portal | `http://127.0.0.1:8767/portal` | `http://100.85.165.84:8767/portal` |
| Robinhood CC | `127.0.0.1:8765` | **do not steal** |

**Discord:** App **GPU Pool** · Primary guild **Glitch Factor** · Invite code `glitch-factor`  
**v1 jobs only:** `probe`, `pytorch_cuda_probe` · Auth MVP: invite/password (OAuth later)  
**Rules:** No Docker · No mock GPU/host data · Never commit `.env` / token paste files  
**Network model:** Private Tailscale/LAN only (binds `0.0.0.0` on host for Tailscale reachability — not open WAN)

---

## Live scorecard (fresh LIVE probe 2026-08-04 ~12:10 CDT)

| # | Check | Result |
|---|--------|--------|
| 1 | Scheduler Tailscale `/status` | **PASS** — HTTP 200 @ `http://100.85.165.84:8766/status` |
| 2 | Portal Tailscale `/portal` | **PASS** — HTTP 200; new “How friends connect” + private-network copy live |
| 3 | `tailscale ip -4` | **PASS** — still `100.85.165.84` (defaults unchanged) |
| 4 | Desktop Connect/Utilize Tailscale status helpers | **PASS** — `test_scheduler` / `pool_status` return actionable Tailscale hints |
| 5 | GPUPool.exe Release | **NEEDS REBUILD** — no release asset yet / packaging Worker must rebuild from this source |

**Demo verdict:** MOSTLY — private-by-design messaging is clear; friends path is Tailscale → portal/EXE → Contribute/Utilize.

---

## Done (with dates)

### Tailscale/LAN UX copy (2026-08-04)
- [x] Softened “public internet” wording everywhere → private Tailscale/LAN + friends join via Tailscale
- [x] Portal: network note, How friends connect card (Home + Connect), clearer dash error
- [x] Desktop: Test Tailscale connection on Utilize/Connect; no vague “DOWN/pool is down”
- [x] `app_backend.PRIVATE_NETWORK_BLURB` + `scheduler_reachability_hint` + `get_friends_connect_text`
- [x] Docs: DOWNLOAD / CONNECTING / DISCORD_MEMBER_QUICKSTART / README / examples
- [x] Portal restarted on `0.0.0.0:8767` to serve new HTML/API

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
