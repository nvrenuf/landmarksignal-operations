param([switch]$Maintenance, [string]$ExpectedUserSid)
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$isAdmin = ([Security.Principal.WindowsPrincipal]$identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$hermesRoot = Join-Path $env:LOCALAPPDATA 'hermes'
$python = Join-Path $hermesRoot 'hermes-agent\venv\Scripts\python.exe'
if (!$Maintenance) {
    if ($isAdmin) { throw 'Run setup as normal Lee. Only protected file maintenance is elevated.' }
    & $python -B (Join-Path $PSScriptRoot 'run_github_projects_checks.py')
    if ($LASTEXITCODE -ne 0) { throw 'Fixture checks failed; nothing installed.' }
    & $python -B (Join-Path $PSScriptRoot 'install_github_projects.py')
    $installExit = $LASTEXITCODE
    if ($installExit -eq 13) {
      $maintenanceProcess = Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') `
        -Verb RunAs -WindowStyle Hidden -Wait -PassThru -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', ('"' + $PSCommandPath + '"'), '-Maintenance', '-ExpectedUserSid', $identity.User.Value)
      $installExit = $maintenanceProcess.ExitCode
    }
    if ($installExit -ne 0) { throw 'Launcher maintenance failed. See the github-projects recovery report.' }
    & $python -B (Join-Path $PSScriptRoot 'verify_github_projects.py')
    if ($LASTEXITCODE -ne 0) { throw 'Installed normal-user verification failed.' }
    Write-Host 'PASS: install verified. Reload only the independently verified idle standalone dashboard to load the new API.'
    exit 0
}
if (!$isAdmin -or $identity.User.Value -ne $ExpectedUserSid) { throw 'Maintenance requires the same Lee account elevated.' }
$manifest = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'github_projects_assets.json') | ConvertFrom-Json
$backup = Join-Path $hermesRoot ('landmarksignal-v1\recovery\github-projects-acls-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $backup | Out-Null
$originalAcls = @{}
$directoryAcls = @{}
$newPaths = @()
foreach ($entry in $manifest) {
    $target = Join-Path $hermesRoot $entry.target
    if (Test-Path -LiteralPath $target) { $originalAcls[$target] = Get-Acl -LiteralPath $target }
    else { $newPaths += $target }
    $directory = Split-Path -Parent $target
    $directoryAcls[$directory] = (Get-Acl -LiteralPath $directory).Sddl
}
$saved = @{}
foreach ($target in $originalAcls.Keys) { $saved[$target] = $originalAcls[$target].Sddl }
$saved | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $backup 'file-acls.before.json') -Encoding UTF8
$directoryAcls | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $backup 'directory-acls.before.json') -Encoding UTF8
$failed = $false
try {
    # A child interpreter may be selected by managed bootstrap. Wait for it and capture only installer output.
    $installer = Start-Process -FilePath $python -Wait -PassThru -WindowStyle Hidden `
        -ArgumentList @('-B', ('"' + (Join-Path $PSScriptRoot 'install_github_projects.py') + '"')) `
        -RedirectStandardOutput (Join-Path $backup 'install.stdout.txt') -RedirectStandardError (Join-Path $backup 'install.stderr.txt')
    if ($installer.ExitCode -ne 0) { throw 'Focused launcher installer failed.' }
} catch {
    $failed = $true
    $_.Exception.Message | Set-Content -LiteralPath (Join-Path $backup 'error.txt')
} finally {
    foreach ($target in $originalAcls.Keys) {
        try {
            if ((Get-Acl -LiteralPath $target).Sddl -ne $originalAcls[$target].Sddl) {
                Set-Acl -LiteralPath $target -AclObject $originalAcls[$target]
            }
            if ((Get-Acl -LiteralPath $target).Sddl -ne $originalAcls[$target].Sddl) { throw 'Original file ACL differs.' }
        } catch { $failed = $true }
    }
    foreach ($target in $newPaths) {
        if (Test-Path -LiteralPath $target) {
            try {
                $acl = Get-Acl -LiteralPath $target
                $rule = [Security.AccessControl.FileSystemAccessRule]::new(
                    [Security.Principal.SecurityIdentifier]::new($ExpectedUserSid),
                    [Security.AccessControl.FileSystemRights]::ReadAndExecute,
                    [Security.AccessControl.AccessControlType]::Allow)
                $acl.AddAccessRule($rule) | Out-Null
                Set-Acl -LiteralPath $target -AclObject $acl
            } catch { $failed = $true }
        }
    }
    foreach ($directory in $directoryAcls.Keys) {
        if ((Get-Acl -LiteralPath $directory).Sddl -ne $directoryAcls[$directory]) { $failed = $true }
    }
    if (!$failed) { 'PASS: original file/directory protections preserved; new helper grants Lee read/execute.' | Set-Content -LiteralPath (Join-Path $backup 'result.txt') }
}
if ($failed) { exit 1 }
exit 0
