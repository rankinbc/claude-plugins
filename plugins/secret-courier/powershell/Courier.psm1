# Courier.psm1 - the only code that reads or writes secret VALUES. Everything else (the model, the CLI, the
# bridge) handles NAMES.
#
# Home:     $env:COURIER_HOME or %USERPROFILE%\.secret-courier (owner-only ACL)
#   secrets.json           dpapi store: name -> DPAPI blob for the current Windows user
#   secrets.manifest.json  name -> description, source, updated_at (never values)
#   audit.jsonl            one line per op: ts, op, status, detail (names only)
# Stores, addressed as <store>:<name>:
#   dpapi    the file above            credman  Windows Credential Manager "secret-courier/<name>" (P/Invoke)
#   env      process environment (SOURCE only)        keyvault  Azure Key Vault "<vault>/<secret>" (SOURCE only,
#            interactive, under the developer's own az login)
# Values travel as SecureString. No value is passed to a cmdlet as a parameter (host module logging records
# those); plaintext exists only inside the .NET calls that need it.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:Home = if ($env:COURIER_HOME) { $env:COURIER_HOME } else { Join-Path $env:USERPROFILE '.secret-courier' }
$script:StorePath = Join-Path $script:Home 'secrets.json'
$script:ManifestPath = Join-Path $script:Home 'secrets.manifest.json'
$script:AuditPath = Join-Path $script:Home 'audit.jsonl'
$script:CredPrefix = 'secret-courier/'
$script:Stores = @('dpapi', 'credman', 'env', 'keyvault')
$script:ReadOnlyStores = @('env', 'keyvault')

if (-not ('CourierCred' -as [type])) {
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class CourierCred {
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct CREDENTIAL {
        public uint Flags; public uint Type; public string TargetName; public string Comment;
        public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten;
        public uint CredentialBlobSize; public IntPtr CredentialBlob; public uint Persist;
        public uint AttributeCount; public IntPtr Attributes; public string TargetAlias; public string UserName;
    }
    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern bool CredReadW(string target, uint type, uint flags, out IntPtr credential);
    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern bool CredWriteW(ref CREDENTIAL credential, uint flags);
    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern bool CredDeleteW(string target, uint type, uint flags);
    [DllImport("advapi32.dll", SetLastError = true)]
    static extern void CredFree(IntPtr cred);
    public static bool Exists(string target) { IntPtr p; if (!CredReadW(target, 1, 0, out p)) return false; CredFree(p); return true; }
    public static string Read(string target) {
        IntPtr p; if (!CredReadW(target, 1, 0, out p)) return null;
        try { var c = (CREDENTIAL)Marshal.PtrToStructure(p, typeof(CREDENTIAL));
              if (c.CredentialBlobSize == 0) return ""; return Marshal.PtrToStringUni(c.CredentialBlob, (int)c.CredentialBlobSize / 2); }
        finally { CredFree(p); }
    }
    public static bool Write(string target, string user, string secret) {
        var bytes = System.Text.Encoding.Unicode.GetBytes(secret);
        var c = new CREDENTIAL(); c.Type = 1; c.TargetName = target; c.UserName = user; c.Persist = 2;
        c.CredentialBlobSize = (uint)bytes.Length; c.CredentialBlob = Marshal.AllocHGlobal(bytes.Length);
        try { Marshal.Copy(bytes, 0, c.CredentialBlob, bytes.Length); return CredWriteW(ref c, 0); }
        finally { Array.Clear(bytes, 0, bytes.Length); Marshal.FreeHGlobal(c.CredentialBlob); }
    }
    public static bool Delete(string target) { return CredDeleteW(target, 1, 0); }
}
"@
}

# --- files and ACLs ------------------------------------------------------------------------------------------

function ConvertTo-CourierSidString([string]$Identity) {
    if ($Identity -match '^S-1-') { return $Identity }
    try { return ([System.Security.Principal.NTAccount]$Identity).Translate([System.Security.Principal.SecurityIdentifier]).Value }
    catch { return $null }
}

function Set-CourierOwnerOnlyAcl {
    <# .SYNOPSIS Restrict a file or directory to the current user (plus SYSTEM and Administrators); strip every
       other explicit ACE, including the logon-session SID Windows copies from the creating token. #>
    param([Parameter(Mandatory)][string]$Path)
    $me = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    & icacls $Path /inheritance:r /grant:r "${me}:(F)" 2>&1 | Out-Null
    $keep = @('NT AUTHORITY\SYSTEM', 'BUILTIN\Administrators')
    foreach ($ace in @((Get-Acl -Path $Path).Access)) {
        $id = $ace.IdentityReference.Value
        if ($id -ieq $me -or $id -in $keep) { continue }
        $sid = ConvertTo-CourierSidString $id
        if ($sid) { & icacls $Path /remove:g "*$sid" 2>&1 | Out-Null }
    }
}

function Get-CourierHome { return $script:Home }

function Initialize-CourierHome {
    if (-not (Test-Path $script:Home)) { New-Item -ItemType Directory -Path $script:Home | Out-Null }
    foreach ($p in @($script:StorePath, $script:ManifestPath)) {
        if (-not (Test-Path $p)) { [IO.File]::WriteAllText($p, '{}') }
    }
    foreach ($p in @($script:Home, $script:StorePath, $script:ManifestPath)) { Set-CourierOwnerOnlyAcl -Path $p }
}

function Read-JsonFile([string]$Path) {
    if (-not (Test-Path $Path)) { return @{} }
    $raw = [IO.File]::ReadAllText($Path)
    if ([string]::IsNullOrWhiteSpace($raw)) { return @{} }
    $obj = $raw | ConvertFrom-Json -AsHashtable
    if ($null -eq $obj) { return @{} }
    return $obj
}

function Write-JsonFile([string]$Path, [hashtable]$Data) {
    $tmp = "$Path.tmp"
    [IO.File]::WriteAllText($tmp, '')
    Set-CourierOwnerOnlyAcl -Path $tmp
    [IO.File]::WriteAllText($tmp, ($Data | ConvertTo-Json -Depth 6))
    Move-Item -Path $tmp -Destination $Path -Force
    Set-CourierOwnerOnlyAcl -Path $Path
}

function Write-CourierAudit {
    <# .SYNOPSIS One JSON line per op: names, store, status, detail. Never a value. #>
    param([Parameter(Mandatory)][string]$Op, [Parameter(Mandatory)][string]$Status, [string]$Detail = '')
    try {
        Initialize-CourierHome
        $line = (@{ ts = (Get-Date).ToUniversalTime().ToString('o'); op = $Op; status = $Status; detail = $Detail } | ConvertTo-Json -Compress)
        [IO.File]::AppendAllText($script:AuditPath, $line + "`n")
        Set-CourierOwnerOnlyAcl -Path $script:AuditPath
    } catch {}
}

# --- names and SecureString -----------------------------------------------------------------------------------

function Test-CourierName {
    <# .SYNOPSIS The one name grammar: lowercase letters, digits, '-', '_', '.' (2-81 chars). #>
    param([Parameter(Mandatory)][string]$Name)
    if ($Name -notmatch '^[a-z0-9][a-z0-9\-_.]{1,80}$') {
        throw "secret name must be lowercase letters, digits, '-', '_' or '.' (2-81 chars)"
    }
}

function ConvertTo-CourierKeyringName {
    param([Parameter(Mandatory)][string]$Name)
    return (($Name -replace '[^A-Za-z0-9]', '_').ToUpperInvariant())
}

function Test-CourierStore([string]$Store) {
    if ($Store -notin $script:Stores) { throw "unknown store '$Store' (one of: $($script:Stores -join ', '))" }
}

function Test-CourierKeyVaultName([string]$Name) {
    if ($Name -notmatch '^[A-Za-z0-9-]{3,24}/[A-Za-z0-9-]{1,127}$') { throw "a keyvault name is <vault>/<secret>" }
}

function ConvertTo-CourierSecureString {
    <# .SYNOPSIS SecureString from a plain string without ConvertTo-SecureString -String (a logged cmdlet parameter). #>
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Plain)
    $ss = New-Object System.Security.SecureString
    foreach ($ch in $Plain.ToCharArray()) { $ss.AppendChar($ch) }
    $ss.MakeReadOnly()
    return $ss
}

function ConvertFrom-CourierSecureString {
    <# .SYNOPSIS Plain string from a SecureString. For the ops that must hand a value to .NET; never for display. #>
    param([Parameter(Mandatory)][SecureString]$Secure)
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

function Assert-CourierInteractive {
    <# .SYNOPSIS Refuse unless a person is at the keyboard: stdin not redirected, a user-interactive session, the host
       not started with -NonInteractive, and (with -Confirm) a typed word. An agent tool fails here before any
       value is read. #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Reason, [string]$Why = 'it reads secret values in memory', [string]$Confirm = '', [string]$Prompt = '')
    $nonInteractiveArg = [Environment]::GetCommandLineArgs() | Where-Object { $_ -match '^-noni' }
    if ([Console]::IsInputRedirected -or -not [Environment]::UserInteractive -or $nonInteractiveArg) {
        throw "$Reason must be run interactively by the developer in their own terminal ($Why)."
    }
    if ($Confirm) {
        $text = if ($Prompt) { $Prompt } else { "$Reason`: type $Confirm to continue" }
        $answer = Read-Host $text
        if ($answer -cne $Confirm) { throw 'Not confirmed; nothing was read.' }
    }
}

function Get-CourierMaskedString {
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Text, [string[]]$Secrets = @())
    foreach ($s in ($Secrets | Where-Object { $_ -and $_.Length -ge 3 } | Sort-Object Length -Descending)) {
        $Text = $Text.Replace($s, '[MASKED]')
    }
    return $Text
}

# --- manifest (names only) ------------------------------------------------------------------------------------

function Set-CourierManifest {
    param([Parameter(Mandatory)][string]$Name, [string]$Description = '', [string]$Source = '', [string]$Store = 'dpapi')
    Initialize-CourierHome
    $manifest = Read-JsonFile $script:ManifestPath
    $entry = @{ description = $Description; source = $Source; store = $Store; updated_at = (Get-Date).ToUniversalTime().ToString('o') }
    if ($manifest.ContainsKey($Name)) {
        if (-not $Description) { $entry.description = $manifest[$Name]['description'] }
        if (-not $Source) { $entry.source = $manifest[$Name]['source'] }
    }
    $manifest[$Name] = $entry
    Write-JsonFile $script:ManifestPath $manifest
}

function Remove-CourierManifest([string]$Name) {
    $manifest = Read-JsonFile $script:ManifestPath
    if ($manifest.ContainsKey($Name)) { $manifest.Remove($Name); Write-JsonFile $script:ManifestPath $manifest }
}

function Get-CourierNames {
    <# .SYNOPSIS Every name the store or the manifest knows, with where it is held. Never values. #>
    [CmdletBinding()]
    param([string[]]$Expected = @())
    Initialize-CourierHome
    $store = Read-JsonFile $script:StorePath
    $manifest = Read-JsonFile $script:ManifestPath
    $names = @($store.Keys) + @($manifest.Keys) + $Expected | Where-Object { $_ } | Sort-Object -Unique
    foreach ($n in $names) {
        $meta = if ($manifest.ContainsKey($n)) { $manifest[$n] } else { @{} }
        $held = @()
        if ($store.ContainsKey($n)) { $held += 'dpapi' }
        if ($n -match '^[a-z0-9][a-z0-9\-_.]{1,80}$' -and [CourierCred]::Exists($script:CredPrefix + $n)) { $held += 'credman' }
        [pscustomobject]@{ name = $n; stores = $held; description = $meta['description']; source = $meta['source']; updated_at = $meta['updated_at'] }
    }
}

# --- store adapters -------------------------------------------------------------------------------------------

function Get-CourierStoreExists {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Store, [Parameter(Mandatory)][string]$Name)
    Test-CourierStore $Store
    switch ($Store) {
        'dpapi'   { Test-CourierName $Name; $data = Read-JsonFile $script:StorePath; return $data.ContainsKey($Name) }
        'credman' { Test-CourierName $Name; return [CourierCred]::Exists($script:CredPrefix + $Name) }
        'env'     { return [bool](Get-Item -Path "Env:$Name" -ErrorAction SilentlyContinue) }
        'keyvault' {
            Test-CourierKeyVaultName $Name
            $vault, $secret = $Name.Split('/', 2)
            $out = & az keyvault secret list --vault-name $vault --query "[?name=='$secret'].name" -o tsv 2>$null
            if ($LASTEXITCODE -ne 0) { throw "keyvault list failed for vault '$vault' (az error; is the az login current?)" }
            return [bool]($out | Where-Object { $_ -and $_.Trim() -eq $secret })
        }
    }
}

function Get-CourierStoreValue {
    <# .SYNOPSIS The value under -Name in -Store as a SecureString. keyvault needs a person at the keyboard. #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Store, [Parameter(Mandatory)][string]$Name)
    Test-CourierStore $Store
    switch ($Store) {
        'dpapi' {
            Test-CourierName $Name
            $data = Read-JsonFile $script:StorePath   # not $store: that is the [string] parameter
            if (-not $data.ContainsKey($Name)) { throw "dpapi holds nothing under '$Name'" }
            return ($data[$Name] | ConvertTo-SecureString)
        }
        'credman' {
            Test-CourierName $Name
            $plain = [CourierCred]::Read($script:CredPrefix + $Name)
            if ($null -eq $plain) { throw "credman holds nothing under '$Name'" }
            try { return (ConvertTo-CourierSecureString -Plain $plain) } finally { $plain = $null }
        }
        'env' {
            $item = Get-Item -Path "Env:$Name" -ErrorAction SilentlyContinue
            if (-not $item) { throw "the environment holds nothing under '$Name'" }
            return (ConvertTo-CourierSecureString -Plain ([string]$item.Value))
        }
        'keyvault' {
            Test-CourierKeyVaultName $Name
            Assert-CourierInteractive -Reason "Reading Key Vault secret '$Name'" -Why 'the value is read in memory under your own az login'
            $vault, $secret = $Name.Split('/', 2)
            $raw = & az keyvault secret show --vault-name $vault --name $secret --query value -o tsv 2>$null
            if ($LASTEXITCODE -ne 0 -or $null -eq $raw) { throw "keyvault read failed for '$Name' (az error; is the az login current?)" }
            try { return (ConvertTo-CourierSecureString -Plain (([string]$raw).Trim())) } finally { $raw = $null }
        }
    }
}

function Get-CourierSecretValue {
    <# .SYNOPSIS Plain-text value for the ops that must hand it to .NET (inject, run, test). Never for display. #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Store, [Parameter(Mandatory)][string]$Name)
    return (ConvertFrom-CourierSecureString -Secure (Get-CourierStoreValue -Store $Store -Name $Name))
}

function Set-CourierStoreValue {
    <# .SYNOPSIS Store -Value under -Name in -Store. env and keyvault are read-only; no overwrite without -Replace. #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Store, [Parameter(Mandatory)][string]$Name, [Parameter(Mandatory)][SecureString]$Value,
          [switch]$Replace, [string]$Description = '', [string]$Source = '')
    Test-CourierStore $Store
    if ($Store -in $script:ReadOnlyStores) { throw "store '$Store' is read-only: values are only ever imported from it" }
    Test-CourierName $Name
    if ($Value.Length -eq 0) { throw "empty value refused for '$Name'" }
    if (-not $Replace -and (Get-CourierStoreExists -Store $Store -Name $Name)) {
        throw "destination ${Store}:$Name already holds a value; pass -Replace to overwrite it"
    }
    Initialize-CourierHome
    switch ($Store) {
        'dpapi' {
            $data = Read-JsonFile $script:StorePath
            $data[$Name] = ($Value | ConvertFrom-SecureString)
            Write-JsonFile $script:StorePath $data
        }
        'credman' {
            $plain = ConvertFrom-CourierSecureString -Secure $Value
            try { if (-not [CourierCred]::Write($script:CredPrefix + $Name, 'secret-courier', $plain)) { throw "credential write failed for '$Name'" } }
            finally { $plain = $null }
        }
    }
    Set-CourierManifest -Name $Name -Description $Description -Source $Source -Store $Store
}

function Remove-CourierStoreValue {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Store, [Parameter(Mandatory)][string]$Name)
    Test-CourierStore $Store
    if ($Store -in $script:ReadOnlyStores) { throw "store '$Store' is read-only: nothing is ever removed from it here" }
    Test-CourierName $Name
    $existed = Get-CourierStoreExists -Store $Store -Name $Name
    switch ($Store) {
        'dpapi'   { $data = Read-JsonFile $script:StorePath; if ($data.ContainsKey($Name)) { $data.Remove($Name); Write-JsonFile $script:StorePath $data } }
        'credman' { if ($existed) { [CourierCred]::Delete($script:CredPrefix + $Name) | Out-Null } }
    }
    if (-not (Get-CourierStoreExists -Store dpapi -Name $Name) -and -not (Get-CourierStoreExists -Store credman -Name $Name)) { Remove-CourierManifest $Name }
    return $existed
}

function Find-CourierStore {
    <# .SYNOPSIS The first store holding -Name (dpapi, credman, env), or $null. keyvault is never searched implicitly. #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Name)
    foreach ($s in @('dpapi', 'credman', 'env')) {
        if ($s -ne 'env') { try { Test-CourierName $Name } catch { continue } }
        if (Get-CourierStoreExists -Store $s -Name $Name) { return $s }
    }
    return $null
}

Export-ModuleMember -Function Get-CourierHome, Initialize-CourierHome, Set-CourierOwnerOnlyAcl, Write-CourierAudit, Test-CourierName, `
    ConvertTo-CourierKeyringName, ConvertTo-CourierSecureString, ConvertFrom-CourierSecureString, Assert-CourierInteractive, `
    Get-CourierMaskedString, Set-CourierManifest, Get-CourierNames, Get-CourierStoreExists, Get-CourierStoreValue, `
    Get-CourierSecretValue, Set-CourierStoreValue, Remove-CourierStoreValue, Find-CourierStore
