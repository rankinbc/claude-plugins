# Start-CourierConsole.ps1 -Title <t> -ScriptPath <ops script> -Arguments <args>
# Opens a real console (a Windows Terminal tab when wt.exe exists, else a new pwsh window) running one ops script,
# so a masked Read-Host prompt has a keyboard in front of it. The agent's own tool has no console: that is the
# point. Prints: STATUS opened <title>
param(
    [Parameter(Mandatory)][string]$Title,
    [Parameter(Mandatory)][string]$ScriptPath,
    [string[]]$Arguments = @()
)
$ErrorActionPreference = 'Stop'
try {
    if (-not (Test-Path -LiteralPath $ScriptPath)) { throw "script not found: $ScriptPath" }
    foreach ($a in $Arguments) { if ($a -match "[`"'\r\n]") { throw 'arguments may not contain quotes or newlines' } }
    $pwsh = (Get-Command pwsh -ErrorAction SilentlyContinue).Source
    if (-not $pwsh) { throw 'pwsh (PowerShell 7) is not on PATH' }
    $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $ScriptPath) + $Arguments
    $wt = (Get-Command wt.exe -ErrorAction SilentlyContinue).Source
    if ($wt) {
        Start-Process -FilePath $wt -ArgumentList (@('new-tab', '--title', $Title, '--', $pwsh) + $argList) | Out-Null
    } else {
        Start-Process -FilePath $pwsh -ArgumentList $argList | Out-Null
    }
    Write-Output "A console window titled '$Title' opened on this machine. Type or paste the value there; the window shows nothing while you type and explains where the value goes. Claude learns only the name and that it was stored; check with 'courier exists <name>' afterwards."
    Write-Output "STATUS opened $Title"
} catch {
    Write-Output "STATUS error $($_.Exception.Message)"
    exit 1
}
