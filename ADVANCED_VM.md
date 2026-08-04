# Workspace VM — GPU Pool ↔ agent-vms

GPU Pool and **agent-vms** are one product surface on Drew’s Windows host:

1. **Contribute** — host worker offers real GPU/CPU/RAM/disk under your caps (+ `host_protect`).
2. **Workspace** — Hermes starts a VirtualBox/Vagrant Ubuntu desktop **using only the CPU/RAM share you chose** (not the whole PC).
3. **Utilize / local model** — pool jobs and `llm_chat` still run on the **host worker** for real NVIDIA access.

Control plane: **Hermes** skill `agent-vm-control` → `bin/agent-vm.cmd` or  
`%LOCALAPPDATA%\hermes\scripts\agent-vm.ps1`.  
Not OpenClaw. No Docker.

## How Drew opens the integrated flow

```bat
cd C:\Users\Drew\Projects\gpu-swarm
start-gpu-pool-app.cmd
```

Then: **Home → 4 · Workspace** (or **Connect → Workspace** card) → **Start / Open workspace**.

That:

1. Reads `data/joiner_settings.json` Contribute caps + `host_protect`
2. Maps them to VirtualBox `--cpus` / `--memory`
3. Calls Hermes `agent-vm` (apply caps if powered off, start if needed)
4. Opens RDP: `mstsc /v:127.0.0.1:3390` · login `vagrant` / `vagrant`

CLI / backend (no UI):

```bat
python -c "from gpu_swarm.app_backend import workspace_status, open_workspace; print(workspace_status()); print(open_workspace())"
```

Hermes direct:

```bat
C:\Users\Drew\Projects\agent-vms\bin\agent-vm.cmd status
C:\Users\Drew\Projects\agent-vms\bin\agent-vm.cmd resources show agent-ubuntu
C:\Users\Drew\Projects\agent-vms\bin\agent-vm.cmd resources apply agent-ubuntu --cpus 2 --memory-mb 4096
```

## Resource mapping (share caps → VM)

| Contribute / host_protect | VirtualBox VM | Notes |
|---------------------------|---------------|--------|
| `max_cpu_percent` (clamped by host_protect ≤70% default) | `vb.cpus` | `floor(host_cores × pct/100)`, leave ≥1 host CPU, max 8 |
| `max_ram_mb` (or auto from share × available RAM) | `vb.memory` | Reserve ≥2 GiB for host; floor 1024 MiB; ceiling 16 GiB |
| `max_vram_mb` / GPU offer | **not applied to VM** | Stays on **host worker** for pool CUDA / `llm_chat` |
| `max_disk_gb` | **not resized on VM** | Pool scheduling soft-cap / capacity ad only |
| (display only) | `--vram` 64 MiB | VirtualBox **framebuffer** VRAM — not NVIDIA memory |

Caps change only when the VM is **powered off** (`Halt` then `Start / Open`). If the VM is already running above the offer, the UI says so.

## Honest GPU limitations

**VirtualBox on Windows does not reliably pass through host NVIDIA GPUs.**

Do **not** expect `nvidia-smi` inside the Ubuntu guest, or “the shared GPU inside the VM.”

Correct model:

| Layer | What it uses |
|-------|----------------|
| Workspace VM | Capped CPU + RAM + XFCE via RDP/console |
| GPU Pool worker on host | Real GPU under Contribute VRAM/CPU caps + host_protect |

## Multi-session (agent-vms)

```bat
bin\agent-vm.cmd session create friend-a --cpus 2 --memory-mb 4096
bin\agent-vm.cmd session up friend-a
bin\agent-vm.cmd session info friend-a
```

Linked clones from golden `agent-ubuntu` snapshot `baseline` (no box redownload). GPU Pool MVP drives the **primary** session; clones are ready for later “rentable workspace” work.

## First-time VM bring-up

If `agent-ubuntu` was never created, do **one** Hermes bring-up (can download the Ubuntu box — do not trigger from the app automatically):

```bat
C:\Users\Drew\Projects\agent-vms\bin\agent-vm.cmd up
C:\Users\Drew\Projects\agent-vms\bin\agent-vm.cmd snapshot save baseline
```

After that, GPU Pool **Start / Open** is the daily path.

## Related

- agent-vms: `AGENTS.md`, `CURRENT_PROGRESS.md`, skill `agent-vm-control`
- Pool join/caps: `CONNECTING.md`, `LOGIN.md`
- Host safety: `gpu_swarm/host_protect.py`
