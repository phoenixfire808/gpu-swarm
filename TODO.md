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
- [ ] Drew: Ollama serve + model + worker restart → full chat e2e (and `llm_ready` on hub)
- [ ] Packaging Worker: publish Windows EXE **v0.1.1+** with host_protect + local_endpoint + llm_chat + workspace bridge + verbose install UX
- [ ] Post member tip: `OPENAI_BASE_URL=http://127.0.0.1:8080/v1`

## Next
- [ ] Streaming on local endpoint (`stream=true`)
- [ ] Allowlisted `whisper_transcribe`
- [ ] Portal Discord OAuth (replace invite/password MVP)
- [ ] Worker advertise `llm_models` into `/status` for richer `/v1/models`
- [ ] Stable public URL (durable tunnel / DNS)
- [ ] Workspace: confirm dialog for halt+start when running above offer
- [ ] Workspace: multi-session create from desktop UI
- [ ] Workspace: disk resize / quota (today: scheduling soft-cap only)

## Blocked
- [ ] Full LLM e2e — Ollama not running on host worker yet
- [ ] OAuth — blocked until auth priority
- [ ] Exact EXE download URL freshness — blocked on packaging Worker Release rebuild

## Next 5
1. Enable Ollama on Drew-Home + restart worker (`llm_ready=yes`)
2. Smoke: local endpoint → chat completion via pool
3. Packaging: `build_exe.ps1 -Clean` → publish **v0.1.1** (`RELEASE.md` commands)
4. Try Workspace: `start-gpu-pool-app.cmd` → Home → Workspace → Start / Open
5. Keep secrets out of git (never `.env` / `data/public_endpoints*`)
