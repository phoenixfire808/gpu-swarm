"""Discord bot for the private GPU Pool.

The bot is intentionally an allowlisted control surface:
- onboarding/help is conversational but deterministic;
- model discovery comes from the scheduler's live ``/models`` catalog;
- chat submits only ``llm_chat`` jobs and never executes arbitrary shell;
- provider credentials stay on contributor machines and are never requested in Discord.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any

import httpx

from gpu_swarm.config import discord_token, scheduler_config


def _guild_id() -> int | None:
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
        response = await client.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()


def _clip(text: str, limit: int = 1900) -> str:
    text = str(text or "")
    return text if len(text) <= limit else text[: limit - 24] + "\n…(truncated)"


def _model_label(entry: dict[str, Any]) -> str:
    provider = str(entry.get("provider") or "openai-compatible")
    worker = str(entry.get("worker_name") or "worker")
    vram = int(entry.get("free_vram_mb") or 0)
    group = entry.get("gpu_group") or {}
    gpu_count = int(group.get("count") or 0) if isinstance(group, dict) else 0
    placement = f"{gpu_count} GPU group" if gpu_count > 1 else "1 GPU"
    state = str(entry.get("mount_state") or "unknown")
    return f"{entry.get('model')} · {provider} · {worker} · {placement} · {state} · {vram} MiB free"


def _setup_text(topic: str) -> str:
    topic = (topic or "start").strip().lower()
    if topic == "contribute":
        return (
            "**Share your PC with GPU Pool**\n"
            "1. Install/open `GPUPool.exe` or clone this repo.\n"
            "2. Enter the host portal URL and invite code supplied by the pool owner.\n"
            "3. Set your own VRAM/CPU/RAM/disk caps.\n"
            "4. Click **Share my PC** or run `python -m gpu_swarm worker`.\n"
            "5. Stop or pause it any time. Your caps are owned by your worker; Discord cannot raise them.\n\n"
            "Only allowlisted GPU/CPU/LLM jobs can run. No arbitrary shell is accepted."
        )
    if topic == "use":
        return (
            "**Use the shared pool**\n"
            "- `/pool` shows capacity and job counts.\n"
            "- `/workers` shows online contributors.\n"
            "- `/submit_probe` runs a safe inventory probe.\n"
            "- `/submit_compute` runs a bounded CUDA/CPU matmul probe.\n"
            "- `/models` shows LLMs currently mounted on online contributors.\n"
            "- `/ask` chats with the model you select from that list."
        )
    if topic == "llm":
        return (
            "**Use a shared LLM**\n"
            "1. Run `/models` and choose a currently mounted model.\n"
            "2. Ask with `/ask question: ...`.\n"
            "3. The scheduler routes the job only to a worker advertising that exact model.\n"
            "4. If the picker says `2-GPU same-worker group`, that runtime can use both local cards to fit a larger model.\n\n"
            "If no models appear, ask a contributor to follow `/route` on their own machine."
        )
    if topic == "custom":
        return (
            "**Mount your own LLM**\n"
            "Run Ollama, LM Studio, vLLM, llama.cpp, or another OpenAI-compatible server locally.\n"
            "Set `GPU_SWARM_LLM_BASE_URL` to its base URL, for example:\n"
            "`GPU_SWARM_LLM_BASE_URL=http://127.0.0.1:1234/v1`\n\n"
            "Ollama also works automatically at `http://127.0.0.1:11434`; LM Studio defaults to `:1234`.\n"
            "Load/list the model, then restart or wait for the worker heartbeat. It will appear in `/models`.\n"
            "When several GPUs are visible on the same worker, Ollama/llama.cpp can place one model across that local GPU group; the picker will label it.\n"
            "The current pool does not merge VRAM across unrelated contributor PCs. That requires a separate distributed vLLM/Ray or equivalent shard cluster.\n\n"
            "Do not paste API keys, `.env` contents, or private URLs into Discord."
        )
    return (
        "**GPU Pool setup**\n"
        "Choose a topic below. The normal path is: open the portal or `GPUPool.exe`, enter the invite code and Discord name, then choose **Share my PC**, **Use the pool**, or **Invite friends**.\n\n"
        "This is a private allowlisted co-op, not a public marketplace. Your machine's offer caps stay under your control."
    )


def build_bot():
    import discord
    from discord.ext import commands

    intents = discord.Intents.default()
    # Needed only for the optional !prefix path. Slash commands and components
    # do not require message content, but retaining this keeps !setup useful.
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)
    bot._selected_models = {}  # type: ignore[attr-defined]

    class SetupView(discord.ui.View):
        def __init__(self) -> None:
            super().__init__(timeout=900)
            options = [
                discord.SelectOption(label="Start here", value="start", description="The normal friend path"),
                discord.SelectOption(label="Share my PC", value="contribute", description="Install and contribute safely"),
                discord.SelectOption(label="Use the pool", value="use", description="Run allowlisted jobs"),
                discord.SelectOption(label="Use a shared LLM", value="llm", description="Pick an online mounted model"),
                discord.SelectOption(label="Mount my own LLM", value="custom", description="Ollama / LM Studio / vLLM"),
            ]
            select = discord.ui.Select(placeholder="What are you trying to do?", options=options, custom_id="gpu_pool_setup_topic")

            async def changed(interaction: discord.Interaction) -> None:
                await interaction.response.edit_message(content=_setup_text(select.values[0]), view=SetupView())

            select.callback = changed
            self.add_item(select)

    class ModelSelectView(discord.ui.View):
        def __init__(self, entries: list[dict[str, Any]]) -> None:
            super().__init__(timeout=900)
            self.entries = entries
            options = []
            for idx, entry in enumerate(entries[:25]):
                options.append(
                    discord.SelectOption(
                        label=_clip(str(entry.get("model") or "model"), 100),
                        value=str(idx),
                        description=_clip(
                            f"{entry.get('provider') or 'openai-compatible'} on {entry.get('worker_name') or 'worker'} · "
                            f"{int((entry.get('gpu_group') or {}).get('count') or 0)} GPU(s) · {entry.get('mount_state') or 'unknown'}",
                            100,
                        ),
                    )
                )
            select = discord.ui.Select(placeholder="Choose the model to route to…", options=options, custom_id="gpu_pool_model_route")

            async def changed(interaction: discord.Interaction) -> None:
                try:
                    entry = self.entries[int(select.values[0])]
                except (IndexError, ValueError):
                    await interaction.response.send_message("That model selection expired. Run `/models` again.", ephemeral=True)
                    return
                state = str(entry.get("mount_state") or "unknown")
                if state == "installed-not-fit-now":
                    group = entry.get("gpu_group") or {}
                    free_mb = int(group.get("free_vram_mb") or 0) if isinstance(group, dict) else 0
                    size_mb = int(entry.get("model_size_mb") or 0)
                    await interaction.response.send_message(
                        f"`{entry.get('model')}` is installed but not safe to mount on the current GPU group "
                        f"({size_mb} MiB model, {free_mb} MiB free before runtime reserve). "
                        "Unload another model or free desktop GPU memory, then run `/models` again.",
                        ephemeral=True,
                    )
                    return
                bot._selected_models[interaction.user.id] = entry  # type: ignore[attr-defined]
                await interaction.response.edit_message(
                    content=(
                        f"**Selected model:** `{entry.get('model')}`\n"
                        f"Provider: `{entry.get('provider')}` · Worker: `{entry.get('worker_name')}`\n"
                        "Now use `/ask question: ...`. The scheduler will verify this exact model is still mounted before leasing."
                    ),
                    view=None,
                )

            select.callback = changed
            self.add_item(select)

    async def send_public_or_ephemeral(ctx: Any, content: str, *, view: Any = None) -> None:
        kwargs: dict[str, Any] = {}
        if view is not None:
            kwargs["view"] = view
        if getattr(ctx, "interaction", None) is not None:
            kwargs["ephemeral"] = True
        await ctx.send(content, **kwargs)

    async def get_models() -> list[dict[str, Any]]:
        payload = await _api("GET", "/models")
        raw = payload.get("data") if isinstance(payload, dict) else []
        return [item for item in raw if isinstance(item, dict) and item.get("model")]

    async def wait_for_job(job_id: str, timeout: float = 240.0) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            job = await _api("GET", f"/jobs/{job_id}")
            if job.get("status") in {"completed", "failed", "cancelled"}:
                return job
            await asyncio.sleep(1.5)
        return {"id": job_id, "status": "timeout"}

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

    @bot.hybrid_command(name="setup", description="Talk through GPU Pool setup")
    async def setup(ctx):
        await send_public_or_ephemeral(ctx, _setup_text("start"), view=SetupView())

    @bot.hybrid_command(name="route", description="Explain how to mount your own LLM")
    async def route(ctx):
        await send_public_or_ephemeral(ctx, _setup_text("custom"))

    @bot.hybrid_command(name="models", description="Choose an online shared LLM model")
    async def models_cmd(ctx):
        try:
            entries = await get_models()
        except Exception as exc:  # noqa: BLE001
            await ctx.send(f"Model catalog unavailable: `{exc}`")
            return
        if not entries:
            await send_public_or_ephemeral(
                ctx,
                "No online LLM mounts are available right now. A contributor can run `/route` on their machine, then wait for the worker heartbeat.",
            )
            return
        lines = ["**Online shared LLM mounts**"]
        for entry in entries[:25]:
            group = entry.get("gpu_group") or {}
            group_text = (
                f"{group.get('count', 0)}-GPU same-worker group"
                if isinstance(group, dict) and int(group.get("count") or 0) > 1
                else "single-GPU"
            )
            lines.append(f"- `{entry.get('model')}` · {entry.get('provider')} · {entry.get('worker_name')} · {group_text} · {entry.get('mount_state', 'unknown')} · {entry.get('free_vram_mb', 0)} MiB free")
        lines.append("\nChoose one below, then use `/ask question: ...`.")
        await send_public_or_ephemeral(ctx, "\n".join(lines), view=ModelSelectView(entries))

    @bot.hybrid_command(name="ask", description="Chat with your selected shared LLM")
    async def ask(ctx, question: str):
        selected = bot._selected_models.get(ctx.author.id)  # type: ignore[attr-defined]
        if not selected:
            await send_public_or_ephemeral(ctx, "Choose a model first with `/models`, then run `/ask question: ...`.")
            return
        await ctx.defer()
        model = str(selected.get("model") or "").strip()
        progress = None
        try:
            job = await _api(
                "POST",
                "/jobs",
                json={
                    "job_type": "llm_chat",
                    "payload": {
                        "model": model,
                        "messages": [{"role": "user", "content": _clip(question, 6000)}],
                        "max_tokens": 768,
                    },
                    "require_gpu": False,
                    "submitted_by": f"discord:{ctx.author}",
                },
            )
            job_id = str(job["id"])
            print(f"[bot] ask queued job={job_id} model={model}", flush=True)
            progress = await ctx.send(
                f"Queued LLM job `{job_id}` for `{model}`. Waiting for the worker…"
            )
            final = await wait_for_job(job_id)
        except Exception as exc:  # noqa: BLE001
            message = f"LLM routing failed before completion: `{exc}`"
            if progress is not None:
                await progress.edit(content=message)
            else:
                await ctx.send(message)
            return
        if final.get("status") == "failed":
            message = f"LLM job failed for `{model}`: `{final.get('error') or 'worker returned an error'}`"
        elif final.get("status") == "timeout":
            message = f"LLM job `{final.get('id')}` is still running. Use `/job_status {final.get('id')}`."
        else:
            result = final.get("result") or {}
            answer = str(result.get("message") or "") if isinstance(result, dict) else ""
            message = f"**{model}**\n{_clip(answer or 'The worker completed the job but returned no final assistant text.') }"
        if progress is not None:
            await progress.edit(content=message)
        else:
            await ctx.send(message)

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
            f"**Jobs:** queued={st['jobs']['queued']} running={st['jobs']['running']} done={st['jobs']['completed']} failed={st['jobs']['failed']}",
        ]
        if st.get("gpus"):
            lines.append("**GPUs:**\n" + "\n".join(f"- {g}" for g in st["gpus"][:12]))
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
        for worker in online[:20]:
            names = ", ".join(g.get("name", "?") for g in (worker.get("gpus") or []))
            models = ", ".join(str(m) for m in (worker.get("llm_models") or [])[:5]) or "no LLM mount"
            lines.append(
                f"- **{worker['name']}** vram={worker['free_vram_mb']} MiB | cpu={worker.get('cpu_cores', 0)}c@{worker.get('max_cpu_percent', '?')}% | "
                f"{names or 'no GPU'} | LLM: `{models}` | by={worker.get('discord_user') or '-'}"
            )
        await ctx.send("\n".join(lines))

    @bot.hybrid_command(name="contribute", description="How to contribute spare GPU/CPU")
    async def contribute(ctx):
        await ctx.send(_setup_text("contribute"))

    @bot.hybrid_command(name="submit_probe", description="Submit a GPU probe job")
    async def submit_probe(ctx):
        await ctx.defer()
        try:
            job = await _api("POST", "/jobs", json={"job_type": "probe", "payload": {}, "require_gpu": False, "submitted_by": str(ctx.author)})
        except Exception as exc:  # noqa: BLE001
            await ctx.send(f"Submit failed: `{exc}`")
            return
        await ctx.send(f"Queued **probe** job `{job['id']}` — use `/job_status {job['id']}`")

    @bot.hybrid_command(name="submit_compute", description="Submit CUDA matmul probe job")
    async def submit_compute(ctx, matrix_size: int = 1024):
        await ctx.defer()
        size = max(64, min(int(matrix_size), 4096))
        try:
            job = await _api("POST", "/jobs", json={"job_type": "pytorch_cuda_probe", "payload": {"matrix_size": size}, "require_gpu": True, "submitted_by": str(ctx.author)})
        except Exception as exc:  # noqa: BLE001
            await ctx.send(f"Submit failed: `{exc}`")
            return
        await ctx.send(f"Queued **pytorch_cuda_probe** ({size}x{size}) job `{job['id']}`")

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
            await ctx.send(f"{header}\n```json\n{_clip(text, 1800)}\n```")
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
            "4. Invite the bot with applications.commands + Send Messages\n"
            "Scheduler + worker work without Discord; bot is optional until token is set.",
            flush=True,
        )
        return 1
    bot = build_bot()
    bot.run(token)
    return 0


def bot_help_check() -> int:
    """Verify command and component wiring without requiring a live token."""
    bot = build_bot()
    names = sorted(c.name for c in bot.commands)
    expected = {"setup", "route", "models", "ask", "pool", "workers", "contribute", "submit_probe", "submit_compute", "job_status"}
    missing = sorted(expected - set(names))
    print("bot commands:", ", ".join(names))
    print("expected setup/model/chat commands:", ", ".join(sorted(expected)))
    if missing:
        print("missing commands:", ", ".join(missing))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run_bot())
