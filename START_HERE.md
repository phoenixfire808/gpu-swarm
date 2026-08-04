# Start here — GPU Pool (plain steps)

**Private compute club for Glitch Factor Discord.**  
Share spare power · use friends' PCs · invite others.

| | |
|--|--|
| **Invite code** | `glitch-factor` |
| **Windows app** | https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe |
| **More help** | [`LOGIN.md`](LOGIN.md) · [`DOWNLOAD.md`](DOWNLOAD.md) |

---

## What can you use this for?

1. **Run AI chat on friends' GPUs** — no NVIDIA needed on your laptop  
2. **Share idle evening/weekend GPU** — set a schedule so the group runs faster  
3. **Shared coding workspace** — optional Linux VM for projects together  
4. **Local AI for Cursor & agents** — localhost OpenAI URL, skip cloud GPU bills  
5. **Quick GPU health checks** — probe/CUDA checks across the pool  
6. **Chat & suggest** — talk with the pool on the web hub  
7. **Invite friends** — every PC that joins gives everyone more compute  

---

## Path A — Web browser (easiest)

**Just do this:**

1. Ask a friend in the pool for the **current web link** (looks like `https://….trycloudflare.com/portal`)
2. Open the link → type invite **`glitch-factor`** and your **Discord name** → click **Join the pool**
3. Pick one big button:
   - **Share my PC** — lend spare GPU/CPU (you choose how much)
   - **Use the pool** — run jobs on friends' machines (no fancy GPU needed on your laptop)
   - **Invite friends** — copy a message and send it on Discord

*Optional:* Tailscale = private network so friends connect safely. Most people use the web link instead.

---

## Path B — Windows app (automatic install)

**Just do this:**

1. Download: https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe
2. Double-click it. If Windows warns you → **More info** → **Run anyway** (only if you trust this GitHub repo)
3. Follow the numbered steps in the app — we install what you need; progress stays on screen
4. Type invite **`glitch-factor`** + your Discord name → **Save + Join**
5. Home → **Share my PC** / **Use the pool** / **Invite friends**

Files live under `%LOCALAPPDATA%\GPUPool\` (separate from your normal Python).

---

## What the buttons mean

| Button | Plain English |
|--------|----------------|
| **Share my PC** | Lend spare GPU/CPU. You set limits. Safety keeps Windows usable. |
| **Use the pool** | Run jobs on whoever is online. No NVIDIA needed on your laptop. |
| **Invite friends** | Copy a short message → paste in Discord → grow the pool. |
| **Connect tools** | URLs for apps and scripts (optional). |
| **Workspace** | Optional Linux desktop (CPU only — no GPU inside the VM). |

---

## What can you use this for?

| Why join | Plain English |
|----------|----------------|
| **Run AI on friends' GPUs** | No NVIDIA on your laptop? Still run chat and jobs on whoever is online. |
| **Share idle evening GPU** | Lend spare power at night or weekends — everyone trains faster together. |
| **Local AI for Cursor & agents** | `OPENAI_BASE_URL=http://127.0.0.1:8080/v1` — pool as a localhost API, no cloud GPU bill. |
| **Quick GPU health checks** | Probe / CUDA jobs across online machines — see what's really available. |
| **Grow the network** | Invite friends — every PC that joins gives everyone more compute. |

**When should we use your PC?** (Share my PC → Contribute)  
Pick **Always on**, **Nights & weekends**, **Next 2 hours**, or a **Custom daily window**. Outside your window the worker still checks in but **pauses new jobs** (like host GPU safety).

---

## Paste into Discord (grow the pool)

```text
**GPU Pool** — add your PC, everyone gets more compute.

Download: https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe
Start here: https://github.com/phoenixfire808/gpu-swarm/blob/master/START_HERE.md

1) Ask for the current web portal link
2) Invite **glitch-factor** + your Discord name
3) Share my PC · Use the pool · Invite friends

No NVIDIA? Still join — Use the pool or Share CPU only.
Private club — invite required.
```

**Host:** run `start-public-access.cmd` so friends can join without Tailscale. Live link is in `data/public_endpoints.share.txt` (changes when you restart the tunnel).
