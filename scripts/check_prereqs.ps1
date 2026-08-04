#Requires -Version 5.1
param(
    [string]$SchedulerUrl = 'http://127.0.0.1:8766',
    [double]$MinDiskGb = 5,
    [switch]$Text,
    [switch]$Json
)
$ErrorActionPreference = 'Continue'
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Find-Python {
    if ($env:GPU_SWARM_PYTHON -and (Test-Path $env:GPU_SWARM_PYTHON)) {
        $ver = & $env:GPU_SWARM_PYTHON -c 'import sys; print(sys.version.split()[0])' 2>$null
        if ($LASTEXITCODE -eq 0 -and $ver) {
            return @{ ok = $true; exe = $env:GPU_SWARM_PYTHON; version = "$ver"; path = $env:GPU_SWARM_PYTHON }
        }
    }
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        $ver = & py -3 -c 'import sys; print(sys.version.split()[0])' 2>$null
        if ($LASTEXITCODE -eq 0 -and $ver) {
            return @{ ok = $true; exe = 'py -3'; version = "$ver"; path = $py.Source }
        }
    }
    foreach ($name in @('python','python3')) {
        $w = Get-Command $name -ErrorAction SilentlyContinue
        if (-not $w) { continue }
        $ver = & $w.Source -c 'import sys; print(sys.version.split()[0])' 2>$null
        if ($LASTEXITCODE -eq 0 -and $ver) {
            return @{ ok = $true; exe = $w.Source; version = "$ver"; path = $w.Source }
        }
    }
    return @{ ok = $false; exe = ''; version = ''; path = ''; message = 'Python 3 not found on PATH' }
}

function Test-NvidiaSmi {
    $path = $null
    $w = Get-Command nvidia-smi -ErrorAction SilentlyContinue
    if ($w) { $path = $w.Source }
    if (-not $path) {
        $cand = Join-Path $env:ProgramFiles 'NVIDIA Corporation\NVSMI\nvidia-smi.exe'
        if (Test-Path $cand) { $path = $cand }
    }
    if (-not $path) {
        return @{ ok = $false; path = ''; gpus = @(); message = 'nvidia-smi not found - install NVIDIA drivers' }
    }
    try {
        $lines = & $path -L 2>&1
        $gpus = New-Object System.Collections.Generic.List[string]
        foreach ($line in $lines) {
            $s = [string]$line
            if ($s -match 'GPU\s+\d+:\s*(.+?)\s*\(') { [void]$gpus.Add($Matches[1].Trim()) }
            elseif ($s -match 'GPU\s+\d+:\s*(.+)$') { [void]$gpus.Add($Matches[1].Trim()) }
        }
        $ok = ($LASTEXITCODE -eq 0)
        $count = $gpus.Count
        $msg = if ($ok) { "nvidia-smi OK ($count GPUs)" } else { 'nvidia-smi failed' }
        return @{ ok = $ok; path = $path; gpus = @($gpus); message = $msg }
    } catch {
        return @{ ok = $false; path = $path; gpus = @(); message = "$_" }
    }
}

function Test-Scheduler([string]$Url) {
    $base = $Url.TrimEnd('/')
    if (-not $base) { return @{ ok = $false; url = ''; status_code = 0; message = 'Empty scheduler URL' } }
    $statusUrl = "$base/status"
    try {
        $resp = Invoke-WebRequest -Uri $statusUrl -UseBasicParsing -TimeoutSec 5
        $code = [int]$resp.StatusCode
        $ok = $code -ge 200 -and $code -lt 300
        $snippet = ''
        try { $snippet = $resp.Content.Substring(0, [Math]::Min(200, $resp.Content.Length)) } catch {}
        $msg = if ($ok) { "Scheduler reachable at $base" } else { "HTTP $code from $statusUrl" }
        return @{ ok = $ok; url = $base; status_code = $code; message = $msg; body_snippet = $snippet }
    } catch {
        return @{ ok = $false; url = $base; status_code = 0; message = "Scheduler unreachable ($statusUrl): $($_.Exception.Message)"; body_snippet = '' }
    }
}

function Get-DiskInfo {
    $target = $RepoRoot
    try {
        $resolved = (Resolve-Path $target).Path
        $rootPath = [System.IO.Path]::GetPathRoot($resolved)
        $drive = Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Root -eq $rootPath } | Select-Object -First 1
        if (-not $drive) {
            $usage = [System.IO.DriveInfo]::new($rootPath)
            $free = [double]$usage.AvailableFreeSpace
            $total = [double]$usage.TotalSize
        } else {
            $free = [double]$drive.Free
            $total = [double]($drive.Free + $drive.Used)
        }
        $freeGb = [math]::Round($free / 1GB, 2)
        $totalGb = [math]::Round($total / 1GB, 2)
        $ok = $freeGb -ge $MinDiskGb
        $msg = if ($ok) { "Disk OK: $freeGb GiB free (need >= $MinDiskGb)" } else { "Low disk: $freeGb GiB free (need >= $MinDiskGb)" }
        return @{ ok = $ok; path = $target; free_gb = $freeGb; total_gb = $totalGb; free_mb = [int][math]::Floor($free / 1MB); total_mb = [int][math]::Floor($total / 1MB); min_disk_gb = $MinDiskGb; message = $msg }
    } catch {
        return @{ ok = $false; path = $target; free_gb = 0; total_gb = 0; free_mb = 0; total_mb = 0; min_disk_gb = $MinDiskGb; message = "Disk check failed: $_" }
    }
}

$python = Find-Python
$nvidia = Test-NvidiaSmi
$scheduler = Test-Scheduler $SchedulerUrl
$disk = Get-DiskInfo
$overall = [bool]($python.ok -and $nvidia.ok -and $scheduler.ok -and $disk.ok)
$result = [ordered]@{ ok = $overall; repo_root = $RepoRoot; python = $python; nvidia_smi = $nvidia; scheduler = $scheduler; disk = $disk; checked_at = (Get-Date).ToString('o'); script = 'scripts/check_prereqs.ps1' }

if ($Text -and -not $Json) {
    function Format-Pass([bool]$b) { if ($b) { 'OK' } else { 'FAIL' } }
    Write-Output ("overall:      {0}" -f (Format-Pass $overall))
    Write-Output ("python:       {0}  {1} ({2})" -f (Format-Pass $python.ok), $python.version, $python.exe)
    Write-Output ("nvidia-smi:   {0}  {1}" -f (Format-Pass $nvidia.ok), $nvidia.message)
    Write-Output ("scheduler:    {0}  {1}" -f (Format-Pass $scheduler.ok), $scheduler.message)
    Write-Output ("disk:         {0}  {1}" -f (Format-Pass $disk.ok), $disk.message)
    if (-not $overall) { exit 1 }
    exit 0
}
$result | ConvertTo-Json -Depth 6
if (-not $overall) { exit 1 }
exit 0