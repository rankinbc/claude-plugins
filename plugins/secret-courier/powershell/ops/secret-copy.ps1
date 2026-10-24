# secret-copy.ps1 <from-store>:<name> <to-store>:<name> [-Replace]
# Moves a value between stores in memory. Prints: STATUS stored <to-store> | STATUS missing | STATUS error ...
param([Parameter(Mandatory)][string]$From, [Parameter(Mandatory)][string]$To, [switch]$Replace)
. (Join-Path $PSScriptRoot '_common.ps1')
try {
    $fs, $fn = Split-StoreName $From 'from'
    $ts, $tn = Split-StoreName $To 'to'
    if ($ts -in @('env', 'keyvault')) { throw "$ts is read-only: an environment variable or a vault is never a destination here" }
    if (-not $Replace -and (Get-CourierStoreExists -Store $ts -Name $tn)) { throw "destination ${ts}:$tn already holds a value; pass -Replace to overwrite it" }
    if (-not (Get-CourierStoreExists -Store $fs -Name $fn)) { Write-Info "Nothing to copy: ${fs}:$fn holds no value."; Write-Status 'missing' '' 'copy'; exit 0 }
    $v = Get-CourierStoreValue -Store $fs -Name $fn
    if ($v.Length -eq 0) { Write-Status 'missing' '' 'copy'; exit 0 }
    Set-CourierStoreValue -Store $ts -Name $tn -Value $v -Replace:$Replace -Source "copied from ${fs}:$fn"
    $v = $null
    Write-Info "Copied '$fn' from $(Get-StoreDescription $fs $fn) into $(Get-StoreDescription $ts $tn). The value moved in memory only; it was not printed, logged or written anywhere else."
    Write-Status 'stored' $ts 'copy'
} catch { Write-StatusError $_.Exception.Message 'copy' }
