# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for GPUPool.exe — build via: powershell -File build_exe.ps1
# Keep the bundle lean: UI + worker path only. No torch, Discord, Jupyter, numpy.
from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

ctk_datas, ctk_binaries, ctk_hidden = collect_all("customtkinter")
try:
    dark_datas = collect_data_files("darkdetect")
except Exception:
    dark_datas = []

extra_datas = [
    ("requirements.txt", "."),
    ("requirements-app.txt", "."),
    ("requirements-joiner.txt", "."),
    ("requirements-cuda.txt", "."),
    ("CONNECTING.md", "."),
    ("DOWNLOAD.md", "."),
    ("LOGIN.md", "."),
    ("ADVANCED_VM.md", "."),
    ("LOCAL_MODEL.md", "."),
    ("SHARED_AGENT_DEV.md", "."),
    ("scripts/install-prereqs.ps1", "scripts"),
    ("scripts/install-prereqs.cmd", "scripts"),
    ("scripts/check_prereqs.ps1", "scripts"),
    ("scripts/check_prereqs.cmd", "scripts"),
    ("scripts/install_joiner_deps.ps1", "scripts"),
    ("scripts/install_joiner_deps.cmd", "scripts"),
    ("scripts/install_cloudflared.ps1", "scripts"),
    ("scripts/install_cloudflared.cmd", "scripts"),
    ("scripts/setup_cloudflare_named.ps1", "scripts"),
    ("scripts/setup_cloudflare_named.cmd", "scripts"),
    ("scripts/cloudflare-access.cmd", "scripts"),
    ("scripts/launch_public.py", "scripts"),
    ("launch-public.cmd", "."),
    ("cloudflare/README.md", "cloudflare"),
    ("cloudflare/gpu-pool.tunnel.yml.example", "cloudflare"),
    ("examples/coding_agent_pool.py", "examples"),
    ("examples/ollama_or_local_offload.md", "examples"),
]
extra_datas += ctk_datas + dark_datas

# Joiner EXE does not need scheduler/portal server stacks at import time.
# Exclude heavy optional stacks that PyInstaller may pull via site-packages.
excludes = [
    # PyInstaller's pkg_resources runtime hook is incompatible with the
    # current setuptools/pkg_resources split and is not used by GPUPool.
    "pkg_resources",
    "setuptools",
    "torch",
    "torchvision",
    "torchaudio",
    "discord",
    # fastapi/uvicorn/starlette kept — Connect Start/Stop local model endpoint
    "aiosqlite",
    "IPython",
    "ipykernel",
    "jupyter",
    "notebook",
    "nbformat",
    "nbconvert",
    "matplotlib",
    "numpy",
    "pandas",
    "scipy",
    "PIL",
    "cv2",
    "pygame",
    "rich",
    "pygments",
    "jedi",
    "parso",
    "pytest",
    "unittest",
    "tkinter.test",
    "freqtrade",
]

a = Analysis(
    ["gpu_pool_entry.py"],
    pathex=["."],
    binaries=ctk_binaries,
    datas=extra_datas,
    hiddenimports=list(ctk_hidden)
    + [
        "customtkinter",
        "darkdetect",
        "httpx",
        "httpcore",
        "anyio",
        "h11",
        "certifi",
        "dotenv",
        "psutil",
        "pydantic",
        "pydantic_core",
        "gpu_swarm",
        "gpu_swarm.app",
        "gpu_swarm.app.desktop_app",
        "gpu_swarm.app_backend",
        "gpu_swarm.cloudflare_access",
        "gpu_swarm.joiner_settings",
        "gpu_swarm.portable_python",
        "gpu_swarm.win_subprocess",
        "gpu_swarm.availability_schedule",
        "gpu_swarm.use_cases",
        "gpu_swarm.diagnostics",
        "gpu_swarm.endpoints",
        "gpu_swarm.public_endpoints",
        "gpu_swarm.worker",
        "gpu_swarm.jobs",
        "gpu_swarm.gpu",
        "gpu_swarm.host",
        "gpu_swarm.client",
        "gpu_swarm.config",
        "gpu_swarm.paths",
        "gpu_swarm.local_endpoint",
        "gpu_swarm.llm_runtime",
        "gpu_swarm.host_protect",
        "gpu_swarm.agent_vm_bridge",
        "gpu_swarm.cli",
        "fastapi",
        "uvicorn",
        "starlette",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="GPUPool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
