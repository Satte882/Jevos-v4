# Erstellt nur die eigene Plugin-Directory, überschreibt keine vorhandenen Plugins ohne -Force.
param([switch]$Force, [string]$VaultPath)
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$config = Get-Content -Raw -LiteralPath (Join-Path $root "config.example.json") | ConvertFrom-Json
$vault = if ($VaultPath) {
    $VaultPath
} elseif (Test-Path (Join-Path $root "config.json")) {
    (Get-Content -Raw -LiteralPath (Join-Path $root "config.json") | ConvertFrom-Json).vault
} else { $config.vault }
if (-not (Test-Path -LiteralPath $vault -PathType Container)) {
    throw "Vault nicht gefunden: $vault"
}
$target = Join-Path $vault ".obsidian\plugins\jev-inbox-bridge"
if ((Test-Path -LiteralPath $target) -and -not $Force) {
    throw "Plugin existiert bereits. Fuer ein ausdrueckliches Update -Force angeben."
}
New-Item -ItemType Directory -Force -Path $target | Out-Null
Copy-Item -LiteralPath (Join-Path $root "obsidian-plugin\manifest.json") -Destination $target -Force
Copy-Item -LiteralPath (Join-Path $root "obsidian-plugin\main.js") -Destination $target -Force
Copy-Item -LiteralPath (Join-Path $root "obsidian-plugin\styles.css") -Destination $target -Force
Write-Host "Plugin kopiert: $target"
Write-Host "In Obsidian unter Community-Plugins 'Jev Inbox Bridge' aktivieren."
Write-Host "In Obsidian Community-Plugin deaktivieren/aktivieren, damit die neuen linken Symbole erscheinen."
Write-Host "Links: Bot = aktuelle Inbox-Notiz einordnen; Schild = Auswahl oder Notiz fuer KI vorbereiten."
Write-Host "Einordnen: Ziel pruefen, Backup bestaetigen und im zweiten Dialog verschieben."
