$ErrorActionPreference = 'Stop'
$paths = @(
    'C:\Users\Drew\Projects\gpu-swarm\scripts\install-prereqs.ps1',
    'C:\Users\Drew\Projects\gpu-swarm\scripts\install_joiner_deps.ps1',
    'C:\Users\Drew\Projects\gpu-swarm\scripts\check_prereqs.ps1',
    'C:\Users\Drew\Projects\gpu-swarm\scripts\install_cloudflared.ps1',
    'C:\Users\Drew\Projects\gpu-swarm\scripts\start_public_tunnel.ps1'
)
$failed = $false
foreach ($p in $paths) {
    $tokens = $null
    $errors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($p, [ref]$tokens, [ref]$errors) | Out-Null
    if ($errors.Count -gt 0) {
        Write-Host ("[{0}] PARSE FAIL" -f $p)
        $errors | ForEach-Object { Write-Host ('  ' + $_.Message + ' (line ' + $_.Extent.StartLineNumber + ')') }
        $failed = $true
    } else {
        Write-Host ("[{0}] parse-ok" -f $p)
    }
}
if ($failed) { exit 1 } else { Write-Host 'ALL-PARSE-OK' }
