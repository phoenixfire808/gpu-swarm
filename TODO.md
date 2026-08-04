# TODO — GPU Pool (stream backlog)

Short evolving list. Detail lives in `CURRENT_PROGRESS.md`.  
Updated: 2026-08-04

## Done
- [x] Scheduler + workers + heartbeats (GPU/CPU/RAM/disk)
- [x] Jobs: `probe`, `pytorch_cuda_probe`
- [x] Discord **GPU Pool** bot (6 slash cmds → Glitch Factor)
- [x] Portal Contribute / Utilize (`0.0.0.0:8767`, Tailscale OK)
- [x] Desktop one-stop wizard (Save+Join / Leave / Utilize)
- [x] `CONNECTING.md` + `GPUPool` client + coding examples
- [x] Prereq / joiner-deps scripts
- [x] Live smoke: scheduler, worker GPUs, portal 200, e2e jobs

## Now
- [ ] Commit dirty **safe** files (no `.env` / token paste / `data/`)
- [ ] `gh auth login`
- [ ] `gh repo create` + push `origin`
- [ ] Discord `/pool` channel smoke (optional, stream)
- [ ] Post member quickstart + repo URL in Glitch Factor

## Next
- [ ] Allowlisted `whisper_transcribe` (reuse DrewLocalVoice/faster-whisper carefully)
- [ ] Bounded `llm_generate` job (not Ollama reverse-proxy)
- [ ] Portal Discord OAuth (replace invite/password MVP)
- [ ] More Utilize UX polish after first external joiner

## Blocked
- [ ] **GitHub push** — blocked on `gh` auth + missing remote
- [ ] Whisper/LLM — blocked on design + deps story (intentional)
- [ ] OAuth — blocked until publish + auth priority

## Next 5
1. Commit safe tree  
2. `gh auth login`  
3. Create remote + push  
4. Live smoke: portal Utilize + `/pool`  
5. Plan Whisper/LLM runners (post-publish)
