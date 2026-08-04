# Start here — GPU Pool in 5 minutes

**Private co-op compute for Glitch Factor Discord.**  
Share spare GPU/CPU · use friends’ machines · invite others so everyone gets more compute.

| | |
|--|--|
| **Invite code** | `glitch-factor` |
| **Windows app** | https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe |
| **Full login guide** | [`LOGIN.md`](LOGIN.md) |
| **Download details** | [`DOWNLOAD.md`](DOWNLOAD.md) |

---

## Why join?

- **More compute together** — every PC that joins makes the pool stronger  
- **No NVIDIA? Still useful** — Use the pool, or Share CPU only (VRAM=0)  
- **You stay in control** — caps you set; host GPU safety ON by default  
- **Grow it** — Invite friends with one Discord paste  

Not a public marketplace. Invite required. No Docker.

---

## Path A — Browser (fastest)

1. Ask a pool member for the **current** public portal link  
   (`https://….trycloudflare.com/portal` — links **rotate** when the host restarts the tunnel)
2. Open it → invite **`glitch-factor`** + your Discord display name → **Join the pool**
3. Pick one big button:
   - **Share my PC** — offer spare GPU/CPU  
   - **Use the pool** — run jobs on online friends  
   - **Invite friends** — copy the Discord blurb and grow the network  

Optional private path (Tailscale): `http://100.85.165.84:8767/portal`

---

## Path B — Windows EXE (automatic install)

1. Download: https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe  
2. Run it. If SmartScreen appears → **More info** → **Run anyway** (only if you trust this GitHub repo)  
3. Sit back — the wizard installs what you need (Python runtime/deps; Tailscale / VirtualBox+Vagrant only if you choose those steps). Progress stays on screen.  
4. Enter invite **`glitch-factor`** + Discord name → **Save + Join**  
5. Home → **Share my PC** / **Use the pool** / **Invite friends**

First-run files live under `%LOCALAPPDATA%\GPUPool\` (isolated — not your global Python).

---

## After you’re in

| Button | Plain English |
|--------|----------------|
| **Share my PC** | Contribute spare GPU/CPU. You set how much. Safety keeps Windows usable. |
| **Use the pool** | Run allowlisted jobs (`probe`, CUDA probe, chat) on online workers. |
| **Invite friends** | Copy portal + invite + download link → paste in Discord. |
| **Connect tools** | Scheduler / local model URLs for agents and scripts. |
| **Workspace** | Optional Linux desktop (CPU/RAM only — no NVIDIA passthrough). |
| **Chat / Suggest** | Talk with the pool; send improvement ideas. |

---

## Paste this into Discord (grow the pool)

```text
**GPU Pool** — add your machine, grow the pool, everyone gets more compute.

Download (Windows): https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe
Start here: https://github.com/phoenixfire808/gpu-swarm/blob/master/START_HERE.md

1) Ask for the current public portal link (or use Tailscale: http://100.85.165.84:8767/portal)
2) Invite **glitch-factor** + your Discord display name
3) Home → Share my PC · Use the pool · Invite friends

No NVIDIA? Still join — Use the pool or Share CPU (VRAM=0).
Private co-op — invite required. No Docker.
```

Host: keep `start-public-access.cmd` running so friends can join without Tailscale. URL is in `data/public_endpoints.share.txt` (gitignored; rotates on tunnel restart).
