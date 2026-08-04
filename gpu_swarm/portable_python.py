"""
Portable / isolated Python for friend installs.

Strategy:
  1. Prefer a healthy system Python 3.10+ (or GPU_SWARM_PYTHON).
  2. If missing / too old / broken → bootstrap NuGet CPython into
     %LOCALAPPDATA%\\GPUPool\\python\\
  3. Create / reuse venv at %LOCALAPPDATA%\\GPUPool\\venv (never global site-packages).
  4. GPUPool.exe UI/worker stays frozen; portable Python is for pip/torch/source path.

Dry-run: ensure_portable_python(dry_run=True) reports the plan without downloading.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any
from urllib.request import urlretrieve

from gpu_swarm.paths import (
    BUNDLE_ROOT,
    PORTABLE_PYTHON_DIR,
    VENV_DIR,
    gpu_pool_home,
    is_frozen,
)

# Pin a known-good Windows x64 CPython. NuGet package includes full stdlib + venv.
PORTABLE_PYTHON_VERSION = "3.12.8"
NUGET_PACKAGE_URL = (
    f"https://www.nuget.org/api/v2/package/python/{PORTABLE_PYTHON_VERSION}"
)
MIN_VERSION = (3, 10)
MAX_VERSION = (3, 12)  # 3.13 optional/fragile for torch wheels


def _run(
    cmd: list[str],
    *,
    timeout: float = 60,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        cwd=cwd,
        env=env,
    )


def _version_ok(exe: str) -> tuple[bool, str]:
    """Return (ok, version_string) for a python executable."""
    try:
        if Path(exe).name.lower() in ("py.exe", "py"):
            proc = None
            for tag in ("-3.12", "-3.11", "-3.10"):
                proc = _run(
                    [
                        exe,
                        tag,
                        "-c",
                        "import sys; print('%d.%d.%d' % sys.version_info[:3]); "
                        "raise SystemExit(0 if (3, 10) <= sys.version_info[:2] <= (3, 12) else 2)",
                    ],
                    timeout=12,
                )
                if proc.returncode == 0:
                    break
            if proc is None:
                return False, ""
        else:
            proc = _run(
                [
                    exe,
                    "-c",
                    "import sys; print('%d.%d.%d' % sys.version_info[:3]); "
                    "raise SystemExit(0 if (3, 10) <= sys.version_info[:2] <= (3, 12) else 2)",
                ],
                timeout=12,
            )
    except (OSError, subprocess.TimeoutExpired):
        return False, ""
    ver = (proc.stdout or "").strip().splitlines()
    version = ver[0].strip() if ver else ""
    return proc.returncode == 0, version


def _real_executable(candidate: str) -> str | None:
    """Resolve py launcher → real python.exe when needed."""
    path = Path(candidate)
    if not path.exists() and not shutil.which(candidate):
        return None
    name = path.name.lower()
    if name in ("py.exe", "py"):
        for tag in ("-3.12", "-3.11", "-3.10"):
            try:
                proc = _run(
                    [candidate, tag, "-c", "import sys; print(sys.executable)"],
                    timeout=12,
                )
            except (OSError, subprocess.TimeoutExpired):
                continue
            resolved = (proc.stdout or "").strip()
            if resolved and Path(resolved).exists():
                return resolved
        return None
    return str(path) if path.exists() else shutil.which(candidate)


def portable_python_exe() -> Path:
    return PORTABLE_PYTHON_DIR / "python.exe"


def venv_python_exe() -> Path:
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def list_system_python_candidates() -> list[str]:
    """Ordered candidates for a non-frozen host Python."""
    env_py = (os.environ.get("GPU_SWARM_PYTHON") or "").strip()
    out: list[str] = []
    if env_py:
        out.append(env_py)
    for p in (venv_python_exe(), portable_python_exe()):
        if p.is_file():
            out.append(str(p))
    for name in ("py", "python", "python3"):
        found = shutil.which(name)
        if found:
            out.append(found)
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    for ver in ("Python312", "Python311", "Python310"):
        out.append(str(local / "Programs" / "Python" / ver / "python.exe"))
        out.append(f"C:\\{ver}\\python.exe")
    seen: set[str] = set()
    unique: list[str] = []
    for c in out:
        key = str(Path(c)).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)
    return unique


def find_usable_python(*, allow_frozen_self: bool = False) -> dict[str, Any]:
    """Find a usable CPython 3.10–3.12 for pip / venv work (skip frozen EXE)."""
    for cand in list_system_python_candidates():
        real = _real_executable(cand)
        if not real:
            continue
        if is_frozen() and not allow_frozen_self:
            try:
                if Path(real).resolve() == Path(sys.executable).resolve():
                    continue
            except OSError:
                pass
        ok, version = _version_ok(real)
        if not ok:
            continue
        try:
            smoke = _run(
                [real, "-c", "import pip, venv, ensurepip; print('ok')"],
                timeout=20,
            )
            pip_ok = smoke.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            pip_ok = False
        source = "venv" if str(VENV_DIR).lower() in real.lower() else (
            "portable" if str(PORTABLE_PYTHON_DIR).lower() in real.lower() else "system"
        )
        return {
            "ok": True,
            "executable": real,
            "version": version,
            "source": source,
            "pip_ok": pip_ok,
            "message": f"Python {version} ({source}) @ {real}",
            "fix": "" if pip_ok else "Interpreter OK but pip/venv broken — bootstrap portable Python.",
        }
    return {
        "ok": False,
        "executable": "",
        "version": "",
        "source": "",
        "pip_ok": False,
        "message": "No usable Python 3.10–3.12 found (system Python missing, unsupported, or broken).",
        "fix": (
            "Click “Bootstrap portable Python” in the wizard, or use GPUPool.exe.\n"
            f"Portable target: {PORTABLE_PYTHON_DIR}\n"
            f"Venv target:     {VENV_DIR}"
        ),
    }


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    urlretrieve(url, str(dest))  # noqa: S310 — fixed NuGet URL


def _extract_nuget_python(nupkg: Path, dest: Path) -> Path:
    """Extract NuGet python package; return path to python.exe."""
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(nupkg, "r") as zf:
        members = [m for m in zf.namelist() if m.startswith("tools/")]
        if not members:
            raise RuntimeError("NuGet python package missing tools/ tree")
        for name in members:
            zf.extract(name, dest)
    tools = dest / "tools"
    exe = tools / "python.exe"
    if not exe.is_file():
        raise RuntimeError(f"python.exe missing after extract: {exe}")
    for item in tools.iterdir():
        target = dest / item.name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(item), str(target))
    shutil.rmtree(tools, ignore_errors=True)
    final = dest / "python.exe"
    if not final.is_file():
        raise RuntimeError(f"flatten failed; missing {final}")
    return final


def download_portable_python(*, dry_run: bool = False) -> dict[str, Any]:
    """Download NuGet CPython into %LOCALAPPDATA%\\GPUPool\\python\\."""
    dest = PORTABLE_PYTHON_DIR
    existing = portable_python_exe()
    if existing.is_file():
        ok, ver = _version_ok(str(existing))
        if ok:
            return {
                "ok": True,
                "skipped": True,
                "dry_run": dry_run,
                "executable": str(existing),
                "version": ver,
                "message": f"Portable Python already present ({ver}) @ {existing}",
            }
    plan = {
        "ok": True,
        "dry_run": dry_run,
        "url": NUGET_PACKAGE_URL,
        "dest": str(dest),
        "version": PORTABLE_PYTHON_VERSION,
        "message": (
            f"Would download CPython {PORTABLE_PYTHON_VERSION} from NuGet → {dest}"
            if dry_run
            else f"Downloading CPython {PORTABLE_PYTHON_VERSION}…"
        ),
    }
    if dry_run:
        return plan

    gpu_pool_home().mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gpupool-py-") as tmp:
        nupkg = Path(tmp) / "python.nupkg"
        try:
            _download(NUGET_PACKAGE_URL, nupkg)
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "message": f"Download failed: {exc}",
                "fix": f"Manual: download {NUGET_PACKAGE_URL} and extract tools\\ to {dest}",
                "url": NUGET_PACKAGE_URL,
            }
        try:
            exe = _extract_nuget_python(nupkg, dest)
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "message": f"Extract failed: {exc}",
                "fix": f"Delete {dest} and retry bootstrap.",
            }
    ok, ver = _version_ok(str(exe))
    if not ok:
        return {
            "ok": False,
            "message": "Portable python.exe extracted but version check failed",
            "executable": str(exe),
            "fix": f"Delete {dest} and retry, or install Python 3.10+ from python.org",
        }
    return {
        "ok": True,
        "skipped": False,
        "executable": str(exe),
        "version": ver,
        "message": f"Portable Python {ver} ready @ {exe}",
    }


def ensure_venv(*, python_exe: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Create %LOCALAPPDATA%\\GPUPool\\venv if missing; return venv python path."""
    vpy = venv_python_exe()
    if vpy.is_file():
        ok, ver = _version_ok(str(vpy))
        if ok:
            return {
                "ok": True,
                "skipped": True,
                "dry_run": dry_run,
                "executable": str(vpy),
                "version": ver,
                "venv": str(VENV_DIR),
                "message": f"Venv already present ({ver}) @ {vpy}",
            }
    base = python_exe or str(portable_python_exe())
    if not Path(base).is_file():
        found = find_usable_python()
        if not found.get("ok"):
            return {
                "ok": False,
                "dry_run": dry_run,
                "message": "No base Python to create venv",
                "fix": found.get("fix") or "Bootstrap portable Python first.",
            }
        base = str(found["executable"])
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "base_python": base,
            "venv": str(VENV_DIR),
            "message": f"Would create venv at {VENV_DIR} using {base}",
        }
    VENV_DIR.parent.mkdir(parents=True, exist_ok=True)
    if VENV_DIR.exists():
        shutil.rmtree(VENV_DIR, ignore_errors=True)
    try:
        proc = _run([base, "-m", "venv", str(VENV_DIR)], timeout=180)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "message": str(exc), "fix": f'"{base}" -m venv "{VENV_DIR}"'}
    if proc.returncode != 0 or not vpy.is_file():
        tail = ((proc.stdout or "") + "\n" + (proc.stderr or ""))[-800:]
        return {
            "ok": False,
            "message": tail or "venv creation failed",
            "fix": f'"{base}" -m venv "{VENV_DIR}"',
        }
    ok, ver = _version_ok(str(vpy))
    return {
        "ok": ok,
        "skipped": False,
        "executable": str(vpy),
        "version": ver,
        "venv": str(VENV_DIR),
        "message": f"Venv ready ({ver}) @ {vpy}",
    }


def install_requirements_into_venv(
    *,
    requirements: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """pip install -r requirements into the isolated venv (no --user / global)."""
    vpy = venv_python_exe()
    if not vpy.is_file():
        return {
            "ok": False,
            "message": "Venv python missing",
            "fix": "Run ensure_portable_python() first.",
        }
    req = requirements
    if req is None:
        for candidate in (
            BUNDLE_ROOT / "requirements-joiner.txt",
            BUNDLE_ROOT / "requirements.txt",
            BUNDLE_ROOT / "requirements-app.txt",
            Path(__file__).resolve().parent.parent / "requirements-joiner.txt",
            Path(__file__).resolve().parent.parent / "requirements.txt",
        ):
            if candidate.is_file():
                req = candidate
                break
    if req is None or not req.is_file():
        return {"ok": False, "message": "requirements file not found", "fix": "Restore requirements-joiner.txt"}
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "executable": str(vpy),
            "requirements": str(req),
            "message": f"Would: {vpy} -m pip install -r {req}",
        }
    try:
        proc = _run(
            [str(vpy), "-m", "pip", "install", "-r", str(req)],
            timeout=900,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "message": str(exc), "fix": f'"{vpy}" -m pip install -r "{req}"'}
    tail = ((proc.stdout or "") + "\n" + (proc.stderr or ""))[-1200:]
    return {
        "ok": proc.returncode == 0,
        "code": proc.returncode,
        "executable": str(vpy),
        "requirements": str(req),
        "message": tail or ("Installed into venv" if proc.returncode == 0 else "pip failed"),
        "fix": "" if proc.returncode == 0 else f'"{vpy}" -m pip install -r "{req}"',
    }


def ensure_portable_python(
    *,
    force_download: bool = False,
    with_venv: bool = True,
    with_requirements: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Full bootstrap: detect → optional download → venv → optional requirements.

    Prefer existing good system/venv Python unless force_download=True.
    """
    actions: list[str] = []
    found = find_usable_python()
    need_download = force_download or not found.get("ok") or not found.get("pip_ok")

    if found.get("ok") and found.get("source") == "venv" and found.get("pip_ok") and not force_download:
        result = {
            "ok": True,
            "dry_run": dry_run,
            "executable": found["executable"],
            "version": found.get("version"),
            "source": "venv",
            "actions": ["reuse_venv"],
            "message": found["message"],
            "venv": str(VENV_DIR),
            "portable_dir": str(PORTABLE_PYTHON_DIR),
            "gpu_pool_home": str(gpu_pool_home()),
        }
        os.environ["GPU_SWARM_PYTHON"] = str(found["executable"])
        return result

    download_info: dict[str, Any] | None = None
    if need_download or not portable_python_exe().is_file():
        if need_download:
            download_info = download_portable_python(dry_run=dry_run)
            actions.append("download_portable" if not download_info.get("skipped") else "portable_present")
            if not download_info.get("ok"):
                return {
                    **download_info,
                    "actions": actions,
                    "dry_run": dry_run,
                    "system": found,
                }
        elif found.get("ok"):
            actions.append("reuse_system")
    else:
        actions.append("portable_present")

    base_exe = str(portable_python_exe()) if portable_python_exe().is_file() else (
        str(found.get("executable") or "")
    )
    venv_info: dict[str, Any] | None = None
    if with_venv:
        venv_info = ensure_venv(python_exe=base_exe or None, dry_run=dry_run)
        actions.append("ensure_venv" if not venv_info.get("skipped") else "venv_present")
        if not venv_info.get("ok"):
            return {
                **venv_info,
                "actions": actions,
                "download": download_info,
                "dry_run": dry_run,
            }
        exe = str(venv_info.get("executable") or "")
    else:
        exe = base_exe

    req_info: dict[str, Any] | None = None
    if with_requirements and with_venv and not dry_run:
        req_info = install_requirements_into_venv(dry_run=dry_run)
        actions.append("pip_requirements")
        if not req_info.get("ok"):
            return {
                **req_info,
                "actions": actions,
                "download": download_info,
                "venv": venv_info,
                "dry_run": dry_run,
            }

    if exe and not dry_run:
        os.environ["GPU_SWARM_PYTHON"] = exe

    ok_ver = ""
    if exe and Path(exe).is_file() and not dry_run:
        _, ok_ver = _version_ok(exe)

    return {
        "ok": True,
        "dry_run": dry_run,
        "executable": exe if not dry_run else (exe or str(venv_python_exe())),
        "version": ok_ver or found.get("version") or PORTABLE_PYTHON_VERSION,
        "source": "venv" if with_venv else "portable",
        "actions": actions,
        "download": download_info,
        "venv": venv_info,
        "requirements": req_info,
        "portable_dir": str(PORTABLE_PYTHON_DIR),
        "venv_dir": str(VENV_DIR),
        "gpu_pool_home": str(gpu_pool_home()),
        "message": (
            f"Dry-run OK — would isolate Python under {gpu_pool_home()}"
            if dry_run
            else f"Isolated Python ready @ {exe}"
        ),
        "fix": "",
    }


def resolve_pip_python() -> str | None:
    """Python to use for pip installs (venv > portable > system). Never frozen EXE."""
    for path in (venv_python_exe(), portable_python_exe()):
        if path.is_file():
            ok, _ = _version_ok(str(path))
            if ok:
                return str(path)
    found = find_usable_python()
    if found.get("ok") and found.get("executable"):
        return str(found["executable"])
    return None


def python_runtime_report() -> dict[str, Any]:
    """UI-facing summary for the wizard Python step."""
    frozen = is_frozen()
    found = find_usable_python()
    vpy = venv_python_exe()
    ppy = portable_python_exe()
    return {
        "ok": bool(found.get("ok")) or frozen,
        "frozen": frozen,
        "app_executable": sys.executable,
        "app_version": (
            "bundled"
            if frozen
            else f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}"
        ),
        "pip_python": found.get("executable") or "",
        "pip_version": found.get("version") or "",
        "pip_source": found.get("source") or "",
        "pip_ok": bool(found.get("pip_ok")) if found.get("ok") else False,
        "portable_present": ppy.is_file(),
        "venv_present": vpy.is_file(),
        "portable_dir": str(PORTABLE_PYTHON_DIR),
        "venv_dir": str(VENV_DIR),
        "gpu_pool_home": str(gpu_pool_home()),
        "min_version": f"{MIN_VERSION[0]}.{MIN_VERSION[1]}",
        "max_version": f"{MAX_VERSION[0]}.{MAX_VERSION[1]}",
        "target_version": PORTABLE_PYTHON_VERSION,
        "message": (
            (
                "GPUPool.exe bundles the app runtime. Optional pip/torch uses an isolated "
                f"Python under {gpu_pool_home()} (not your system Python)."
            )
            if frozen
            else (
                found.get("message")
                or "No usable Python 3.10+ — bootstrap portable Python into LocalAppData."
            )
        ),
        "fix": (
            ""
            if (frozen or found.get("ok"))
            else (
                found.get("fix")
                or "Bootstrap portable Python 3.12 into %LOCALAPPDATA%\\GPUPool\\python\\ "
                "and a venv at %LOCALAPPDATA%\\GPUPool\\venv — do not fight global site-packages."
            )
        ),
        "conflict_hint": (
            "This machine’s system Python is missing, unsupported (need 3.10–3.12), or broken. "
            "GPU Pool will use an isolated portable Python + venv under "
            f"%LOCALAPPDATA%\\GPUPool\\ instead of global site-packages."
            if not found.get("ok") and not frozen
            else (
                ""
                if found.get("source") in ("venv", "portable") or frozen
                else "Using system Python for now; if installs fail, bootstrap portable Python."
            )
        ),
    }
