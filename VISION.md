# Vision — plug in any home machine

**Goal:** Anyone Drew invites can open a **browser**, log in, and contribute spare home hardware — **GPU, CPU, RAM, and SSD** — the same way you’d plug a PC into a co-op pool.

**How members join (target UX):** open the web portal → sign in → set soft caps → Join. Portal is expected at **`http://<host>:8767/portal`** (scheduler stays on **`:8766`**). Desktop app and CLI remain supported power-user paths.

## Honest v1 (what’s real today vs later)

| Resource | v1 truth |
|----------|----------|
| **GPU / CPU** | Jobs actually run here — probe / CUDA (and later allowlisted work) on the worker that leases them. |
| **RAM / SSD** | Advertised for **scheduling and capacity planning** (soft caps, “who has headroom”). Not a magic shared disk or pooled memory fabric. |
| **Browser login** | Primary UX for friends; Discord bot for status/submit; native desktop joiner for power users. |

No public marketplace. Trust-LAN / Tailscale. Allowlisted jobs only — no arbitrary shell from Discord.

See also: [`README.md`](README.md), [`DISCORD_MEMBER_QUICKSTART.md`](DISCORD_MEMBER_QUICKSTART.md), [`ADVANCED_VM.md`](ADVANCED_VM.md).
