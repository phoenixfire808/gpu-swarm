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
- [x] Workspace VM MVP — GPU Pool → Hermes agent-vm with Contribute/host_protect CPU+RAM caps
- [x] Verbose install + plain-language UX + install-prereqs automation
- [x] **Share / Invite others** grow flow (`share_invite.py`, portal + desktop copy buttons)
- [x] Personal-name scrub; `FRIEND_LAPTOP.md` → `NO_GPU_LAPTOP.md`
- [x] Console window spam fix (`win_subprocess`, hidden `start-*.cmd`)
- [x] Use-case onboarding copy (portal + desktop + START_HERE)
- [x] Availability timers MVP (Contribute schedule + worker lease pause)

## Now
- [x] Packaging Worker: publish Windows EXE **v0.1.1** (hub + Invite friends + host_protect + START_HERE)
- [x] Portal newcomer UX + growth docs (`START_HERE.md`, punchy invite blurbs)
- [x] One-click public website launcher (`launch-public.cmd`) with fresh Quick Tunnel verification
- [x] End-to-end local/public portal + allowlisted probe smoke (2026-08-08)
- [ ] Post member tip: `OPENAI_BASE_URL=http://127.0.0.1:18080/v1` (or `:8080` when free)

## Next
- [ ] Shared Agent Dev: multi-session create from Pool UI (`session create` CLI exists)
- [ ] Streaming on local endpoint (`stream=true`)
- [ ] Allowlisted `whisper_transcribe`
- [ ] Portal Discord OAuth (replace invite/password MVP)
- [ ] Worker advertise `llm_models` into `/status` for richer `/v1/models`
- [ ] Stable public URL (named Cloudflare tunnel + DNS prepared; `cloudflared tunnel login` certificate still pending)
- [ ] Workspace: confirm dialog for halt+start when running above offer
- [ ] Workspace: disk resize / quota (today: scheduling soft-cap only)
- [ ] Prefer a small default Ollama model for light chat smoke

## Blocked
- [ ] Light `llm_chat` completion smoke — only large ~27B GGUF local; host_protect pausing on high util
- [ ] OAuth — blocked until auth priority
- [x] Exact EXE download URL freshness — v0.1.1 Release asset live

## Next 5
1. Discord blast: paste START_HERE blurb + current public portal URL
2. Friend trial: EXE or portal → invite → Share my PC / Use the pool / Invite friends
3. Workspace Start/Open from desktop when needed (RDP 3390)
4. Optional: smaller Ollama model for safe chat smoke
5. Keep secrets out of git (never `.env` / auth keys / `data/public_endpoints*` / `portal.db`)
