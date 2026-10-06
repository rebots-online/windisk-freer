#Requires -Version 5.1
<#
.SYNOPSIS
    build-release.ps1 -- full release pipeline for Disk Occupancy.

.DESCRIPTION
    Stamps the version (Admin-Manual canonical stamper -- MINOR bumps on
    EVERY run, BUILD = epoch-minutes % 100000), then builds all release
    deliverables flat into dist\ (the tracked release surface, AD-6 --
    prior releases' artifacts are NEVER cleared):

      dist\windisk-freer-v<ver>-win64.exe        (PyInstaller onefile)
      dist\windisk-freer-v<ver>-win64-nsis.exe  (NSIS)
      dist\windisk-freer-v<ver>-win64.msi       (WiX MSI)
      dist\windisk-freer-v<ver>-win64.msix      (MSIX, dev-signed)

    All intermediates live in build\ (gitignored); only stamped
    artifacts land in dist\. All version references are stamped
    outputs -- version.txt is canonical; never hand-edit installer.nsi
    or appxmanifest versions.

    NOTE: 'wix build' is invoked with --acceptEula, which accepts the
    WiX OSMF EULA for that invocation only (see wixtoolset.org/osmf).

    Usage:  powershell -File scripts\build-release.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

$SDK   = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64"
$NSIS  = "C:\Program Files (x86)\NSIS\Bin\makensis.exe"
$WIX   = "$env:USERPROFILE\.dotnet\tools\wix.exe"
$PFX   = "$Root\build\msix-cert\DiskOccupancy-dev.pfx"
$PFXPW = "diskoccupancy-dev"

# -- 1. stamp version (bump lives inside the stamper) -------------------------
& powershell -NoProfile -File "$Root\scripts\update-version.ps1" -ProjectRoot $Root
$VER = (Get-Content "$Root\version.txt" -Raw).Trim()
$vp  = $VER -split '\.'
$MSIXVER = "{0}.{1}.{2}.0" -f [int]$vp[0], [int]$vp[1], [int]$vp[2]
Write-Host ""
Write-Host "=== release version: $VER (msix $MSIXVER) ===" -ForegroundColor Cyan

# -- 2. PyInstaller onefile -> intermediate, then copy stamped name to dist --
python -m PyInstaller packaging\disk_occupancy.spec --noconfirm `
    --distpath build\onefile --workpath build\onefile-work | Select-Object -Last 3
Copy-Item "$Root\build\onefile\DiskOccupancy.exe" `
    "$Root\dist\windisk-freer-v$VER-win64.exe" -Force

# -- 3. NSIS installer (reads version.txt itself via !define /file) ----------
Push-Location "$Root\packaging"
& $NSIS installer.nsi | Select-Object -Last 6
Pop-Location

# -- 4. onedir payload (shared by MSI + MSIX) --------------------------------
python -m PyInstaller packaging\disk_occupancy_onedir.spec --noconfirm `
    --distpath build\msix --workpath build\msix-work | Select-Object -Last 3

# -- 4a. MSI (WiX) -- harvests the clean onedir payload BEFORE msix staging --
if (-not (Test-Path $WIX)) { throw "WiX not found - install with: dotnet tool install -g wix" }
& $WIX build --acceptEula "$Root\packaging\disk-occupancy.wxs" `
    -d "Version=$VER" -d "PayloadDir=$Root\build\msix\DiskOccupancy" `
    -bindfiles -pdbtype none `
    -o "$Root\dist\windisk-freer-v$VER-win64.msi" | Select-Object -Last 4

# -- 4b. stage + pack + sign MSIX --------------------------------------------
python "$Root\scripts\make-msix-assets-d20261005.py" | Select-Object -Last 1

$payload = "$Root\build\msix\DiskOccupancy"
Copy-Item "$Root\packaging\appxmanifest.xml" "$payload\AppxManifest.xml"
# stamp the 4-part package version into the staged manifest's Identity
$mani = [System.IO.File]::ReadAllText("$payload\AppxManifest.xml")
$mani = [regex]::Replace($mani, '(?s)(<Identity[^>]*?Version=")[^"]*(")',
    ('${1}' + $MSIXVER + '$2'))
[System.IO.File]::WriteAllText("$payload\AppxManifest.xml", $mani)
New-Item -ItemType Directory -Force "$payload\Assets" | Out-Null
Copy-Item "$Root\build\msix-assets\*.png" "$payload\Assets\"
Copy-Item "$Root\LICENSE.txt", "$Root\LICENSE-Qt-LGPL.txt" $payload

$msixOut = "$Root\dist\windisk-freer-v$VER-win64.msix"
& "$SDK\makeappx.exe" pack /d "$payload" /p $msixOut /o | Select-Object -Last 2
& "$SDK\signtool.exe" sign /fd SHA256 /f $PFX /p $PFXPW $msixOut

# -- 5. summary ---------------------------------------------------------------
Write-Host ""
Write-Host "=== artifacts ($VER) ===" -ForegroundColor Cyan
Get-ChildItem "$Root\dist" -Filter "*$VER*" |
    ForEach-Object { "{0,12:N0}  {1}" -f $_.Length, $_.FullName }
