# CURRENT_PROGRESS — GPU Pool (gpu-swarm)

Living scorecard for the private Discord GPU/CPU co-op.  
**Updated:** 2026-08-04 ~14:10 CDT · **v0.1.1 EXE published** + portal newcomer UX + growth docs.

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
**Living docs:** [`TODO.md`](TODO.md) · [`ROADMAP.md`](ROADMAP.md) · [`CHANGELOG.md`](CHANGELOG.md) · [`START_HERE.md`](START_HERE.md) · [`SHARED_AGENT_DEV.md`](SHARED_AGENT_DEV.md)

---

## Ready-to-go checklist (2026-08-04 ~14:05 CDT)

**Verdict: YES — usable from tip + publishing v0.1.1 EXE.**

| # | Check | Result |
|---|--------|--------|
| 1 | Scheduler + portal + hub UI | **PASS** — three huge Share / Use / Invite actions |
| 2 | Workers online | **PASS** — host worker + joiner; **`llm_ready=yes`** after Ollama serve |
| 3 | Share / Invite grow flow | **SHIPPED** — punchy Discord blurbs + portal Invite friends |
| 4 | Personal-name scrub | **SHIPPED** — docs/UI use host / friend / pool member |
| 5 | Wizard **Network & Workspace** | **SHIPPED** — automatic install copy |
| 6 | Workspace bridge | **PASS** — Hermes ready; no NVIDIA passthrough |
| 7 | Public Cloudflare path | **PASS** when tunnel up (URL rotates; gitignored) |
| 8 | Published EXE freshness | **PASS** — [v0.1.1](https://github.com/phoenixfire808/gpu-swarm/releases/tag/v0.1.1) |

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

Friend: download EXE or open public portal → invite `glitch-factor` → Share my PC / Use the pool / Invite friends.  
Start: [`START_HERE.md`](START_HERE.md).

### Primary UX (under 30 seconds)

1. **Join** — portal or EXE + invite `glitch-factor` + display name  
2. **Share my PC** — Contribute with caps  
3. **Use the pool** — Utilize jobs (no NVIDIA needed)  
4. **Invite friends** — copy Discord blurb and grow the network  

---

## Done (this turn)

- [x] Portal newcomer UX — hero + login simplify; three huge actions; How it works; secondary Chat/Suggest
- [x] `START_HERE.md` + punchy invite blurbs (`share_invite.py`, Discord quickstart, RELEASE_NOTES)
- [x] Welcome copy — “we'll install what you need”
- [x] DOWNLOAD / LOGIN / README point at v0.1.1 + growth path
- [x] Publish **GPUPool.exe v0.1.1** + `gh release` (smoke: Welcome process started)
- [x] Commit + push growth/docs/UX

## Next

- Restart portal so live hub serves new UX (if still on old HTML)
- Post Discord invite blurb so friends join
- Multi-session `session create` from Pool UI
- Keep secrets out of git

## Do not

- Heavy CUDA / load 27B GGUF during packaging
- Commit `.env`, Tailscale auth keys, `data/portal.db`, `data/public_endpoints*`, `dist/*.exe`
- Claim NVIDIA passthrough into VirtualBox guests
