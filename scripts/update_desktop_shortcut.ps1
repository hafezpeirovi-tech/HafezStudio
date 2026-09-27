$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$appDirectory = Join-Path $projectRoot 'release-upscale-candidate-20260927-03\win-unpacked'
$appExe = Join-Path $appDirectory 'Hafez Studio.exe'
if (-not (Test-Path -LiteralPath $appExe -PathType Leaf)) { throw 'Updated application is missing.' }
$desktopDirectory = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktopDirectory 'Hafez Studio.lnk'
$backupDirectory = Join-Path $projectRoot ('backups\desktop-shortcut-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backupDirectory -ErrorAction Stop | Out-Null
if (Test-Path -LiteralPath $shortcutPath) {
    Copy-Item -LiteralPath $shortcutPath -Destination (Join-Path $backupDirectory 'Hafez Studio.lnk')
}
$shellObject = New-Object -ComObject WScript.Shell
$shortcut = $shellObject.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $appExe
$shortcut.WorkingDirectory = $appDirectory
$shortcut.Arguments = ''
$shortcut.Description = 'Hafez Studio - YouTube, Reels, Podcast and independent local Upscale'
$shortcut.IconLocation = "$appExe,0"
$shortcut.Save()
$verified = $shellObject.CreateShortcut($shortcutPath)
if ($verified.TargetPath -ne $appExe -or $verified.WorkingDirectory -ne $appDirectory) {
    throw 'Shortcut verification failed. Previous link is preserved in the backup.'
}
[pscustomobject]@{Shortcut=$shortcutPath; Target=$verified.TargetPath; Backup=$backupDirectory; Verified=$true} | ConvertTo-Json
