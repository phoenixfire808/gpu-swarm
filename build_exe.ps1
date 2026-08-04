#Requires -Version 5.1
<#
.SYNOPSIS
  Build GPUPool.exe (Windows onefile) with PyInstaller.

.DESCRIPTION
  Reproducible release build. Does NOT bundle torch/CUDA or Discord secrets.
  Output: dist\GPUPool.exe

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
#>
param(
    [switch]$Clean,
    [switch]$SkipInstallCheck
)

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot
Set-Location $RepoRoot

function Resolve-Python {
    if ($env:GPU_SWARM_PYTHON -and (Test-Path $env:GPU_SWARM_PYTHON)) {
        return $env:GPU_SWARM_PYTHON
    }
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        $exe = & py -3 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $exe) { return $exe.Trim() }
    }
    foreach ($name in @("python", "python3")) {
        $w = Get-Command $name -ErrorAction SilentlyContinue
        if ($w) { return $w.Source }
    }
    throw "Python 3.10+ not found. Install from https://www.python.org/downloads/windows/"
}

$Python = Resolve-Python
Write-Host "Using Python: $Python"

if (-not $SkipInstallCheck) {
    & $Python -c "import PyInstaller" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing PyInstaller (missing)..."
        & $Python -m pip install --user "pyinstaller>=6.0"
        if ($LASTEXITCODE -ne 0) { throw "pip install pyinstaller failed" }
    }
    # Ensure app deps used by Analysis are importable (avoid reinstall if present).
    & $Python -c "import customtkinter, httpx, psutil, pydantic, dotenv, fastapi, uvicorn, aiosqlite" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing requirements-app.txt (missing joiner deps)..."
        & $Python -m pip install --user -r (Join-Path $RepoRoot "requirements-app.txt")
        if ($LASTEXITCODE -ne 0) { throw "pip install requirements-app failed" }
    }
}

if ($Clean) {
    foreach ($d in @("build", "dist")) {
        $p = Join-Path $RepoRoot $d
        if (Test-Path $p) {
            Write-Host "Cleaning $p"
            Remove-Item -Recurse -Force $p
        }
    }
}

$spec = Join-Path $RepoRoot "gpu_pool.spec"
if (-not (Test-Path $spec)) { throw "Missing gpu_pool.spec" }

Write-Host "Running PyInstaller (onefile windowed GPUPool.exe)..."
& $Python -m PyInstaller --noconfirm --clean $spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed (exit $LASTEXITCODE)" }

$exe = Join-Path $RepoRoot "dist\GPUPool.exe"
if (-not (Test-Path $exe)) { throw "Expected output missing: $exe" }

$size = (Get-Item $exe).Length
Write-Host ""
Write-Host "OK: $exe"
Write-Host ("Size: {0:N1} MB" -f ($size / 1MB))
Write-Host "Notes:"
Write-Host "  - No .env / secrets are bundled"
Write-Host "  - Torch/CUDA not shipped (optional first-run / system Python)"
Write-Host "  - Contributors still need NVIDIA drivers + Tailscale"
Write-Host "  - Publish: gh release create v0.1.0 dist/GPUPool.exe --title ... --notes-file ..."
exit 0
