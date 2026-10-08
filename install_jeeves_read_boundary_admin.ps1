param([Parameter(Mandatory=$true)][string]$ExpectedUserSid)
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if ($identity.User.Value -ne $ExpectedUserSid -or
    !$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error 'Maintenance requires elevated Lee identity; no other account may install it.'
    exit 1
}
$report = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Jeeves-Read-Boundary-Admin.txt'
$root = Join-Path $env:LOCALAPPDATA 'hermes'
$profile = Join-Path $root 'profiles\jeeves'
$python = Join-Path $root 'hermes-agent\venv\Scripts\python.exe'
$acls = @{}
$directoryAcls = @{}
$failed = $false
$logDirectory = Join-Path $root ('landmarksignal-v1\recovery\read-admin-' + [guid]::NewGuid().ToString('N'))
$transcribing = $false
try {
    Start-Transcript -LiteralPath $report -Force | Out-Null
    $transcribing = $true
    $paths = @(Join-Path $profile 'plugins\landmarksignal-execution\policy.py')
    foreach ($home in @($root, $profile)) {
        $copy = Join-Path $home 'plugins\landmarksignal-launch\dashboard\runner\landmarksignal_policy.py'
        if (Test-Path -LiteralPath $copy -PathType Leaf) { $paths += $copy }
    }
    foreach ($path in $paths) {
        $acls[$path] = Get-Acl -LiteralPath $path
        $directory = Split-Path -Parent $path
        $directoryAcls[$directory] = (Get-Acl -LiteralPath $directory).Sddl
    }
    New-Item -ItemType Directory -Path $logDirectory | Out-Null
    $securityBackup = @{}
    foreach ($path in $acls.Keys) { $securityBackup[$path] = $acls[$path].Sddl }
    $securityBackup | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $logDirectory 'file-acls.before.json') -Encoding UTF8
    Write-Host '=== Elevated maintenance: policy files only ==='
    $helper = Join-Path $PSScriptRoot 'repair_jeeves_read_boundary.py'
    $installation = Start-Process -FilePath $python -Wait -PassThru -NoNewWindow `
        -ArgumentList @('-B', ('"' + $helper + '"')) `
        -RedirectStandardOutput (Join-Path $logDirectory 'stdout.txt') `
        -RedirectStandardError (Join-Path $logDirectory 'stderr.txt')
    Get-Content -LiteralPath (Join-Path $logDirectory 'stdout.txt') | Write-Host
    Get-Content -LiteralPath (Join-Path $logDirectory 'stderr.txt') | Write-Host
    if ($installation.ExitCode -ne 0) { throw "Policy installer exit code: $($installation.ExitCode)" }
} catch {
    $failed = $true
    Write-Host ('STOPPED: ' + $_.Exception.Message)
} finally {
    foreach ($path in $acls.Keys) {
        try {
            # Replacement creates a new file. Restore its exact previous owner/DACL.
            if ((Get-Acl -LiteralPath $path).Sddl -ne $acls[$path].Sddl) {
                Set-Acl -LiteralPath $path -AclObject $acls[$path]
            }
            if ((Get-Acl -LiteralPath $path).Sddl -ne $acls[$path].Sddl) {
                throw "File protection differs after maintenance: $path"
            }
        } catch {
            $failed = $true
            Write-Host ('ACL VERIFICATION FAILED: ' + $_.Exception.Message)
        }
    }
    foreach ($directory in $directoryAcls.Keys) {
        if ((Get-Acl -LiteralPath $directory).Sddl -ne $directoryAcls[$directory]) {
            $failed = $true
            Write-Host "DIRECTORY ACL CHANGED: $directory"
        }
    }
    if (!$failed) { Write-Host 'PASS: original file and directory protections preserved.' }
    Write-Host 'No Hermes runtime, dashboard, model, task or SSH tunnel was launched by this elevated step.'
    if ($transcribing) { Stop-Transcript | Out-Null }
}
if ($failed) { exit 1 }
exit 0
