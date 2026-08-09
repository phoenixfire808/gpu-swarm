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
- [x] Cloudflare installer integration: Quick Tunnel default + Named Tunnel guide/config template
- [x] Clean rebuild and focused packaged GUI smoke for `dist/GPUPool.exe` (2026-08-08)
- [ ] Post member tip: `OPENAI_BASE_URL=http://127.0.0.1:18080/v1` (or `:8080` when free)

## Next
- [ ] Shared Agent Dev: multi-session create from Pool UI (`session create` CLI exists)
- [ ] Streaming on local endpoint (`stream=true`)
- [ ] Allowlisted `whisper_transcribe`
- [ ] Portal Discord OAuth (replace invite/password MVP)
- [x] worker advertise `llm_models` into `/status` for richer `/v1/models`

## In progress — Discord setup + shared LLM routing
- [x] Persist online worker LLM mounts (`provider`, endpoint kind, model IDs, worker identity) in scheduler status.
- [x] Route `llm_chat` only to workers advertising the requested exact model; keep `gpu-pool/auto` as explicit fallback selection.
- [x] Add Discord `/setup`, `/route`, `/models`, and `/ask` flows with a model dropdown and setup help.
- [x] Add desktop LLM routing card with provider instructions, refreshable mounted-model dropdown, and selected-model persistence.
- [x] Add same-worker GPU-group metadata and larger-model placement guidance.
- [x] Add installed/loaded/fit-now model residency and safety-margin admission state.
- [ ] Run a bounded larger-model placement test only when the GPU/display headroom is safe; record per-GPU VRAM and unload receipt.
- [ ] Add explicit distributed multi-node inference lane only after private-network/Ray/NCCL design and acceptance tests.
- [x] Document Ollama, LM Studio, vLLM, and generic OpenAI-compatible contributor setup without exposing credentials.
- [x] Verify bot command wiring, scheduler model catalog, worker advertisement, model-filtered lease behavior, and packaged/source UI imports.
- [ ] Stable public URL (named Cloudflare tunnel + DNS prepared; `cloudflared tunnel login` certificate still pending)
- [ ] Workspace: confirm dialog for halt+start when running above offer
- [ ] Workspace: disk resize / quota (today: scheduling soft-cap only)
- [ ] Prefer a small default Ollama model for light chat smoke

## Blocked
- [x] Light `llm_chat` completion smoke — LFM local model served `GPU_FIT_METADATA_OK`; larger 27B placement remains safety-gated
- [ ] OAuth — blocked until auth priority
- [x] Exact EXE download URL freshness — v0.1.1 Release asset live

## Next 5
1. Discord blast: paste START_HERE blurb + current public portal URL
2. Friend trial: EXE or portal → invite → Share my PC / Use the pool / Invite friends
3. Workspace Start/Open from desktop when needed (RDP 3390)
4. Optional: smaller Ollama model for safe chat smoke
5. Keep secrets out of git (never `.env` / auth keys / `data/public_endpoints*` / `portal.db`)
