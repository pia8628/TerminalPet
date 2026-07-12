# TerminalPet build script
# Usage: powershell -File scripts/build.ps1 [-Version 1.0]
# Requires: pip install -r requirements.txt -r requirements-build.txt
#
# NOTE: keep this file ASCII-only. Windows PowerShell 5.1 without a UTF-8
# BOM can misdecode multi-byte characters (e.g. full-width CJK punctuation)
# using the legacy system codepage, which can corrupt string parsing and
# silently skip statements. Put any user-facing localized text in the
# packaged app/installer instead, where Python controls the encoding.

param(
    [string]$Version = "1.0"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "==> Cleaning previous build output"
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "dist"
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "pyinstaller-work"
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "release"

if (-not (Test-Path "build\icon.ico")) {
    Write-Host "==> Generating build/icon.ico"
    python -c "from PIL import Image; Image.open('assets/wolf_done.png').convert('RGBA').save('build/icon.ico', format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"
}

Write-Host "==> Building TerminalPet.exe (GUI pet)"
Push-Location build
pyinstaller pet.spec --distpath ..\dist --workpath ..\pyinstaller-work --noconfirm
Pop-Location

Write-Host "==> Building PetState.exe (hook state writer)"
Push-Location build
pyinstaller set_state.spec --distpath ..\dist --workpath ..\pyinstaller-work --noconfirm
Pop-Location

Write-Host "==> Building Setup-TerminalPet.exe (installer)"
Push-Location build
pyinstaller setup.spec --distpath ..\dist --workpath ..\pyinstaller-work --noconfirm
Pop-Location

$ReleaseName = "TerminalPet-v$Version-win64"
$ReleaseDir = "release\$ReleaseName"

Write-Host "==> Assembling release directory: $ReleaseDir"
New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null
New-Item -ItemType Directory -Force -Path "$ReleaseDir\state" | Out-Null

Copy-Item "dist\TerminalPet\*" "$ReleaseDir\" -Recurse
Copy-Item "dist\PetState\*" "$ReleaseDir\state\" -Recurse
Copy-Item "dist\Setup-TerminalPet.exe" "$ReleaseDir\"
Copy-Item "使用說明.txt" "$ReleaseDir\"

Write-Host "==> Compressing zip"
$ZipPath = "release\$ReleaseName.zip"
Remove-Item -Force -ErrorAction SilentlyContinue $ZipPath
Compress-Archive -Path "$ReleaseDir\*" -DestinationPath $ZipPath

Write-Host ""
Write-Host "Done. Release package at: $ZipPath"
