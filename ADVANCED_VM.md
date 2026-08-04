# Advanced: agent-vms (optional)

GPU Pool contributors should join with the **native host worker** (web portal or desktop app). That path uses real GPUs via `nvidia-smi` and soft caps for VRAM / CPU / RAM / disk.

**agent-vms** (`C:\Users\Drew\Projects\agent-vms` on Drew’s machine) is a **separate** stack: VirtualBox + Vagrant Ubuntu desktops for isolated agent workspaces (RDP/GUI). Hermes controls it via skill `agent-vm-control` — not through OpenClaw, and **not** through the GPU Pool Discord bot.

## What it is / isn’t

| Use agent-vms when… | Do **not** expect… |
|---------------------|--------------------|
| You want a full Linux desktop sandbox for an agent | NVIDIA GPU passthrough from a Windows VirtualBox VM |
| You need an isolated workspace beside the pool | The VM to magically become a GPU Pool worker with host VRAM |

VirtualBox on Windows does **not** reliably expose host NVIDIA GPUs into the guest. Do not document or demo “VM GPU dedication” as if passthrough works. Contribute spare compute from the **host** with the portal/desktop joiner instead.

## Link only

If `agent-vms` is present locally, see that project’s `AGENTS.md` / `CURRENT_PROGRESS.md` for `bin/agent-vm.cmd` usage. GPU Pool docs treat it as optional advanced reading, not the default join path.
