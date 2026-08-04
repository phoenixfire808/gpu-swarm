#Requires -Version 5.1
<#
.SYNOPSIS
  Idempotent joiner dependency install into %LOCALAPPDATA%\GPUPool\venv

.DESCRIPTION
  Prefer isolated venv over broken system Python / global site-packages.
  Core deps: requirements-joiner.txt (fallback requirements.txt).
  Optional CUDA torch: -WithTorchCuda → requirements-cuda.txt
  Supported: Windows x64 + CPython 3.10–3.12 (prefer 3.12). 3.13 not used by default.
#>
param(
    [switch]$WithTorchCuda,
    [string]$TorchIndexUrl = "https://download.pytorch.org/whl/cu128",
    [switch]$Force,
    [switch]$Quiet,
    [switch]$BootstrapPortable
)
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$ReqJoiner = Join-Path $RepoRoot "requirements-joiner.txt"
$ReqLegacy = Join-Path $RepoRoot "requirements.txt"
$ReqCuda = Join-Path $RepoRoot "requirements-cuda.txt"
if (-not (Test-Path $ReqJoiner)) {
    if (Test-Path $ReqLegacy) {
        Write-Warning "requirements-joiner.txt missing; falling back to requirements.txt"
        $ReqJoiner = $ReqLegacy
    } else {
        Write-Error "Missing requirements-joiner.txt"
        exit 2
    }
}

$GpuPoolRoot = Join-Path $env:LOCALAPPDATA "GPUPool"
$VenvDir = Join-Path $GpuPoolRoot "venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$PortablePython = Join-Path $GpuPoolRoot "python\python.exe"

$script:PyArgs = @()

function Resolve-SeedPython {
    if ($env:GPU_SWARM_PYTHON -and (Test-Path $env:GPU_SWARM_PYTHON)) {
        return $env:GPU_SWARM_PYTHON
    }
    if (Test-Path $PortablePython) { return $PortablePython }
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        foreach ($tag in @("-3.12", "-3.11", "-3.10")) {
            $exe = & py $tag -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $exe) {
                $ok = & py $tag -c "import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] <= (3, 12) else 1)" 2>$null
                if ($LASTEXITCODE -eq 0) { return $exe.Trim() }
            }
        }
    }
    foreach ($name in @("python", "python3")) {
        $w = Get-Command $name -ErrorAction SilentlyContinue
        if (-not $w) { continue }
        & $w.Source -c "import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] <= (3, 12) else 1)" 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { return $w.Source }
    }
    return $null
}

function Ensure-GpuPoolVenv {
    if ((Test-Path $VenvPython) -and -not $Force) {
        & $VenvPython -c "import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] <= (3, 12) else 1)" 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { return $true }
    }
    $seed = Resolve-SeedPython
    if (-not $seed) {
        if ($BootstrapPortable) {
            Write-Host "Bootstrapping portable Python via gpu_swarm.portable_python ..."
            $launcher = Get-Command py -ErrorAction SilentlyContinue
            if (-not $launcher) { throw "No seed Python to bootstrap portable runtime. Use GPUPool.exe." }
            & py -3 -c "from gpu_swarm.portable_python import ensure_portable_python; import json; print(json.dumps(ensure_portable_python(with_venv=True, with_requirements=False)))"
            if (-not (Test-Path $VenvPython)) { throw "Portable bootstrap did not create $VenvPython" }
            return $true
        }
        throw "Python 3.10+ not found. Run wizard Bootstrap portable Python, GPUPool.exe, or: install_joiner_deps.ps1 -BootstrapPortable"
    }
    Write-Host "Creating isolated venv: $VenvDir (seed=$seed)"
    New-Item -ItemType Directory -Force -Path $GpuPoolRoot | Out-Null
    if (Test-Path $VenvDir) { Remove-Item -Recurse -Force $VenvDir }
    & $seed -m venv $VenvDir
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPython)) {
        throw "Failed to create venv at $VenvDir"
    }
    return $true
}

function Invoke-VenvPip {
    param([Parameter(Mandatory=$true)][string[]]$PipArgs)
    $all = @("-m", "pip") + $PipArgs
    if ($Quiet) { $all += "-q" }
    & $VenvPython @all
    return $LASTEXITCODE
}

function Test-JoinerImports {
    $probeFile = Join-Path $env:TEMP "gpu_swarm_probe_imports.py"
    @"
import importlib, sys
mods = ["httpx", "dotenv", "fastapi", "uvicorn", "psutil", "pydantic", "aiosqlite", "customtkinter"]
missing = []
for m in mods:
    try:
        importlib.import_module(m)
    except ImportError:
        missing.append(m)
print("MISSING:" + ",".join(missing))
sys.exit(0 if not missing else 1)
"@ | Set-Content -Path $probeFile -Encoding UTF8
    $out = & $VenvPython $probeFile 2>&1 | Out-String
    Remove-Item -Force $probeFile -ErrorAction SilentlyContinue
    $missing = @()
    foreach ($line in $out.Split([char]10)) {
        $t = $line.Trim([char]13)
        if ($t.StartsWith("MISSING:")) {
            $raw = $t.Substring(8).Trim()
            if ($raw) { $missing = @($raw.Split(",") | Where-Object { $_ }) }
        }
    }
    return @{ ok = ($missing.Count -eq 0); missing = $missing; raw = $out }
}

function Test-TorchCuda {
    $probeFile = Join-Path $env:TEMP "gpu_swarm_probe_torch.py"
    @"
import torch
print("torch", torch.__version__)
print("cuda", torch.cuda.is_available())
raise SystemExit(0 if torch.cuda.is_available() else 1)
"@ | Set-Content -Path $probeFile -Encoding UTF8
    try {
        $out = & $VenvPython $probeFile 2>&1 | Out-String
        $code = $LASTEXITCODE
    } catch {
        Remove-Item -Force $probeFile -ErrorAction SilentlyContinue
        return @{ ok = $false; message = "$_" }
    }
    Remove-Item -Force $probeFile -ErrorAction SilentlyContinue
    return @{ ok = ($code -eq 0); message = $out.Trim() }
}

[void](Ensure-GpuPoolVenv)
$env:GPU_SWARM_PYTHON = $VenvPython
$script:PyArgs = @($VenvPython)
Write-Host ("Using isolated Python: {0}" -f $VenvPython)

$probe = Test-JoinerImports
$actions = New-Object System.Collections.Generic.List[string]

if ($Force -or -not $probe.ok) {
    Write-Host "Installing from $ReqJoiner into GPUPool venv (no --user)..."
    $code = Invoke-VenvPip @("install", "-r", $ReqJoiner)
    if ($code -ne 0) { Write-Error "pip install -r requirements-joiner failed (exit $code)"; exit $code }
    [void]$actions.Add("pip_install_joiner_requirements")
} else {
    Write-Host "Joiner requirements already satisfied - skipping pip -r"
    [void]$actions.Add("skip_requirements_satisfied")
}

$torchResult = $null
if ($WithTorchCuda) {
    $t = Test-TorchCuda
    if ($t.ok -and -not $Force) {
        Write-Host ("torch CUDA already available - {0}" -f $t.message)
        [void]$actions.Add("skip_torch_cuda_present")
        $torchResult = $t
    } else {
        Write-Host ("Installing CUDA torch from {0} (large download)..." -f $TorchIndexUrl)
        if (Test-Path $ReqCuda) {
            $code = Invoke-VenvPip @("install", "-r", $ReqCuda, "--index-url", $TorchIndexUrl)
        } else {
            $code = Invoke-VenvPip @("install", "torch", "--index-url", $TorchIndexUrl)
        }
        if ($code -ne 0) { Write-Error "torch CUDA install failed (exit $code)"; exit $code }
        [void]$actions.Add("pip_install_torch_cuda")
        $torchResult = Test-TorchCuda
    }
}

$final = Test-JoinerImports
$summary = [ordered]@{
    ok = [bool]$final.ok
    python = $VenvPython
    venv = $VenvDir
    gpu_pool_home = $GpuPoolRoot
    actions = @($actions)
    missing = @($final.missing)
    with_torch_cuda = [bool]$WithTorchCuda
    torch = $torchResult
    requirements = $ReqJoiner
    script = "scripts/install_joiner_deps.ps1"
}
$summary | ConvertTo-Json -Depth 5
if (-not $final.ok) { exit 1 }
exit 0
