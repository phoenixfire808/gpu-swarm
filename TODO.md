# TODO — GPU Pool (stream backlog)

Short evolving list. Detail lives in `CURRENT_PROGRESS.md`.  
Updated: 2026-08-04 · GitHub: https://github.com/phoenixfire808/gpu-swarm

## Done
- [x] Scheduler + workers + heartbeats (GPU/CPU/RAM/disk)
- [x] Jobs: `probe`, `pytorch_cuda_probe`
- [x] Discord **GPU Pool** bot (6 slash cmds → Glitch Factor)
- [x] Portal Contribute / Utilize (`0.0.0.0:8767`, Tailscale OK)
- [x] Desktop one-stop wizard (Save+Join / Leave / Utilize)
- [x] `CONNECTING.md` + `GPUPool` client + coding examples
- [x] Prereq / joiner-deps scripts (isolated `%LOCALAPPDATA%\GPUPool\venv`)
- [x] Live smoke: scheduler, worker GPUs, portal 200, e2e jobs
- [x] `gh auth login` (phoenixfire808)
- [x] Public GitHub publish + push — https://github.com/phoenixfire808/gpu-swarm
- [x] `DOWNLOAD.md` + EXE-first Discord quickstart + `.gitignore` PyInstaller rules (`!gpu_pool.spec`)
- [x] Friend diagnostics: `diagnostics.py` + Copy/Submit UI + portal `/api/diagnostics`
- [x] Portable Python bootstrap: `portable_python.py` + wizard + EXE first-run hook
- [x] Local model endpoint + Connect Start/Stop UI (`LOCAL_MODEL.md`, `llm_chat`)

## Now
- [x] Packaging Worker: publish Windows EXE v0.1.0 with portable_python + diagnostics
- [ ] Rebuild/publish EXE with Connect local-endpoint controls
- [ ] Discord `/pool` channel smoke (optional, stream)
- [ ] Post member quickstart + EXE link + “Submit diagnostics on failure” in Glitch Factor

## Next
- [ ] Ensure ≥1 worker has Ollama (or compat) for `llm_chat`
- [ ] Allowlisted `whisper_transcribe` (reuse DrewLocalVoice/faster-whisper carefully)
- [ ] Portal Discord OAuth (replace invite/password MVP)
- [ ] More Utilize UX polish after first external joiner

## Blocked
- [ ] Whisper — blocked on design + deps story (intentional)
- [ ] OAuth — blocked until auth priority (repo is public)
- [ ] EXE with local-endpoint Connect UI — needs packaging rebuild

## Next 5
1. Rebuild GPUPool.exe so Connect local-endpoint ships  
2. Post EXE-first member quickstart + LOCAL_MODEL tip in Glitch Factor  
3. Live smoke: Start local endpoint → paste into an AI app  
4. Ollama on a contributor worker for real chat  
5. Keep secrets out of git (never `.env`)  
