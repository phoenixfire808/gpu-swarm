#Requires -Version 5.1
<#
.SYNOPSIS
  Guided GPU Pool named Cloudflare Tunnel setup and optional launch.

.DESCRIPTION
  Installs cloudflared if needed, completes the user's local Cloudflare login,
  creates or reuses one named tunnel, routes DNS, writes a GPU Pool-only config
  under %USERPROFILE%\\.cloudflared, and optionally launches the tunnel.

  This script never reads or prints credential contents. It never touches the
  Mission Control/OpenClaw tunnel.yml.
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Hostname,
    [string]$TunnelName = "gpu-pool",
    [string]$ConfigPath = "",
    [switch]$Launch,
    [switch]$Json,
    [switch]$KeepOpen
)

$ErrorActionPreference = "Stop"
$CloudflareHome = Join-Path $env:USERPROFILE ".cloudflared"
$RepoOrBundleRoot = Split-Path -Parent $PSScriptRoot
$InstallDir = Join-Path ($env:LOCALAPPDATA) "GPUPool\tools"
$LaunchPid = 0
$TunnelId = ""
$ConfigPath = if ($ConfigPath) { [Environment]::ExpandEnvironmentVariables($ConfigPath) } else { Join-Path $CloudflareHome "gpu-pool.yml" }

function Finish([bool]$Ok, [string]$Message, [int]$Code = 0, [hashtable]$Extra = @{}) {
    $result = [ordered]@{
        ok = $Ok
        message = $Message
        code = $Code
        hostname = $Hostname
        tunnel_name = $TunnelName
        config_path = $ConfigPath
    }
    foreach ($key in $Extra.Keys) { $result[$key] = $Extra[$key] }
    if ($Json) {
        $result | ConvertTo-Json -Compress
    } else {
        if ($Ok) { Write-Host "[GPU Pool] $Message" -ForegroundColor Green }
        else { Write-Host "[GPU Pool] ERROR: $Message" -ForegroundColor Red }
        if ($Extra.ContainsKey("next_step")) { Write-Host "Next: $($Extra.next_step)" }
        if ($Extra.ContainsKey("public_url") -and $Extra.public_url) { Write-Host "Portal: $($Extra.public_url)/portal" }
        if ($Extra.ContainsKey("pid") -and $Extra.pid) { Write-Host "cloudflared PID: $($Extra.pid)" }
    }
    if ($KeepOpen -and -not $Json) {
        [void](Read-Host "Press Enter to close this Cloudflare setup window")
    }
    exit $Code
}

function Resolve-Cloudflared {
    $candidates = @(
        (Join-Path $InstallDir "cloudflared.exe"),
        (Join-Path $RepoOrBundleRoot "tools\cloudflared.exe"),
        (Join-Path $PSScriptRoot "..\tools\cloudflared.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) { return (Resolve-Path -LiteralPath $candidate).Path }
    }
    $command = Get-Command cloudflared.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $command = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    return $null
}

function Invoke-Cloudflared([string[]]$Arguments) {
    $output = (& $script:Cloudflared @Arguments 2>&1 | Out-String)
    return @{ code = $LASTEXITCODE; text = $output.Trim() }
}

function Get-ExistingTunnelId {
    $listed = Invoke-Cloudflared @("tunnel", "list", "--output", "json")
    if ($listed.code -ne 0) { return "" }
    $raw = $listed.text
    $start = $raw.IndexOf("[")
    $end = $raw.LastIndexOf("]")
    if ($start -lt 0 -or $end -le $start) { return "" }
    try { $items = $raw.Substring($start, $end - $start + 1) | ConvertFrom-Json } catch { return "" }
    foreach ($item in @($items)) {
        if ([string]$item.name -eq $TunnelName) { return [string]$item.id }
    }
    return ""
}

function Wait-Http([string]$Url, [int]$Seconds = 45) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 6
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) { return $true }
        } catch { }
        Start-Sleep -Seconds 1
    }
    return $false
}

try {
    if ($Hostname -notmatch '^[A-Za-z0-9.-]+\.[A-Za-z]{2,}$') {
        Finish $false "Hostname must look like gpu-pool.example.com and must belong to a Cloudflare-managed domain." 2
    }
    if ($TunnelName -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$') {
        Finish $false "Tunnel name contains unsupported characters." 2
    }
    New-Item -ItemType Directory -Force -Path $CloudflareHome | Out-Null
    $script:Cloudflared = Resolve-Cloudflared
    if (-not $script:Cloudflared) {
        $installer = Join-Path $PSScriptRoot "install_cloudflared.ps1"
        if (-not (Test-Path -LiteralPath $installer)) { Finish $false "Cloudflare installer missing: $installer" 3 }
        Write-Host "[GPU Pool] Installing cloudflared into $InstallDir..."
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installer -Quiet -InstallDir $InstallDir
        $script:Cloudflared = Resolve-Cloudflared
    }
    if (-not $script:Cloudflared) { Finish $false "cloudflared could not be installed or found." 3 }

    $certPath = Join-Path $CloudflareHome "cert.pem"
    if (-not (Test-Path -LiteralPath $certPath)) {
        Write-Host "[GPU Pool] Cloudflare login is required. A browser window will open; choose the domain that owns $Hostname."
        $login = Invoke-Cloudflared @("tunnel", "login")
        if ($login.code -ne 0 -or -not (Test-Path -LiteralPath $certPath)) {
            Finish $false "Cloudflare login did not complete. Finish the browser authorization, then run this setup again." 4 @{ next_step = "Run cloudflared tunnel login and choose the Cloudflare-managed domain for $Hostname." }
        }
    }

    $TunnelId = Get-ExistingTunnelId
    if (-not $TunnelId) {
        Write-Host "[GPU Pool] Creating or registering tunnel '$TunnelName'..."
        $created = Invoke-Cloudflared @("tunnel", "create", $TunnelName)
        $uuid = [regex]::Match($created.text, '(?i)[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
        if ($created.code -ne 0 -or -not $uuid.Success) {
            Finish $false "Could not create tunnel '$TunnelName'. It may already exist under another account or the login lacks permission." 5 @{ next_step = "Run cloudflared tunnel list and use a unique tunnel name." }
        }
        $TunnelId = $uuid.Value
    }

    $credentialPath = Join-Path $CloudflareHome ("{0}.json" -f $TunnelId)
    if (-not (Test-Path -LiteralPath $credentialPath)) {
        Finish $false "The named tunnel credential file was not created; no tunnel was launched." 6 @{ next_step = "Confirm the Cloudflare account can create tunnels, then retry." }
    }

    $configDir = Split-Path -Parent $ConfigPath
    New-Item -ItemType Directory -Force -Path $configDir | Out-Null
    $credentialYaml = $credentialPath.Replace('\', '/')
    @(
        "tunnel: $TunnelId",
        "credentials-file: $credentialYaml",
        "",
        "ingress:",
        "  - hostname: $Hostname",
        "    service: http://127.0.0.1:8767",
        "  - service: http_status:404"
    ) | Set-Content -LiteralPath $ConfigPath -Encoding UTF8

    Write-Host "[GPU Pool] Routing DNS for $Hostname..."
    $route = Invoke-Cloudflared @("tunnel", "route", "dns", $TunnelName, $Hostname)
    if ($route.code -ne 0 -and $route.text -notmatch '(?i)already exists|already routed|same record') {
        Finish $false "DNS routing failed for $Hostname. The domain may not be managed by this Cloudflare account." 7 @{ next_step = "Verify the hostname's domain is in the selected Cloudflare account." }
    }

    if (-not $Launch) {
        Finish $true "Named Cloudflare tunnel is configured and ready to launch." 0 @{ tunnel_id = $TunnelId; next_step = "Run setup_cloudflare_named.cmd -Hostname $Hostname -TunnelName $TunnelName -Launch." }
    }

    Write-Host "[GPU Pool] Launching named tunnel '$TunnelName'..."
    $started = Start-Process -FilePath $script:Cloudflared -ArgumentList @("tunnel", "--config", $ConfigPath, "run", $TunnelName) -WorkingDirectory $CloudflareHome -WindowStyle Hidden -PassThru
    $LaunchPid = $started.Id
    Start-Sleep -Seconds 2
    if ($started.HasExited) {
        Finish $false "Named tunnel exited immediately with code $($started.ExitCode). Review the Cloudflare helper log." 8 @{ tunnel_id = $TunnelId; pid = $LaunchPid }
    }
    $publicUrl = "https://$Hostname"
    if (-not (Wait-Http "$publicUrl/portal" 45) -or -not (Wait-Http "$publicUrl/pool-api/status" 20)) {
        Finish $false "Named tunnel is running, but the public portal/API did not verify yet." 9 @{ tunnel_id = $TunnelId; pid = $LaunchPid; public_url = $publicUrl; next_step = "Keep the local portal running and retry the public checks from the app." }
    }
    Finish $true "Named Cloudflare tunnel created, DNS routed, launched, and verified." 0 @{ tunnel_id = $TunnelId; pid = $LaunchPid; public_url = $publicUrl; next_step = "Share the verified portal URL with the pool invite code." }
} catch {
    Finish $false "Cloudflare setup failed: $($_.Exception.Message)" 10
}
