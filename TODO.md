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

## Now
- [x] Packaging Worker: publish Windows EXE v0.1.0 with portable_python + diagnostics
- [ ] Discord `/pool` channel smoke (optional, stream)
- [ ] Post member quickstart + EXE link + “Submit diagnostics on failure” in Glitch Factor

## Next
- [ ] Allowlisted `whisper_transcribe` (reuse DrewLocalVoice/faster-whisper carefully)
- [ ] Bounded `llm_generate` job (not Ollama reverse-proxy)
- [ ] Portal Discord OAuth (replace invite/password MVP)
- [ ] More Utilize UX polish after first external joiner

## Blocked
- [ ] Whisper/LLM — blocked on design + deps story (intentional)
- [ ] OAuth — blocked until auth priority (repo is public)
## Next 5
1. Post EXE download + diagnostics tip in Glitch Factor  
2. Live smoke: portal Utilize + `/pool` + diagnostics submit  
3. Plan Whisper/LLM runners  
4. Keep secrets out of git (never `.env`)  
5. Rebuild EXE when friend-onboarding UX changes land again  
