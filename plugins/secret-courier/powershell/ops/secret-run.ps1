# secret-run.ps1 -EnvSpec <base64 json {VAR: "<store>:<name>"}> -CommandSpec <base64 json ["exe", "arg", ...]>
# Runs one command with the named values in ITS environment only (transit: nothing is written anywhere). The
# child's console is inherited; both specs travel base64-encoded so the child's own flags never bind to this
# script's parameters. Prints: STATUS exit <code> | STATUS missing <name>
param(
    [Parameter(Mandatory)][string]$EnvSpec,
    [Parameter(Mandatory)][string]$CommandSpec
)
. (Join-Path $PSScriptRoot '_common.ps1')
function ConvertFrom-Base64Json([string]$Text) {
    return ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($Text)) | ConvertFrom-Json -AsHashtable)
}
try {
    $envMap = ConvertFrom-Base64Json $EnvSpec
    $command = @(ConvertFrom-Base64Json $CommandSpec)
    if (-not $command -or -not $command[0]) { throw 'nothing to run' }
    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = [string]$command[0]
    foreach ($a in $command[1..($command.Count - 1)]) { if ($null -ne $a) { $psi.ArgumentList.Add([string]$a) } }
    $psi.UseShellExecute = $false
    foreach ($var in $envMap.Keys) {
        if ($var -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') { throw 'an environment variable name is letters, digits and _' }
        $s, $n = Split-StoreName ([string]$envMap[$var]) 'env'
        if (-not (Get-CourierStoreExists -Store $s -Name $n)) { Write-Info "${s}:$n holds no value; the command was not started."; Write-Status 'missing' $n 'run'; exit 0 }
        $psi.Environment[$var] = Get-CourierSecretValue -Store $s -Name $n
    }
    $vars = @($envMap.Keys) -join ', '
    $p = [System.Diagnostics.Process]::Start($psi)
    $p.WaitForExit()
    $psi = $null
    Write-Info "Ran $($command[0]) with $vars set in its environment only; the process has exited with code $($p.ExitCode) and the value is gone with it. Nothing was written to disk."
    Write-Status 'exit' "$($p.ExitCode)" 'run'
    exit $p.ExitCode
} catch { Write-StatusError $_.Exception.Message 'run' }
