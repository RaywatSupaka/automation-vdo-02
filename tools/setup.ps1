$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
Set-Location (Split-Path -Parent $PSScriptRoot)
if (!(Test-Path '.venv/Scripts/python.exe')) {
    & py -3.11 -m venv .venv
    if ($LASTEXITCODE) { throw 'Python 3.11 is required' }
}
$taskNodeVersion = 'v24.21.0'
$taskNodeRoot = Join-Path (Get-Location) ".tools/node-$taskNodeVersion-win-x64"
if (!(Test-Path "$taskNodeRoot/node.exe")) {
    New-Item -ItemType Directory -Force .tools | Out-Null
    $taskZipName = "node-$taskNodeVersion-win-x64.zip"
    Invoke-WebRequest "https://nodejs.org/dist/$taskNodeVersion/$taskZipName" -UseBasicParsing -OutFile ".tools/$taskZipName"
    $taskSums = (Invoke-WebRequest "https://nodejs.org/dist/$taskNodeVersion/SHASUMS256.txt" -UseBasicParsing).Content
    $taskHashLine = $taskSums -split "`n" | Where-Object { $_.Trim().EndsWith($taskZipName) }
    $taskHash = ($taskHashLine -split '\s+')[0]
    if ((Get-FileHash ".tools/$taskZipName").Hash.ToLower() -ne $taskHash) { throw 'Node checksum mismatch' }
    Expand-Archive -LiteralPath ".tools/$taskZipName" -DestinationPath .tools -Force
}
$env:PATH = "$taskNodeRoot;" + $env:PATH
& .venv/Scripts/python.exe -m pip install -c requirements.lock.txt -e '.[dev,desktop]'
if ($LASTEXITCODE) { throw 'Python dependency installation failed' }
Push-Location frontend
try {
    & npm.cmd ci
    if ($LASTEXITCODE) { throw 'Frontend dependency installation failed' }
    & npm.cmd run build
    if ($LASTEXITCODE) { throw 'Frontend build failed' }
    & npx.cmd playwright install chromium
    if ($LASTEXITCODE) { throw 'Test browser installation failed' }
} finally { Pop-Location }
Write-Output 'Ready. Run RUN_DEV.bat, or .venv\Scripts\python.exe tools\check.py --scope workflow'
