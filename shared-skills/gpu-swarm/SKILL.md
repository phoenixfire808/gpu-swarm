# gpu-swarm — operate the private GPU co-op pool

Private Discord contribution pool. Scheduler + workers + optional Discord bot.
Project: `C:\Users\Drew\Projects\gpu-swarm`
Stack: Python FastAPI scheduler, SQLite, Windows workers, `nvidia-smi` + PyTorch CUDA jobs.
**No Docker. No mocks. No arbitrary shell jobs.**

## Utilize from code (coding agents)

```python
from gpu_swarm.client import GPUPool
pool = GPUPool()  # or set GPU_SWARM_SCHEDULER_URL
pool.status()
pool.submit_probe(wait=True)
pool.submit_cuda_probe(wait=True)
```

Same scheduler API as `examples/coding_agent_pool.py`: `POST /jobs`, `GET /status`.  
See `CONNECTING.md` and `examples/hermes_pool_skill.md`.

## Commands

```bash
cd C:\Users\Drew\Projects\gpu-swarm
python -m gpu_swarm scheduler
python -m gpu_swarm worker --name Drew-Home
python -m gpu_swarm utilize status
python -m gpu_swarm utilize probe --wait
python -m gpu_swarm utilize cuda --wait
python -m gpu_swarm submit probe --wait
python -m gpu_swarm bot --check
python -m gpu_swarm bot
python examples/coding_agent_pool.py --job probe
```

## Env

Copy `.env.example` → `.env`. Set `DISCORD_BOT_TOKEN` only when ready.
Scheduler port **8766** (8765 is Robinhood). Tailscale: `--host 0.0.0.0` + `GPU_SWARM_SCHEDULER_URL=http://100.85.165.84:8766`.

## Safety

- Allowlisted jobs only: `probe`, `pytorch_cuda_probe`
- Do not wipe Hermes MEMORY.md / USER.md / SOUL.md / credentials / vault
- Prefer LAN/Tailscale; not a public marketplace
