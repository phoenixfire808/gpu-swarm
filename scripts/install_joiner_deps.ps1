#Requires -Version 5.1
param(
    [switch]$WithTorchCuda,
    [string]$TorchIndexUrl = "https://download.pytorch.org/whl/cu128",
    [switch]$Force,
    [switch]$Quiet
)
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$ReqFile = Join-Path $RepoRoot "requirements.txt"
if (-not (Test-Path $ReqFile)) { Write-Error "Missing requirements.txt at $ReqFile"; exit 2 }

$script:PyArgs = @()

function Resolve-PythonArgs {
    if ($env:GPU_SWARM_PYTHON -and (Test-Path $env:GPU_SWARM_PYTHON)) { return @($env:GPU_SWARM_PYTHON) }
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        & py -3 -c "import sys" 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { return @("py", "-3") }
    }
    foreach ($name in @("python", "python3")) {
        $w = Get-Command $name -ErrorAction SilentlyContinue
        if (-not $w) { continue }
        & $w.Source -c "import sys" 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { return @($w.Source) }
    }
    throw "Python 3 not found."
}

function Invoke-PyCmd {
    param([Parameter(Mandatory=$true)][AllowEmptyCollection()][string[]]$ExtraArgs)
    $cmd = [string]$script:PyArgs[0]
    $rest = @()
    if ($script:PyArgs.Count -gt 1) { $rest = @($script:PyArgs[1..($script:PyArgs.Count - 1)]) }
    $all = @($rest) + @($ExtraArgs)
    if ($all.Count -gt 0) { & $cmd @all } else { & $cmd }
    return $LASTEXITCODE
}

function Test-JoinerImports {
    $probeFile = Join-Path $env:TEMP "gpu_swarm_probe_imports.py"
    @"
import importlib, sys
mods = ["httpx", "dotenv", "fastapi", "uvicorn", "psutil", "pydantic", "aiosqlite"]
optional = ["customtkinter"]
missing, opt_missing = [], []
for m in mods:
    try:
        importlib.import_module(m)
    except ImportError:
        missing.append(m)
for m in optional:
    try:
        importlib.import_module(m)
    except ImportError:
        opt_missing.append(m)
print("MISSING:" + ",".join(missing))
print("OPT_MISSING:" + ",".join(opt_missing))
sys.exit(0 if not missing else 1)
"@ | Set-Content -Path $probeFile -Encoding UTF8
    $out = Invoke-PyCmd @($probeFile) 2>&1 | Out-String
    Remove-Item -Force $probeFile -ErrorAction SilentlyContinue
    $missing = @(); $optMissing = @()
    foreach ($line in $out.Split([char]10)) {
        $t = $line.Trim([char]13)
        if ($t.StartsWith("MISSING:")) {
            $raw = $t.Substring(8).Trim()
            if ($raw) { $missing = @($raw.Split(",") | Where-Object { $_ }) }
        }
        if ($t.StartsWith("OPT_MISSING:")) {
            $raw = $t.Substring(12).Trim()
            if ($raw) { $optMissing = @($raw.Split(",") | Where-Object { $_ }) }
        }
    }
    return @{ ok = ($missing.Count -eq 0); missing = $missing; optional_missing = $optMissing; raw = $out }
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
        $out = Invoke-PyCmd @($probeFile) 2>&1 | Out-String
        Remove-Item -Force $probeFile -ErrorAction SilentlyContinue
        return @{ ok = ($LASTEXITCODE -eq 0); message = $out.Trim() }
    } catch {
        Remove-Item -Force $probeFile -ErrorAction SilentlyContinue
        return @{ ok = $false; message = "$_" }
    }
}

$script:PyArgs = @(Resolve-PythonArgs)
Write-Host ("Using Python: {0}" -f ($script:PyArgs -join " "))

$probe = Test-JoinerImports
$actions = New-Object System.Collections.Generic.List[string]
$inVenv = [bool]($env:VIRTUAL_ENV -or $env:CONDA_PREFIX)
$pipExtra = @("-m", "pip", "install")
if (-not $inVenv) { $pipExtra += "--user" }
if ($Quiet) { $pipExtra += "-q" }

if ($Force -or -not $probe.ok) {
    Write-Host "Installing from requirements.txt (idempotent pip)..."
    $code = Invoke-PyCmd ($pipExtra + @("-r", $ReqFile))
    if ($code -ne 0) { Write-Error "pip install -r requirements.txt failed (exit $code)"; exit $code }
    [void]$actions.Add("pip_install_requirements")
} else {
    Write-Host "Core requirements already satisfied - skipping pip -r requirements.txt"
    [void]$actions.Add("skip_requirements_satisfied")
}

$probe2 = Test-JoinerImports
if ($probe2.optional_missing -contains "customtkinter") {
    Write-Host "Installing customtkinter (desktop joiner UI)..."
    $code = Invoke-PyCmd ($pipExtra + @("customtkinter>=5.2"))
    if ($code -ne 0) { Write-Error "customtkinter install failed"; exit $code }
    [void]$actions.Add("pip_install_customtkinter")
}

$torchResult = $null
if ($WithTorchCuda) {
    $t = Test-TorchCuda
    if ($t.ok -and -not $Force) {
        Write-Host ("torch CUDA already available - {0}" -f $t.message)
        [void]$actions.Add("skip_torch_cuda_present")
        $torchResult = $t
    } else {
        Write-Host ("Installing torch with CUDA wheels from {0} (large download)..." -f $TorchIndexUrl)
        $code = Invoke-PyCmd ($pipExtra + @("torch", "--index-url", $TorchIndexUrl))
        if ($code -ne 0) { Write-Error "torch CUDA install failed (exit $code)"; exit $code }
        [void]$actions.Add("pip_install_torch_cuda")
        $torchResult = Test-TorchCuda
    }
}

$final = Test-JoinerImports
$summary = [ordered]@{
    ok = [bool]$final.ok
    python = ($script:PyArgs -join " ")
    actions = @($actions)
    missing = @($final.missing)
    optional_missing = @($final.optional_missing)
    with_torch_cuda = [bool]$WithTorchCuda
    torch = $torchResult
    repo_root = $RepoRoot
    script = "scripts/install_joiner_deps.ps1"
}
$summary | ConvertTo-Json -Depth 5
if (-not $final.ok) { exit 1 }
exit 0
