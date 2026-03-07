$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $root "Logical.py"
$iconPath = Join-Path $root "logo.ico"
$runtimeDir = Join-Path $root "_runtime"

if (-not (Test-Path $scriptPath)) {
    throw "Missing file: $scriptPath"
}
if (-not (Test-Path $iconPath)) {
    throw "Missing file: $iconPath"
}
New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null

pyinstaller `
  --noconfirm `
  --clean `
  --noupx `
  --onefile `
  --windowed `
  --name Logical `
  --distpath (Join-Path $root "dist") `
  --workpath (Join-Path $root "build") `
  --specpath $root `
  --runtime-tmpdir "$runtimeDir" `
  --add-data "$iconPath;." `
  --icon "$iconPath" `
  "$scriptPath"

Write-Host "Built: $(Join-Path $root 'dist\\Logical.exe')"
