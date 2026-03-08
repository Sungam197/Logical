$ErrorActionPreference = "Stop"

$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$root = @(
    $scriptDir,
    (Split-Path -Parent $scriptDir)
) | Where-Object { $_ -and (Test-Path (Join-Path $_ "Logical.py")) } | Select-Object -First 1
if (-not $root) {
    throw "Could not find project root containing Logical.py"
}
$scriptPath = Join-Path $root "Logical.py"
$iconPath = Join-Path $root "logo.ico"
$distPath = Join-Path $root "dist"
$workPath = Join-Path $root "build"
$specPath = $root

if (-not (Test-Path $scriptPath)) {
    throw "Missing file: $scriptPath"
}
if (-not (Test-Path $iconPath)) {
    throw "Missing file: $iconPath"
}

$pyExe = $null
$pyArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    $pyExe = "py"
    $pyArgs = @("-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pyExe = "python"
} else {
    throw "Python was not found in PATH. Install Python 3 and try again."
}

Push-Location $root
try {
    & $pyExe @pyArgs -m PyInstaller `
      --noconfirm `
      --clean `
      --noupx `
      --onefile `
      --windowed `
      --name Logical `
      --distpath "$distPath" `
      --workpath "$workPath" `
      --specpath "$specPath" `
      --add-data "logo.ico;." `
      --exclude-module numpy `
      --exclude-module OpenGL `
      --exclude-module pkg_resources `
      --collect-submodules "setuptools._vendor.jaraco" `
      --icon "logo.ico" `
      "Logical.py"
} finally {
    Pop-Location
}

Write-Host "Built: $(Join-Path $root 'dist\\Logical.exe')"
