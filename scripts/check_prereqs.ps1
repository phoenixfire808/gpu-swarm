#Requires -Version 5.1
<#
.SYNOPSIS
  GPU Pool one-stop prerequisite check (real probes, no mocks).

.DESCRIPTION
  Reports: Python OK, nvidia-smi OK, scheduler reachable, disk space.
  Default output is JSON. Use -Text for human-readable lines.
  Invoked by app_backend.check_prereqs() or directly from the wizard/CLI.

.PARAMETER SchedulerUrl
  Scheduler base URL to probe (GET /status). Default: http://127.0.0.1:8766

.PARAMETER MinDiskGb
  Warn if free space on project drive is below this many GiB (default 5).

.PARAMETER Text
  Emit clear text instead of JSON.

.PARAMETER Json
  Emit JSON (default). Explicit alias for callers.
#>
[CmdletBinding()]
param(
    [string]$SchedulerUrl = "http://127.0.0.1:8766",
    [double]$MinDiskGb = 5,
    [switch]$Text,
    [switch]$Json
)

$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Find-Python {
    $candidates = @()
    if ($env:GPU_SWARM_PYTHON) { $candidates += $env:GPU_SWARM_PYTHON }
    foreach ($cmd in @("py", "python", "python3")) {
        $w = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($w) { $candidates += $w.Source }
    }
    foreach ($c in $candidates) {
        try {
            if ($c -eq "py" -or (Split-Path -Leaf $c) -match '^py(\.exe)?$') {
                $ver = & py -3 -c "import sys; print(sys.version.split()[0])" 2>$null
                if ($LASTEXITCODE -eq 0 -and $ver) {
                    return @{ ok = $true; exe = "py -3"; version = "$ver"; path = (Get-Command py).Source }
                }
            } else {
                $ver = & $c -c "import sys; print(sys.version.split()[0])" 2>$null
                if ($LASTEXITCODE -eq 0 -and $ver) {
                    return @{ ok = $true; exe = $c; version = "$ver"; path = $c }
                }
            }
        } catch { }
    }
    return @{ ok = $false; exe = ""; version = ""; path = ""; message = "Python 3 not found on PATH (try python.org or 'py -3')" }
}

function Test-NvidiaSmi {
    $path = $null
    $w = Get-Command "nvidia-smi" -ErrorAction SilentlyContinue
    if ($w) { $path = $w.Source }
    if (-not $path) {
        $cand = Join-Path ${env:ProgramFiles} "NVIDIA Corporation\NVSMI\nvidia-smi.exe"
        if (Test-Path $cand) { $path = $cand }
    }
    if (-not $path) {
        return @{ ok = $false; path = ""; gpus = @(); message = "nvidia-smi not found — install NVIDIA drivers" }
    }
    try {
        $out = & $path -L 2>&1 | Out-String
        $gpus = @()
        foreach ($line in ($out -split "`r?`n")) {
            if ($line -match 'GPU\s+\d+:\s*(.+?)\s*\(') { $gpus += $Matches[1].Trim() }
            elseif ($line -match 'GPU\s+\d+:\s*(.+)$') { $gpus += $Matches[1].Trim() }
        }
        $ok = $LASTEXITCODE -eq 0
        return @{
            ok = $ok
            path = $path
            gpus = $gpus
            message = if ($ok) { "nvidia-smi OK ($($gpus.Count) GPU(s))" } else { "nvidia-smi failed: $out" }
        }
    } catch {
        return @{ ok = $false; path = $path; gpus = @(); message = "$_" }
    }
}

function Test-Scheduler([string]$Url) {
    $base = $Url.TrimEnd("/")
    if (-not $base) {
        return @{ ok = $false; url = ""; status_code = 0; message = "Empty scheduler URL" }
    }
    $statusUrl = "$base/status"
    try {
        $resp = Invoke-WebRequest -Uri $statusUrl -UseBasicParsing -TimeoutSec 5
        $code = [int]$resp.StatusCode
        $ok = $code -ge 200 -and $code -lt 300
        $snippet = ""
        try { $snippet = $resp.Content.Substring(0, [Math]::Min(200, $resp.Content.Length)) } catch { }
        return @{
            ok = $ok
            url = $base
            status_code = $code
            message = if ($ok) { "Scheduler reachable at $base" } else { "HTTP $code from $statusUrl" }
            body_snippet = $snippet
        }
    } catch {
        return @{
            ok = $false
            url = $base
            status_code = 0
            message = "Scheduler unreachable ($statusUrl): $($_.Exception.Message)"
            body_snippet = ""
        }
    }
}

function Get-DiskInfo {
    $target = $RepoRoot
    try {
        $drive = (Get-Item $target).PSDrive
        if (-not $drive) {
            $rootPath = [System.IO.Path]::GetPathRoot((Resolve-Path $target))
            $drive = Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Root -eq $rootPath } | Select-Object -First 1
        }
        $free = [double]$drive.Free
        $used = [double]$drive.Used
        $total = $free + $used
        $freeGb = [math]::Round($free / 1GB, 2)
        $totalGb = [math]::Round($total / 1GB, 2)
        $ok = $freeGb -ge $MinDiskGb
        return @{
            ok = $ok
            path = $target
            free_gb = $freeGb
            total_gb = $totalGb
            free_mb = [int][math]::Floor($free / 1MB)
            total_mb = [int][math]::Floor($total / 1MB)
            min_disk_gb = $MinDiskGb
            message = if ($ok) { "Disk OK: ${freeGb} GiB free (need >= $MinDiskGb)" } else { "Low disk: ${freeGb} GiB free (need >= $MinDiskGb)" }
        }
    } catch {
        return @{
            ok = $false
            path = $target
            free_gb = 0
            total_gb = 0
            free_mb = 0
            total_mb = 0
            min_disk_gb = $MinDiskGb
            message = "Disk check failed: $_"
        }
    }
}

$python = Find-Python
$nvidia = Test-NvidiaSmi
$scheduler = Test-Scheduler $SchedulerUrl
$disk = Get-DiskInfo

$overall = [bool]($python.ok -and $nvidia.ok -and $scheduler.ok -and $disk.ok)

$result = [ordered]@{
    ok = $overall
    repo_root = $RepoRoot
    python = $python
    nvidia_smi = $nvidia
    scheduler = $scheduler
    disk = $disk
    checked_at = (Get-Date).ToString("o")
}

if ($Text -and -not $Json) {
    $pass = { param($b) if ($b) { "OK" } else { "FAIL" } }
    Write-Output ("overall:      {0}" -f (& $pass $overall))
    Write-Output ("python:       {0}  {1} ({2})" -f (& $pass $python.ok), $python.version, $python.exe)
    Write-Output ("nvidia-smi:   {0}  {1}" -f (& $pass $nvidia.ok), $nvidia.message)
    Write-Output ("scheduler:    {0}  {1}" -f (& $pass $scheduler.ok), $scheduler.message)
    Write-Output ("disk:         {0}  {1}" -f (& $pass $disk.ok), $disk.message)
    if (-not $overall) { exit 1 }
    exit 0
}

$result | ConvertTo-Json -Depth 6 -Compress:$false
if (-not $overall) { exit 1 }
exit 0
