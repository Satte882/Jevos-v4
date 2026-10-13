$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$bin = Join-Path $root ".local\jev\jev.exe"
$model = Join-Path $root ".local\jev\model"
if (-not (Test-Path -LiteralPath $bin -PathType Leaf) -or -not (Test-Path -LiteralPath $model -PathType Container)) {
    throw "Jevos fehlt. Zuerst scripts/install-jev.ps1 ausführen."
}
# Der Server bindet gemäß Upstream-Default nur 127.0.0.1:8017.
Write-Host "Jevos lokal starten: http://127.0.0.1:8017/health"
Write-Host "Dieses Fenster offen lassen. Mit Strg+C beenden."
Push-Location (Split-Path -Parent $bin)
try {
    # No idle shape compilation; reserve CPU capacity for the desktop UI.
    & $bin serve --warmup 0 --threads 4
    if ($LASTEXITCODE -ne 0) { throw "jev.exe wurde mit Exitcode $LASTEXITCODE beendet." }
}
finally {
    Pop-Location
}
