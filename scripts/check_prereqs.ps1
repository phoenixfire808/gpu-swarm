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
    $gpuHome = Join-Path $env:LOCALAPPDATA 'GPUPool'
    $venvPy = Join-Path $gpuHome 'venv\Scripts\python.exe'
    $portablePy = Join-Path $gpuHome 'python\python.exe'
    if ($env:GPU_SWARM_PYTHON -and (Test-Path $env:GPU_SWARM_PYTHON)) {
        $ver = & $env:GPU_SWARM_PYTHON -c 'import sys; print(sys.version.split()[0])' 2>$null
        if ($LASTEXITCODE -eq 0 -and $ver) {
            return @{ ok = $true; exe = $env:GPU_SWARM_PYTHON; version = "$ver"; path = $env:GPU_SWARM_PYTHON; source = 'GPU_SWARM_PYTHON' }
        }
    }
    foreach ($cand in @($venvPy, $portablePy)) {
        if (-not (Test-Path $cand)) { continue }
        $ver = & $cand -c 'import sys; print(sys.version.split()[0])' 2>$null
        if ($LASTEXITCODE -eq 0 -and $ver) {
            return @{ ok = $true; exe = $cand; version = "$ver"; path = $cand; source = 'GPUPool-isolated' }
        }
    }
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        $ver = & py -3 -c 'import sys; print(sys.version.split()[0])' 2>$null
        if ($LASTEXITCODE -eq 0 -and $ver) {
            return @{ ok = $true; exe = 'py -3'; version = "$ver"; path = $py.Source; source = 'py-launcher' }
        }
    }
    foreach ($name in @('python','python3')) {
        $w = Get-Command $name -ErrorAction SilentlyContinue
        if (-not $w) { continue }
        $ver = & $w.Source -c 'import sys; print(sys.version.split()[0])' 2>$null
        if ($LASTEXITCODE -eq 0 -and $ver) {
            return @{ ok = $true; exe = $w.Source; version = "$ver"; path = $w.Source; source = 'PATH' }
        }
    }
    return @{ ok = $false; exe = ''; version = ''; path = ''; message = 'Python 3.10+ not found — bootstrap portable Python or use GPUPool.exe' }
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

function Get-VirtualBoxProbe {
    $paths = @(
        (Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Oracle\VirtualBox\VBoxManage.exe')
    )
    $exe = $null
    foreach ($p in $paths) { if (Test-Path $p) { $exe = $p; break } }
    $cmd = Get-Command VBoxManage -ErrorAction SilentlyContinue
    if (-not $exe -and $cmd) { $exe = $cmd.Source }
    if (-not $exe) {
        return @{ ok = $false; installed = $false; path = ''; version = ''; message = 'VirtualBox not installed (needed only for Workspace VM)' }
    }
    $ver = ''
    try { $ver = (& $exe --version 2>$null | Select-Object -First 1).ToString().Trim() } catch {}
    return @{ ok = $true; installed = $true; path = $exe; version = $ver; message = "VirtualBox OK ($ver)" }
}

function Get-VagrantProbe {
    $paths = @(
        (Join-Path $env:ProgramFiles 'Vagrant\bin\vagrant.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Vagrant\bin\vagrant.exe')
    )
    $exe = $null
    foreach ($p in $paths) { if (Test-Path $p) { $exe = $p; break } }
    $cmd = Get-Command vagrant -ErrorAction SilentlyContinue
    if (-not $exe -and $cmd) { $exe = $cmd.Source }
    if (-not $exe) {
        return @{ ok = $false; installed = $false; path = ''; version = ''; message = 'Vagrant not installed (needed only for Workspace VM)' }
    }
    $ver = ''
    try { $ver = (& $exe --version 2>$null | Select-Object -First 1).ToString().Trim() } catch {}
    return @{ ok = $true; installed = $true; path = $exe; version = $ver; message = "Vagrant OK ($ver)" }
}

function Get-TailscaleProbe {
    $paths = @(
        (Join-Path $env:ProgramFiles 'Tailscale\tailscale.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Tailscale\tailscale.exe')
    )
    $exe = $null
    foreach ($p in $paths) { if (Test-Path $p) { $exe = $p; break } }
    $cmd = Get-Command tailscale -ErrorAction SilentlyContinue
    if (-not $exe -and $cmd) { $exe = $cmd.Source }
    if (-not $exe) {
        return @{ ok = $false; installed = $false; logged_in = $false; ipv4 = ''; path = ''; message = 'Tailscale not installed (optional if public portal is up)' }
    }
    $ipv4 = ''
    $loggedIn = $false
    try {
        $ipOut = & $exe ip -4 2>$null | Select-Object -First 1
        if ($ipOut -match '100\.\d+\.\d+\.\d+') { $ipv4 = $Matches[0]; $loggedIn = $true }
    } catch {}
    $msg = if ($loggedIn) { "Tailscale OK ($ipv4)" } else { 'Tailscale installed — login still needed' }
    return @{ ok = $true; installed = $true; logged_in = $loggedIn; ipv4 = $ipv4; path = $exe; message = $msg }
}

$python = Find-Python
$nvidia = Test-NvidiaSmi
$scheduler = Test-Scheduler $SchedulerUrl
$disk = Get-DiskInfo
$virtualbox = Get-VirtualBoxProbe
$vagrant = Get-VagrantProbe
$tailscale = Get-TailscaleProbe
# NVIDIA / Tailscale / Workspace tools optional — share path needs python+scheduler+disk
$overall = [bool]($python.ok -and $scheduler.ok -and $disk.ok)
$result = [ordered]@{
    ok = $overall
    repo_root = $RepoRoot
    python = $python
    nvidia_smi = $nvidia
    nvidia_required = $false
    cpu_only_ok = -not [bool]$nvidia.ok
    scheduler = $scheduler
    disk = $disk
    virtualbox = $virtualbox
    vagrant = $vagrant
    tailscale = $tailscale
    workspace_tools_ready = [bool]($virtualbox.ok -and $vagrant.ok)
    checked_at = (Get-Date).ToString('o')
    script = 'scripts/check_prereqs.ps1'
    note = 'No NVIDIA? Utilize or CPU contribute. No Tailscale? Use public portal. Workspace needs VirtualBox+Vagrant — run scripts/install-prereqs.cmd'
}

if ($Text -and -not $Json) {
    function Format-Pass([bool]$b) { if ($b) { 'OK' } else { 'FAIL' } }
    function Format-Opt([bool]$b) { if ($b) { 'OK' } else { 'SKIP (optional)' } }
    Write-Output ("overall:      {0}" -f (Format-Pass $overall))
    Write-Output ("python:       {0}  {1} ({2})" -f (Format-Pass $python.ok), $python.version, $python.exe)
    Write-Output ("nvidia-smi:   {0}  {1}" -f (Format-Opt $nvidia.ok), $nvidia.message)
    if (-not $nvidia.ok) { Write-Output "note:         No NVIDIA — Utilize or CPU contribute still OK" }
    Write-Output ("scheduler:    {0}  {1}" -f (Format-Pass $scheduler.ok), $scheduler.message)
    Write-Output ("disk:         {0}  {1}" -f (Format-Pass $disk.ok), $disk.message)
    Write-Output ("tailscale:    {0}  {1}" -f (Format-Opt $tailscale.ok), $tailscale.message)
    Write-Output ("virtualbox:   {0}  {1}" -f (Format-Opt $virtualbox.ok), $virtualbox.message)
    Write-Output ("vagrant:      {0}  {1}" -f (Format-Opt $vagrant.ok), $vagrant.message)
    if (-not $overall) { exit 1 }
    exit 0
}
$result | ConvertTo-Json -Depth 6
if (-not $overall) { exit 1 }
exit 0