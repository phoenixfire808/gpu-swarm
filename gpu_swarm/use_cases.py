"""Plain-English benefit list for onboarding (portal, desktop, docs)."""

from __future__ import annotations

USE_CASES: tuple[dict[str, str], ...] = (
    {
        "title": "Run AI chat on friends' GPUs",
        "body": "Your laptop has no NVIDIA? Still run chat and AI jobs on whoever is online.",
    },
    {
        "title": "Share idle evening GPU",
        "body": "Lend spare power at night or on weekends — the group trains and runs faster together.",
    },
    {
        "title": "Shared coding workspace",
        "body": "Optional Linux desktop (VM) for working on a project together — CPU/RAM only.",
    },
    {
        "title": "Local AI for Cursor & agents",
        "body": "Open a localhost OpenAI-compatible URL so your tools use the pool without cloud GPU bills.",
    },
    {
        "title": "Quick GPU health checks",
        "body": "Probe and CUDA checks across online machines — see what's really available.",
    },
    {
        "title": "Chat & suggest improvements",
        "body": "Talk with the pool on the web hub and send ideas to make it better.",
    },
    {
        "title": "Grow the network",
        "body": "Invite friends — every PC that joins gives everyone more compute.",
    },
)


def format_use_cases_bullets() -> str:
    lines = []
    for i, item in enumerate(USE_CASES, 1):
        lines.append(f"{i}. {item['title']} — {item['body']}")
    return "\n".join(lines)


def format_use_cases_short() -> str:
    return " · ".join(item["title"] for item in USE_CASES[:4]) + " · …"
