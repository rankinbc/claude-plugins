# secret-test.ps1 <name> -Url <https url> [-Auth bearer|basic-pat|token|header:<Name>] [-Expect 200] [-Header k=v ...]
# Read-only probe of an endpoint with the named secret through HttpClient (no cmdlet ever sees the value).
# The URL comes from config/endpoints.json via the bridge, never from the model. Prints: STATUS valid <code> |
# STATUS invalid <code> | STATUS missing
param(
    [Parameter(Mandatory)][string]$Name,
    [Parameter(Mandatory)][string]$Url,
    [string]$Auth = 'bearer',
    [int]$Expect = 200,
    [string[]]$Header = @()
)
. (Join-Path $PSScriptRoot '_common.ps1')
try {
    Test-CourierName $Name
    if ($Url -notmatch '^https://') { throw 'endpoint must be https' }
    $store = Find-CourierStore -Name $Name
    if (-not $store) { Write-Info "No store holds '$Name'; nothing was sent."; Write-Status 'missing' '' 'test'; exit 0 }
    $value = Get-CourierSecretValue -Store $store -Name $Name
    $client = [System.Net.Http.HttpClient]::new()
    try {
        $client.Timeout = [TimeSpan]::FromSeconds(20)
        $req = [System.Net.Http.HttpRequestMessage]::new([System.Net.Http.HttpMethod]::Get, $Url)
        switch -Regex ($Auth) {
            '^basic-pat$' { $req.Headers.Authorization = [System.Net.Http.Headers.AuthenticationHeaderValue]::new('Basic', [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":$value"))) }
            '^bearer$'    { $req.Headers.Authorization = [System.Net.Http.Headers.AuthenticationHeaderValue]::new('Bearer', $value) }
            '^token$'     { $req.Headers.TryAddWithoutValidation('Authorization', "token $value") | Out-Null }
            '^header:(.+)$' { $req.Headers.TryAddWithoutValidation($Matches[1], $value) | Out-Null }
            default       { throw "unknown auth scheme $Auth" }
        }
        foreach ($h in $Header) { $k, $v = $h.Split('=', 2); if ($k -and $null -ne $v) { $req.Headers.TryAddWithoutValidation($k, $v) | Out-Null } }
        $resp = $client.SendAsync($req).GetAwaiter().GetResult()
        $code = [int]$resp.StatusCode
    } finally { $value = $null; $client.Dispose() }
    $host_ = ([Uri]$Url).Host
    Write-Info "Sent one GET to $host_ over HTTPS with '$Name' in the $Auth header; the response code was $code. The value was held in memory for that request only and was not logged."
    if ($code -eq $Expect) { Write-Status 'valid' "$code" 'test' } else { Write-Status 'invalid' "$code" 'test' }
} catch { Write-StatusError $_.Exception.Message 'test' }
