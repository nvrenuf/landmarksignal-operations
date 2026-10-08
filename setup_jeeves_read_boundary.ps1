param([string]$InstalledAclBackup)
$ErrorActionPreference = 'Stop'
$report = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Jeeves-Read-Boundary-Repair.txt'
$root = Join-Path $env:LOCALAPPDATA 'hermes'
$runtime = Join-Path $root 'hermes-agent'
$python = Join-Path $runtime 'venv\Scripts\python.exe'
$transcribing = $false
try {
    Start-Transcript -LiteralPath $report -Force | Out-Null
    $transcribing = $true
    Write-Host '=== JEEVES CARD READ / BLOCKER REPORT REPAIR ==='
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Run this setup in regular PowerShell. Only the maintenance installer is elevated.'
    }
    if (!(Test-Path -LiteralPath $python -PathType Leaf)) { throw "Python not found: $python" }
    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort 9119 -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique)
    if ($listeners.Count -ne 1) { throw 'Expected one existing browser dashboard on port 9119. Nothing changed.' }
    $dashboardPid = [int]$listeners[0]
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$dashboardPid"
    if (!$process -or $process.Name -notmatch '^python(w)?\.exe$' -or
        $process.CommandLine -notmatch 'hermes_cli\.main' -or
        $process.CommandLine -notmatch '\bdashboard\b' -or
        !$process.ExecutablePath.StartsWith(($root + '\'), [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Port 9119 is not the previously reviewed standalone dashboard. Nothing changed.'
    }
    $owner = Invoke-CimMethod -InputObject $process -MethodName GetOwner
    if ($owner.ReturnValue -ne 0 -or ($owner.Domain + '\' + $owner.User) -ine
        [Security.Principal.WindowsIdentity]::GetCurrent().Name) {
        throw 'Dashboard is owned by another account. Nothing changed.'
    }
    $ancestorId = $process.ParentProcessId
    for ($level = 0; $level -lt 12 -and $ancestorId -gt 0; $level++) {
        $ancestor = Get-CimInstance Win32_Process -Filter "ProcessId=$ancestorId"
        if (!$ancestor) { break }
        if ($ancestor.Name -ieq 'Hermes.exe') { throw 'Dashboard is Desktop-managed. Nothing changed.' }
        if ($ancestor.ParentProcessId -eq $ancestorId) { break }
        $ancestorId = $ancestor.ParentProcessId
    }
    $processCreated = $process.CreationDate
    Write-Host '=== Verify read access and continued execution denial ==='
    & $python -B (Join-Path $PSScriptRoot 'test_jeeves_read_boundary.py')
    if ($LASTEXITCODE -ne 0) { throw 'Boundary checks failed. No installation performed.' }
    Write-Host '=== Back up and install inspected policy correction ==='
    if ($InstalledAclBackup) {
        $expectedBackupRoot = Join-Path $root 'landmarksignal-v1\recovery'
        $backupItem = Get-Item -LiteralPath $InstalledAclBackup -ErrorAction Stop
        if (!$backupItem.PSIsContainer -or $backupItem.Parent.FullName -ine $expectedBackupRoot -or
            $backupItem.Name -notmatch '^read-admin-[a-f0-9]{32}$') {
            throw 'Unexpected saved ACL backup location. Nothing changed.'
        }
        $savedSecurity = Get-Content -Raw -LiteralPath (Join-Path $backupItem.FullName 'file-acls.before.json') | ConvertFrom-Json
        $expectedPaths = @(Join-Path $root 'profiles\jeeves\plugins\landmarksignal-execution\policy.py')
        foreach ($profileDirectory in @($root, (Join-Path $root 'profiles\jeeves'))) {
            $copy = Join-Path $profileDirectory 'plugins\landmarksignal-launch\dashboard\runner\landmarksignal_policy.py'
            if (Test-Path -LiteralPath $copy -PathType Leaf) { $expectedPaths += $copy }
        }
        $sourceText = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'landmarksignal_policy.py'), [Text.Encoding]::UTF8).Replace("`r`n", "`n")
        if (@($savedSecurity.PSObject.Properties).Count -ne $expectedPaths.Count) {
            throw 'Saved security snapshot does not cover exactly the installed policy copies.'
        }
        foreach ($path in $expectedPaths) {
            $before = $savedSecurity.PSObject.Properties[$path].Value
            $after = (Get-Acl -LiteralPath $path).Sddl
            # Accept only the observed auto-inherited DACL control flag difference.
            # Owner, group, protected flags, ACE order, principals and rights remain exact.
            if (!$before -or $before.Replace('D:AI(', 'D:(') -cne $after.Replace('D:AI(', 'D:(')) {
                throw "Actual security difference remains: $path"
            }
            if ([IO.File]::ReadAllText($path, [Text.Encoding]::UTF8).Replace("`r`n", "`n") -cne $sourceText) {
                throw "Installed policy content differs: $path"
            }
        }
        Write-Host 'PASS: installed contents and saved permissions match; only the observed AI flag is normalized.'
        & $python -B (Join-Path $PSScriptRoot 'repair_jeeves_read_boundary.py')
        if ($LASTEXITCODE -ne 0) { throw 'Installed policy verification stopped. Dashboard left running.' }
    } else {
    Write-Host 'Windows will request administrator approval for the protected policy update only.'
    $maintenance = Join-Path $PSScriptRoot 'install_jeeves_read_boundary_admin.ps1'
    $admin = Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') `
        -Verb RunAs -Wait -PassThru -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass',
            '-File', ('"' + $maintenance + '"'), '-ExpectedUserSid', $identity.User.Value)
    $adminReport = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Jeeves-Read-Boundary-Admin.txt'
    if (Test-Path -LiteralPath $adminReport) { Get-Content -LiteralPath $adminReport | Write-Host }
    if ($admin.ExitCode -ne 0) { throw 'Elevated policy repair stopped. Dashboard left running; return the reports.' }
    }
    Write-Host '=== Reload existing standalone browser dashboard ==='
    $current = Get-CimInstance Win32_Process -Filter "ProcessId=$dashboardPid"
    if (!$current -or $current.CreationDate -ne $processCreated) {
        throw 'Dashboard process changed during repair. Files installed; reload remains pending.'
    }
    Stop-Process -Id $dashboardPid -ErrorAction Stop
    $deadline = (Get-Date).AddSeconds(15)
    do {
        $remaining = @(Get-NetTCPConnection -State Listen -LocalPort 9119 -ErrorAction SilentlyContinue)
        if (!$remaining.Count) { break }
        Start-Sleep -Milliseconds 250
    } while ((Get-Date) -lt $deadline)
    if ($remaining.Count) { throw 'Port 9119 remains occupied. No second server started.' }
    $logs = Join-Path $root ('landmarksignal-v1\read-repair-dashboard-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $logs | Out-Null
    $launcher = Start-Process -FilePath $python -WorkingDirectory $runtime -PassThru -WindowStyle Hidden `
        -ArgumentList @('-B', '-m', 'hermes_cli.main', '--profile', 'jeeves', 'dashboard', '--skip-build', '--port', '9119', '--no-open') `
        -RedirectStandardOutput (Join-Path $logs 'stdout.log') -RedirectStandardError (Join-Path $logs 'stderr.log')
    $deadline = (Get-Date).AddSeconds(45)
    $responding = $false
    do {
        try {
            $response = Invoke-WebRequest 'http://127.0.0.1:9119/' -UseBasicParsing -TimeoutSec 2
            $responding = $response.StatusCode -eq 200
        } catch {}
        if (!$responding) { Start-Sleep -Milliseconds 500 }
    } while (!$responding -and (Get-Date) -lt $deadline)
    if (!$responding) { throw "Dashboard reload incomplete. Startup logs: $logs" }
    Write-Host 'PASS: browser dashboard responds. This is availability, not a worker acceptance test.'
    Write-Host 'No model server, SSH tunnel, Desktop app, or gateway was restarted.'
    Write-Host 'No tasks retried or approved. Keep the two Issue 9 cards Blocked.'
    Write-Host 'Remaining: verify an approved native execution entry before moving cards to Ready.'
    Start-Process 'http://127.0.0.1:9119/kanban?profile=jeeves'
} catch {
    Write-Host ('STOPPED: ' + $_.Exception.Message)
    throw
} finally {
    if ($transcribing) { Stop-Transcript | Out-Null }
    Write-Host "Report: $report"
}
