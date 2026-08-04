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
- [x] Prereq / joiner-deps scripts
- [x] Live smoke: scheduler, worker GPUs, portal 200, e2e jobs
- [x] `gh auth login` (phoenixfire808)
- [x] Public GitHub publish + push — https://github.com/phoenixfire808/gpu-swarm

## Now
- [ ] Discord `/pool` channel smoke (optional, stream)
- [ ] Post member quickstart + repo URL in Glitch Factor (https://github.com/phoenixfire808/gpu-swarm)

## Next
- [ ] Allowlisted `whisper_transcribe` (reuse DrewLocalVoice/faster-whisper carefully)
- [ ] Bounded `llm_generate` job (not Ollama reverse-proxy)
- [ ] Portal Discord OAuth (replace invite/password MVP)
- [ ] More Utilize UX polish after first external joiner

## Blocked
- [ ] Whisper/LLM — blocked on design + deps story (intentional)
- [ ] OAuth — blocked until auth priority (repo is public)

## Next 5
1. Live smoke: portal Utilize + `/pool`  
2. Post member quickstart + repo URL in Glitch Factor  
3. Plan Whisper/LLM runners  
4. Portal Discord OAuth when ready  
5. Keep secrets out of git (never `.env`)
