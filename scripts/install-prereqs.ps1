#Requires -Version 5.1
<#
.SYNOPSIS
  Detect / install friend join prerequisites: Tailscale, VirtualBox, Vagrant.

.DESCRIPTION
  Plain-language, verbose, idempotent. Skips anything already installed.
  - Tailscale = private friend network (optional if public Cloudflare portal is up)
  - VirtualBox = shared Workspace VM (agent-vms / Hermes)
  - Vagrant   = Workspace VM lifecycle (agent-vms)
  Never prints or commits auth keys. Uses TS_AUTHKEY / GPU_SWARM_TAILSCALE_AUTHKEY
  from the environment only when present (unattended join).

.PARAMETER DetectOnly
  Probe and print status; do not download or install.

.PARAMETER SkipTailscale / SkipVirtualBox / SkipVagrant
  Skip that component entirely.

.PARAMETER WorkspaceTools
  Ensure VirtualBox + Vagrant (default ON unless -Skip*).

.PARAMETER ConnectTailscale
  After install/detect, run `tailscale up` (auth key or interactive login).

.PARAMETER Json
  Emit a final JSON object (progress lines may appear before it).
#>
param(
    [switch]$DetectOnly,
    [switch]$SkipTailscale,
    [switch]$SkipVirtualBox,
    [switch]$SkipVagrant,
    [switch]$SkipExtensionPack,
    [switch]$WorkspaceTools = $true,
    [switch]$ConnectTailscale,
    [switch]$Json,
    [switch]$Quiet,
    [string]$TailscaleAuthKey = ""
)
$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$CacheDir = Join-Path $env:LOCALAPPDATA "GPUPool\prereq-cache"
$script:StepTotal = 4
$script:StepNum = 0
$script:Actions = New-Object System.Collections.Generic.List[string]
$script:Warnings = New-Object System.Collections.Generic.List[string]

function Write-Step {
    param([string]$Label, [string]$Why = "", [int]$Percent = -1)
    $script:StepNum++
    $pct = if ($Percent -ge 0) { $Percent } else {
        [int](($script:StepNum / [math]::Max($script:StepTotal, 1)) * 100)
    }
    $banner = "[{0}/{1}] {2}" -f $script:StepNum, $script:StepTotal, $Label
    if (-not $Quiet) {
        Write-Host ""
        Write-Host "==== GPU Pool setup ====" -ForegroundColor Cyan
        Write-Host $banner -ForegroundColor Green
        if ($Why) { Write-Host ("     Why: {0}" -f $Why) -ForegroundColor DarkGray }
        Write-Progress -Activity "GPU Pool prerequisites" -Status $banner -PercentComplete ([math]::Min(99, $pct))
    }
}

function Write-Info([string]$Msg) {
    if (-not $Quiet) { Write-Host ("  {0}" -f $Msg) }
}

function Write-WarnMsg([string]$Msg) {
    [void]$script:Warnings.Add($Msg)
    if (-not $Quiet) { Write-Host ("  WARN: {0}" -f $Msg) -ForegroundColor Yellow }
}

function Find-Winget {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\winget.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Microsoft\WindowsApps\winget.exe"),
        "C:\Program Files\WindowsApps\Microsoft.DesktopAppInstaller_*\winget.exe"
    )
    $cmd = Get-Command winget -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) { return $cmd.Source }
    foreach ($c in $candidates) {
        if ($c -match '\*') {
            $hit = Get-Item $c -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($hit) { return $hit.FullName }
        } elseif (Test-Path $c) {
            return $c
        }
    }
    return $null
}

function Test-IsAdmin {
    try {
        $id = [Security.Principal.WindowsIdentity]::GetCurrent()
        $p = New-Object Security.Principal.WindowsPrincipal($id)
        return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    } catch { return $false }
}

function Invoke-ElevatedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string]$ArgumentList = "",
        [string]$PlainWhy = "Windows needs permission to install this app."
    )
    Write-Info $PlainWhy
    Write-Info "A User Account Control (UAC) prompt may appear  -  click Yes to continue."
    try {
        $p = Start-Process -FilePath $FilePath -ArgumentList $ArgumentList -Verb RunAs -Wait -PassThru
        return @{ ok = ($p.ExitCode -eq 0 -or $null -eq $p.ExitCode); code = $p.ExitCode }
    } catch {
        Write-WarnMsg "Elevation cancelled or failed: $_"
        return @{ ok = $false; code = -1; error = "$_" }
    }
}

function Get-VirtualBoxInfo {
    $paths = @(
        (Join-Path $env:ProgramFiles "Oracle\VirtualBox\VBoxManage.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Oracle\VirtualBox\VBoxManage.exe")
    )
    $exe = $null
    foreach ($p in $paths) { if (Test-Path $p) { $exe = $p; break } }
    $cmd = Get-Command VBoxManage -ErrorAction SilentlyContinue
    if (-not $exe -and $cmd) { $exe = $cmd.Source }
    if (-not $exe) {
        return @{ ok = $false; installed = $false; path = ""; version = ""; extpack = $false; message = "VirtualBox not installed" }
    }
    $ver = ""
    try { $ver = (& $exe --version 2>$null | Select-Object -First 1).ToString().Trim() } catch {}
    $ext = $false
    try {
        $packs = & $exe list extpacks 2>$null | Out-String
        if ($packs -match "Oracle VM VirtualBox Extension Pack" -or $packs -match "Usable:\s*true") {
            $ext = $true
        }
    } catch {}
    return @{
        ok = $true
        installed = $true
        path = $exe
        version = $ver
        extpack = $ext
        message = "VirtualBox OK ($ver)"
    }
}

function Get-VagrantInfo {
    $paths = @(
        (Join-Path $env:ProgramFiles "Vagrant\bin\vagrant.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Vagrant\bin\vagrant.exe")
    )
    $exe = $null
    foreach ($p in $paths) { if (Test-Path $p) { $exe = $p; break } }
    $cmd = Get-Command vagrant -ErrorAction SilentlyContinue
    if (-not $exe -and $cmd) { $exe = $cmd.Source }
    if (-not $exe) {
        return @{ ok = $false; installed = $false; path = ""; version = ""; message = "Vagrant not installed" }
    }
    $ver = ""
    try { $ver = (& $exe --version 2>$null | Select-Object -First 1).ToString().Trim() } catch {}
    return @{ ok = $true; installed = $true; path = $exe; version = $ver; message = "Vagrant OK ($ver)" }
}

function Get-TailscaleInfo {
    $paths = @(
        (Join-Path $env:ProgramFiles "Tailscale\tailscale.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Tailscale\tailscale.exe")
    )
    $exe = $null
    foreach ($p in $paths) { if (Test-Path $p) { $exe = $p; break } }
    $cmd = Get-Command tailscale -ErrorAction SilentlyContinue
    if (-not $exe -and $cmd) { $exe = $cmd.Source }
    if (-not $exe) {
        return @{
            ok = $false; installed = $false; path = ""; version = ""
            logged_in = $false; ipv4 = ""; message = "Tailscale not installed"
        }
    }
    $ver = ""
    try { $ver = (& $exe version 2>$null | Select-Object -First 1).ToString().Trim() } catch {}
    $ipv4 = ""
    $loggedIn = $false
    try {
        $status = & $exe status --json 2>$null | Out-String
        if ($status) {
            $obj = $status | ConvertFrom-Json
            if ($obj.Self -and $obj.Self.DNSName) { $loggedIn = $true }
            if ($obj.Self -and $obj.Self.TailscaleIPs) {
                foreach ($ip in @($obj.Self.TailscaleIPs)) {
                    if ($ip -match '^100\.') { $ipv4 = $ip; break }
                }
            }
        }
    } catch {}
    if (-not $ipv4) {
        try {
            $ipOut = & $exe ip -4 2>$null | Select-Object -First 1
            if ($ipOut -match '100\.\d+\.\d+\.\d+') { $ipv4 = $Matches[0]; $loggedIn = $true }
        } catch {}
    }
    $msg = if ($loggedIn) { "Tailscale OK  -  on network ($ipv4)" } else { "Tailscale installed  -  not logged in yet" }
    return @{
        ok = $true
        installed = $true
        path = $exe
        version = $ver
        logged_in = $loggedIn
        ipv4 = $ipv4
        message = $msg
    }
}

function Install-ViaWinget {
    param([string]$Id, [string]$Label)
    $winget = Find-Winget
    if (-not $winget) { return @{ ok = $false; method = "winget"; message = "winget not available" } }
    Write-Info "Using Windows Package Manager (winget) for $Label..."
    Write-Info "Package: $Id  -  this may take a few minutes; progress prints below."
    $args = @(
        "install", "--id", $Id, "-e", "--accept-package-agreements", "--accept-source-agreements", "--disable-interactivity"
    )
    try {
        $out = & $winget @args 2>&1 | ForEach-Object { "$_" }
        foreach ($line in $out) { Write-Info $line }
        $code = $LASTEXITCODE
        # 0 = ok, -1978335189 / 0x8A15002B often means already installed
        if ($code -eq 0 -or $code -eq -1978335189) {
            return @{ ok = $true; method = "winget"; message = "$Label installed/present via winget"; code = $code }
        }
        return @{ ok = $false; method = "winget"; message = "$Label winget exit $code"; code = $code; output = ($out -join "`n") }
    } catch {
        return @{ ok = $false; method = "winget"; message = "$_" }
    }
}

function Get-LatestVirtualBoxUrls {
    # Prefer known stable 7.1/7.2 Windows installer from Oracle CDN listing page scrape-lite.
    # Fallback: open download page for the friend.
    $versionPage = "https://download.virtualbox.org/virtualbox/LATEST-STABLE.TXT"
    try {
        $ver = (Invoke-WebRequest -Uri $versionPage -UseBasicParsing -TimeoutSec 20).Content.Trim()
        if ($ver -match '^\d+\.\d+\.\d+') {
            $base = "https://download.virtualbox.org/virtualbox/$ver"
            $exeName = "VirtualBox-$ver-Win.exe"
            # Build number is in the filename on the directory listing  -  probe common pattern via index
            $idx = (Invoke-WebRequest -Uri "$base/" -UseBasicParsing -TimeoutSec 30).Content
            if ($idx -match "VirtualBox-$([regex]::Escape($ver))-(\d+)-Win\.exe") {
                $build = $Matches[1]
                $exeName = "VirtualBox-$ver-$build-Win.exe"
            }
            $extName = $null
            if ($idx -match "Oracle_VirtualBox_Extension_Pack-$([regex]::Escape($ver))\S*\.vbox-extpack") {
                $extName = $Matches[0]
            } else {
                $extName = "Oracle_VirtualBox_Extension_Pack-$ver.vbox-extpack"
            }
            return @{
                ok = $true
                version = $ver
                installer_url = "$base/$exeName"
                extpack_url = "$base/$extName"
            }
        }
    } catch {
        Write-WarnMsg "Could not resolve VirtualBox latest URL: $_"
    }
    return @{
        ok = $false
        download_page = "https://www.virtualbox.org/wiki/Downloads"
        message = "Open the VirtualBox download page and run the Windows installer"
    }
}

function Install-VirtualBox {
    Write-Step "VirtualBox (shared Workspace VM)" "Lets friends open a Linux desktop workspace capped to Contribute share settings."
    $info = Get-VirtualBoxInfo
    if ($info.installed) {
        Write-Info "Already installed  -  skipping download. $($info.message)"
        [void]$script:Actions.Add("virtualbox:skip-present")
        return $info
    }
    if ($DetectOnly) {
        Write-Info "Detect-only: VirtualBox missing."
        return $info
    }
    $wg = Install-ViaWinget -Id "Oracle.VirtualBox" -Label "VirtualBox"
    if ($wg.ok) {
        [void]$script:Actions.Add("virtualbox:winget")
        Start-Sleep -Seconds 2
        return Get-VirtualBoxInfo
    }
    Write-Info "winget path unavailable or failed  -  trying official Oracle installer..."
    New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null
    $urls = Get-LatestVirtualBoxUrls
    if (-not $urls.ok) {
        Write-WarnMsg $urls.message
        Write-Info "Opening VirtualBox downloads in your browser..."
        Start-Process $urls.download_page
        [void]$script:Actions.Add("virtualbox:opened-download-page")
        return Get-VirtualBoxInfo
    }
    $dest = Join-Path $CacheDir ("VirtualBox-" + $urls.version + "-Win.exe")
    if (-not (Test-Path $dest)) {
        Write-Info "Downloading VirtualBox $($urls.version)..."
        Write-Info $urls.installer_url
        try {
            Import-Module BitsTransfer -ErrorAction SilentlyContinue
            if (Get-Command Start-BitsTransfer -ErrorAction SilentlyContinue) {
                Start-BitsTransfer -Source $urls.installer_url -Destination $dest -DisplayName "VirtualBox download"
            } else {
                Invoke-WebRequest -Uri $urls.installer_url -OutFile $dest -UseBasicParsing
            }
        } catch {
            Write-WarnMsg "Download failed: $_"
            Start-Process "https://www.virtualbox.org/wiki/Downloads"
            [void]$script:Actions.Add("virtualbox:download-failed-opened-page")
            return Get-VirtualBoxInfo
        }
    } else {
        Write-Info "Using cached installer: $dest"
    }
    Write-Info "Launching VirtualBox installer (silent when possible)..."
    # Oracle Windows installer: --silent --ignore-reboot; needs admin
    $elev = Invoke-ElevatedProcess -FilePath $dest -ArgumentList "--silent --ignore-reboot" `
        -PlainWhy "Installing VirtualBox so Workspace VMs can run. Admin approval is required once."
    [void]$script:Actions.Add("virtualbox:installer-exit:$($elev.code)")
    Start-Sleep -Seconds 3
    $after = Get-VirtualBoxInfo
    if (-not $after.installed) {
        Write-WarnMsg "Silent install may need a reboot, or UAC was declined. Opening installer UI..."
        Start-Process $dest
        [void]$script:Actions.Add("virtualbox:opened-ui-installer")
    }
    if (-not $SkipExtensionPack -and $after.installed -and -not $after.extpack -and $urls.extpack_url) {
        $extDest = Join-Path $CacheDir ("ExtensionPack-" + $urls.version + ".vbox-extpack")
        try {
            if (-not (Test-Path $extDest)) {
                Write-Info "Downloading VirtualBox Extension Pack (USB/RDP helpers)..."
                Invoke-WebRequest -Uri $urls.extpack_url -OutFile $extDest -UseBasicParsing
            }
            Write-Info "Installing Extension Pack (may prompt for license / UAC)..."
            $vb = $after.path
            $extArgs = "extpack install --replace `"$extDest`""
            Invoke-ElevatedProcess -FilePath $vb -ArgumentList $extArgs `
                -PlainWhy "Extension Pack improves RDP/USB support for Workspace VMs."
            [void]$script:Actions.Add("virtualbox:extpack")
        } catch {
            Write-WarnMsg "Extension Pack skipped: $_ (Workspace still works for basic RDP)"
        }
    }
    return Get-VirtualBoxInfo
}

function Get-LatestVagrantMsiUrl {
    try {
        $api = "https://api.github.com/repos/hashicorp/vagrant/releases/latest"
        $rel = Invoke-RestMethod -Uri $api -Headers @{ "User-Agent" = "GPUPool-prereqs" } -TimeoutSec 30
        foreach ($a in $rel.assets) {
            if ($a.name -match 'vagrant_.*_windows_amd64\.msi$') {
                return @{ ok = $true; url = $a.browser_download_url; version = $rel.tag_name; name = $a.name }
            }
        }
    } catch {
        Write-WarnMsg "Could not resolve Vagrant release: $_"
    }
    return @{ ok = $false; download_page = "https://developer.hashicorp.com/vagrant/install" }
}

function Install-VagrantTool {
    Write-Step "Vagrant (Workspace VM helper)" "Used with VirtualBox so Hermes/agent-vms can create and start the shared Ubuntu workspace."
    $info = Get-VagrantInfo
    if ($info.installed) {
        Write-Info "Already installed  -  skipping. $($info.message)"
        [void]$script:Actions.Add("vagrant:skip-present")
        return $info
    }
    if ($DetectOnly) {
        Write-Info "Detect-only: Vagrant missing."
        return $info
    }
    $wg = Install-ViaWinget -Id "Hashicorp.Vagrant" -Label "Vagrant"
    if ($wg.ok) {
        [void]$script:Actions.Add("vagrant:winget")
        Start-Sleep -Seconds 2
        return Get-VagrantInfo
    }
    New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null
    $msi = Get-LatestVagrantMsiUrl
    if (-not $msi.ok) {
        Write-WarnMsg "Open Vagrant install page and run the Windows MSI."
        Start-Process $msi.download_page
        [void]$script:Actions.Add("vagrant:opened-download-page")
        return Get-VagrantInfo
    }
    $dest = Join-Path $CacheDir $msi.name
    if (-not (Test-Path $dest)) {
        Write-Info "Downloading Vagrant $($msi.version)..."
        Write-Info $msi.url
        try {
            Invoke-WebRequest -Uri $msi.url -OutFile $dest -UseBasicParsing
        } catch {
            Write-WarnMsg "Download failed: $_"
            Start-Process "https://developer.hashicorp.com/vagrant/install"
            return Get-VagrantInfo
        }
    }
    Write-Info "Installing Vagrant (msiexec quiet)  -  UAC may appear..."
    $elev = Invoke-ElevatedProcess -FilePath "msiexec.exe" -ArgumentList "/i `"$dest`" /qn /norestart" `
        -PlainWhy "Installing Vagrant so Workspace VMs can be created without manual setup."
    [void]$script:Actions.Add("vagrant:msi-exit:$($elev.code)")
    Start-Sleep -Seconds 2
    $after = Get-VagrantInfo
    if (-not $after.installed) {
        Write-WarnMsg "Quiet install incomplete  -  opening MSI for manual Next/Next."
        Start-Process $dest
        [void]$script:Actions.Add("vagrant:opened-msi-ui")
    }
    return Get-VagrantInfo
}

function Install-TailscaleTool {
    Write-Step "Tailscale (private friend network)" "Puts you on the private pool network so portal/scheduler URLs work without the public tunnel."
    $info = Get-TailscaleInfo
    if ($info.installed) {
        Write-Info "Already installed  -  skipping download. $($info.message)"
        [void]$script:Actions.Add("tailscale:skip-present")
    } elseif ($DetectOnly) {
        Write-Info "Detect-only: Tailscale missing."
    } else {
        $wg = Install-ViaWinget -Id "Tailscale.Tailscale" -Label "Tailscale"
        if ($wg.ok) {
            [void]$script:Actions.Add("tailscale:winget")
            Start-Sleep -Seconds 3
        } else {
            New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null
            $msiUrl = "https://pkgs.tailscale.com/stable/tailscale-setup-latest-amd64.msi"
            $dest = Join-Path $CacheDir "tailscale-setup-latest-amd64.msi"
            Write-Info "Downloading Tailscale installer..."
            try {
                Invoke-WebRequest -Uri $msiUrl -OutFile $dest -UseBasicParsing
                Write-Info "Installing Tailscale  -  UAC may appear..."
                $elev = Invoke-ElevatedProcess -FilePath "msiexec.exe" -ArgumentList "/i `"$dest`" /qn /norestart" `
                    -PlainWhy "Installing Tailscale so you can join the private Glitch Factor network."
                [void]$script:Actions.Add("tailscale:msi-exit:$($elev.code)")
                Start-Sleep -Seconds 3
            } catch {
                Write-WarnMsg "Tailscale download/install failed: $_  -  opening download page."
                Start-Process "https://tailscale.com/download/windows"
                [void]$script:Actions.Add("tailscale:opened-download-page")
            }
        }
        $info = Get-TailscaleInfo
        if (-not $info.installed) {
            Write-WarnMsg "Tailscale still missing. Install from https://tailscale.com/download then re-run."
        }
    }

    # Connect / login
    $key = $TailscaleAuthKey
    if (-not $key) { $key = $env:GPU_SWARM_TAILSCALE_AUTHKEY }
    if (-not $key) { $key = $env:TS_AUTHKEY }
    $wantConnect = $ConnectTailscale -or ($key -and $key.Trim().Length -gt 0)
    if ($info.installed -and -not $info.logged_in -and ($wantConnect -or -not $DetectOnly)) {
        Write-Info "Next: sign in to Tailscale (browser or auth key)."
        Write-Info "Ask the host which tailnet / account to use (Glitch Factor). Never paste auth keys into chat logs."
        if ($DetectOnly -and -not $wantConnect) {
            return Get-TailscaleInfo
        }
        $ts = (Get-TailscaleInfo).path
        if ($key -and $key.Trim().Length -gt 0) {
            Write-Info "Connecting with auth key from environment (key not printed)..."
            try {
                & $ts up --auth-key=$key --unattended 2>&1 | ForEach-Object { Write-Info "$_" }
                [void]$script:Actions.Add("tailscale:authkey-up")
            } catch {
                Write-WarnMsg "Auth-key join failed: $_  -  falling back to interactive login."
                Start-Process $ts -ArgumentList "up" -WindowStyle Hidden
                [void]$script:Actions.Add("tailscale:interactive-up-fallback")
            }
        } else {
            Write-Info "Opening Tailscale login  -  approve in the browser, then return here."
            try {
                Start-Process $ts -ArgumentList "up" -WindowStyle Hidden
                [void]$script:Actions.Add("tailscale:interactive-up")
            } catch {
                Write-WarnMsg "Could not launch tailscale up: $_  -  open the Tailscale app from the Start menu and Log in."
                Start-Process "https://login.tailscale.com/start"
                [void]$script:Actions.Add("tailscale:opened-login-page")
            }
        }
        Start-Sleep -Seconds 2
        $info = Get-TailscaleInfo
    }
    return $info
}

# --- main ---
Write-Info "GPU Pool  -  automated prerequisites"
Write-Info "Already-installed tools are detected and skipped (no re-download)."
Write-Info "Public Cloudflare portal remains an alternative if you skip Tailscale."
if (-not (Test-IsAdmin)) {
    Write-Info "Running as normal user  -  installs that need admin will show a UAC prompt."
}

$doWorkspace = [bool]$WorkspaceTools -and -not ($SkipVirtualBox -and $SkipVagrant)
$result = [ordered]@{
    ok = $true
    detect_only = [bool]$DetectOnly
    virtualbox = $null
    vagrant = $null
    tailscale = $null
    actions = @()
    warnings = @()
    next_steps = @()
    checked_at = (Get-Date).ToString("o")
    script = "scripts/install-prereqs.ps1"
}

if (-not $SkipTailscale) {
    $result.tailscale = Install-TailscaleTool
} else {
    $result.tailscale = @{ ok = $true; skipped = $true; message = "skipped" }
}

if ($doWorkspace -and -not $SkipVirtualBox) {
    $result.virtualbox = Install-VirtualBox
} else {
    $result.virtualbox = @{ ok = $true; skipped = $true; message = "skipped (not required for Contribute/Utilize)" }
}

if ($doWorkspace -and -not $SkipVagrant) {
    $result.vagrant = Install-VagrantTool
} else {
    $result.vagrant = @{ ok = $true; skipped = $true; message = "skipped (not required for Contribute/Utilize)" }
}

Write-Step "Summary  -  what to click next" "Join the pool; Workspace is optional." 100

$shareReady = $true
$ts = $result.tailscale
if ($ts -and -not $ts.skipped -and -not $ts.installed) {
    # Tailscale optional when public portal exists  -  warn only
    Write-WarnMsg "Tailscale missing  -  use the host's public portal URL, or install Tailscale and login."
}
if ($ts -and $ts.installed -and -not $ts.logged_in -and -not $ts.skipped) {
    Write-WarnMsg "Tailscale installed but not logged in yet  -  finish login, then open the portal."
}

$wsReady = $true
if ($doWorkspace) {
    if ($result.virtualbox -and -not $result.virtualbox.skipped -and -not $result.virtualbox.installed) { $wsReady = $false }
    if ($result.vagrant -and -not $result.vagrant.skipped -and -not $result.vagrant.installed) { $wsReady = $false }
}

$result.actions = @($script:Actions)
$result.warnings = @($script:Warnings)
$result.workspace_tools_ready = $wsReady
$result.share_path_ready = $shareReady
$result.next_steps = @(
    "Open GPU Pool app (or start-gpu-pool-app.cmd) -> finish wizard",
    "Sign in with invite code glitch-factor + your Discord display name",
    "Home -> Contribute (share GPU/CPU) or Utilize (use the pool)",
    "Optional: Connect -> Start local model endpoint  OR  Home -> Workspace (needs VirtualBox+Vagrant)",
    "Public path (no Tailscale): ask the host for current trycloudflare.com/portal link"
)

Write-Info ""
Write-Info "Share path (Contribute / Utilize): ready to continue in the app."
if ($wsReady) {
    Write-Info "Workspace tools: VirtualBox + Vagrant look good."
} elseif ($doWorkspace) {
    Write-Info "Workspace tools: finish any open installers, then re-run Detect."
}
Write-Info "Next: invite glitch-factor -> Contribute or Utilize."

$result.ok = $true
if (-not $Quiet) { Write-Progress -Activity "GPU Pool prerequisites" -Completed }

if ($Json -or -not $Quiet) {
    # Always emit JSON last for app_backend parser
    $result | ConvertTo-Json -Depth 6
}
exit 0
