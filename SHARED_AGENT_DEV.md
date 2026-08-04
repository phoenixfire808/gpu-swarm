# Shared Agent Development Space

**Ready-to-go path (source tip)** for friends to share compute and work on projects together.

**What this is for:** a private Glitch Factor co-op — join the hub, chat, share GPU/CPU, open an optional Workspace VM, and point agent tools at the pool’s OpenAI-compatible endpoint. Not a public marketplace. No Docker. No NVIDIA passthrough into the VM.

---

## Can Drew use it today?

**YES — from repo tip (source).** Published `GPUPool.exe` v0.1.0 is stale; use source until v0.1.1.

| Surface | Status today |
|---------|----------------|
| Hub / portal / chat / suggestions | Live when portal+scheduler run |
| Contribute / Utilize | Live |
| Install prereqs (Tailscale / VBox / Vagrant) | Automated detect-or-install (`scripts/install-prereqs.cmd`) |
| Workspace VM (Hermes / agent-ubuntu) | Ready — Start/Open from app or CLI; RDP `127.0.0.1:3390` |
| Local model endpoint | Code ready; needs Ollama up + worker `llm_ready=yes` |
| Multi-friend simultaneous project rooms | Partial — one primary Workspace + CLI linked clones (`session create`) |

---

## Friend path (minimal friction)

### A) From source (ready now)

```bat
cd C:\Users\Drew\Projects\gpu-swarm
scripts\install-prereqs.cmd
REM Approve UAC if asked. Finish Tailscale browser login if prompted (ONE clear step).
REM Optional unattended Tailscale: set GPU_SWARM_TAILSCALE_AUTHKEY=tskey-... (never commit)
start-gpu-pool-app.cmd
```

Wizard order:

1. **Welcome** — what GPU Pool is for  
2. **Network & Workspace** — Detect / Install & connect (skips what’s already installed)  
3. **Python & Deps** — Bootstrap if needed  
4. Identity → Connect → Caps → **Join**  
5. **Home** → Contribute or Utilize  

Invite: **`glitch-factor`** + Discord display name.

### B) Browser only (no EXE)

| Path | URL |
|------|-----|
| Public (when tunnel up) | Ask Drew / `data/public_endpoints.share.txt` → `https://….trycloudflare.com/portal` |
| Tailscale | `http://100.85.165.84:8767/portal` |
| Local (Drew PC) | `http://127.0.0.1:8767/portal` |

Login → peers on hub → Chat → Utilize / Contribute → optional Workspace.

### C) Manual steps that stay one click

| Step | Why |
|------|-----|
| UAC Yes | Windows requires admin for VirtualBox / Vagrant / Tailscale MSI |
| Tailscale browser login | Needs your account on Drew’s tailnet (or env auth key) |
| SmartScreen → More info → Run anyway | Unsigned EXE only (source path avoids this) |

---

## Drew host — launch checklist

```bat
cd C:\Users\Drew\Projects\gpu-swarm
start-scheduler-lan.cmd
start-portal.cmd
start-worker.cmd
start-bot.cmd
REM optional public friends without Tailscale:
start-public-access.cmd
REM optional model endpoint for agents:
ollama serve
start-local-endpoint.cmd
start-gpu-pool-app.cmd
```

Workspace (capped VM; GPU stays on host worker):

```bat
cd C:\Users\Drew\Projects\agent-vms
bin\agent-vm.cmd status
bin\agent-vm.cmd up
REM or from GPU Pool: Home -> Workspace -> Start / Open
mstsc /v:127.0.0.1:3390
REM login: vagrant / vagrant
```

Multi-session (linked clone — CLI today):

```bat
bin\agent-vm.cmd session create friend-a --cpus 2 --memory-mb 4096
bin\agent-vm.cmd session up friend-a
bin\agent-vm.cmd session info friend-a
```

---

## Capable harness (what works now)

| Layer | How |
|-------|-----|
| **Pool OpenAI endpoint** | `start-local-endpoint.cmd` → `OPENAI_BASE_URL=http://127.0.0.1:8080/v1` · model id `gpu-pool` |
| **Host inference** | Ollama on contributor (`llm_ready=yes`); jobs type `llm_chat` |
| **Workspace desktop** | RDP into agent-ubuntu — shared project via Vagrant synced folder; code/agents on the VM |
| **Agents (Cursor / OpenAI clients)** | Point at `OPENAI_BASE_URL` above — network GPU via API, not a PCI adapter in the VM |
| **Hermes** | Sole VM control: skill `agent-vm-control` / `bin/agent-vm.cmd` |

Example:

```bat
set OPENAI_BASE_URL=http://127.0.0.1:8080/v1
REM Cursor / Continue / Open WebUI / any OpenAI-compatible client
```

Honest: VirtualBox guests do **not** get NVIDIA passthrough. GPU work runs on the **host worker** through the pool.

See also: [`LOCAL_MODEL.md`](LOCAL_MODEL.md) · [`ADVANCED_VM.md`](ADVANCED_VM.md) · [`examples/coding_agent_pool.py`](examples/coding_agent_pool.py)

---

## Automated vs still manual

| Automated | Still manual (one clear step) |
|-----------|-------------------------------|
| Detect Tailscale / VirtualBox / Vagrant | UAC approve |
| Download + silent/winget install when missing | Tailscale login (browser) unless `GPU_SWARM_TAILSCALE_AUTHKEY` / `TS_AUTHKEY` set |
| Skip re-download if present | Invite code + display name |
| Wizard progress + Python bootstrap | First Workspace cold `vagrant up` (Drew once) |
| Contribute caps → VM CPU/RAM map | EXE publish v0.1.1 (source ready now) |

---

## Remaining gaps (multi-friend rooms)

- Pool UI “create project session” for linked clones (CLI works today)
- Fresh friend EXE with Network Hub + install-prereqs step
- Lighter default chat model on host (large local GGUF exists; first load is heavy — avoid stress tests)
- Per-session credentials / remote RDP bind (agent-vms phase 2)
