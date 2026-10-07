$ErrorActionPreference = 'Stop'
$report = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Jeeves-Document-Handoff-Setup.txt'
$root = Join-Path $env:LOCALAPPDATA 'hermes'
$runtime = Join-Path $root 'hermes-agent'
$python = Join-Path $runtime 'venv\Scripts\python.exe'
$started = $false
try {
    Start-Transcript -LiteralPath $report -Force | Out-Null
    $started = $true
    Write-Host '=== DOCUMENT HANDOFF SETUP - NO MODEL CALL OR DISPATCH ==='
    if (!(Test-Path -LiteralPath $python -PathType Leaf)) { throw "Python missing: $python" }

    # Hermes consumes --profile before managed-interpreter relaunch, so the
    # listening child need not retain that flag. Effective Jeeves configuration
    # is verified by preparation; API launches enforce the selected profile.
    # Only restart the existing native browser dashboard owned by this user.
    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort 9119 -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique)
    if ($listeners.Count -ne 1) { throw 'Expected one existing browser dashboard on port 9119. Nothing changed.' }
    $dashboardPid = [int]$listeners[0]
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$dashboardPid"
    if (!$process -or $process.Name -notmatch '^python(w)?\.exe$' -or
        $process.CommandLine -notmatch 'hermes_cli\.main' -or
        $process.CommandLine -notmatch '\bdashboard\b' -or
        !$process.ExecutablePath.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Port 9119 is not the reviewed Jeeves browser dashboard. Nothing changed.'
    }
    $owner = Invoke-CimMethod -InputObject $process -MethodName GetOwner
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    if ($owner.ReturnValue -ne 0 -or ($owner.Domain + '\' + $owner.User) -ine $identity) {
        throw 'Dashboard process belongs to another account. Nothing changed.'
    }
    $ancestorId = $process.ParentProcessId
    for ($level = 0; $level -lt 12 -and $ancestorId -gt 0; $level++) {
        $ancestor = Get-CimInstance Win32_Process -Filter "ProcessId=$ancestorId"
        if (!$ancestor) { break }
        if ($ancestor.Name -ieq 'Hermes.exe') {
            throw 'This dashboard is Desktop-managed. Leave it running and return this report; no files changed.'
        }
        if ($ancestor.ParentProcessId -eq $ancestorId) { break }
        $ancestorId = $ancestor.ParentProcessId
    }
    $processCreated = $process.CreationDate

    Write-Host '=== Back up launcher and prepare the exact held card ==='
    & $python -B (Join-Path $PSScriptRoot 'prepare_document_handoff.py')
    if ($LASTEXITCODE -ne 0) { throw 'Preparation stopped. No dashboard restart performed. Return this report.' }

    Write-Host '=== Restart browser dashboard only ==='
    $current = Get-CimInstance Win32_Process -Filter "ProcessId=$dashboardPid"
    if (!$current -or $current.CreationDate -ne $processCreated) {
        throw 'Dashboard ownership changed during preparation. Card remains held; return this report.'
    }
    Stop-Process -Id $dashboardPid -ErrorAction Stop
    $deadline = (Get-Date).AddSeconds(15)
    do {
        $remaining = @(Get-NetTCPConnection -State Listen -LocalPort 9119 -ErrorAction SilentlyContinue)
        if (!$remaining.Count) { break }
        Start-Sleep -Milliseconds 250
    } while ((Get-Date) -lt $deadline)
    if ($remaining.Count) { throw 'Port 9119 is still occupied. Card remains held; no second server started.' }

    $logs = Join-Path $root ('landmarksignal-v1\dashboard-start-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $logs | Out-Null
    $launcher = Start-Process -FilePath $python -WorkingDirectory $runtime -PassThru -WindowStyle Hidden `
        -ArgumentList @('-B', '-m', 'hermes_cli.main', '--profile', 'jeeves', 'dashboard', '--skip-build', '--port', '9119', '--no-open') `
        -RedirectStandardOutput (Join-Path $logs 'stdout.log') -RedirectStandardError (Join-Path $logs 'stderr.log')
    $deadline = (Get-Date).AddSeconds(45)
    $responding = $false
    do {
        try {
            $response = Invoke-WebRequest -Uri 'http://127.0.0.1:9119/' -UseBasicParsing -TimeoutSec 2
            $responding = $response.StatusCode -eq 200
        } catch {}
        if (!$responding) { Start-Sleep -Milliseconds 500 }
    } while (!$responding -and (Get-Date) -lt $deadline)
    if (!$responding) { throw "Dashboard did not respond. Prepared card remains held. Startup logs: $logs" }
    Write-Host 'PASS: browser dashboard responds; model server and SSH tunnel were not restarted.'
    Write-Host 'NEXT: select Issue #6: Planned bot roster draft; expand Review exact task scope.'
    Write-Host 'Type APPROVE ISSUE 6 and click Approve and run when ready.'
    Write-Host 'Leave the result in Review for content inspection. No bots are created by this task.'
    Start-Process 'http://127.0.0.1:9119/kanban?profile=jeeves'
} finally {
    if ($started) { Stop-Transcript | Out-Null }
    if (Test-Path -LiteralPath $report) {
        Write-Host "Report: $report"
        Start-Process explorer.exe -ArgumentList ('/select,"{0}"' -f $report)
    }
}
