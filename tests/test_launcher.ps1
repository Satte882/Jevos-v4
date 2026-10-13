# Regression under the same Windows PowerShell 5.1 used by Obsidian.
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$temporary = Join-Path ([IO.Path]::GetTempPath()) ("jev-launcher-" + [guid]::NewGuid())
try {
    New-Item -ItemType Directory -Path (Join-Path $temporary "scripts") | Out-Null
    Copy-Item -LiteralPath (Join-Path $repo "scripts\start-ui.ps1") -Destination (Join-Path $temporary "scripts")
    # No .env or real Python process: verify keyless background startup never prompts.
    Remove-Item Env:\TYPESAFE_API_KEY -ErrorAction SilentlyContinue
    function Read-Host { throw "Background launcher must not prompt" }
    function py {
        if (($args -join " ") -ne "-3 -m inbox_assistant.web") { throw "Unexpected Python command" }
        $global:jevTestPythonCalled = $true
        $global:LASTEXITCODE = 0
    }
    $global:jevTestPythonCalled = $false
    & (Join-Path $temporary "scripts\start-ui.ps1") -NonInteractive
    if (-not $global:jevTestPythonCalled) { throw "Keyless startup did not invoke Python" }

    # Exercise routing and server reuse without opening browsers or reading a vault.
    function Invoke-WebRequest {
        $global:jevTestChecks++
        if ($global:jevTestCold -and $global:jevTestChecks -eq 1) { throw "Synthetic stopped server" }
        return [pscustomobject]@{StatusCode = 200; Content = "<title>Obsidian Inbox-Assistent</title>"}
    }
    function Start-Process {
        param($FilePath, $ArgumentList, $WorkingDirectory, $WindowStyle, [switch]$PassThru)
        $global:jevTestLaunches += $FilePath
        if ($FilePath -eq "powershell.exe") {
            if ($WindowStyle -ne "Hidden" -or $ArgumentList -notlike '*-NonInteractive*') {
                throw "Server must start hidden and without prompts"
            }
            return [pscustomobject]@{HasExited = $false}
        }
    }
    foreach ($cold in @($false, $true)) {
        foreach ($view in @("inbox", "anonymize")) {
            $global:jevTestCold = $cold
            $global:jevTestChecks = 0
            $global:jevTestLaunches = @()
            & (Join-Path $repo "scripts\launch-ui.ps1") -View $view
            $url = if ($view -eq "inbox") { "http://127.0.0.1:8765/" } else { "http://127.0.0.1:8765/anonymize" }
            $expected = if ($cold) { @("powershell.exe", $url) } else { @($url) }
            if (($global:jevTestLaunches -join "|") -ne ($expected -join "|")) { throw "Unexpected launcher routing" }
        }
    }
    Write-Output "Windows launcher: keyless startup and four routing/reuse cases OK"
} finally {
    # Only the unique temporary directory created above is removed.
    Remove-Item -LiteralPath $temporary -Recurse -Force -ErrorAction SilentlyContinue
}
