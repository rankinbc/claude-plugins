# secret-sinks.ps1 [-Repo <substring>]   Prints one line per sink "<id> <format> <path> keys=<k1,k2> written=<ts>" then STATUS listed <n>
param([string]$Repo = '')
. (Join-Path $PSScriptRoot '_common.ps1')
try {
    $rows = @(Get-CourierSinks -Repo $Repo)
    foreach ($r in $rows) { Write-Output "$($r.id) $($r.format) $($r.path) keys=$(@($r.keys) -join ',') written=$($r.written_at)" }
    if ($rows.Count -eq 0) { Write-Info "No plaintext copies are outstanding: every value lives only in its encrypted store." }
    else { Write-Info "$($rows.Count) plaintext cop$(if ($rows.Count -eq 1) { 'y is' } else { 'ies are' }) on disk for programs to read (each git-ignored or outside any repo, readable only by you). Remove one with 'courier sweep --id <id>' or all with 'courier sweep'." }
    Write-Status 'listed' "$($rows.Count)" 'sinks'
} catch { Write-StatusError $_.Exception.Message 'sinks' }
