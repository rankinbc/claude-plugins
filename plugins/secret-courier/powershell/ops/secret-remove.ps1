# secret-remove.ps1 <store>:<name>      Prints: STATUS removed <store> | STATUS missing
param([Parameter(Mandatory)][string]$Spec)
. (Join-Path $PSScriptRoot '_common.ps1')
try {
    $s, $n = Split-StoreName $Spec 'spec'
    if (Remove-CourierStoreValue -Store $s -Name $n) {
        Write-Info "Removed '$n' from $(Get-StoreDescription $s $n). Plaintext copies written earlier by 'courier inject' are listed by 'courier sinks' and are not touched by this."
        Write-Status 'removed' $s 'remove'
    } else {
        Write-Info "${s}:$n held no value; nothing changed."
        Write-Status 'missing' '' 'remove'
    }
} catch { Write-StatusError $_.Exception.Message 'remove' }
