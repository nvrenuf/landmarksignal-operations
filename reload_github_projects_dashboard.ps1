$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
if (([Security.Principal.WindowsPrincipal]$identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Dashboard must run as normal Lee, not administrator.'
}
$hermesRoot = Join-Path $env:LOCALAPPDATA 'hermes'
$runtime = Join-Path $hermesRoot 'hermes-agent'
$python = Join-Path $runtime 'venv\Scripts\python.exe'
$listeners = @(Get-NetTCPConnection -State Listen -LocalPort 9119 | Select-Object -ExpandProperty OwningProcess -Unique)
if ($listeners.Count -ne 1) { throw 'Expected exactly one existing dashboard listener.' }
$dashboardPid = [int]$listeners[0]
$process = Get-CimInstance Win32_Process -Filter "ProcessId=$dashboardPid"
if (!$process -or $process.Name -notmatch '^python(w)?\.exe$' -or
    $process.CommandLine -notmatch 'hermes_cli\.main' -or $process.CommandLine -notmatch '\bdashboard\b' -or
    !$process.ExecutablePath.StartsWith(($hermesRoot + '\'), [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Listener is not the standalone Hermes dashboard.'
}
$owner = Invoke-CimMethod -InputObject $process -MethodName GetOwner
if ($owner.ReturnValue -ne 0 -or ($owner.Domain + '\' + $owner.User) -ine $identity.Name) { throw 'Dashboard belongs to another account.' }
$ancestorId = $process.ParentProcessId
for ($i=0; $i -lt 12 -and $ancestorId -gt 0; $i++) {
    $ancestor = Get-CimInstance Win32_Process -Filter "ProcessId=$ancestorId"
    if (!$ancestor) { break }
    if ($ancestor.Name -ieq 'Hermes.exe') { throw 'Desktop-managed dashboard must not be restarted.' }
    if ($ancestor.ParentProcessId -eq $ancestorId) { break }
    $ancestorId = $ancestor.ParentProcessId
}
$probe = @'
import sqlite3,sys
from pathlib import Path
from contextlib import closing
root=Path(sys.argv[1])
with closing(sqlite3.connect((root/'kanban/boards/landmarksignal/kanban.db').as_uri()+'?mode=ro',uri=True)) as c:
    assert not c.execute("SELECT count(*) FROM tasks WHERE status='running' OR worker_pid IS NOT NULL OR claim_lock IS NOT NULL").fetchone()[0], 'Active task markers'
    assert not c.execute('SELECT count(*) FROM task_runs WHERE ended_at IS NULL').fetchone()[0], 'Unfinished runs'
print('PASS: no running cards, worker markers or unfinished runs')
'@
# Standard Python is sufficient for this read-only SQLite check; no runtime bootstrap or config read.
$probe | python -B - $hermesRoot
if ($LASTEXITCODE -ne 0) { throw 'Work may be running; no reload.' }
$current = Get-CimInstance Win32_Process -Filter "ProcessId=$dashboardPid"
if (!$current -or $current.CreationDate -ne $process.CreationDate) { throw 'Dashboard process changed.' }
Stop-Process -Id $dashboardPid -ErrorAction Stop
$deadline = (Get-Date).AddSeconds(15)
do {
    $remaining = @(Get-NetTCPConnection -State Listen -LocalPort 9119 -ErrorAction SilentlyContinue)
    if (!$remaining.Count) { break }
    Start-Sleep -Milliseconds 250
} while ((Get-Date) -lt $deadline)
if ($remaining.Count) { throw 'Port remains occupied; no second server started.' }
$logs = Join-Path $hermesRoot ('landmarksignal-v1\recovery\github-projects-dashboard-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $logs | Out-Null
$launcher = Start-Process -FilePath $python -WorkingDirectory $runtime -PassThru -WindowStyle Hidden `
    -ArgumentList @('-B','-m','hermes_cli.main','--profile','jeeves','dashboard','--skip-build','--port','9119','--no-open') `
    -RedirectStandardOutput (Join-Path $logs 'stdout.log') -RedirectStandardError (Join-Path $logs 'stderr.log')
$deadline = (Get-Date).AddSeconds(45)
$responding = $false
do {
    try { $response = Invoke-WebRequest 'http://127.0.0.1:9119/' -UseBasicParsing -TimeoutSec 2; $responding = $response.StatusCode -eq 200 } catch {}
    if (!$responding) { Start-Sleep -Milliseconds 500 }
} while (!$responding -and (Get-Date) -lt $deadline)
if (!$responding) { throw "Dashboard reload incomplete. Logs: $logs" }
Write-Host "PASS: standalone dashboard reloaded as $($identity.Name). Previous listener: $dashboardPid. Logs: $logs"
