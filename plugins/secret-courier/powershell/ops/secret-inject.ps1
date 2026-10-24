# secret-inject.ps1 -Target <file or csproj> -Format dotenv|json|user-secrets -Map KEY=<store>:<name> ... [-Replace]
# Writes the named values into a consumer's local config (a sink): owner-ACL'd, git-ignored (dotenv/json) and
# recorded in the ledger so `courier sweep` can remove it. Prints: STATUS stored <path> keys=<n> | STATUS missing <name>
param(
    [Parameter(Mandatory)][string]$Target,
    [Parameter(Mandatory)][string]$Format,
    [Parameter(Mandatory)][string[]]$Map,
    [switch]$Replace
)
. (Join-Path $PSScriptRoot '_common.ps1')
try {
    $entries = @{}
    foreach ($m in $Map) {
        if ($m -notmatch '^([A-Za-z_][\w:.-]*)=(.+)$') { throw "map entries are KEY=<store>:<name>" }
        $key, $spec = $Matches[1], $Matches[2]
        $s, $n = Split-StoreName $spec 'map'
        if (-not (Get-CourierStoreExists -Store $s -Name $n)) { Write-Info "${s}:$n holds no value; nothing was written."; Write-Status 'missing' $n 'inject'; exit 0 }
        $entries[$key] = Get-CourierStoreValue -Store $s -Name $n
    }
    $r = Write-CourierSink -Target $Target -Format $Format -Entries $entries -Replace:$Replace
    $entries = $null
    $where = if ($Format -eq 'user-secrets') { 'outside any repository, under your profile' } else { 'git ignores it, so it cannot be committed' }
    Write-Info "Wrote $($r.keys -join ', ') in plain text into $($r.path) ($Format). This is a copy a program will read: $where, and the file is readable only by $env:USERNAME. It is recorded in the ledger as $($r.id); remove it with 'courier sweep --id $($r.id)' when the job is done."
    Write-Status 'stored' "$($r.path) keys=$($r.keys.Count)" 'inject'
} catch { Write-StatusError $_.Exception.Message 'inject' }
