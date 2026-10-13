# Startet nur das lokale UI auf 127.0.0.1; optional TypeSafe-Key für diese Sitzung.
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $repo
$hasKey = $false
try {
    # Ein optionaler lokaler .env-Eintrag vermeidet die wiederholte Key-Eingabe.
    # Keine Code-Ausführung und kein generisches Importieren fremder Variablen.
    # Eine bereits gesetzte Umgebungsvariable hat Vorrang.
    if (-not $env:TYPESAFE_API_KEY) {
        $envFile = Join-Path $repo ".env"
        if (Test-Path -LiteralPath $envFile -PathType Leaf) {
            $keyLines = @(Get-Content -LiteralPath $envFile -Encoding UTF8 |
                Where-Object { $_ -match '^\s*TYPESAFE_API_KEY\s*=' })
            if ($keyLines.Count -gt 1) {
                throw "In .env steht TYPESAFE_API_KEY mehrfach. Bitte nur einen Eintrag behalten."
            }
            if ($keyLines.Count -eq 1) {
                $keyValue = ($keyLines[0] -replace '^\s*TYPESAFE_API_KEY\s*=\s*', '').Trim()
                if ($keyValue.Length -ge 2 -and (
                    ($keyValue.StartsWith('"') -and $keyValue.EndsWith('"')) -or
                    ($keyValue.StartsWith("'") -and $keyValue.EndsWith("'"))
                )) {
                    $keyValue = $keyValue.Substring(1, $keyValue.Length - 2)
                }
                if ($keyValue) {
                    $env:TYPESAFE_API_KEY = $keyValue
                    $hasKey = $true
                    Write-Host "TypeSafe-Key aus lokaler .env geladen."
                }
            }
        }
    }
    if (-not $env:TYPESAFE_API_KEY) {
        $cloud = Read-Host "TypeSafe Jev Cloud in dieser Sitzung nutzbar machen? (J/N)"
        if ($cloud -eq "J") {
            $secret = Read-Host "TypeSafe API-Key (verdeckt; NICHT in Git speichern)" -AsSecureString
            $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
            try { $env:TYPESAFE_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
            finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
            $hasKey = $true
        }
    }
    Write-Host "UI: http://127.0.0.1:8765  (mit Strg+C beenden)"
    $venvPython = Join-Path $repo ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython) {
        & $venvPython -m inbox_assistant.web
    } else {
        py -3 -m inbox_assistant.web
    }
    if ($LASTEXITCODE -ne 0) { throw "Webanwendung wurde mit Fehler beendet." }
} finally {
    if ($hasKey) { Remove-Item Env:\TYPESAFE_API_KEY -ErrorAction SilentlyContinue }
    Pop-Location
}
