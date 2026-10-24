# Dot-sourced by every op. An op takes NAMES, prints exactly one "STATUS <status> <detail>" line, never a value,
# and reduces an exception to its message (which the bridge redacts again before the model sees it).
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path (Split-Path $PSScriptRoot -Parent) 'Courier.psm1') -Force
Import-Module (Join-Path (Split-Path $PSScriptRoot -Parent) 'CourierSinks.psm1') -Force

function Split-StoreName([string]$Spec, [string]$What) {
    if ($Spec -notmatch '^(dpapi|credman|env|keyvault):(.+)$') { throw "$What must be <store>:<name> with store one of dpapi, credman, env, keyvault" }
    return @($Matches[1], $Matches[2])
}

function Write-Info([string]$Text) {
    # One plain sentence for the person: what happened to the value and where it is now. Never a value.
    Write-Output ($Text -replace '[\r\n]+', ' ')
}

function Get-StoreDescription([string]$Store, [string]$Name) {
    switch ($Store) {
        'dpapi'    { return "the DPAPI file store ($(Join-Path (Get-CourierHome) 'secrets.json')), encrypted for the Windows account $env:USERNAME; only code running as you can decrypt it" }
        'credman'  { return "Windows Credential Manager as 'secret-courier/$Name', encrypted by the OS for the account $env:USERNAME" }
        'env'      { return "the environment variable $Name of this process (a source only; nothing is stored here)" }
        'keyvault' { return "Azure Key Vault $Name, read in memory under your own az login (a source only)" }
        default    { return $Store }
    }
}

function Write-Status([string]$Status, [string]$Detail = '', [string]$Op = '') {
    if ($Op) { Write-CourierAudit -Op $Op -Status $Status -Detail $Detail }
    if ($Detail) { Write-Output "STATUS $Status $Detail" } else { Write-Output "STATUS $Status" }
}

function Write-StatusError([string]$Message, [string]$Op = '') {
    $msg = ($Message -replace '[\r\n]+', ' ')
    if ($Op) { Write-CourierAudit -Op $Op -Status 'error' -Detail $msg }
    Write-Output "STATUS error $msg"
    exit 1
}
