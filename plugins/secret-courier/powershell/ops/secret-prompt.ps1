# secret-prompt.ps1 <name> [store] [-Description d] [-Source s] [-Replace]
# Runs in a console opened by Start-CourierConsole.ps1. Asks for the value with a masked prompt and stores it.
# The value never appears on screen, in a command line, or in this script's output.
param([Parameter(Mandatory)][string]$Name, [string]$Store = 'dpapi', [string]$Description = '', [string]$Source = '', [switch]$Replace)
. (Join-Path $PSScriptRoot '_common.ps1')
try {
    Test-CourierName $Name
    if ($Store -notin @('dpapi', 'credman')) { throw 'store must be dpapi or credman (env and keyvault are sources only)' }
    Assert-CourierInteractive -Reason "secret-prompt $Name" -Why 'the value is typed at a masked prompt'
    if (-not $Replace -and (Get-CourierStoreExists -Store $Store -Name $Name)) { throw "${Store}:$Name already holds a value; pass -Replace to overwrite it" }
    Write-Host ""
    Write-Host "secret-courier: a value is needed for '$Name'" -ForegroundColor Cyan
    if ($Description) { Write-Host "  What it is for: $Description" }
    if ($Source) { Write-Host "  Where it comes from: $Source" }
    Write-Host ""
    Write-Host "  Where it goes: $(Get-StoreDescription $Store $Name)." -ForegroundColor DarkGray
    Write-Host "  What Claude sees: only the name '$Name' and the word 'stored'. This window is the only place the value exists in clear, and it shows nothing while you type." -ForegroundColor DarkGray
    Write-Host "  Nothing leaves this machine. If you paste, the clipboard is cleared afterwards." -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "Type or paste the value and press Enter. Press Enter on an empty line to cancel."
    $ss = Read-Host -AsSecureString -Prompt $Name
    if ($ss.Length -eq 0) { Write-Status 'missing' 'cancelled' 'prompt'; exit 0 }
    Set-CourierStoreValue -Store $Store -Name $Name -Value $ss -Replace:$Replace -Description $Description -Source $Source
    # the value was probably pasted: clear the clipboard if it still holds it, so no later clipboard read sees it
    try {
        $plain = ConvertFrom-CourierSecureString -Secure $ss
        if ((Get-Clipboard -Raw -ErrorAction SilentlyContinue) -eq $plain) { Set-Clipboard -Value ' ' }
        $plain = $null
    } catch {}
    $ss = $null
    Write-Info "'$Name' was stored in $(Get-StoreDescription $Store $Name). Nothing else was written."
    Write-Status 'stored' $Store 'prompt'
    Write-Host ""
    Write-Host "Stored '$Name'. Nothing else was written. You can close this window and tell Claude to continue." -ForegroundColor Green
} catch { Write-StatusError $_.Exception.Message 'prompt' }
