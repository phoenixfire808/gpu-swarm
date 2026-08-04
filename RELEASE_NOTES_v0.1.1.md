# GPU Pool v0.1.1 — Windows EXE

One-click Windows joiner for the private Glitch Factor GPU pool.  
**Add your machine · grow the pool · everyone gets more compute.**

## Download

**[GPUPool.exe](https://github.com/phoenixfire808/gpu-swarm/releases/download/v0.1.1/GPUPool.exe)**  
(~29 MB onefile · also via [latest](https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe))

**Start in 5 minutes:** https://github.com/phoenixfire808/gpu-swarm/blob/master/START_HERE.md  
**Full login guide:** https://github.com/phoenixfire808/gpu-swarm/blob/master/LOGIN.md  
**Download / install details:** https://github.com/phoenixfire808/gpu-swarm/blob/master/DOWNLOAD.md

---

## Friend path (plain English)

1. **Download** `GPUPool.exe` (link above) — or open the host’s **current** public portal URL in a browser  
2. **SmartScreen** may warn (unsigned) → More info → Run anyway *if you trust this GitHub repo*  
3. **Sit back** — the wizard installs what you need (Python runtime/deps; Tailscale / VirtualBox+Vagrant only if you choose those steps). Progress stays on screen.  
4. **Invite** `glitch-factor` + your Discord display name → Join  
5. Home → pick one big button:
   - **Share my PC** — offer spare GPU/CPU (you set caps; safety ON)
   - **Use the pool** — run jobs (no NVIDIA needed on your laptop)
   - **Invite friends** — paste a Discord blurb and grow the network  

**Public portal:** ask the host for the current `https://….trycloudflare.com/portal` (URL rotates when the tunnel restarts — host must keep `cloudflared` / `start-public-access.cmd` up).  
**Tailscale (optional):** `http://100.85.165.84:8767/portal`

---

## What’s new since v0.1.0

- **Host GPU safety** (`host_protect`) — default ON so Contribute won’t freeze Windows  
- **Workspace** — optional Hermes agent-vms Linux desktop (CPU/RAM only; no NVIDIA passthrough)  
- **Network Hub** — clear Share / Use / Invite home; web hub Chat + Suggest  
- **Invite others** — punchy Discord blurbs + copy buttons to grow the pool  
- **Local model endpoint** + `llm_chat` job path (needs a contributor running Ollama)  
- **Verbose install** — step labels, percent / package names, logs stay visible  
- **Tk post_ui fix** — desktop app no longer crashes on background UI updates  

---

## Paste into Discord (grow the pool)

```text
**GPU Pool** — add your machine, grow the pool, everyone gets more compute.

Download: https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe
Start here: https://github.com/phoenixfire808/gpu-swarm/blob/master/START_HERE.md

1) Ask for the current public portal link (or Tailscale: http://100.85.165.84:8767/portal)
2) Invite **glitch-factor** + your Discord display name
3) Home → Share my PC · Use the pool · Invite friends

No NVIDIA? Still join — Use the pool or Share CPU (VRAM=0).
```

---

## Honest limits

- Public trycloudflare URLs **rotate** when the tunnel restarts — ask the host for a fresh link  
- Workspace VM does **not** get NVIDIA passthrough; GPU stays on the host pool worker  
- Full chat e2e needs a contributor with Ollama (`llm_ready`)  
- Not bundled: Torch/CUDA wheels, Discord secrets, scheduler/portal server processes  

See `START_HERE.md`, `DOWNLOAD.md`, and `LOGIN.md` on GitHub.
