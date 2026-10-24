# Courier.Tests.ps1 - the core module against a FAKE home ($env:COURIER_HOME under $TestDrive) and a pester-only
# Credential Manager target. Every name and value is fake.
Describe 'Courier.psm1' {
    BeforeAll {
        $script:Root = Split-Path $PSScriptRoot -Parent
        $script:SavedHome = $env:COURIER_HOME
        $env:COURIER_HOME = Join-Path $TestDrive 'home'
        Import-Module (Join-Path $script:Root 'Courier.psm1') -Force
        $script:Name = "pester-fake-$([Guid]::NewGuid().ToString('N').Substring(0, 12))"
        $script:FakeValue = 'pester-fake-value-7'
        $script:Secure = ConvertTo-CourierSecureString -Plain $script:FakeValue
    }
    AfterAll {
        foreach ($store in @('dpapi', 'credman')) { try { Remove-CourierStoreValue -Store $store -Name $script:Name | Out-Null } catch {} }
        if ($null -ne $script:SavedHome) { $env:COURIER_HOME = $script:SavedHome } else { Remove-Item Env:COURIER_HOME -ErrorAction SilentlyContinue }
        Import-Module (Join-Path $script:Root 'Courier.psm1') -Force
    }

    It 'validates the name grammar and maps keyring names' {
        { Test-CourierName -Name 'Bad Name' } | Should -Throw
        { Test-CourierName -Name 'ok-name.1_x' } | Should -Not -Throw
        ConvertTo-CourierKeyringName -Name 'my-api.key' | Should -Be 'MY_API_KEY'
    }

    It 'dpapi: round trip, owner-only ACL, value never in clear on disk, manifest holds names only' {
        Set-CourierStoreValue -Store dpapi -Name $script:Name -Value $script:Secure -Description 'pester' -Source 'nowhere'
        Get-CourierStoreExists -Store dpapi -Name $script:Name | Should -BeTrue
        $got = Get-CourierStoreValue -Store dpapi -Name $script:Name
        $got | Should -BeOfType [SecureString]
        (ConvertFrom-CourierSecureString -Secure $got) | Should -Be $script:FakeValue
        $storeFile = Join-Path $env:COURIER_HOME 'secrets.json'
        [IO.File]::ReadAllText($storeFile) | Should -Not -BeLike "*$($script:FakeValue)*"
        [IO.File]::ReadAllText((Join-Path $env:COURIER_HOME 'secrets.manifest.json')) | Should -BeLike "*$($script:Name)*"
        $acl = Get-Acl -Path $storeFile
        $me = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
        @($acl.Access | Where-Object { $_.IdentityReference.Value -notin @($me, 'NT AUTHORITY\SYSTEM', 'BUILTIN\Administrators') }).Count | Should -Be 0
        Find-CourierStore -Name $script:Name | Should -Be 'dpapi'
        (Get-CourierNames | Where-Object { $_.name -eq $script:Name }).stores | Should -Contain 'dpapi'
        Remove-CourierStoreValue -Store dpapi -Name $script:Name | Should -BeTrue
        Get-CourierStoreExists -Store dpapi -Name $script:Name | Should -BeFalse
        [IO.File]::ReadAllText((Join-Path $env:COURIER_HOME 'secrets.manifest.json')) | Should -Not -BeLike "*$($script:Name)*"
    }

    It 'refuses to overwrite without -Replace and refuses an empty value' {
        Set-CourierStoreValue -Store dpapi -Name $script:Name -Value $script:Secure
        { Set-CourierStoreValue -Store dpapi -Name $script:Name -Value $script:Secure } | Should -Throw '*-Replace*'
        { Set-CourierStoreValue -Store dpapi -Name $script:Name -Value $script:Secure -Replace } | Should -Not -Throw
        { Set-CourierStoreValue -Store dpapi -Name 'empty-one' -Value (New-Object System.Security.SecureString) } | Should -Throw '*empty*'
        Remove-CourierStoreValue -Store dpapi -Name $script:Name | Out-Null
    }

    It 'credman: write, exists, read and remove on a pester-only target' {
        Set-CourierStoreValue -Store credman -Name $script:Name -Value $script:Secure
        Get-CourierStoreExists -Store credman -Name $script:Name | Should -BeTrue
        (ConvertFrom-CourierSecureString -Secure (Get-CourierStoreValue -Store credman -Name $script:Name)) | Should -Be $script:FakeValue
        Remove-CourierStoreValue -Store credman -Name $script:Name | Should -BeTrue
        Get-CourierStoreExists -Store credman -Name $script:Name | Should -BeFalse
    }

    It 'env and keyvault are sources only' {
        $envName = 'COURIER_PESTER_FAKE_SOURCE'
        try {
            Set-Item -Path "Env:$envName" -Value $script:FakeValue
            Get-CourierStoreExists -Store env -Name $envName | Should -BeTrue
            (ConvertFrom-CourierSecureString -Secure (Get-CourierStoreValue -Store env -Name $envName)) | Should -Be $script:FakeValue
            { Set-CourierStoreValue -Store env -Name $envName -Value $script:Secure } | Should -Throw '*read-only*'
            { Set-CourierStoreValue -Store keyvault -Name 'vault/name' -Value $script:Secure } | Should -Throw '*read-only*'
        } finally { Remove-Item -Path "Env:$envName" -ErrorAction SilentlyContinue }
        Find-CourierStore -Name 'pester-absent-name' | Should -BeNullOrEmpty
    }

    It 'Assert-CourierInteractive and a keyvault read refuse a non-interactive host' {
        $mod = Join-Path $script:Root 'Courier.psm1'
        $out = & pwsh -NoProfile -NonInteractive -Command "Import-Module '$mod' -Force; Assert-CourierInteractive -Reason 'pester'" 2>&1 | Out-String
        $LASTEXITCODE | Should -Not -Be 0
        $out | Should -BeLike '*interactively*'
        $out = & pwsh -NoProfile -NonInteractive -Command "Import-Module '$mod' -Force; Get-CourierStoreValue -Store keyvault -Name 'pester-vault/pester-name'" 2>&1 | Out-String
        $out | Should -BeLike '*interactively*'
    }

    It 'audit lines carry names and statuses only' {
        Write-CourierAudit -Op 'pester' -Status 'ok' -Detail $script:Name
        $line = (Get-Content -Path (Join-Path $env:COURIER_HOME 'audit.jsonl') | Select-Object -Last 1) | ConvertFrom-Json
        $line.op | Should -Be 'pester'
        $line.detail | Should -Be $script:Name
    }
}
