# Erstellt lokales Python-Environment und installiert das deutsche NER-Modell.
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $root
try {
    $python = Join-Path $root ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $python)) {
        py -3 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Python-Venv konnte nicht erstellt werden." }
    }
    & $python -m pip install -r requirements-redaction.txt
    if ($LASTEXITCODE -ne 0) { throw "spaCy-Installation fehlgeschlagen." }
    & $python -m spacy download de_core_news_md
    if ($LASTEXITCODE -ne 0) { throw "Deutsches NER-Modell konnte nicht installiert werden." }
    & $python -c "import spacy; nlp=spacy.load('de_core_news_md'); assert 'ner' in nlp.pipe_names"
    if ($LASTEXITCODE -ne 0) { throw "Deutsches NER-Modell nicht nutzbar." }
    Write-Host "Die lokale Textbereinigung ist installiert."
} finally { Pop-Location }
