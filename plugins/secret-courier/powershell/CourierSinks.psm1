# CourierSinks.psm1 - plaintext copies a consumer needs (a .env, an appsettings.local.json, dotnet user-secrets)
# are "sinks": written only here, owner-ACL'd, gitignore-verified, and recorded in the ledger
# (<home>\sinks.json: path, format, keys, repo, written_at - never values) so `courier sweep` can find and
# remove every one of them later. Nothing here prints a value; file writes go through [IO.File], never a
# cmdlet with the value as a parameter.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# No -Force here: a forced nested import would move Courier into this module's scope and out of the caller's
# (the ops scripts import Courier first, then this module).
if (-not (Get-Module Courier)) { Import-Module (Join-Path $PSScriptRoot 'Courier.psm1') }

$script:SinksPath = Join-Path (Get-CourierHome) 'sinks.json'
$script:Formats = @('dotenv', 'json', 'user-secrets')

function Read-Sinks {
    if (-not (Test-Path $script:SinksPath)) { return @() }
    $raw = [IO.File]::ReadAllText($script:SinksPath)
    if ([string]::IsNullOrWhiteSpace($raw)) { return @() }
    $obj = $raw | ConvertFrom-Json -AsHashtable
    if ($null -eq $obj -or -not $obj.ContainsKey('sinks')) { return @() }
    return @($obj['sinks'])
}

function Write-Sinks([object[]]$Sinks) {
    Initialize-CourierHome
    $tmp = "$($script:SinksPath).tmp"
    [IO.File]::WriteAllText($tmp, (@{ sinks = @($Sinks) } | ConvertTo-Json -Depth 6))
    Set-CourierOwnerOnlyAcl -Path $tmp
    Move-Item -Path $tmp -Destination $script:SinksPath -Force
    Set-CourierOwnerOnlyAcl -Path $script:SinksPath
}

function Get-CourierSinks {
    <# .SYNOPSIS The ledger: every plaintext copy this plugin wrote and has not swept. Paths and key names only. #>
    [CmdletBinding()]
    param([string]$Repo = '')
    $all = Read-Sinks
    if ($Repo) { $all = @($all | Where-Object { $_['repo'] -and ($_['repo'] -like "*$Repo*") }) }
    foreach ($s in $all) { [pscustomobject]$s }
}

function Add-CourierSink {
    param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)][string]$Format, [Parameter(Mandatory)][string[]]$Keys,
          [string]$Repo = '', [string]$Origin = 'inject')
    $sinks = @(Read-Sinks | Where-Object { $_['path'] -ne $Path })
    $existing = Read-Sinks | Where-Object { $_['path'] -eq $Path } | Select-Object -First 1
    $allKeys = @($Keys)
    if ($existing) { $allKeys = @(@($existing['keys']) + $Keys | Sort-Object -Unique) }
    $entry = @{ id = ([Guid]::NewGuid().ToString('N').Substring(0, 12)); path = $Path; format = $Format; keys = $allKeys
                repo = $Repo; origin = $Origin; written_at = (Get-Date).ToUniversalTime().ToString('o') }
    if ($existing) { $entry.id = $existing['id'] }
    Write-Sinks ($sinks + @($entry))
    return $entry.id
}

function Remove-CourierSinkEntry([string]$Id) {
    Write-Sinks (@(Read-Sinks | Where-Object { $_['id'] -ne $Id }))
}

function Get-CourierRepoRoot([string]$Path) {
    <# .SYNOPSIS The git work tree holding -Path, or $null. #>
    $dir = if (Test-Path -LiteralPath $Path -PathType Container) { $Path } else { Split-Path -Parent $Path }
    if (-not $dir -or -not (Test-Path -LiteralPath $dir)) { return $null }
    $out = & git -C $dir rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $out) { return $null }
    return ([string]$out).Trim()
}

function Test-CourierTargetIgnored([string]$Path) {
    <# .SYNOPSIS True when git would ignore -Path (so it can never be committed). A path outside any repo is false. #>
    $root = Get-CourierRepoRoot $Path
    if (-not $root) { return $false }
    & git -C $root check-ignore -q -- $Path 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Resolve-CourierUserSecretsPath([string]$Target) {
    <# .SYNOPSIS %APPDATA%\Microsoft\UserSecrets\<id>\secrets.json for a UserSecretsId or a .csproj carrying one. #>
    $id = $Target
    if ($Target -like '*.csproj') {
        $xml = [xml][IO.File]::ReadAllText($Target)
        $id = ($xml.Project.PropertyGroup | ForEach-Object { $_.UserSecretsId } | Where-Object { $_ } | Select-Object -First 1)
        if (-not $id) { throw "no <UserSecretsId> in $Target (run dotnet user-secrets init)" }
    }
    return (Join-Path $env:APPDATA "Microsoft\UserSecrets\$id\secrets.json")
}

function Set-JsonPath([hashtable]$Doc, [string]$Key, [string]$Value) {
    $parts = $Key -split ':'
    $cur = $Doc
    for ($i = 0; $i -lt $parts.Length - 1; $i++) {
        if (-not $cur.ContainsKey($parts[$i]) -or -not ($cur[$parts[$i]] -is [hashtable])) { $cur[$parts[$i]] = @{} }
        $cur = $cur[$parts[$i]]
    }
    $cur[$parts[-1]] = $Value
}

function Remove-JsonPath([hashtable]$Doc, [string]$Key) {
    <# Removes the leaf and every parent object the removal leaves empty. #>
    $parts = $Key -split ':'
    $chain = @($Doc)
    $cur = $Doc
    for ($i = 0; $i -lt $parts.Length - 1; $i++) {
        if (-not $cur.ContainsKey($parts[$i]) -or -not ($cur[$parts[$i]] -is [hashtable])) { return }
        $cur = $cur[$parts[$i]]
        $chain += $cur
    }
    if ($cur.ContainsKey($parts[-1])) { $cur.Remove($parts[-1]) }
    for ($i = $chain.Length - 1; $i -gt 0; $i--) {
        if ($chain[$i].Count -eq 0) { $chain[$i - 1].Remove($parts[$i - 1]) } else { break }
    }
}

function Write-CourierSink {
    <# .SYNOPSIS Merge -Entries (key -> SecureString) into the target file in -Format, owner-ACL it, record it.
       Refuses a target that git would not ignore (dotenv/json) so the copy can never be committed. #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Target, [Parameter(Mandatory)][string]$Format,
          [Parameter(Mandatory)][hashtable]$Entries, [switch]$Replace)
    if ($Format -notin $script:Formats) { throw "format must be one of: $($script:Formats -join ', ')" }
    $path = if ($Format -eq 'user-secrets') { Resolve-CourierUserSecretsPath $Target } else { [IO.Path]::GetFullPath($Target) }
    $repo = ''
    if ($Format -ne 'user-secrets') {
        $repo = Get-CourierRepoRoot $path
        if (-not $repo) { throw "not-a-repo: $path is outside any git work tree; a plaintext copy must live where git ignores it" }
        if (-not (Test-CourierTargetIgnored $path)) { throw "not-ignored: git does not ignore $path; add it to .gitignore first" }
    }
    $dir = Split-Path -Parent $path
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $existingText = if (Test-Path -LiteralPath $path) { [IO.File]::ReadAllText($path) } else { '' }
    $keys = @($Entries.Keys)
    if ($Format -eq 'dotenv') {
        $lines = if ($existingText) { @($existingText -split "`r?`n") } else { @() }
        foreach ($k in $keys) {
            $present = $lines | Where-Object { $_ -match "^\s*$([regex]::Escape($k))\s*=" }
            if ($present -and -not $Replace) { throw "$k already set in $path; pass -Replace" }
            $v = ConvertFrom-CourierSecureString -Secure $Entries[$k]
            $line = "$k=$v"
            $replaced = $false
            $lines = @($lines | ForEach-Object { if ($_ -match "^\s*$([regex]::Escape($k))\s*=") { $replaced = $true; $line } else { $_ } })
            if (-not $replaced) { $lines += $line }
            $v = $null; $line = $null
        }
        $text = (($lines | Where-Object { $null -ne $_ }) -join "`n").TrimEnd("`n") + "`n"
    } else {
        $doc = if ($existingText.Trim()) { $existingText | ConvertFrom-Json -AsHashtable } else { @{} }
        if ($null -eq $doc) { $doc = @{} }
        foreach ($k in $keys) {
            $cur = $doc
            $parts = $k -split ':'
            $has = $true
            foreach ($p in $parts) { if ($cur -is [hashtable] -and $cur.ContainsKey($p)) { $cur = $cur[$p] } else { $has = $false; break } }
            if ($has -and -not $Replace) { throw "$k already set in $path; pass -Replace" }
            Set-JsonPath $doc $k (ConvertFrom-CourierSecureString -Secure $Entries[$k])
        }
        $text = ($doc | ConvertTo-Json -Depth 20) + "`n"
    }
    if (-not (Test-Path -LiteralPath $path)) { [IO.File]::WriteAllText($path, ''); Set-CourierOwnerOnlyAcl -Path $path }
    [IO.File]::WriteAllText($path, $text)
    $text = $null
    Set-CourierOwnerOnlyAcl -Path $path
    $id = Add-CourierSink -Path $path -Format $Format -Keys $keys -Repo $repo
    return [pscustomobject]@{ id = $id; path = $path; keys = $keys }
}

function Remove-CourierSink {
    <# .SYNOPSIS Strip the keys this plugin wrote from the sink (delete the file when nothing else is left) and drop
       the ledger entry. #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Id, [switch]$WhatIf)
    $entry = Read-Sinks | Where-Object { $_['id'] -eq $Id } | Select-Object -First 1
    if (-not $entry) { return $null }
    $path = [string]$entry['path']
    if ($WhatIf) { return [pscustomobject]@{ id = $Id; path = $path; keys = @($entry['keys']); action = 'would-sweep' } }
    if (Test-Path -LiteralPath $path) {
        $text = [IO.File]::ReadAllText($path)
        if ($entry['format'] -eq 'dotenv') {
            $keep = @(($text -split "`r?`n") | Where-Object { $line = $_; -not ($entry['keys'] | Where-Object { $line -match "^\s*$([regex]::Escape($_))\s*=" }) })
            $rest = ($keep | Where-Object { $_.Trim() }) -join "`n"
            if ($rest.Trim()) { [IO.File]::WriteAllText($path, $rest + "`n") } else { Remove-Item -LiteralPath $path -Force }
        } else {
            $doc = if ($text.Trim()) { $text | ConvertFrom-Json -AsHashtable } else { @{} }
            if ($null -eq $doc) { $doc = @{} }
            foreach ($k in $entry['keys']) { Remove-JsonPath $doc $k }
            if ($doc.Count -gt 0) { [IO.File]::WriteAllText($path, (($doc | ConvertTo-Json -Depth 20) + "`n")) } else { Remove-Item -LiteralPath $path -Force }
        }
        $text = $null
    }
    Remove-CourierSinkEntry $Id
    return [pscustomobject]@{ id = $Id; path = $path; keys = @($entry['keys']); action = 'swept' }
}

Export-ModuleMember -Function Get-CourierSinks, Add-CourierSink, Write-CourierSink, Remove-CourierSink, Test-CourierTargetIgnored, Get-CourierRepoRoot, Resolve-CourierUserSecretsPath
