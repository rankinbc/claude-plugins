#Requires -Version 5.1
<#
.SYNOPSIS
    Reports which declared secrets are set, by key name only.

.DESCRIPTION
    Compares the keys declared in .env.example against the keys present in .env
    and prints one line per key: set, empty, or missing.

    Secret VALUES are never read into output, never returned, and never logged.
    This script is safe for Claude to run -- it is how Claude learns whether the
    project is configured without being able to see any value.

    Exit code 0 when every declared key has a value; 1 otherwise.

.PARAMETER Quiet
    Suppress the table and return only the exit code.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/secure/Test-Readiness.ps1

    Windows PowerShell 5.1 (ships with Windows). -ExecutionPolicy Bypass is needed
    because the default Windows client policy refuses to run .ps1 files.

.EXAMPLE
    pwsh -File scripts/secure/Test-Readiness.ps1

    PowerShell 7 (Windows, macOS, Linux).
#>
[CmdletBinding()]
param(
    [string]$ProjectRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)),
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'

$examplePath = Join-Path $ProjectRoot '.env.example'
$envPath     = Join-Path $ProjectRoot '.env'

if (-not (Test-Path $examplePath)) {
    if (-not $Quiet) { Write-Host "No .env.example - this project declares no secrets. Nothing to configure." }
    exit 0
}

function Get-DeclaredKeys {
    param([string]$Path)

    $keys = New-Object System.Collections.Generic.List[string]
    foreach ($line in [System.IO.File]::ReadAllLines($Path)) {
        $trimmed = $line.Trim()
        if ($trimmed -eq '' -or $trimmed.StartsWith('#')) { continue }
        if ($trimmed -match '^([A-Za-z_][A-Za-z0-9_]*)\s*=') { $keys.Add($Matches[1]) }
    }
    return $keys
}

function Get-PresentKeys {
    <# Returns KEY -> $true when the value is non-empty. Values are discarded immediately. #>
    param([string]$Path)

    $present = @{}
    if (-not (Test-Path $Path)) { return $present }

    foreach ($line in [System.IO.File]::ReadAllLines($Path)) {
        $trimmed = $line.Trim()
        if ($trimmed -eq '' -or $trimmed.StartsWith('#')) { continue }
        if ($trimmed -match '^([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$') {
            $present[$Matches[1]] = ($Matches[2].Trim().Trim('"').Trim("'") -ne '')
        }
    }
    return $present
}

$declared = Get-DeclaredKeys -Path $examplePath
$present  = Get-PresentKeys  -Path $envPath

$rows = foreach ($key in $declared) {
    $status = if (-not $present.ContainsKey($key)) { 'missing' }
              elseif (-not $present[$key])        { 'empty'   }
              else                                { 'set'     }
    [pscustomobject]@{ Key = $key; Status = $status }
}

$unset = @($rows | Where-Object { $_.Status -ne 'set' })

if (-not $Quiet) {
    if (-not (Test-Path $envPath)) {
        Write-Host "No .env yet. Run scripts/secure/Set-ProjectSecrets.ps1 in your own terminal."
        Write-Host ""
    }
    $rows | Format-Table -AutoSize | Out-String | Write-Host
    Write-Host ("{0}/{1} declared keys set." -f ($rows.Count - $unset.Count), $rows.Count)
    if ($unset.Count -gt 0) {
        Write-Host "Run scripts/secure/Set-ProjectSecrets.ps1 to fill the rest." -ForegroundColor Yellow
    }
}

if ($unset.Count -gt 0) { exit 1 }
exit 0
