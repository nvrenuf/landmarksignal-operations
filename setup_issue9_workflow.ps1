$ErrorActionPreference = 'Stop'
$report = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Jeeves-Issue9-Workflow-Setup.txt'
$root = Join-Path $env:LOCALAPPDATA 'hermes'
$runtime = Join-Path $root 'hermes-agent'
$python = Join-Path $runtime 'venv\Scripts\python.exe'
$transcribing = $false
try {
    Start-Transcript -LiteralPath $report -Force | Out-Null
    $transcribing = $true
    Write-Host '=== JEEVES ISSUE 9 WORKFLOW CORRECTIONS ==='
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
    & $python -B (Join-Path $PSScriptRoot 'test_issue9_workflow.py')
    if ($LASTEXITCODE -ne 0) { throw 'Native tool checks failed. Nothing installed.' }
    Write-Host 'Windows will request administrator approval for the protected policy update only.'
    $maintenance = Join-Path $PSScriptRoot 'install_issue9_workflow_admin.ps1'
    $admin = Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') `
        -Verb RunAs -Wait -PassThru -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass',
            '-File', ('"' + $maintenance + '"'), '-ExpectedUserSid', $identity.User.Value)
    $adminReport = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Jeeves-Issue9-Workflow-Admin.txt'
    if (Test-Path -LiteralPath $adminReport) { Get-Content -LiteralPath $adminReport | Write-Host }
    if ($admin.ExitCode -ne 0) { throw 'Elevated policy repair stopped. Dashboard left running; return the reports.' }
    & $python -B (Join-Path $PSScriptRoot 'verify_issue9_hooks.py')
    if ($LASTEXITCODE -ne 0) { throw 'Installed hook verification stopped. Return the report.' }
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
    Write-Host 'Ready launches work. Worker output must go to Review; Lee completes from the dashboard.'
    Write-Host 'Open a fresh Jeeves browser chat. Native tools use the existing Hermes approval settings.'
    Start-Process 'http://127.0.0.1:9119/jeeves-launch?profile=jeeves'
} catch {
    Write-Host ('STOPPED: ' + $_.Exception.Message)
    throw
} finally {
    if ($transcribing) { Stop-Transcript | Out-Null }
    Write-Host "Report: $report"
}
