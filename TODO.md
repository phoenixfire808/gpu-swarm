# TODO — GPU Pool (stream backlog)

Short evolving list. Detail: `CURRENT_PROGRESS.md` · plan: `ROADMAP.md` · history: `CHANGELOG.md`.  
Updated: 2026-08-04 · GitHub: https://github.com/phoenixfire808/gpu-swarm

## Done
- [x] Scheduler + workers + heartbeats (GPU/CPU/RAM/disk)
- [x] Jobs: `probe`, `pytorch_cuda_probe`, **`llm_chat`**
- [x] Discord **GPU Pool** bot (6 slash cmds → Glitch Factor)
- [x] Portal Contribute / Utilize / Connect
- [x] Desktop one-stop wizard + Connect local model endpoint
- [x] `CONNECTING.md` + `LOCAL_MODEL.md` + coding examples
- [x] Local Pool Endpoint (`local-endpoint` / `start-local-endpoint.cmd`)
- [x] Friend diagnostics + portable Python bootstrap
- [x] Public GitHub publish — https://github.com/phoenixfire808/gpu-swarm
- [x] **Contributor offer ownership** — only owner changes caps; cross-user PATCH 403
- [x] **Host GPU safety ceiling** — default ON; ≤55% VRAM offer; pause at ≥65% util / low free VRAM
- [x] Living docs + Cursor rule (TODO / ROADMAP / CHANGELOG / DESIGN / CURRENT_PROGRESS)
- [x] **Network Hub portal** — peer mesh UI + live `/status` workers (`portal_hub.html`)
- [x] **Pool chat** + **suggestions/review inbox** (portal sqlite APIs)

## Now
- [x] Workspace VM MVP — GPU Pool → Hermes agent-vm with Contribute/host_protect CPU+RAM caps
- [x] Verbose install progress + plain-language friend UX (scripts, wizard, DOWNLOAD/LOGIN/FRIEND docs)
- [x] **install-prereqs automation** — Tailscale / VirtualBox / Vagrant detect-or-install + wizard Network & Workspace
- [x] **Ready-to-go source tip** — SHARED_AGENT_DEV.md; hub/worker/workspace/prereqs usable today
- [x] Ollama serve + Drew-Home `llm_ready=yes` (endpoint `/v1/models` OK; skipped 27B chat load)
- [ ] Packaging Worker: publish Windows EXE **v0.1.1+** (hub + workspace + install-prereqs + host_protect)
- [ ] Post member tip: `OPENAI_BASE_URL=http://127.0.0.1:18080/v1` (or `:8080` when free)

## Next
- [ ] Shared Agent Dev: multi-session create from Pool UI (`session create` CLI exists)
- [ ] Streaming on local endpoint (`stream=true`)
- [ ] Allowlisted `whisper_transcribe`
- [ ] Portal Discord OAuth (replace invite/password MVP)
- [ ] Worker advertise `llm_models` into `/status` for richer `/v1/models`
- [ ] Stable public URL (durable tunnel / DNS)
- [ ] Workspace: confirm dialog for halt+start when running above offer
- [ ] Workspace: disk resize / quota (today: scheduling soft-cap only)
- [ ] Prefer a small default Ollama model for light chat smoke

## Blocked
- [ ] Light `llm_chat` completion smoke — only large ~27B GGUF local; host_protect pausing on high util
- [ ] OAuth — blocked until auth priority
- [ ] Exact EXE download URL freshness — blocked on packaging Worker Release rebuild

## Next 5
1. Packaging: `build_exe.ps1 -Clean` → publish **v0.1.1** (`RELEASE.md`)
2. Friend trial: `install-prereqs` → app → invite → Contribute/Utilize
3. Workspace Start/Open from desktop when needed (RDP 3390)
4. Optional: smaller Ollama model for safe chat smoke
5. Keep secrets out of git (never `.env` / auth keys / `data/public_endpoints*`)
