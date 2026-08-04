# Ollama / local models ↔ GPU Pool (honest v1)

**Short answer:** v1 does **not** proxy Ollama, OpenAI-compatible `/v1/chat`, or arbitrary inference.
The pool runs **allowlisted jobs only**. Today that means connectivity + CUDA proof jobs — not “send my LLM prompt to a remote GPU.”

Use this guide if you run Ollama / LM Studio / a coding agent locally and want a real path into the co-op pool.

## What works today

| Job type | What it does | Useful for |
|----------|--------------|------------|
| `probe` | Live `nvidia-smi` inventory on a worker | “Is the pool up? Who has free VRAM?” |
| `pytorch_cuda_probe` | Bounded CUDA (or CPU fallback) matmul via PyTorch | Prove a worker can run real GPU compute |

Submit from a coding agent:

```bat
cd C:\Users\Drew\Projects\gpu-swarm
python examples\coding_agent_pool.py --job probe --scheduler-url http://127.0.0.1:8766
python examples\coding_agent_pool.py --job pytorch_cuda_probe --matrix-size 1024
```

Or CLI:

```bat
python -m gpu_swarm submit probe --wait
python -m gpu_swarm submit pytorch_cuda_probe --matrix-size 1024 --wait
```

Remote members (Tailscale): set `GPU_SWARM_SCHEDULER_URL=http://100.85.165.84:8766`.

## What does **not** work yet

- Pointing Ollama `OLLAMA_HOST` at the scheduler
- Offloading chat/completions / embeddings through the pool
- Arbitrary shell, `pip install`, or “run this Python file” jobs
- Whisper / STT as a pool job (planned; see below)

That is intentional: Discord / portal / agents must not get remote code execution on members’ PCs.

## Practical local + pool split (v1)

Keep **inference local**; use the pool for **capacity discovery and CUDA health**:

1. Run Ollama (or your IDE model) on your own GPU as usual.
2. Before a heavy local job, call `coding_agent_pool.py --job probe` (or Discord `/workers`) to see who else is online and how much free VRAM they advertise.
3. Use `pytorch_cuda_probe` to confirm a contributor’s CUDA stack is alive before you ask them to host a future allowlisted job type.

Contribute your spare GPU via portal / desktop app / CLI worker — see [`CONNECTING.md`](../CONNECTING.md).

## Path to Whisper / LLM job types later

There are **no Whisper runners in this repo yet**. Progress note: reuse DrewLocalVoice / faster-whisper later without breaking that stack.

When adding a real useful type (e.g. `whisper_transcribe` or a bounded `llm_generate`):

1. **Design a narrow contract** — fixed model id, max audio/token size, no shell, no download URLs from Discord.
2. **Register the name** in `gpu_swarm/__init__.py` → `ALLOWED_JOB_TYPES`.
3. **Implement a runner** in `gpu_swarm/jobs.py` and add it to `RUNNERS`.
4. **Wire submit surfaces** that should expose it:
   - Scheduler already rejects unknown types via `ALLOWED_JOB_TYPES`
   - Portal Utilize allowlist (`UTILIZE_JOB_TYPES` / catalog in `app_backend.py`)
   - Discord slash only if members should trigger it
   - CLI `choices=` / docs / `examples/coding_agent_pool.py` `ALLOWED`
5. **Ship on workers that already have the deps** — do not force every contributor to install Whisper/LLM stacks.
6. **Cap results** (`MAX_RESULT_BYTES`) and keep payloads bounded.

### Sketch: future `whisper_transcribe` (not implemented)

```text
payload: { "audio_b64": "...", "language": "en", "model": "base" }  # size-capped
runner: call local faster-whisper on the leasing worker only
result: { "text": "...", "segments": [...], "device": "cuda:0" }
```

### Sketch: future bounded LLM (not “open Ollama”)

Prefer a **single allowlisted model + max tokens**, invoked by the worker process — not a reverse-proxy to members’ Ollama daemons. That keeps the security story the same as `pytorch_cuda_probe`.

## How to add a new allowlisted job type (checklist)

Files to touch:

| Step | File |
|------|------|
| 1. Name | `gpu_swarm/__init__.py` — `ALLOWED_JOB_TYPES` |
| 2. Runner | `gpu_swarm/jobs.py` — function + `RUNNERS[...]` |
| 3. Submit defaults | `gpu_swarm/scheduler.py` / CLI if special `require_gpu` / payload |
| 4. Portal / app | `gpu_swarm/portal.py`, `gpu_swarm/app_backend.py` catalog |
| 5. Discord (optional) | `gpu_swarm/bot.py` |
| 6. Docs / agent script | this file, `CONNECTING.md`, `examples/coding_agent_pool.py` |

**Do not** add `shell`, `pip_list`, or generic `echo` jobs — even “safe” shell expands into RCE under Discord/agent pressure.

## Safety reminders

- Scheduler/portal stay on Tailscale / LAN — not the public internet.
- Never put Discord bot tokens in agent prompts or example scripts.
- No Docker in this project’s ops path.
