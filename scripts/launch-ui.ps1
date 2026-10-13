# Ein-Klick-Launcher für die lokale Weboberfläche (Windows)
param(
    [ValidateSet("inbox", "anonymize")]
    [string]$View = "inbox",
    [switch]$NoOpen,
    [ValidatePattern('^[a-f0-9]{64}$')]
    [string]$HandoffId
)
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$homeUrl = "http://127.0.0.1:8765/"
$targetUrl = if ($View -eq "anonymize") { "$($homeUrl)anonymize" } else { $homeUrl }
if ($HandoffId) {
    if ($View -ne "anonymize") { throw 'HandoffId requires the anonymize view.' }
    $targetUrl = $targetUrl + '#handoff=' + $HandoffId
}

function Test-JevosUI {
    try {
        $response = Invoke-WebRequest -Uri $homeUrl -UseBasicParsing -TimeoutSec 2
        return ($response.StatusCode -eq 200 -and $response.Content.Contains("<title>Obsidian Inbox-Assistent</title>"))
    } catch {
        return $false
    }
}

try {
    if (-not (Test-JevosUI)) {
        $script = Join-Path $repo "scripts\start-ui.ps1"
        if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
            throw "Server-Startskript nicht gefunden: $script"
        }
        $quotedScript = '"' + $script + '"'
        # Eigenständiger Hintergrundprozess lädt .env über start-ui.ps1.
        $server = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File $quotedScript -NonInteractive" -WorkingDirectory $repo -WindowStyle Hidden -PassThru
        $ready = $false
        for ($i = 0; $i -lt 50; $i++) {
            if (Test-JevosUI) {
                $ready = $true
                break
            }
            if ($server.HasExited) {
                throw "Der lokale Server wurde beendet. Port 8765 und Python-Installation prüfen."
            }
            Start-Sleep -Milliseconds 300
        }
        if (-not $ready) {
            throw "Lokale Oberfläche konnte nicht erreicht werden. Port 8765 prüfen."
        }
    }
    if (-not $NoOpen) { Start-Process -FilePath $targetUrl }
} catch {
    $message = "Jevos konnte nicht geöffnet werden." + [Environment]::NewLine + [Environment]::NewLine + $_.Exception.Message
    Write-Warning $message
    try {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show($message, "Jevos - Startfehler", "OK", "Error") | Out-Null
    } catch { }
    exit 1
}
