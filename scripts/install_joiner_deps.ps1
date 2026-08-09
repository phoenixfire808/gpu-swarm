#Requires -Version 5.1
<#
.SYNOPSIS
  Idempotent joiner dependency install into %LOCALAPPDATA%\GPUPool\venv

.DESCRIPTION
  Prefer isolated venv over broken system Python / global site-packages.
  Core deps: requirements-joiner.txt (fallback requirements.txt).
  Optional CUDA torch: -WithTorchCuda -> requirements-cuda.txt
  Supported: Windows x64 + CPython 3.10-3.12 (prefer 3.12). 3.13 not used by default.

  Always prints human-readable step labels + Write-Progress so friends can see
  what is happening (download / folder / packages / GPU check).
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
$script:StepTotal = if ($WithTorchCuda) { 6 } else { 5 }
$script:StepNum = 0

function Write-GpuPoolStep {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [int]$PercentComplete = -1,
        [string]$Detail = ""
    )
    $script:StepNum++
    $pct = if ($PercentComplete -ge 0) {
        $PercentComplete
    } else {
        [int](($script:StepNum / [math]::Max($script:StepTotal, 1)) * 100)
    }
    $banner = "[{0}/{1}] {2}" -f $script:StepNum, $script:StepTotal, $Label
    Write-Host ""
    Write-Host ("==== GPU Pool install ====") -ForegroundColor Cyan
    Write-Host $banner -ForegroundColor Green
    if ($Detail) { Write-Host ("     {0}" -f $Detail) -ForegroundColor DarkGray }
    if (-not $Quiet) {
        Write-Progress -Activity "GPU Pool install" -Status $banner -PercentComplete ([math]::Min(99, $pct))
    }
}

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
            Write-GpuPoolStep "Downloading Python runtime..." -Detail "Bootstrapping portable CPython via gpu_swarm.portable_python"
            $launcher = Get-Command py -ErrorAction SilentlyContinue
            if (-not $launcher) { throw "No seed Python to bootstrap portable runtime. Use GPUPool.exe." }
            & py -3 -c "from gpu_swarm.portable_python import ensure_portable_python; import json; print(json.dumps(ensure_portable_python(with_venv=True, with_requirements=False)))"
            if (-not (Test-Path $VenvPython)) { throw "Portable bootstrap did not create $VenvPython" }
            return $true
        }
        throw "Python 3.10-3.12 not found (3.13 skipped by default). Run wizard Bootstrap portable Python, GPUPool.exe, or: install_joiner_deps.ps1 -BootstrapPortable"
    }
    Write-GpuPoolStep "Creating GPUPool folder..." -Detail $GpuPoolRoot
    New-Item -ItemType Directory -Force -Path $GpuPoolRoot | Out-Null
    Write-GpuPoolStep "Creating isolated Python environment..." -Detail ("seed={0} -> {1}" -f $seed, $VenvDir)
    if (Test-Path $VenvDir) { Remove-Item -Recurse -Force $VenvDir }
    & $seed -m venv $VenvDir
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPython)) {
        throw "Failed to create venv at $VenvDir"
    }
    return $true
}

function Invoke-VenvPip {
    param(
        [Parameter(Mandatory = $true)][string[]]$PipArgs,
        [string]$ProgressLabel = "Installing dependencies..."
    )
    $all = @("-m", "pip") + $PipArgs
    if ($Quiet) {
        $all += "-q"
        & $VenvPython @all
        return $LASTEXITCODE
    }
    # Stream pip so package names stay visible (do not hide failures).
    Write-Host (">>> {0}" -f $ProgressLabel) -ForegroundColor Yellow
    Write-Host (">>> {0} -m pip {1}" -f $VenvPython, ($PipArgs -join " ")) -ForegroundColor DarkGray
    $allVerbose = $all + @("--progress-bar", "on")
    & $VenvPython @allVerbose
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

Write-Host ""
Write-Host "GPU Pool - friend install helper" -ForegroundColor Cyan
Write-Host "What this does: prepares an isolated Python folder so you can Contribute" -ForegroundColor DarkGray
Write-Host "(share spare GPU/CPU) or Utilize (run jobs). No Docker. Logs stay on screen." -ForegroundColor DarkGray
Write-Host ("Folder: {0}" -f $GpuPoolRoot) -ForegroundColor DarkGray

Write-GpuPoolStep "Checking for a usable Python..." -PercentComplete 5
[void](Ensure-GpuPoolVenv)
$env:GPU_SWARM_PYTHON = $VenvPython
$script:PyArgs = @($VenvPython)
Write-Host ("Using isolated Python: {0}" -f $VenvPython) -ForegroundColor Green

$probe = Test-JoinerImports
$actions = New-Object System.Collections.Generic.List[string]

if ($Force -or -not $probe.ok) {
    Write-GpuPoolStep "Installing dependencies..." -Detail ("from {0} (pip output below - leave this window open)" -f $ReqJoiner) -PercentComplete 40
    $code = Invoke-VenvPip -PipArgs @("install", "-r", $ReqJoiner) -ProgressLabel "Installing dependencies from requirements-joiner.txt..."
    if ($code -ne 0) {
        Write-Host ""
        Write-Host "INSTALL FAILED - pip exit $code. Scroll up for the error; do not close this window yet." -ForegroundColor Red
        Write-Error "pip install -r requirements-joiner failed (exit $code)"
        exit $code
    }
    [void]$actions.Add("pip_install_joiner_requirements")
} else {
    Write-GpuPoolStep "Dependencies already installed - skipping pip." -PercentComplete 50 -Detail "Use -Force to repair/reinstall"
    [void]$actions.Add("skip_requirements_satisfied")
}

$torchResult = $null
if ($WithTorchCuda) {
    $t = Test-TorchCuda
    if ($t.ok -and -not $Force) {
        Write-GpuPoolStep "CUDA PyTorch already available - skipping." -PercentComplete 75 -Detail $t.message
        [void]$actions.Add("skip_torch_cuda_present")
        $torchResult = $t
    } else {
        Write-GpuPoolStep "Downloading CUDA PyTorch (large)..." -Detail ("index {0} - several GB; keep window open" -f $TorchIndexUrl) -PercentComplete 70
        if (Test-Path $ReqCuda) {
            $code = Invoke-VenvPip -PipArgs @("install", "-r", $ReqCuda, "--index-url", $TorchIndexUrl) -ProgressLabel "Installing CUDA torch..."
        } else {
            $code = Invoke-VenvPip -PipArgs @("install", "torch", "--index-url", $TorchIndexUrl) -ProgressLabel "Installing CUDA torch..."
        }
        if ($code -ne 0) {
            Write-Host "CUDA torch install FAILED (exit $code). Contribute/Utilize still work without it." -ForegroundColor Red
            Write-Error "torch CUDA install failed (exit $code)"
            exit $code
        }
        [void]$actions.Add("pip_install_torch_cuda")
        $torchResult = Test-TorchCuda
    }
}

Write-GpuPoolStep "Checking GPU..." -PercentComplete 90 -Detail "nvidia-smi optional - Utilize works without NVIDIA"
$nvidia = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nvidia) {
    try {
        $gpuLine = & nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>$null | Select-Object -First 3
        if ($gpuLine) {
            Write-Host "GPU detected:" -ForegroundColor Green
            $gpuLine | ForEach-Object { Write-Host ("  * {0}" -f $_) }
        } else {
            Write-Host "nvidia-smi present but no GPU lines (drivers ok?)." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "nvidia-smi check skipped: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "No NVIDIA GPU tools on this PC - fine. Use Utilize (or Contribute with VRAM=0)." -ForegroundColor Yellow
}

$final = Test-JoinerImports
Write-GpuPoolStep "Setup ready." -PercentComplete 100 -Detail $(if ($final.ok) { "You can start the desktop app or join the pool." } else { "Some packages still missing." })
if (-not $Quiet) { Write-Progress -Activity "GPU Pool install" -Completed }

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
if (-not $final.ok) {
    Write-Host "FAILED - missing: $($final.missing -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host ""
Write-Host "OK - isolated install finished." -ForegroundColor Green
Write-Host "Next: start-gpu-pool-app.cmd  OR  download GPUPool.exe from GitHub Releases." -ForegroundColor Cyan
Write-Host "Login: invite code glitch-factor + your Discord display name. See LOGIN.md" -ForegroundColor DarkGray
exit 0
