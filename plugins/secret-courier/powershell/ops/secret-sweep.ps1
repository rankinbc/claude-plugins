# secret-sweep.ps1 [-Id <id>] [-OlderDays <n>] [-Repo <substring>] [-WhatIf]
# Removes the keys this plugin wrote from every matching sink (deleting a file left empty) and drops the ledger
# entries. Prints one line per sink, then STATUS swept <n> | STATUS listed <n> (with -WhatIf)
param([string]$Id = '', [int]$OlderDays = -1, [string]$Repo = '', [switch]$WhatIf)
. (Join-Path $PSScriptRoot '_common.ps1')
try {
    $rows = @(Get-CourierSinks -Repo $Repo)
    if ($Id) { $rows = @($rows | Where-Object { $_.id -eq $Id }) }
    if ($OlderDays -ge 0) {
        $cutoff = (Get-Date).ToUniversalTime().AddDays(-$OlderDays)
        $rows = @($rows | Where-Object { [DateTime]::Parse($_.written_at).ToUniversalTime() -le $cutoff })
    }
    $n = 0
    foreach ($r in $rows) {
        $res = Remove-CourierSink -Id $r.id -WhatIf:$WhatIf
        if ($res) { Write-Output "$($res.action) $($res.path) keys=$(@($res.keys) -join ',')"; $n++ }
    }
    if ($WhatIf) {
        Write-Info "$n plaintext cop$(if ($n -eq 1) { 'y' } else { 'ies' }) would be removed; nothing was changed (dry run)."
        Write-Status 'listed' "$n" 'sweep'
    } else {
        Write-Info "Removed the keys this plugin wrote from $n file$(if ($n -ne 1) { 's' }) (a file left empty was deleted) and dropped the ledger entries. The encrypted stores are untouched."
        Write-Status 'swept' "$n" 'sweep'
    }
} catch { Write-StatusError $_.Exception.Message 'sweep' }
