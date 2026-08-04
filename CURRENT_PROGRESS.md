# CURRENT_PROGRESS — GPU Pool (gpu-swarm)

Living scorecard for the private Discord GPU/CPU co-op.  
**Updated:** 2026-08-04 ~13:35 CDT · **Share/Invite grow + personal-name scrub** pushed.

**GitHub:** https://github.com/phoenixfire808/gpu-swarm (public)

| Service | Local | Tailscale |
|---------|-------|-----------|
| Scheduler | `http://127.0.0.1:8766` | `http://100.85.165.84:8766` |
| Portal | `http://127.0.0.1:8767/portal` | `http://100.85.165.84:8767/portal` |
| **Local model endpoint** | `http://127.0.0.1:18080/v1` (8080 busy → fallback) | localhost only |
| Public portal (when tunnel up) | see `data/public_endpoints.share.txt` | — |
| Robinhood CC | `127.0.0.1:8765` | **do not steal** |

**Discord:** App **GPU Pool** · Primary guild **Glitch Factor** · Invite code `glitch-factor` (product setting via `GPU_SWARM_INVITE_CODES`)  
**v1 jobs:** `probe`, `pytorch_cuda_probe`, **`llm_chat`** · Auth MVP: invite/password (OAuth later)  
**Rules:** No Docker · No mock GPU/host data · Never commit `.env` / token paste files / `data/public_endpoints*` / `data/portal.db`  
**Living docs:** [`TODO.md`](TODO.md) · [`ROADMAP.md`](ROADMAP.md) · [`CHANGELOG.md`](CHANGELOG.md) · [`SHARED_AGENT_DEV.md`](SHARED_AGENT_DEV.md)

---

## Ready-to-go checklist (2026-08-04 ~13:35 CDT)

**Verdict: YES — usable today from repo tip (source).** Friend EXE still stale until v0.1.1.

| # | Check | Result |
|---|--------|--------|
| 1 | Scheduler + portal + hub UI | **PASS** — Hub / Share my PC / Use the pool / Invite others |
| 2 | Workers online | **PASS** — host worker + joiner; **`llm_ready=yes`** after Ollama serve |
| 3 | Share / Invite grow flow | **SHIPPED** — `share_invite.py` + portal **Invite others** + desktop mode |
| 4 | Personal-name scrub | **SHIPPED** — docs/UI use host / friend / pool member; `NO_GPU_LAPTOP.md` |
| 5 | Wizard **Network & Workspace** | **SHIPPED (source)** |
| 6 | Workspace bridge | **PASS** — Hermes ready; no NVIDIA passthrough |
| 7 | Public Cloudflare path | **PASS** when tunnel up (URL rotates; gitignored) |
| 8 | Published EXE freshness | **FAIL** — Release v0.1.0 stale; use source |

### How the host launches (ready copy)

```bat
cd C:\Users\Drew\Projects\gpu-swarm
scripts\install-prereqs.cmd
start-scheduler-lan.cmd
start-portal.cmd
start-worker.cmd
ollama serve
start-local-endpoint.cmd
start-gpu-pool-app.cmd
REM optional friends without Tailscale:
start-public-access.cmd
```

Friend: `scripts\install-prereqs.cmd` → `start-gpu-pool-app.cmd` → invite `glitch-factor` → Share my PC / Use the pool / Invite others.  
Shared agent story: [`SHARED_AGENT_DEV.md`](SHARED_AGENT_DEV.md).  
Workspace RDP: `mstsc /v:127.0.0.1:3390` · `vagrant`/`vagrant`.

### Primary UX (under 30 seconds)

1. **Join** — portal or app + invite `glitch-factor` + display name  
2. **Share my PC** — Contribute with caps  
3. **Use the pool** — Utilize jobs (no NVIDIA needed)  
4. **Invite others** — copy friend message / portal / download link  

---

## Done (this turn)

- [x] Personal-name scrub (friend anecdotes, sample display names, “ask Drew” → host/pool admin)
- [x] Renamed `FRIEND_LAPTOP.md` → `NO_GPU_LAPTOP.md`
- [x] Share / Invite grow flow (`gpu_swarm/share_invite.py`, portal hub, desktop Home)
- [x] DOWNLOAD / LOGIN / README / Discord blurb / wizard Welcome tightened
- [x] Living docs updated; commit + push (no secrets)

## Next

- Publish **GPUPool.exe v0.1.1+** (hub + workspace + invite share + host_protect)
- Multi-session `session create` from Pool UI
- Lighter default chat model for smoke
- Keep secrets out of git

## Do not

- Heavy CUDA / load 27B GGUF / PyInstaller during agent sessions unless the host operator asks
- Commit `.env`, Tailscale auth keys, `data/portal.db`, `data/public_endpoints*`
- Claim NVIDIA passthrough into VirtualBox guests
