#Requires -Version 5.1
<#
.SYNOPSIS
  Download cloudflared.exe into tools/ if missing (no Docker, no installer).
#>
param(
    [switch]$Force,
    [switch]$Quiet
)
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ToolsDir = Join-Path $RepoRoot "tools"
$ExePath = Join-Path $ToolsDir "cloudflared.exe"
$DownloadUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"

function Write-Info([string]$Msg) {
    if (-not $Quiet) { Write-Host $Msg }
}

if ((Test-Path $ExePath) -and -not $Force) {
    Write-Info "[cloudflared] already present: $ExePath"
    try {
        $ver = & $ExePath --version 2>&1 | Select-Object -First 1
        Write-Info "[cloudflared] $ver"
    } catch {
        Write-Info "[cloudflared] binary present (version check skipped)"
    }
    Write-Output $ExePath
    exit 0
}

New-Item -ItemType Directory -Force -Path $ToolsDir | Out-Null
$tmp = Join-Path $env:TEMP ("cloudflared-windows-amd64-" + [guid]::NewGuid().ToString("n") + ".exe")
Write-Info "[cloudflared] downloading $DownloadUrl"
try {
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $tmp -UseBasicParsing
    if (-not (Test-Path $tmp) -or ((Get-Item $tmp).Length -lt 1MB)) {
        throw "Download failed or file too small"
    }
    Move-Item -Force -Path $tmp -Destination $ExePath
} finally {
    if (Test-Path $tmp) { Remove-Item -Force $tmp -ErrorAction SilentlyContinue }
}

Write-Info "[cloudflared] installed: $ExePath"
try {
    $ver = & $ExePath --version 2>&1 | Select-Object -First 1
    Write-Info "[cloudflared] $ver"
} catch { }
Write-Output $ExePath
exit 0
