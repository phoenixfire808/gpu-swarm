#Requires -Version 5.1
<#
.SYNOPSIS
  Download cloudflared.exe for the optional GPU Pool public-access path.

.DESCRIPTION
  Installs only the Cloudflare connector binary. It does not log in, create a
  tunnel, or store credentials. Quick Tunnel mode needs no account; named mode
  is started later from a user-owned config outside the repository.
#>
param(
    [switch]$Force,
    [switch]$Quiet,
    [switch]$Json,
    [string]$InstallDir = ""
)
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not $InstallDir) { $InstallDir = Join-Path $RepoRoot "tools" }
$ToolsDir = [Environment]::ExpandEnvironmentVariables($InstallDir)
$ExePath = Join-Path $ToolsDir "cloudflared.exe"
$DownloadUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"

function Write-Info([string]$Msg) {
    if (-not $Quiet) { Write-Host $Msg }
}

function Finish([bool]$Ok, [string]$Message, [int]$Code = 0) {
    $result = [ordered]@{
        ok = $Ok
        path = $ExePath
        message = $Message
        code = $Code
        install_dir = $ToolsDir
    }
    if ($Json) { $result | ConvertTo-Json -Compress }
    else { Write-Output $ExePath }
    exit $Code
}

try {
    New-Item -ItemType Directory -Force -Path $ToolsDir | Out-Null
    if ((Test-Path $ExePath) -and -not $Force) {
        Write-Info "[cloudflared] already present: $ExePath"
        $ver = ""
        try { $ver = (& $ExePath --version 2>&1 | Select-Object -First 1).ToString().Trim() } catch { }
        Write-Info "[cloudflared] $ver"
        Finish $true "Cloudflare helper already installed" 0
    }

    $tmp = Join-Path $env:TEMP ("cloudflared-windows-amd64-" + [guid]::NewGuid().ToString("n") + ".exe")
    try {
        Write-Info "[cloudflared] downloading $DownloadUrl"
        Invoke-WebRequest -Uri $DownloadUrl -OutFile $tmp -UseBasicParsing -TimeoutSec 180
        if (-not (Test-Path $tmp) -or ((Get-Item $tmp).Length -lt 1MB)) {
            throw "Download failed or file too small"
        }
        Move-Item -Force -Path $tmp -Destination $ExePath
    } finally {
        if (Test-Path $tmp) { Remove-Item -Force $tmp -ErrorAction SilentlyContinue }
    }

    Write-Info "[cloudflared] installed: $ExePath"
    $ver = ""
    try { $ver = (& $ExePath --version 2>&1 | Select-Object -First 1).ToString().Trim() } catch { }
    Write-Info "[cloudflared] $ver"
    Finish $true "Cloudflare helper installed" 0
} catch {
    Write-Info "[cloudflared] ERROR: $_"
    if ($Json) {
        ([ordered]@{ ok = $false; path = $ExePath; message = "$_"; code = 1; install_dir = $ToolsDir } | ConvertTo-Json -Compress)
        exit 1
    }
    exit 1
}
