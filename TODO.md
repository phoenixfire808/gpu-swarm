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
- [ ] Packaging Worker: publish Windows EXE with portable_python + diagnostics
- [ ] Discord `/pool` channel smoke (optional, stream)
- [ ] Post member quickstart + “Submit diagnostics on failure” in Glitch Factor

## Next
- [ ] Allowlisted `whisper_transcribe` (reuse DrewLocalVoice/faster-whisper carefully)
- [ ] Bounded `llm_generate` job (not Ollama reverse-proxy)
- [ ] Portal Discord OAuth (replace invite/password MVP)
- [ ] More Utilize UX polish after first external joiner

## Blocked
- [ ] Whisper/LLM — blocked on design + deps story (intentional)
- [ ] OAuth — blocked until auth priority (repo is public)
- [ ] Exact EXE download URL — blocked on packaging Worker Release asset name

## Next 5
1. Packaging Worker Release + EXE (diagnostics + portable Python)  
2. Post EXE-first member quickstart + diagnostics tip in Glitch Factor  
3. Live smoke: portal Utilize + `/pool` + diagnostics submit  
4. Plan Whisper/LLM runners  
5. Keep secrets out of git (never `.env`)
