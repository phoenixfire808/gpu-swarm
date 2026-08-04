# CURRENT_PROGRESS — GPU Pool (gpu-swarm)

Living scorecard for Drew’s private Discord GPU/CPU co-op.  
**Updated:** 2026-08-04 ~12:50 CDT · Workspace VM MVP (GPU Pool ↔ Hermes agent-vms).

**GitHub:** https://github.com/phoenixfire808/gpu-swarm (public)

| Service | Local | Tailscale |
|---------|-------|-----------|
| Scheduler | `http://127.0.0.1:8766` | `http://100.85.165.84:8766` |
| Portal | `http://127.0.0.1:8767/portal` | `http://100.85.165.84:8767/portal` |
| **Local model endpoint** | `http://127.0.0.1:8080/v1` | (localhost only by default) |
| Robinhood CC | `127.0.0.1:8765` | **do not steal** |

**Discord:** App **GPU Pool** · Primary guild **Glitch Factor** · Invite code `glitch-factor`  
**v1 jobs:** `probe`, `pytorch_cuda_probe`, **`llm_chat`** · Auth MVP: invite/password (OAuth later)  
**Rules:** No Docker · No mock GPU/host data · Never commit `.env` / token paste files / `data/public_endpoints*`  
**Network model:** Private Tailscale/LAN (+ optional public tunnel when Drew runs `start-public-access.cmd`)  
**Living docs:** [`TODO.md`](TODO.md) · [`ROADMAP.md`](ROADMAP.md) · [`CHANGELOG.md`](CHANGELOG.md) · [`DESIGN.md`](DESIGN.md)

---

## Live scorecard (2026-08-04 ~12:45 CDT)

| # | Check | Result |
|---|--------|--------|
| 1 | Scheduler accepts `llm_chat` | **PASS** — job queued when no `llm_ready` worker |
| 2 | Local endpoint boot | **PASS** — `/health` + `GET /v1/models` |
| 3 | Ollama on Drew host | **INSTALLED, not running** — need `ollama serve` + model pull + worker restart |
| 4 | Full chat e2e via pool | **BLOCKED** until host Ollama + worker `llm_ready=yes` |
| 5 | Desktop Connect button | **CODE READY** — Start local model endpoint |
| 6 | Portal Connect local-model block | **CODE READY** |
| 7 | Docs `LOCAL_MODEL.md` | **PASS** |
| 8 | Host protect on Drew-Home | **PASS** — worker restarted; `host_protect=ON` |
| 9 | Living docs + Cursor rule | **PASS** — ROADMAP / CHANGELOG / DESIGN / `.cursor/rules` |
| 10 | Workspace VM bridge | **CODE READY** — offer→CPU/RAM map + Connect/Home UI; light `agent-vm` status only (no vagrant up / no CUDA stress) |

**Demo verdict:** Friends can start a localhost OpenAI-compatible endpoint and list models. Chat completes once Drew runs Ollama on a contributor worker. Desktop stays protected by host_protect defaults. Drew can open **Workspace** from the desktop app for a capped Ubuntu VM (GPU stays on host worker).

---

## Done (with dates)

### Durable project memory (2026-08-04)
- [x] `ROADMAP.md` · `CHANGELOG.md` · `DESIGN.md` · refreshed `TODO.md` / this file
- [x] Cursor rule `.cursor/rules/project-memory.mdc` — always update progress/TODO/CHANGELOG on ship

### Friend login docs (2026-08-04)
- [x] `LOGIN.md` — invite/display name, Paths A/B/C, Contribute/Utilize/Connect, troubleshooting
- [x] Cross-links from README, DISCORD_MEMBER_QUICKSTART, DOWNLOAD, FRIEND_LAPTOP, CONNECTING

### Local Pool Endpoint + llm_chat (2026-08-04)
- [x] `gpu_swarm/local_endpoint.py` + CLI + `start-local-endpoint.cmd`
- [x] Allowlisted job `llm_chat` → worker-local Ollama / OpenAI-compatible runtime
- [x] Lease filter: only `llm_ready` workers take `llm_chat`
- [x] Desktop Connect: Start / Stop / Copy `OPENAI_BASE_URL`
- [x] Portal Connect: local model instructions · `LOCAL_MODEL.md`

### Friend diagnostics + portable Python (2026-08-04)
- [x] diagnostics / portable Python / wizard submit

### Tailscale/LAN UX + Desktop three-mode (2026-08-04)
- [x] Private-network messaging, Utilize/Connect, portal friends cards

### Contributor offer-cap ownership (2026-08-04)
- [x] Worker source of truth for caps; portal owner-only PATCH; scheduler rejects force-caps
- [x] Unit check: `tests/test_offer_ownership.py`

### Host GPU safety ceiling (2026-08-04)
- [x] `gpu_swarm/host_protect.py` — durable desktop safety (default ON)
- [x] Defaults: offer ≤55% total VRAM · pause lease when util ≥65% or free VRAM <1536 MiB · CPU offer ≤70% · CUDA matrix ≤1024
- [x] Worker applies ceiling + pauses `lease()`; Contribute checkbox / env tunables
- [x] Packaging: `gpu_pool.spec` + frozen EXE local-endpoint path include host_protect
- [x] Light unit tests only (`tests/test_host_protect.py`) — **no** CUDA e2e / stress / PyInstaller

### Workspace VM ↔ agent-vms (2026-08-04)
- [x] `gpu_swarm/agent_vm_bridge.py` — map Contribute/`host_protect` → VM cpus/memory; call Hermes `agent-vm`
- [x] Desktop: Home **4 · Workspace** + Connect Workspace card (Start/Open, RDP, Halt)
- [x] `app_backend` APIs: `workspace_status` / `open_workspace` / `halt_workspace` / `apply_workspace_caps`
- [x] agent-vms: `resources show|apply` + `--cpus`/`--memory-mb` on `up` / `session create|up`
- [x] Docs: `ADVANCED_VM.md` rewrite · CONNECTING / portal / skill notes
- [x] Unit tests: `tests/test_agent_vm_bridge.py` (mapping only)
- [x] Honest GPU: no VirtualBox NVIDIA passthrough — pool worker keeps GPU share
- [ ] Remaining for full ship: EXE includes bridge; halt+start confirm UX; multi-session UI; optional disk quota; cold `vagrant up` only when Drew asks

---

### Network Hub + chat + suggestions (2026-08-04 ~12:50 CDT)
- [x] Portal All-in-One Network Hub (`gpu_swarm/portal_hub.html`) — copper/steel peer-mesh aesthetic; live workers from scheduler
- [x] Pool chat: `GET/POST /api/chat` + `/api/presence` (sqlite, poll ~2.5s, empty state when quiet)
- [x] Suggestions: `GET/POST /api/suggestions` + PATCH status open/read/done — Review inbox in hub
- [x] `/api/workspace` slot (real agent-vms probe) · desktop Home “Network Hub” copy + web hub link
- [x] Light verify: portal 200, chat post/list, suggestion mark read, dashboard workers online — **no CUDA stress**
- [x] Shipped to GitHub with Workspace MVP (same push)

---

## In progress

- [ ] Drew: start Ollama + pull model + worker restart → full chat e2e
- [ ] Packaging Worker: rebuild EXE (include host_protect + local_endpoint + llm_chat + workspace bridge + portal_hub.html)
- [ ] Keep scorecard/TODO/CHANGELOG in sync on every ship

---

## Next (prioritized)

1. **Enable Ollama on Drew-Home worker** — `ollama serve`, `ollama pull llama3.2`, restart worker, smoke chat via local endpoint.
2. Try Workspace: `start-gpu-pool-app.cmd` → Home → Workspace → Start / Open (RDP 3390).
3. Packaging Worker rebuild EXE (must include workspace bridge).
4. Member onboarding: `OPENAI_BASE_URL=http://127.0.0.1:8080/v1`.
5. Optional: streaming chat on local endpoint.

### Next 5 Drew should care about right now

1. Run Ollama on the host worker (`llm_ready=yes` in worker log).
2. Open Workspace from the desktop app (capped VM; GPU stays on host worker).
3. Tell aariff01: Connect → Start local model endpoint → paste `OPENAI_BASE_URL`.
4. Packaging EXE rebuild (host_protect + workspace).
5. Keep `.env` / tokens / public endpoint files local — never commit.

---

## Blocked

| Blocker | Why | Unblock |
|---------|-----|---------|
| **Full LLM e2e** | Ollama installed but not running; workers not yet `llm_ready` | `ollama serve` + pull + worker restart |
| **Portal OAuth** | MVP invite/password only | Implement when auth story ready |
| **EXE asset** | Needs packaging rebuild | Worker publishes Release |

---

## Local model — how friends use it

```bat
start-local-endpoint.cmd
set OPENAI_BASE_URL=http://127.0.0.1:8080/v1
```

Point Open WebUI / LM Studio / Continue / Cursor at that URL.  
Honest: **network GPU via API**, not a PCI/Windows display adapter. See `LOCAL_MODEL.md`.

## What Drew runs for LLM jobs

```bat
ollama serve
ollama pull llama3.2
start-worker.cmd
REM expect: [worker] llm_ready=yes
```

## How to relaunch host services

```bat
cd C:\Users\Drew\Projects\gpu-swarm
start-scheduler-lan.cmd
start-portal.cmd
start-bot.cmd
start-worker.cmd
start-local-endpoint.cmd
start-gpu-pool-app.cmd
```

---

## Do not

- Commit `.env`, `DISCORD_BOT_TOKEN_PASTE.txt`, tokens, or `data/` (incl. `public_endpoints*`)
- Use Docker for this stack
- Steal port `8765` (Robinhood)
- Wipe Hermes durable memory / reuse Jarvis bot token
- Invent green checks — re-probe `/status` + portal when updating this file
- Heavy CUDA / PyInstaller stress during agent sessions unless Drew asks

## 2026-08-04 12:30 CDT — STOP heavy GPU-swarm test load
- Killed Wizard-OneStop worker PID 31696 (extra test joiner pegging GPU)
- Killed friend-laptop-verify bash PID 36712 (probe submit/wait); portal child died with it
- Restored portal only on :8767 (PID 23368); no new jobs/tests/EXE
- Left: scheduler :8766, portal :8767, bot, cloudflared, Drew-Home worker, local-endpoint :18080
- GPU after: 5060 Ti ~26% / ~1.8 GiB; 2070 SUPER idle/empty
- Not found running: pytest, pyinstaller, app_backend_smoke, coding_agent_pool, pytorch_cuda_probe loops, ollama pull
