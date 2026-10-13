# Installiert die festgepinnten Original-Archive in .local/jev (kein globaler Installer).
# Hersteller-Release: https://github.com/feder-cr/jev/releases/tag/jevos-v4
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$target = Join-Path $root ".local\jev"
$base = "https://github.com/feder-cr/jev/releases/download/jevos-v4"
$packages = @(
    @{ Name = "jev-windows-x64.zip"; Sha256 = "e70f03b008d10a35adbe8313f32238d233182c8eff5df75d9a5b3212834b271d" },
    @{ Name = "jevos-v4-openvino-int8.zip"; Sha256 = "b86c2b55aa97d4f89af5660251a1c943ff9ed52712568bfb4ad44fa734aaeb8c" }
)
$tmp = Join-Path ([IO.Path]::GetTempPath()) ("jevos-v4-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
try {
    foreach ($package in $packages) {
        $filename = $package.Name
        $archive = Join-Path $tmp $filename
        Write-Host "Download: $filename"
        Invoke-WebRequest -Uri "$base/$filename" -OutFile $archive
        $sha = (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash.ToLowerInvariant()
        if ($sha -ne $package.Sha256) {
            throw "SHA-256 stimmt nicht: $filename (erwartet: $($package.Sha256), erhalten: $sha)"
        }
        Write-Host "SHA-256 OK: $filename"
    }

    $binDir = Join-Path $tmp "binary_unpack"
    $modelDir = Join-Path $tmp "model_unpack"
    Expand-Archive -LiteralPath (Join-Path $tmp "jev-windows-x64.zip") -DestinationPath $binDir -Force
    Expand-Archive -LiteralPath (Join-Path $tmp "jevos-v4-openvino-int8.zip") -DestinationPath $modelDir -Force

    $binary = @(Get-ChildItem -LiteralPath $binDir -Recurse -File -Filter "jev.exe")
    if ($binary.Count -ne 1) { throw "jev.exe nicht eindeutig im Windows-Archiv gefunden." }
    $modelSource = Join-Path $modelDir "model"
    if (-not (Test-Path -LiteralPath $modelSource -PathType Container)) {
        $modelSource = $modelDir
    }
    if (-not @(Get-ChildItem -LiteralPath $modelSource -Recurse -File -Filter "*.xml").Count) {
        throw "Keine OpenVINO-Modell-Datei (*.xml) im Modellarchiv gefunden."
    }

    New-Item -ItemType Directory -Path $target -Force | Out-Null
    Get-ChildItem -LiteralPath $binary[0].DirectoryName | Copy-Item -Destination $target -Recurse -Force
    $installedModel = Join-Path $target "model"
    New-Item -ItemType Directory -Path $installedModel -Force | Out-Null
    Get-ChildItem -LiteralPath $modelSource | Copy-Item -Destination $installedModel -Recurse -Force

    if (-not (Test-Path -LiteralPath (Join-Path $target "jev.exe"))) {
        throw "Installation unvollständig: jev.exe fehlt."
    }
    Write-Host "Installation abgeschlossen: $target"
    Write-Host "Jetzt in einem PowerShell-Fenster: powershell -ExecutionPolicy Bypass -File .\scripts\start-jev.ps1"
}
finally {
    if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force }
}
