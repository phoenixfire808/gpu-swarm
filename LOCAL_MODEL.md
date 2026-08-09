# Pool as a local GPU for your AI apps

**Honest framing:** this is a **network GPU via an OpenAI-compatible API**, not a fake Windows display adapter or PCI device. Apps that speak `OPENAI_BASE_URL` (Open WebUI, LM Studio, Continue, Cursor, etc.) can use the pool like a local model endpoint.

## Quick start (Utilize / client laptop)

CPU-only friends (no NVIDIA) run the **Local Pool Endpoint** on their machine:

```bat
cd C:\Users\Drew\Projects\gpu-swarm
start-local-endpoint.cmd
REM or: python -m gpu_swarm local-endpoint
```

Default bind: `http://127.0.0.1:8080` (falls back to `11434` if 8080 is taken).

Paste into your AI app:

```bat
set OPENAI_BASE_URL=http://127.0.0.1:8080/v1
```

| Client | Setting |
|--------|---------|
| Open WebUI | OpenAI API base → `http://127.0.0.1:8080/v1` |
| LM Studio | OpenAI-compatible → same URL |
| Continue | `apiBase` / OpenAI provider → same URL |
| Cursor | OpenAI-compatible base URL → same URL |

Model id to request: `gpu-pool` (or `gpu-pool/auto`). The worker picks a real Ollama model when present.

Desktop app: **Connect → Start local model endpoint** (copies `OPENAI_BASE_URL=…`).

## What it does

```
Your AI app  →  localhost:8080/v1/chat/completions
             →  GPU Pool scheduler (llm_chat job)
             →  contributor worker with Ollama / OpenAI-compatible runtime
             →  response back to your app
```

Endpoints on the local service:

- `GET /v1/models`
- `POST /v1/chat/completions` (non-streaming; `stream=true` later)
- `GET /api/tags` (Ollama-compatible model list)
- `GET /health`

## Host worker (Contribute) — what the host must run

`llm_chat` jobs only lease to workers with **`llm_ready=yes`**.

On the GPU machine (Host-PC or any GPU friend):

1. Install [Ollama](https://ollama.com) (already present on the host PC if you see `ollama.exe` under Local\Programs\Ollama).
2. Start it and pull a model:

```bat
ollama serve
ollama pull llama3.2
```

3. Confirm: `curl http://127.0.0.1:11434/api/tags`
4. Restart the GPU Pool worker (`start-worker.cmd` or desktop Contribute) so it logs:

```text
[worker] llm_ready=yes kind=ollama models=llama3.2
```

Optional env overrides on the worker:

```bat
set OLLAMA_HOST=http://127.0.0.1:11434
set GPU_SWARM_LLM_BASE_URL=ollama=http://127.0.0.1:11434
```

For the Docker-hosted Ollama runtime used by the current Windows worker, the host mapping is:

```text
http://127.0.0.1:11435  →  container Ollama :11434
```

The `ollama=` prefix matters: it selects Ollama's native `/api/chat` adapter and direct-response mode rather than treating Ollama as a generic OpenAI-compatible server.

If no LLM runtime is found, the job fails with clear enablement instructions (not a silent hang).

## Roles

| Role | Machine | What to run |
|------|---------|-------------|
| **Utilize** (client) | CPU laptop | Local endpoint + point AI apps at `OPENAI_BASE_URL` |
| **Contribute** (host) | GPU PC | Worker + Ollama (or other OpenAI-compatible server) |

## Job type `llm_chat` (allowlisted)

Payload:

```json
{
  "model": "gpu-pool",
  "messages": [{"role": "user", "content": "hello"}],
  "max_tokens": 512
}
```

SDK:

```python
from gpu_swarm.client import GPUPool
pool = GPUPool("http://127.0.0.1:8766")
job = pool.submit_llm_chat(
    [{"role": "user", "content": "hi"}],
    model="gpu-pool",
    max_tokens=256,
    wait=True,
)
print(job["result"]["message"])
```

## Safety / limits

- Allowlisted job only — no arbitrary shell from Discord/portal/agents.
- Local endpoint binds **localhost** by default (not the public internet).
- Results are size-capped (`MAX_RESULT_BYTES`).
- Streaming chat is not implemented yet — turn streaming off in clients.
- Private Tailscale/LAN pool (plus optional public tunnel when the host runs it).

## Troubleshooting receipts

### Discord job completes with no visible answer

A worker job can reach `completed` while the provider response contains an empty assistant message. The pool now treats that as a failed job and reports the reason in Discord. The common cause is a reasoning-capable model consuming the entire output budget without emitting final content. Use a bounded larger output budget or choose a mounted chat model that returns direct final text; do not expose hidden reasoning as the answer.

### Installed model versus mounted model

`/models` reports provider-installed models and live Ollama residency separately:

- `loaded`: currently resident in the provider runtime.
- `fit-now`: not resident, but the current local GPU group has enough free VRAM plus a safety reserve estimate.
- `installed-not-fit-now`: present on disk but not safe to auto-load with current GPU/display usage.

The Discord selector refuses `installed-not-fit-now` models instead of allowing an automatic OOM or desktop freeze.

### Same-worker GPU grouping

A model route labeled `same-worker-multi-gpu` means multiple GPUs are visible to one provider runtime on one physical worker. It does not mean VRAM from different PCs has been merged. Cross-machine model sharding requires a separate distributed inference cluster with explicit tensor/pipeline parallelism, private networking, and failure handling.

## Related

- `CONNECTING.md` — Contribute / Utilize / Connect map
- `examples/ollama_or_local_offload.md` — older notes (superseded for chat by this doc)
- Desktop Connect panel · Portal Connect → Local model endpoint
