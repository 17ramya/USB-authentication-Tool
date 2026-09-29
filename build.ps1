<#
.SYNOPSIS
    Builds the distributable Windows executable of the USB Authentication Tool.

.DESCRIPTION
    Creates (or reuses) the local .venv, installs the pinned build requirements
    from requirements-dev.txt, runs the test suite, then packages main.py into a
    single dist\USB-Authentication-Tool.exe with PyInstaller and prints the
    SHA-256 checksum of the result.

.EXAMPLE
    .\build.ps1

.EXAMPLE
    .\build.ps1 -Clean -SkipTests
#>
[CmdletBinding()]
param(
    # Delete build\ and dist\ before packaging.
    [switch]$Clean,

    # Package without running the test suite (not recommended for a release).
    [switch]$SkipTests,

    # Interpreter used to create the virtual environment.
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$requirements = Join-Path $PSScriptRoot "requirements-dev.txt"
$spec = Join-Path $PSScriptRoot "usb-auth.spec"
$exe = Join-Path $PSScriptRoot "dist\USB-Authentication-Tool.exe"

if ($Clean) {
    Write-Host "Removing previous build output..." -ForegroundColor Cyan
    Remove-Item -Recurse -Force (Join-Path $PSScriptRoot "build"), (Join-Path $PSScriptRoot "dist") `
        -ErrorAction SilentlyContinue
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "Creating virtual environment in .venv..." -ForegroundColor Cyan
    & $Python -m venv (Join-Path $PSScriptRoot ".venv")
}

Write-Host "Installing build requirements..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade --quiet pip
& $venvPython -m pip install --quiet -r $requirements
if ($LASTEXITCODE -ne 0) { throw "installing requirements failed" }

if (-not $SkipTests) {
    Write-Host "Running tests..." -ForegroundColor Cyan
    & $venvPython -m pytest
    if ($LASTEXITCODE -ne 0) { throw "tests failed - the executable was not built" }
}

Write-Host "Packaging with PyInstaller..." -ForegroundColor Cyan
& $venvPython -m PyInstaller --noconfirm $spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$hash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
Write-Host ""
Write-Host "Built    : $exe" -ForegroundColor Green
Write-Host "SHA256   : $hash" -ForegroundColor Green
Write-Host "Smoke    : & '$exe' --version" -ForegroundColor DarkGray
