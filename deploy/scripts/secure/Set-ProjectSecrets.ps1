#Requires -Version 5.1
<#
.SYNOPSIS
    Populates the project-root .env from the key names declared in .env.example.

.DESCRIPTION
    Prompts once per key declared in .env.example and writes the values to .env.
    Values are read as SecureString, are never echoed to the console, and never
    appear in the summary output -- only key names do.

    Run this yourself in a terminal. Do NOT ask Claude to run it: Claude Code
    executes shell commands with stdin attached to the null device, so the
    prompt loop would read EOF immediately and write empty values.

.PARAMETER Force
    Re-prompt for every key, including ones that already have a value in .env.
    Without it, keys that are already set are shown and skipped.

.EXAMPLE
    .\scripts\secure\Set-ProjectSecrets.ps1

.EXAMPLE
    .\scripts\secure\Set-ProjectSecrets.ps1 -Force
#>
[CmdletBinding()]
param(
    [string]$ProjectRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)),
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$examplePath = Join-Path $ProjectRoot '.env.example'
$envPath     = Join-Path $ProjectRoot '.env'

if (-not (Test-Path $examplePath)) {
    Write-Error ".env.example not found at $examplePath. This project declares no secrets."
    exit 1
}

function Read-EnvKeys {
    <# Parses .env.example into ordered [pscustomobject]@{ Key; Hint }. #>
    param([string]$Path)

    $entries = New-Object System.Collections.Generic.List[object]
    $pendingComment = @()

    foreach ($line in [System.IO.File]::ReadAllLines($Path)) {
        $trimmed = $line.Trim()

        if ($trimmed -eq '') { $pendingComment = @(); continue }

        if ($trimmed.StartsWith('#')) {
            $pendingComment += $trimmed.TrimStart('#').Trim()
            continue
        }

        if ($trimmed -match '^([A-Za-z_][A-Za-z0-9_]*)\s*=') {
            $entries.Add([pscustomobject]@{
                Key  = $Matches[1]
                Hint = ($pendingComment -join ' ')
            })
        }
        $pendingComment = @()
    }

    return $entries
}

function Read-ExistingValues {
    <# Returns a hashtable of KEY -> raw value. Values are never printed. #>
    param([string]$Path)

    $existing = @{}
    if (-not (Test-Path $Path)) { return $existing }

    foreach ($line in [System.IO.File]::ReadAllLines($Path)) {
        $trimmed = $line.Trim()
        if ($trimmed -eq '' -or $trimmed.StartsWith('#')) { continue }
        if ($trimmed -match '^([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$') {
            $existing[$Matches[1]] = $Matches[2]
        }
    }
    return $existing
}

function ConvertFrom-SecureStringPlain {
    param([System.Security.SecureString]$Secure)

    if ($null -eq $Secure -or $Secure.Length -eq 0) { return '' }

    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try   { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

function Format-EnvValue {
    <# Quote only when the raw value would not survive a bare dotenv parse. #>
    param([string]$Value)

    if ($Value -match '[\s#"'']' ) {
        return '"' + ($Value -replace '"', '\"') + '"'
    }
    return $Value
}

$entries  = Read-EnvKeys -Path $examplePath
$existing = Read-ExistingValues -Path $envPath

if ($entries.Count -eq 0) {
    Write-Host ".env.example declares no keys. Nothing to do."
    exit 0
}

Write-Host ""
Write-Host "Setting project secrets -> $envPath"
Write-Host "Values are hidden as you type and are never echoed back."
Write-Host "Press Enter on a prompt to leave that key unchanged."
Write-Host ""

$resolved = [ordered]@{}
$summary  = New-Object System.Collections.Generic.List[object]

foreach ($entry in $entries) {
    $key       = $entry.Key
    $hasValue  = $existing.ContainsKey($key) -and $existing[$key].Trim() -ne ''

    if ($hasValue -and -not $Force) {
        $resolved[$key] = $existing[$key]
        $summary.Add([pscustomobject]@{ Key = $key; Status = 'kept' })
        Write-Host ("  {0,-32} already set - skipping" -f $key)
        continue
    }

    if ($entry.Hint) { Write-Host ("  {0}" -f $entry.Hint) -ForegroundColor DarkGray }

    $prompt = if ($hasValue) { "  $key (Enter to keep current)" } else { "  $key" }
    $secure = Read-Host -Prompt $prompt -AsSecureString
    $plain  = ConvertFrom-SecureStringPlain -Secure $secure

    if ($plain -eq '') {
        if ($hasValue) {
            $resolved[$key] = $existing[$key]
            $summary.Add([pscustomobject]@{ Key = $key; Status = 'kept' })
        } else {
            $resolved[$key] = ''
            $summary.Add([pscustomobject]@{ Key = $key; Status = 'MISSING' })
        }
    } else {
        $resolved[$key] = Format-EnvValue -Value $plain
        $summary.Add([pscustomobject]@{ Key = $key; Status = 'set' })
    }

    Remove-Variable plain -ErrorAction SilentlyContinue
}

# Carry over any key present in .env but no longer declared in .env.example,
# so hand-added values are not silently dropped.
foreach ($key in $existing.Keys) {
    if (-not $resolved.Contains($key)) {
        $resolved[$key] = $existing[$key]
        $summary.Add([pscustomobject]@{ Key = $key; Status = 'kept (undeclared)' })
    }
}

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add('# Written by scripts/secure/Set-ProjectSecrets.ps1')
$lines.Add('# Gitignored and deny-listed in .claude/settings.local.json. Never commit this file.')
$lines.Add('')
foreach ($key in $resolved.Keys) { $lines.Add("$key=$($resolved[$key])") }

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllLines($envPath, $lines, $utf8NoBom)

Write-Host ""
Write-Host "Wrote $envPath"
$summary | Format-Table -AutoSize | Out-String | Write-Host

$missing = @($summary | Where-Object { $_.Status -eq 'MISSING' })
if ($missing.Count -gt 0) {
    Write-Warning ("{0} key(s) still unset: {1}" -f $missing.Count, (($missing | ForEach-Object { $_.Key }) -join ', '))
    exit 1
}

Write-Host "All declared keys have values. Run scripts/secure/Test-Readiness.ps1 to confirm." -ForegroundColor Green
exit 0
