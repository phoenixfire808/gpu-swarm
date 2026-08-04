# TODO — GPU Pool (stream backlog)

Short evolving list. Detail lives in `CURRENT_PROGRESS.md`.  
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

## Now
- [ ] Drew: Ollama serve + model + worker restart → full chat e2e
- [ ] Packaging Worker: publish Windows EXE with local_endpoint + llm_chat
- [ ] Post member tip: `OPENAI_BASE_URL=http://127.0.0.1:8080/v1`

## Next
- [ ] Streaming on local endpoint (`stream=true`)
- [ ] Allowlisted `whisper_transcribe`
- [ ] Portal Discord OAuth (replace invite/password MVP)
- [ ] Worker advertise `llm_models` into `/status` for richer `/v1/models`

## Blocked
- [ ] Full LLM e2e — Ollama not running on host worker yet
- [ ] OAuth — blocked until auth priority
- [ ] Exact EXE download URL — blocked on packaging Worker Release asset name

## Next 5
1. Enable Ollama on Drew-Home + restart worker (`llm_ready=yes`)
2. Smoke: local endpoint → chat completion via pool
3. Packaging Worker Release + EXE
4. Tell friends (aariff01) Connect → Start local model endpoint
5. Keep secrets out of git (never `.env`)
