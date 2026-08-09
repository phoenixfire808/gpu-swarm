#Requires -Version 5.1
<#
.SYNOPSIS
  Start a Cloudflare quick tunnel to the portal (8767).
  One public HTTPS URL -- portal UI + /pool-api proxy to scheduler.
  No Cloudflare account required (trycloudflare.com).

.NOTES
  Writes:
    data/public_endpoints.json
    data/public_endpoints.share.txt
  Keep this window open while friends need access.

  2026-08-07 fix: replaced literal arrow chars with ASCII in user-facing
  strings so they don't get mojibake-decoded by Windows PowerShell's default
  cp1252 console encoding. Also forced UTF-8 OutputEncoding at the top of the
  script body (statements MUST come after param() in 5.1 or parsing fails).
#>

param(
    [int]$PortalPort = 8767,
    [string]$LocalPortal = "http://127.0.0.1:8767",
    [switch]$SkipPortalCheck,
    [switch]$AlsoScheduler,
    [int]$SchedulerPort = 8766
)

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$DataDir = Join-Path $RepoRoot "data"
$JsonPath = Join-Path $DataDir "public_endpoints.json"
$SharePath = Join-Path $DataDir "public_endpoints.share.txt"
$LogPath = Join-Path $DataDir "cloudflared_portal.log"
$PidPath = Join-Path $DataDir "cloudflared_portal.pid"
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null

$install = Join-Path $PSScriptRoot "install_cloudflared.ps1"
$ExePath = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $install -Quiet | Select-Object -Last 1
if (-not $ExePath -or -not (Test-Path $ExePath)) {
    throw "cloudflared.exe missing after install_cloudflared.ps1"
}

if (-not $SkipPortalCheck) {
    try {
        $r = Invoke-WebRequest -Uri "$LocalPortal/health" -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -ne 200) { throw "portal health HTTP $($r.StatusCode)" }
        Write-Host "[public] portal OK at $LocalPortal/health"
    } catch {
        Write-Host "[public] WARNING: portal not reachable at $LocalPortal -- start start-portal.cmd first"
        Write-Host "         $($_.Exception.Message)"
    }
}

# Stop previous tunnel if we own a pid file
if (Test-Path $PidPath) {
    try {
        $old = [int](Get-Content $PidPath -ErrorAction SilentlyContinue | Select-Object -First 1)
        if ($old -gt 0) {
            $p = Get-Process -Id $old -ErrorAction SilentlyContinue
            if ($p -and $p.ProcessName -match "cloudflared") {
                Write-Host "[public] stopping previous cloudflared pid $old"
                Stop-Process -Id $old -Force -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 1
            }
        }
    } catch { }
}

$target = "http://127.0.0.1:$PortalPort"
Write-Host "[public] starting quick tunnel -> $target"
Write-Host "[public] no Cloudflare login required (trycloudflare.com)"
Write-Host "[public] leave this window open; Ctrl+C to stop"
Write-Host ""

if (Test-Path $LogPath) { Remove-Item -Force $LogPath -ErrorAction SilentlyContinue }

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $ExePath
$psi.Arguments = "tunnel --url $target --no-autoupdate"
$psi.WorkingDirectory = $RepoRoot
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.CreateNoWindow = $true

$proc = New-Object System.Diagnostics.Process
$proc.StartInfo = $psi

$script:PublicUrl = $null
$urlRegex = [regex]'https://[a-zA-Z0-9-]+\.trycloudflare\.com'

$outHandler = {
    if (-not $EventArgs.Data) { return }
    $line = $EventArgs.Data
    Add-Content -Path $LogPath -Value $line
    Write-Host $line
    if (-not $script:PublicUrl) {
        $m = $urlRegex.Match($line)
        if ($m.Success) { $script:PublicUrl = $m.Value.TrimEnd("/") }
    }
}
$errHandler = {
    if (-not $EventArgs.Data) { return }
    $line = $EventArgs.Data
    Add-Content -Path $LogPath -Value $line
    Write-Host $line
    if (-not $script:PublicUrl) {
        $m = $urlRegex.Match($line)
        if ($m.Success) { $script:PublicUrl = $m.Value.TrimEnd("/") }
    }
}

Register-ObjectEvent -InputObject $proc -EventName OutputDataReceived -Action $outHandler | Out-Null
Register-ObjectEvent -InputObject $proc -EventName ErrorDataReceived -Action $errHandler | Out-Null

[void]$proc.Start()
$proc.BeginOutputReadLine()
$proc.BeginErrorReadLine()
$proc.Id | Set-Content -Path $PidPath -Encoding ascii

$deadline = (Get-Date).AddSeconds(45)
while (-not $script:PublicUrl -and (Get-Date) -lt $deadline -and -not $proc.HasExited) {
    Start-Sleep -Milliseconds 400
    # Also scrape log in case event timing missed a line
    if (Test-Path $LogPath) {
        $m = $urlRegex.Match((Get-Content $LogPath -Raw -ErrorAction SilentlyContinue))
        if ($m.Success) { $script:PublicUrl = $m.Value.TrimEnd("/") }
    }
}

if (-not $script:PublicUrl) {
    Write-Host ""
    Write-Host "[public] BLOCKER: no trycloudflare.com URL appeared within 45s."
    Write-Host "         Check $LogPath"
    Write-Host "         If cloudflared asks to login, quick tunnels may be blocked on this network;"
    Write-Host "         fallback: ngrok http $PortalPort (documented in DOWNLOAD.md)."
    if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
    exit 2
}

$portalPublic = $script:PublicUrl
$portalPath = "$portalPublic/portal"
$poolApi = "$portalPublic/pool-api"
$updated = (Get-Date).ToUniversalTime().ToString("o")

$payload = [ordered]@{
    mode                 = "cloudflared_quick"
    portal_public_url    = $portalPublic
    portal_path          = $portalPath
    pool_api_public_url  = $poolApi
    scheduler_local      = "http://127.0.0.1:$SchedulerPort"
    portal_local         = $LocalPortal
    updated_at           = $updated
    invite_code          = "glitch-factor"
    note                 = "Public HTTPS via Cloudflare quick tunnel -- no Tailscale needed. Invite code still required. Use pool_api_public_url for scheduler API (portal /pool-api proxy)."
    cloudflared_pid      = $proc.Id
}
$payload | ConvertTo-Json -Depth 5 | Set-Content -Path $JsonPath -Encoding utf8

$share = @"
GPU Pool -- public access (no Tailscale needed)
----------------------------------------------
Portal:     $portalPath
Pool API:   $poolApi  (proxies scheduler; allowlisted jobs only)
Invite:     glitch-factor

Laptop / no NVIDIA: open Portal -> sign in with invite + display name -> Utilize.
Optional: Contribute CPU/RAM/disk with VRAM=0.
Tailscale is optional while this tunnel is running.
Updated:    $updated
"@
Set-Content -Path $SharePath -Value $share -Encoding utf8

Write-Host ""
Write-Host "============================================================"
Write-Host " PUBLIC ACCESS READY -- share with pool members (e.g. YourDiscordName)"
Write-Host "============================================================"
Write-Host " Portal:   $portalPath"
Write-Host " Pool API: $poolApi"
Write-Host " Invite:   glitch-factor"
Write-Host " Share:    $SharePath"
Write-Host "============================================================"
Write-Host ""

# Optional second quick tunnel for raw scheduler (usually unnecessary)
if ($AlsoScheduler) {
    Write-Host "[public] AlsoScheduler: starting second tunnel for :$SchedulerPort (optional)"
    $schedLog = Join-Path $DataDir "cloudflared_scheduler.log"
    $schedPsi = New-Object System.Diagnostics.ProcessStartInfo
    $schedPsi.FileName = $ExePath
    $schedPsi.Arguments = "tunnel --url http://127.0.0.1:$SchedulerPort --no-autoupdate"
    $schedPsi.WorkingDirectory = $RepoRoot
    $schedPsi.UseShellExecute = $false
    $schedPsi.RedirectStandardOutput = $true
    $schedPsi.RedirectStandardError = $true
    $schedPsi.CreateNoWindow = $true
    $schedProc = New-Object System.Diagnostics.Process
    $schedProc.StartInfo = $schedPsi
    [void]$schedProc.Start()
    $schedProc.BeginOutputReadLine()
    $schedProc.BeginErrorReadLine()
    Start-Sleep -Seconds 8
    if (Test-Path $schedLog) {
        $sm = $urlRegex.Match((Get-Content $schedLog -Raw -ErrorAction SilentlyContinue))
        if ($sm.Success) {
            Write-Host "[public] Scheduler public URL: $($sm.Value)  (prefer /pool-api instead)"
        }
    }
}

try {
    while (-not $proc.HasExited) {
        Start-Sleep -Seconds 2
        # Refresh share file timestamp so UI can detect liveness
        if ($script:PublicUrl) {
            $payload.updated_at = (Get-Date).ToUniversalTime().ToString("o")
            $payload | ConvertTo-Json -Depth 5 | Set-Content -Path $JsonPath -Encoding utf8
        }
    }
} finally {
    Write-Host "[public] tunnel process exited (code $($proc.ExitCode))"
    if (Test-Path $PidPath) { Remove-Item -Force $PidPath -ErrorAction SilentlyContinue }
}
exit $(if ($proc.ExitCode) { $proc.ExitCode } else { 0 })
