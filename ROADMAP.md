# ROADMAP — GPU Pool

Near-term → later. Detail and live status: [`CURRENT_PROGRESS.md`](CURRENT_PROGRESS.md) · checklist: [`TODO.md`](TODO.md).  
**Updated:** 2026-08-04

## Now (ship / verify)

1. **Host GPU safety (`host_protect`)** — shipped in source (default ON). Confirm live on Drew-Home; include in next EXE.
2. **Ollama + `llm_chat` e2e** — `ollama serve` + model pull + worker `llm_ready=yes` → chat via local endpoint.
3. **Packaging Worker EXE** — rebuild `GPUPool.exe` with `host_protect` + local endpoint + `llm_chat` (fastapi bundled).
4. **Member tip** — friends use `OPENAI_BASE_URL=http://127.0.0.1:8080/v1`.
5. **Living docs habit** — keep TODO / ROADMAP / CHANGELOG / CURRENT_PROGRESS current on every ship.

## Next

| Item | Notes |
|------|--------|
| Streaming local endpoint | `stream=true` on `/v1/chat/completions` |
| Worker `llm_models` → `/status` | Richer OpenAI-compatible `/v1/models` |
| Stable public URL | Durable tunnel / DNS when Drew wants friends without Tailscale |
| Allowlisted `whisper_transcribe` | Same job-lease pattern as `llm_chat` |
| Portal Discord OAuth | Replace invite/password MVP |
| **agent-vms ↔ GPU Pool integration** | **In progress / planned** — optional workspace/VM mode beside host worker; Hermes owns VMs; **no** fake GPU passthrough (see [`ADVANCED_VM.md`](ADVANCED_VM.md)) |

## Later

- Stronger Utilize UX for laptop / no-NVIDIA friends
- Quotas / fair-share scheduling across contributors
- Signed Windows builds (reduce SmartScreen friction)
- Broader allowlisted job set (still no arbitrary shell from Discord)
- agent-vms phase 2: Tailscale/VPN, per-session credentials (in `agent-vms` repo)

## Explicit non-goals (v1)

- Docker for this stack
- Public marketplace
- NVIDIA GPU passthrough into VirtualBox guests as the join path
- Heavy CUDA / PyInstaller stress on Drew’s desktop during agent work

## Cross-repo

| Repo | Role |
|------|------|
| [gpu-swarm](https://github.com/phoenixfire808/gpu-swarm) | Pool product (scheduler, portal, worker, EXE, Discord) |
| `agent-vms` (local; publish when ready) | Hermes-controlled VirtualBox/Vagrant workspaces — separate control plane |
