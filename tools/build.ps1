$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$taskNode = Get-ChildItem '.tools/node-*-win-x64' -Directory -ErrorAction SilentlyContinue | Select-Object -Last 1
if ($taskNode) { $env:PATH = $taskNode.FullName + ';' + $env:PATH }
Push-Location frontend
try {
    & npm.cmd run build
    if ($LASTEXITCODE) { throw 'UI build failed' }
} finally { Pop-Location }
& .venv/Scripts/python.exe -m PyInstaller packaging/smartflow.spec --noconfirm
if ($LASTEXITCODE) { throw 'EXE build failed' }
$taskVersion = & .venv/Scripts/python.exe -c 'from smartflow import __version__; print(__version__)'
$taskManifest = @{
    version = $taskVersion
    source_commit = (& git rev-parse HEAD 2>$null)
    source_dirty = [bool](& git status --porcelain)
    built_at = [DateTime]::UtcNow.ToString('o')
    provider = 'simulator'
    exe_sha256 = (Get-FileHash 'dist/SmartFlow Next/SmartFlow Next.exe').Hash
    clean_machine_verified = $false
}
$taskManifest | ConvertTo-Json | Set-Content -Encoding UTF8 'dist/SmartFlow Next/build-manifest.json'
Write-Output 'Built dist/SmartFlow Next/SmartFlow Next.exe (portable directory; keep all files together)'
