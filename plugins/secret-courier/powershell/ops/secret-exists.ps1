# secret-exists.ps1 <name>      Prints: STATUS found <store> | STATUS missing
param([Parameter(Mandatory)][string]$Name)
. (Join-Path $PSScriptRoot '_common.ps1')
try {
    Test-CourierName $Name
    $s = Find-CourierStore -Name $Name
    if ($s) {
        Write-Info "'$Name' is held in $(Get-StoreDescription $s $Name). Its value was not read for this check."
        Write-Status 'found' $s 'exists'
    } else {
        Write-Info "No store holds '$Name' (checked dpapi, credman and the environment). Run 'courier prompt $Name' to enter it at a masked prompt."
        Write-Status 'missing' '' 'exists'
    }
} catch { Write-StatusError $_.Exception.Message 'exists' }
