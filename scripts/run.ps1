# Interaktive Auswahl: exakt ein Provider pro Durchlauf.
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $root ".venv\Scripts\python.exe"
$prefix = @()
if (-not (Test-Path -LiteralPath $python)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $python = "py"
        $prefix = @("-3")
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $python = "python"
    } else {
        throw "Python 3 fehlt. Installiere es von python.org."
    }
}
Write-Host ""
Write-Host "Waehle den Provider fuer DIESEN Test:"
Write-Host "  1 - Jevos-v4 LOKAL | 6 Demobeispiele"
Write-Host "  2 - Jev CLOUD      | 6 Demobeispiele"
Write-Host "  3 - Jevos-v4 LOKAL | Obsidian (nur lesen)"
Write-Host "  4 - Jev CLOUD      | Obsidian (Notizen werden hochgeladen!)"
$selection = Read-Host "Auswahl (1-4)"
if ($selection -notin @("1", "2", "3", "4")) { throw "Keine gueltige Auswahl." }
$provider = if ($selection -in @("1", "3")) { "local" } else { "jev" }
$action = if ($selection -in @("1", "2")) { "demo" } else { "vault" }
$cliArgs = @("--provider", $provider, $action, "--mode", "all")
if ($action -eq "vault") {
    $vault = Read-Host "Vollstaendigen Obsidian-Vault-Pfad eingeben"
    if ([string]::IsNullOrWhiteSpace($vault)) { throw "Vault-Pfad fehlt." }
    $cliArgs += @("--vault", $vault, "--limit", "20")
    if ($provider -eq "jev") {
        Write-Warning "20 ECHTE Notizen werden an die TypeSafe-CLOUD uebertragen; API-Kosten moeglich!"
        if ((Read-Host "Nur zum Bestaetigen exakt JA eingeben") -cne "JA") { throw "Abgebrochen." }
        $cliArgs += "--allow-cloud-vault"
    }
}
$promptedKey = $false
if ($provider -eq "jev" -and -not $env:TYPESAFE_API_KEY) {
    $secret = Read-Host "TypeSafe API Key (verborgene Eingabe)" -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
    try { $env:TYPESAFE_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
    $promptedKey = $true
}
Push-Location $root
try {
    & $python @prefix -m jevos_local @cliArgs
    if ($LASTEXITCODE -ne 0) { throw "Test fehlgeschlagen (Exitcode $LASTEXITCODE)." }
} finally {
    Pop-Location
    if ($promptedKey) { Remove-Item Env:\TYPESAFE_API_KEY -ErrorAction SilentlyContinue }
}
