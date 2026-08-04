# gpu-swarm — operate the private GPU co-op pool

Private Discord contribution pool. Scheduler + workers + optional Discord bot.
Project: `C:\Users\Drew\Projects\gpu-swarm`
Stack: Python FastAPI scheduler, SQLite, Windows workers, `nvidia-smi` + PyTorch CUDA jobs.
**No Docker. No mocks. No arbitrary shell jobs.**

## Commands

```bash
cd C:\Users\Drew\Projects\gpu-swarm
python -m gpu_swarm scheduler
python -m gpu_swarm worker --name Drew-Home
python -m gpu_swarm status
python -m gpu_swarm submit probe --wait
python -m gpu_swarm submit pytorch_cuda_probe --wait
python -m gpu_swarm bot --check
python -m gpu_swarm bot
```

## Env

Copy `.env.example` → `.env`. Set `DISCORD_BOT_TOKEN` only when ready.
Default bind `127.0.0.1:8765`. For Tailscale multi-house: `--host 0.0.0.0` + members set `GPU_SWARM_SCHEDULER_URL`.

## Safety

- Allowlisted jobs only: `probe`, `pytorch_cuda_probe`
- Do not wipe Hermes MEMORY.md / USER.md / SOUL.md / credentials / vault
- Prefer LAN/Tailscale; not a public marketplace
