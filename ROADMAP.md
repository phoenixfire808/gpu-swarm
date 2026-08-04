# ROADMAP — GPU Pool

Near-term → later. Detail and live status: [`CURRENT_PROGRESS.md`](CURRENT_PROGRESS.md) · checklist: [`TODO.md`](TODO.md).  
**Updated:** 2026-08-04

## Now (ship / verify)

1. **Ready-to-go shared agent-dev space (source tip)** — hub + worker + Workspace + `install-prereqs` automation. See [`SHARED_AGENT_DEV.md`](SHARED_AGENT_DEV.md).
2. **Automated friend prereqs** — `scripts/install-prereqs.ps1` (+ wizard **Network & Workspace**): Tailscale / VirtualBox / Vagrant detect-or-install; UAC + Tailscale login remain one clear click.
3. **Host GPU safety (`host_protect`)** — shipped; live on Drew-Home; include in next EXE.
4. **Ollama + `llm_chat`** — host Ollama up; workers can advertise `llm_ready=yes`. Prefer light models for chat smoke (large GGUF already local — avoid stress loads).
5. **Packaging Worker EXE v0.1.1+** — still required for one-click friends; source path is the ready path today.
6. **Member tip** — `OPENAI_BASE_URL=http://127.0.0.1:8080/v1` (or `:18080` if 8080 busy).
7. **Workspace VM MVP** — Home → Workspace / Hermes `agent-vm`; multi-session via CLI `session create`.
8. **Network Hub + pool chat + suggestions** — shipped in source.

## Next

| Item | Notes |
|------|--------|
| **Shared Agent Development Space** | Multi-friend project rooms UI; expose `session create` from Pool; synced-folder project story |
| Streaming local endpoint | `stream=true` on `/v1/chat/completions` |
| Chat WebSocket (optional) | Polling works; WS if tunnel-friendly |
| Worker `llm_models` → `/status` | Richer OpenAI-compatible `/v1/models` |
| Stable public URL | Durable tunnel / DNS when Drew wants friends without Tailscale |
| Allowlisted `whisper_transcribe` | Same job-lease pattern as `llm_chat` |
| Portal Discord OAuth | Replace invite/password MVP |
| Workspace polish | Halt+start confirm when above offer; multi-session UI; EXE includes bridge + install-prereqs |
| agent-vms phase 2 | Tailscale/VPN + per-session creds (in `agent-vms` repo) |

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
