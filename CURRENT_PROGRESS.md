# CURRENT_PROGRESS — GPU Pool (gpu-swarm)

Living scorecard for Drew’s private Discord GPU/CPU co-op.  
**Updated:** 2026-08-04 ~12:25 CDT · Friend login docs (`LOGIN.md`) + Local Pool Endpoint / `llm_chat`.

**GitHub:** https://github.com/phoenixfire808/gpu-swarm (public)

| Service | Local | Tailscale |
|---------|-------|-----------|
| Scheduler | `http://127.0.0.1:8766` | `http://100.85.165.84:8766` |
| Portal | `http://127.0.0.1:8767/portal` | `http://100.85.165.84:8767/portal` |
| **Local model endpoint** | `http://127.0.0.1:8080/v1` | (localhost only by default) |
| Robinhood CC | `127.0.0.1:8765` | **do not steal** |

**Discord:** App **GPU Pool** · Primary guild **Glitch Factor** · Invite code `glitch-factor`  
**v1 jobs:** `probe`, `pytorch_cuda_probe`, **`llm_chat`** · Auth MVP: invite/password (OAuth later)  
**Rules:** No Docker · No mock GPU/host data · Never commit `.env` / token paste files  
**Network model:** Private Tailscale/LAN (+ optional public tunnel when Drew runs `start-public-access.cmd`)

---

## Live scorecard (2026-08-04 ~12:20 CDT)

| # | Check | Result |
|---|--------|--------|
| 1 | Scheduler accepts `llm_chat` | **PASS** — job queued when no `llm_ready` worker |
| 2 | Local endpoint boot | **PASS** — `/health` + `GET /v1/models` |
| 3 | Ollama on Drew host | **INSTALLED, not running** — need `ollama serve` + model pull + worker restart |
| 4 | Full chat e2e via pool | **BLOCKED** until host Ollama + worker `llm_ready=yes` |
| 5 | Desktop Connect button | **CODE READY** — Start local model endpoint |
| 6 | Portal Connect local-model block | **CODE READY** |
| 7 | Docs `LOCAL_MODEL.md` | **PASS** |

**Demo verdict:** Friends can start a localhost OpenAI-compatible endpoint and list models. Chat completes once Drew runs Ollama on a contributor worker.

---

## Done (with dates)

### Friend login docs (2026-08-04)
- [x] `LOGIN.md` — invite/display name, where to get info, Paths A/B/C, form fields, Contribute/Utilize/Connect, troubleshooting, Drew host section, Discord blurb
- [x] Cross-links from README, DISCORD_MEMBER_QUICKSTART, DOWNLOAD, FRIEND_LAPTOP, CONNECTING

### Local Pool Endpoint + llm_chat (2026-08-04)
- [x] `gpu_swarm/local_endpoint.py` + CLI `python -m gpu_swarm local-endpoint` + `start-local-endpoint.cmd`
- [x] Allowlisted job `llm_chat` → worker-local Ollama / OpenAI-compatible runtime
- [x] Lease filter: only `llm_ready` workers take `llm_chat`
- [x] Desktop Connect: Start / Stop / Copy `OPENAI_BASE_URL`
- [x] Portal Connect: local model instructions
- [x] `LOCAL_MODEL.md` — honest “network GPU via API”
- [x] Verified: endpoint boots, models list, job path accepts `llm_chat` (queued without Ollama)

### Friend diagnostics + portable Python (2026-08-04)
- [x] diagnostics / portable Python / wizard submit (prior)

### Tailscale/LAN UX + Desktop three-mode (2026-08-04)
- [x] Private-network messaging, Utilize/Connect, portal friends cards

---

## In progress

- [ ] Drew: start Ollama + pull model + restart worker → full chat e2e
- [ ] Packaging Worker: rebuild EXE (include local_endpoint + llm_chat)
- [ ] Keep scorecard/TODO in sync

---

## Next (prioritized)

1. **Enable Ollama on Drew-Home worker** — `ollama serve`, `ollama pull llama3.2`, restart worker, smoke chat via local endpoint.
2. Packaging Worker rebuild EXE.
3. Member onboarding: point friends at `OPENAI_BASE_URL=http://127.0.0.1:8080/v1`.
4. Optional: streaming chat on local endpoint.
5. Whisper allowlisted job (still separate).

### Next 5 Drew should care about right now

1. Run Ollama on the host worker (`llm_ready=yes` in worker log).
2. Restart workers after this pull (scheduler already restarted for allowlist).
3. Tell aariff01: Connect → Start local model endpoint → paste `OPENAI_BASE_URL`.
4. Packaging EXE rebuild later.
5. Keep `.env` / tokens local — never commit.

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

- Commit `.env`, `DISCORD_BOT_TOKEN_PASTE.txt`, tokens, or `data/`
- Use Docker for this stack
- Steal port `8765` (Robinhood)
- Wipe Hermes durable memory / reuse Jarvis bot token
- Invent green checks — re-probe `/status` + portal when updating this file
