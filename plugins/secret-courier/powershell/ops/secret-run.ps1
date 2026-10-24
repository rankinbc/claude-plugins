# secret-run.ps1 -EnvSpec <base64 json {VAR: "<store>:<name>"}> -CommandSpec <base64 json ["exe", "arg", ...]>
# Runs one command with the named values in ITS environment only (transit: nothing is written anywhere). The
# child's stdout/stderr are CAPTURED and redacted: every injected value and its base64 / url-encoded / reversed
# forms are masked before anything is relayed, so `courier run ... -- echo $SECRET` cannot print the value back
# to the model. Both specs travel base64-encoded so the child's own flags never bind to this script's parameters.
# Residual limit: a child that transforms the value (hashes, splits, re-encodes it) can still emit it. Because
# the streams are captured, the child is non-interactive. Prints: STATUS exit <code> | STATUS missing <name>
param(
    [Parameter(Mandatory)][string]$EnvSpec,
    [Parameter(Mandatory)][string]$CommandSpec
)
. (Join-Path $PSScriptRoot '_common.ps1')
function ConvertFrom-Base64Json([string]$Text) {
    return ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($Text)) | ConvertFrom-Json -AsHashtable)
}
function Get-CourierMaskForms([string]$Value) {
    # the value plus the cheap transforms a child might print it through: exact, base64 (utf8 + ascii),
    # url-encoded, and reversed. (A deeper transform is the documented residual limit.)
    $forms = @($Value)
    try { $forms += [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Value)) } catch {}
    try { $forms += [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($Value)) } catch {}
    try { $forms += [Uri]::EscapeDataString($Value) } catch {}
    try { $ca = $Value.ToCharArray(); [Array]::Reverse($ca); $forms += (-join $ca) } catch {}
    return $forms
}
try {
    $envMap = ConvertFrom-Base64Json $EnvSpec
    $command = @(ConvertFrom-Base64Json $CommandSpec)
    if (-not $command -or -not $command[0]) { throw 'nothing to run' }
    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = [string]$command[0]
    foreach ($a in $command[1..($command.Count - 1)]) { if ($null -ne $a) { $psi.ArgumentList.Add([string]$a) } }
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $masks = @()
    foreach ($var in $envMap.Keys) {
        if ($var -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') { throw 'an environment variable name is letters, digits and _' }
        $s, $n = Split-StoreName ([string]$envMap[$var]) 'env'
        if (-not (Get-CourierStoreExists -Store $s -Name $n)) { Write-Info "${s}:$n holds no value; the command was not started."; Write-Status 'missing' $n 'run'; exit 0 }
        $val = Get-CourierSecretValue -Store $s -Name $n
        $psi.Environment[$var] = $val
        if ($val.Length -ge 3) { $masks += Get-CourierMaskForms $val }
        $val = $null
    }
    $vars = @($envMap.Keys) -join ', '
    $p = [System.Diagnostics.Process]::Start($psi)
    $out = $p.StandardOutput.ReadToEnd()
    $err = $p.StandardError.ReadToEnd()
    $p.WaitForExit()
    $psi = $null
    # mask every injected value (and its cheap encodings) out of what the child printed, then relay it
    $out = Get-CourierMaskedString -Text $out -Secrets $masks
    $err = Get-CourierMaskedString -Text $err -Secrets $masks
    $masks = $null
    $cap = 20000
    if ($out.Length -gt $cap) { $out = $out.Substring(0, $cap) + "`n...[output truncated by secret-courier]" }
    if ($err.Length -gt $cap) { $err = $err.Substring(0, $cap) + "`n...[output truncated by secret-courier]" }
    if ($out.Trim()) { Write-Output $out.TrimEnd() }
    if ($err.Trim()) { Write-Output ("[stderr] " + $err.TrimEnd()) }
    Write-Info "Ran $($command[0]) with $vars set in its environment only; the process has exited with code $($p.ExitCode) and the value is gone with it. Its output was captured and redacted; nothing was written to disk."
    Write-Status 'exit' "$($p.ExitCode)" 'run'
    exit $p.ExitCode
} catch { Write-StatusError $_.Exception.Message 'run' }
