"""Discord bot for private GPU co-op pool commands."""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

import httpx

from gpu_swarm.config import discord_token, scheduler_config


def _guild_id() -> int | None:
    import os

    raw = (os.environ.get("DISCORD_GUILD_ID") or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _scheduler_base() -> str:
    c = scheduler_config()
    return f"http://{c.host if c.host != '0.0.0.0' else '127.0.0.1'}:{c.port}"


async def _api(method: str, path: str, **kwargs: Any) -> Any:
    url = f"{_scheduler_base()}{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.request(method, url, **kwargs)
        r.raise_for_status()
        return r.json()


def build_bot():
    import discord
    from discord.ext import commands

    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        print(f"[bot] logged in as {bot.user}", flush=True)
        try:
            gid = _guild_id()
            if gid is not None:
                guild = discord.Object(id=gid)
                bot.tree.copy_global_to(guild=guild)
                synced = await bot.tree.sync(guild=guild)
                print(f"[bot] synced {len(synced)} guild slash command(s) to {gid}", flush=True)
            else:
                synced = await bot.tree.sync()
                print(f"[bot] synced {len(synced)} global slash command(s)", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[bot] slash sync warning: {exc}", flush=True)

    @bot.hybrid_command(name="pool", description="Show GPU pool status")
    async def pool(ctx):
        await ctx.defer()
        try:
            st = await _api("GET", "/status")
        except Exception as exc:  # noqa: BLE001
            await ctx.send(f"Scheduler unreachable: `{exc}`")
            return
        lines = [
            f"**Workers online:** {st['workers_online']}/{st['workers_total']}",
            f"**VRAM free/total:** {st['free_vram_mb']} / {st['total_vram_mb']} MiB",
            f"**CPU cores:** {st.get('cpu_cores', 0)}",
            f"**RAM avail/total:** {st.get('ram_available_mb', 0)} / {st.get('ram_total_mb', 0)} MiB",
            f"**Disk free:** {st.get('disk_free_mb', 0)} MiB",
            f"**Jobs:** queued={st['jobs']['queued']} running={st['jobs']['running']} "
            f"done={st['jobs']['completed']} failed={st['jobs']['failed']}",
        ]
        if st.get("gpus"):
            lines.append("**GPUs:**")
            for g in st["gpus"][:12]:
                lines.append(f"- {g}")
        await ctx.send("\n".join(lines))

    @bot.hybrid_command(name="workers", description="List online workers")
    async def workers_cmd(ctx):
        await ctx.defer()
        try:
            workers = await _api("GET", "/workers")
        except Exception as exc:  # noqa: BLE001
            await ctx.send(f"Scheduler unreachable: `{exc}`")
            return
        online = [w for w in workers if w.get("online")]
        if not online:
            await ctx.send("No online workers.")
            return
        lines = []
        for w in online[:20]:
            names = ", ".join(g.get("name", "?") for g in (w.get("gpus") or []))
            lines.append(
                f"- **{w['name']}** vram={w['free_vram_mb']} MiB | "
                f"cpu={w.get('cpu_cores', 0)}c@{w.get('max_cpu_percent', '?')}% | "
                f"ram={w.get('ram_available_mb', 0)}/{w.get('ram_total_mb', 0)} MiB | "
                f"disk={w.get('disk_free_mb', 0)} MiB | {names or 'no GPU'} "
                f"| by={w.get('discord_user') or '-'}"
            )
        await ctx.send("\n".join(lines))

    @bot.hybrid_command(name="contribute", description="How to contribute spare GPU/CPU")
    async def contribute(ctx):
        msg = (
            "**Contribute spare GPU/CPU to this private co-op**\n"
            "1. Clone/open `gpu-swarm` on your Windows PC\n"
            "2. Set `GPU_SWARM_SCHEDULER_URL` to the pool host (LAN/Tailscale)\n"
            "3. Run: `python -m gpu_swarm worker --name YourDiscordName`\n"
            "4. Leave it idle-friendly; Ctrl+C to stop anytime\n"
            "Only allowlisted jobs run (`probe`, `pytorch_cuda_probe`) — no arbitrary shell."
        )
        await ctx.send(msg)

    @bot.hybrid_command(name="submit_probe", description="Submit a GPU probe job")
    async def submit_probe(ctx):
        await ctx.defer()
        try:
            job = await _api(
                "POST",
                "/jobs",
                json={
                    "job_type": "probe",
                    "payload": {},
                    "require_gpu": False,
                    "submitted_by": str(ctx.author),
                },
            )
        except Exception as exc:  # noqa: BLE001
            await ctx.send(f"Submit failed: `{exc}`")
            return
        await ctx.send(f"Queued **probe** job `{job['id']}` — use `/job_status {job['id']}`")

    @bot.hybrid_command(name="submit_compute", description="Submit CUDA matmul probe job")
    async def submit_compute(ctx, matrix_size: int = 1024):
        await ctx.defer()
        size = max(64, min(int(matrix_size), 4096))
        try:
            job = await _api(
                "POST",
                "/jobs",
                json={
                    "job_type": "pytorch_cuda_probe",
                    "payload": {"matrix_size": size},
                    "require_gpu": True,
                    "submitted_by": str(ctx.author),
                },
            )
        except Exception as exc:  # noqa: BLE001
            await ctx.send(f"Submit failed: `{exc}`")
            return
        await ctx.send(
            f"Queued **pytorch_cuda_probe** ({size}x{size}) job `{job['id']}`"
        )

    @bot.hybrid_command(name="job_status", description="Get job status / result")
    async def job_status(ctx, job_id: str):
        await ctx.defer()
        try:
            job = await _api("GET", f"/jobs/{job_id}")
        except Exception as exc:  # noqa: BLE001
            await ctx.send(f"Lookup failed: `{exc}`")
            return
        status = job.get("status")
        header = f"**Job** `{job_id}` — **{status}** ({job.get('job_type')})"
        if status == "completed" and job.get("result") is not None:
            text = json.dumps(job["result"], indent=2)
            if len(text) > 1800:
                text = text[:1800] + "\n… truncated"
            await ctx.send(f"{header}\n```json\n{text}\n```")
        elif status == "failed":
            await ctx.send(f"{header}\nError: `{job.get('error')}`")
        else:
            await ctx.send(f"{header}\nworker={job.get('worker_id')}")

    return bot


def run_bot() -> int:
    token = discord_token()
    if not token:
        print(
            "DISCORD_BOT_TOKEN not set.\n"
            "1. Copy .env.example → .env\n"
            "2. Create a Discord application bot token\n"
            "3. Set DISCORD_BOT_TOKEN=...\n"
            "4. Invite the bot to your private server with applications.commands + Send Messages\n"
            "Scheduler + worker work without Discord; bot is optional until token is set.",
            flush=True,
        )
        return 1
    bot = build_bot()
    bot.run(token)
    return 0


def bot_help_check() -> int:
    """Verify bot module wires without requiring a live token."""
    bot = build_bot()
    names = sorted(c.name for c in bot.commands)
    print("bot commands:", ", ".join(names))
    print("hybrid/slash ready: pool, workers, contribute, submit_probe, submit_compute, job_status")
    return 0


async def _unused():  # keep asyncio import used for type checkers / future
    await asyncio.sleep(0)
