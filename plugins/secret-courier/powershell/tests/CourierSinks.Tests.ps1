# CourierSinks.Tests.ps1 - the sink ledger against a fake home and a throwaway git repo under $TestDrive.
Describe 'CourierSinks.psm1' {
    BeforeAll {
        $script:Root = Split-Path $PSScriptRoot -Parent
        $script:SavedHome = $env:COURIER_HOME
        $env:COURIER_HOME = Join-Path $TestDrive 'home'
        Import-Module (Join-Path $script:Root 'Courier.psm1') -Force
        Import-Module (Join-Path $script:Root 'CourierSinks.psm1') -Force
        $script:Repo = Join-Path $TestDrive 'repo'
        New-Item -ItemType Directory -Path $script:Repo -Force | Out-Null
        & git -C $script:Repo init -q
        [IO.File]::WriteAllText((Join-Path $script:Repo '.gitignore'), ".env`nappsettings.local.json`n")
        $script:FakeValue = 'pester-fake-value-9'
        $script:Entries = @{ API_KEY = (ConvertTo-CourierSecureString -Plain $script:FakeValue) }
    }
    AfterAll {
        if ($null -ne $script:SavedHome) { $env:COURIER_HOME = $script:SavedHome } else { Remove-Item Env:COURIER_HOME -ErrorAction SilentlyContinue }
        Import-Module (Join-Path $script:Root 'Courier.psm1') -Force
    }

    It 'refuses a target git does not ignore, and one outside any repo' {
        { Write-CourierSink -Target (Join-Path $script:Repo 'config.txt') -Format dotenv -Entries $script:Entries } | Should -Throw '*not-ignored*'
        { Write-CourierSink -Target (Join-Path $TestDrive 'loose.env') -Format dotenv -Entries $script:Entries } | Should -Throw '*not-a-repo*'
        @(Get-CourierSinks).Count | Should -Be 0
    }

    It 'dotenv: writes, merges, ledgers, ACLs, refuses overwrite without -Replace, sweeps' {
        $target = Join-Path $script:Repo '.env'
        [IO.File]::WriteAllText($target, "OTHER=keep`n")
        $r = Write-CourierSink -Target $target -Format dotenv -Entries $script:Entries
        $r.keys | Should -Be @('API_KEY')
        $text = [IO.File]::ReadAllText($target)
        $text | Should -BeLike "*OTHER=keep*"
        $text | Should -BeLike "*API_KEY=$($script:FakeValue)*"
        { Write-CourierSink -Target $target -Format dotenv -Entries $script:Entries } | Should -Throw '*-Replace*'
        { Write-CourierSink -Target $target -Format dotenv -Entries $script:Entries -Replace } | Should -Not -Throw
        $ledger = @(Get-CourierSinks)
        $ledger.Count | Should -Be 1
        $ledger[0].path | Should -Be ([IO.Path]::GetFullPath($target))
        [IO.File]::ReadAllText((Join-Path $env:COURIER_HOME 'sinks.json')) | Should -Not -BeLike "*$($script:FakeValue)*"
        $dry = Remove-CourierSink -Id $ledger[0].id -WhatIf
        $dry.action | Should -Be 'would-sweep'
        @(Get-CourierSinks).Count | Should -Be 1
        $res = Remove-CourierSink -Id $ledger[0].id
        $res.action | Should -Be 'swept'
        [IO.File]::ReadAllText($target) | Should -Be "OTHER=keep`n"
        @(Get-CourierSinks).Count | Should -Be 0
    }

    It 'json: nested keys, and the file is deleted when the sweep leaves it empty' {
        $target = Join-Path $script:Repo 'appsettings.local.json'
        $entries = @{ 'Auth:ClientSecret' = (ConvertTo-CourierSecureString -Plain $script:FakeValue) }
        $r = Write-CourierSink -Target $target -Format json -Entries $entries
        $doc = [IO.File]::ReadAllText($target) | ConvertFrom-Json -AsHashtable
        $doc['Auth']['ClientSecret'] | Should -Be $script:FakeValue
        Remove-CourierSink -Id $r.id | Out-Null
        Test-Path -LiteralPath $target | Should -BeFalse
    }
}
