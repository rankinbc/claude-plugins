# Ops.Tests.ps1 - the STATUS contract of every op, run as a separate pwsh (the way the bridge runs them), against a
# fake home. Output never contains the fake value.
Describe 'ops/*.ps1' {
    BeforeAll {
        $script:Root = Split-Path $PSScriptRoot -Parent
        $script:Ops = Join-Path $script:Root 'ops'
        $script:SavedHome = $env:COURIER_HOME
        $env:COURIER_HOME = Join-Path $TestDrive 'home'
        Import-Module (Join-Path $script:Root 'Courier.psm1') -Force
        $script:Name = "pester-ops-$([Guid]::NewGuid().ToString('N').Substring(0, 12))"
        $script:FakeValue = 'pester-fake-value-11'
        Set-CourierStoreValue -Store dpapi -Name $script:Name -Value (ConvertTo-CourierSecureString -Plain $script:FakeValue)
        $script:Run = {
            param([string]$Op, [string[]]$ArgList)
            $out = & pwsh -NoProfile -NonInteractive -File (Join-Path $script:Ops "$Op.ps1") @ArgList 2>&1 | Out-String
            [pscustomobject]@{ out = $out; status = (($out -split "`r?`n") | Where-Object { $_ -like 'STATUS *' } | Select-Object -Last 1); code = $LASTEXITCODE }
        }
    }
    AfterAll {
        foreach ($store in @('dpapi', 'credman')) { try { Remove-CourierStoreValue -Store $store -Name $script:Name | Out-Null } catch {} }
        try { Remove-CourierStoreValue -Store credman -Name "$($script:Name)-copy" | Out-Null } catch {}
        if ($null -ne $script:SavedHome) { $env:COURIER_HOME = $script:SavedHome } else { Remove-Item Env:COURIER_HOME -ErrorAction SilentlyContinue }
        Import-Module (Join-Path $script:Root 'Courier.psm1') -Force
    }

    It 'exists: found / missing' {
        $r = & $script:Run 'secret-exists' @($script:Name)
        $r.status | Should -Be 'STATUS found dpapi'
        $r.out | Should -BeLike "*is held in the DPAPI file store*"
        $r.out | Should -BeLike "*was not read*"
        (& $script:Run 'secret-exists' @('pester-absent-name')).status | Should -Be 'STATUS missing'
        (& $script:Run 'secret-exists' @('Bad Name')).status | Should -BeLike 'STATUS error*'
    }

    It 'names: lists the name with its store, never the value' {
        $r = & $script:Run 'secret-names' @()
        $r.out | Should -BeLike "*$($script:Name) dpapi*"
        $r.out | Should -Not -BeLike "*$($script:FakeValue)*"
        $r.status | Should -BeLike 'STATUS listed *'
    }

    It 'copy: dpapi to credman, no overwrite without -Replace, env never a destination' {
        $copy = "$($script:Name)-copy"
        (& $script:Run 'secret-copy' @("dpapi:$($script:Name)", "credman:$copy")).status | Should -Be 'STATUS stored credman'
        (& $script:Run 'secret-copy' @("dpapi:$($script:Name)", "credman:$copy")).status | Should -BeLike 'STATUS error*-Replace*'
        (& $script:Run 'secret-copy' @("dpapi:$($script:Name)", "env:X")).status | Should -BeLike 'STATUS error*read-only*'
        (& $script:Run 'secret-copy' @("dpapi:pester-absent-name", "credman:other")).status | Should -Be 'STATUS missing'
        (ConvertFrom-CourierSecureString -Secure (Get-CourierStoreValue -Store credman -Name $copy)) | Should -Be $script:FakeValue
        (& $script:Run 'secret-remove' @("credman:$copy")).status | Should -Be 'STATUS removed credman'
        (& $script:Run 'secret-remove' @("credman:$copy")).status | Should -Be 'STATUS missing'
    }

    It 'prompt: refuses a non-interactive host before touching the store' {
        $r = & $script:Run 'secret-prompt' @('pester-prompt-name')
        $r.status | Should -BeLike 'STATUS error*interactively*'
        Get-CourierStoreExists -Store dpapi -Name 'pester-prompt-name' | Should -BeFalse
    }

    It 'test: refuses a non-https endpoint and reports missing without a network call' {
        (& $script:Run 'secret-test' @($script:Name, '-Url', 'http://example.com')).status | Should -BeLike 'STATUS error*https*'
        (& $script:Run 'secret-test' @('pester-absent-name', '-Url', 'https://example.invalid/')).status | Should -Be 'STATUS missing'
    }

    It 'run: the value reaches only the child environment' {
        $b64 = { param($o) [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($o | ConvertTo-Json -Compress))) }
        $envSpec = & $b64 @{ PESTER_SECRET = "dpapi:$($script:Name)" }
        $cmdSpec = & $b64 @('pwsh', '-NoProfile', '-Command', 'if ($env:PESTER_SECRET.Length -eq 20) { exit 7 } else { exit 3 }')
        $r = & $script:Run 'secret-run' @('-EnvSpec', $envSpec, '-CommandSpec', $cmdSpec)
        $r.status | Should -Be 'STATUS exit 7'
        $env:PESTER_SECRET | Should -BeNullOrEmpty
        $r.out | Should -Not -BeLike "*$($script:FakeValue)*"
    }

    It 'inject and sweep: a git-ignored dotenv sink, ledgered, then removed' {
        $repo = Join-Path $TestDrive 'repo-ops'
        New-Item -ItemType Directory -Path $repo -Force | Out-Null
        & git -C $repo init -q
        [IO.File]::WriteAllText((Join-Path $repo '.gitignore'), ".env`n")
        $target = Join-Path $repo '.env'
        $r = & $script:Run 'secret-inject' @('-Target', $target, '-Format', 'dotenv', '-Map', "API_KEY=dpapi:$($script:Name)")
        $r.status | Should -BeLike 'STATUS stored *keys=1'
        $r.out | Should -Not -BeLike "*$($script:FakeValue)*"
        $r.out | Should -BeLike "*courier sweep --id *"
        [IO.File]::ReadAllText($target) | Should -BeLike "*API_KEY=$($script:FakeValue)*"
        (& $script:Run 'secret-sinks' @()).out | Should -BeLike "*dotenv *.env keys=API_KEY*"
        (& $script:Run 'secret-sweep' @('-WhatIf')).status | Should -Be 'STATUS listed 1'
        Test-Path -LiteralPath $target | Should -BeTrue
        (& $script:Run 'secret-sweep' @()).status | Should -Be 'STATUS swept 1'
        Test-Path -LiteralPath $target | Should -BeFalse
        (& $script:Run 'secret-sinks' @()).status | Should -Be 'STATUS listed 0'
    }
}
