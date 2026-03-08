param(
    [switch]$SkipExeBuild
)

$ErrorActionPreference = "Stop"

$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$root = @(
    $scriptDir,
    (Split-Path -Parent $scriptDir)
) | Where-Object { $_ -and (Test-Path (Join-Path $_ "Logical.py")) } | Select-Object -First 1
if (-not $root) {
    throw "Could not find project root containing Logical.py"
}

$buildExeScript = Join-Path $scriptDir "build_exe.ps1"
$issPath = Join-Path $scriptDir "installer.iss"

if (-not (Test-Path $issPath)) {
    throw "Missing file: $issPath"
}

if (-not $SkipExeBuild) {
    if (-not (Test-Path $buildExeScript)) {
        throw "Missing file: $buildExeScript"
    }
    & powershell -ExecutionPolicy Bypass -File $buildExeScript
}

$exePath = Join-Path $root "dist\Logical.exe"
if (-not (Test-Path $exePath)) {
    throw "Missing EXE: $exePath. Build failed or dist output is missing."
}

$iscc = $null
$isccCmd = Get-Command iscc -ErrorAction SilentlyContinue
if ($isccCmd) {
    $iscc = $isccCmd.Source
}
if (-not $iscc) {
    $candidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
    )
    $iscc = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}
if (-not $iscc) {
    throw "Inno Setup compiler not found. Install Inno Setup 6: https://jrsoftware.org/isinfo.php"
}

& $iscc "/DMySourceDir=$root" $issPath

$installerOut = Join-Path $root "installer_output\Logical.exe"
if (Test-Path $installerOut) {
    Write-Host "Installer built: $installerOut"
} else {
    Write-Host "Build completed. Check: $(Join-Path $root 'installer_output')"
}
