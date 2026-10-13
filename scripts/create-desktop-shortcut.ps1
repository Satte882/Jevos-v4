# Desktop-Verknüpfung zum lokalen Browser-Launcher (nur Windows).
param([switch]$Force)
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$script = Join-Path $root "scripts\launch-ui.ps1"
$desktop = [Environment]::GetFolderPath("DesktopDirectory")
$shortcutPath = Join-Path $desktop "Jevos - KI-Assistent.lnk"
if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
    throw "Launcher fehlt: $script"
}
if ((Test-Path -LiteralPath $shortcutPath) -and -not $Force) {
    throw "Desktop-Verknuepfung existiert bereits: $shortcutPath. Fuer ein Update -Force angeben."
}
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut($shortcutPath)
$link.TargetPath = Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"
$link.Arguments = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $script + '" -View inbox'
$link.WorkingDirectory = $root
$link.Description = "Jevos Inbox-Assistent und Textbereinigung im Browser öffnen"
$link.Save()
Write-Host "Desktop-Verknuepfung erstellt: $shortcutPath"
