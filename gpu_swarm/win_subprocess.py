"""Windows subprocess helpers — hide console windows for background GPU Pool work."""

from __future__ import annotations

import subprocess
import sys

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)


def creation_flags(*, new_group: bool = False) -> int:
    """Return Windows creationflags that suppress new console windows."""
    if sys.platform != "win32":
        return 0
    flags = CREATE_NO_WINDOW
    if new_group:
        flags |= CREATE_NEW_PROCESS_GROUP
    return flags


def popen_kwargs(*, new_group: bool = False) -> dict:
    flags = creation_flags(new_group=new_group)
    return {"creationflags": flags} if flags else {}


def run_kwargs(*, new_group: bool = False) -> dict:
    return popen_kwargs(new_group=new_group)
