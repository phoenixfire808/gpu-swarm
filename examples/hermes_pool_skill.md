# Hermes / Cursor — plug into GPU Pool

Project: `C:\Users\Drew\Projects\gpu-swarm`  
One-pager: [`CONNECTING.md`](../CONNECTING.md)

## Env

```bat
set GPU_SWARM_SCHEDULER_URL=http://127.0.0.1:8766
REM members on Tailscale:
REM set GPU_SWARM_SCHEDULER_URL=http://100.85.165.84:8766
```

## Python (under 5 lines)

```python
from gpu_swarm.client import GPUPool
pool = GPUPool()
print(pool.status()["workers_online"])
result = pool.submit_probe(wait=True)   # or pool.submit_cuda_probe(wait=True)
```

Same HTTP as [`coding_agent_pool.py`](coding_agent_pool.py): `POST /jobs`, `GET /jobs/{id}`, `GET /status`.

## CLI

```bash
cd C:\Users\Drew\Projects\gpu-swarm
python -m gpu_swarm utilize status
python -m gpu_swarm utilize probe --wait
python -m gpu_swarm utilize cuda --wait
python examples/coding_agent_pool.py --job probe
python examples/use_pool_from_script.py --cuda
```

## Rules

- Allowlisted jobs only: `probe`, `pytorch_cuda_probe`
- No Docker / no mocks / no arbitrary shell on workers
- Do not expose scheduler to the public internet
- Do not wipe Hermes MEMORY/USER/SOUL/credentials/vault
