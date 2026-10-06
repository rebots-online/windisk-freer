#Requires -Version 5.1
<#
.SYNOPSIS
    build-release.ps1 — full release pipeline for Disk Occupancy.

.DESCRIPTION
    Stamps the version (Admin-Manual canonical stamper — MINOR bumps on
    EVERY run, BUILD = epoch-minutes % 100000) then builds all three
    deliverables into dist\:

      dist\DiskOccupancy.exe                          (PyInstaller onefile)
      dist\installer\Disk Occupancy-<ver>-setup.exe   (NSIS)
      dist\installer\DiskOccupancy-<ver>.msix         (MSIX, dev-signed)

    All version references are stamped outputs — version.txt is canonical;
    never hand-edit installer.nsi or the staged AppxManifest.xml versions.

    Usage:  powershell -File scripts\build-release.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

$SDK   = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64"
$NSIS  = "C:\Program Files (x86)\NSIS\Bin\makensis.exe"
$PFX   = "$Root\build\msix-cert\DiskOccupancy-dev.pfx"
$PFXPW = "diskoccupancy-dev"

# ── 1. stamp version (bump lives inside the stamper) ─────────────────────────
& powershell -NoProfile -File "$Root\scripts\update-version.ps1" -ProjectRoot $Root
$VER = (Get-Content "$Root\version.txt" -Raw).Trim()
$vp  = $VER -split '\.'
$MSIXVER = "{0}.{1}.{2}.0" -f [int]$vp[0], [int]$vp[1], [int]$vp[2]
Write-Host "`n=== release version: $VER (msix $MSIXVER) ===`n" -ForegroundColor Cyan

# ── 2. PyInstaller onefile → dist\DiskOccupancy.exe ──────────────────────────
python -m PyInstaller packaging\disk_occupancy.spec --noconfirm `
    --distpath dist --workpath build | Select-Object -Last 3

# ── 3. NSIS installer (reads version.txt itself via !define /file) ───────────
Push-Location "$Root\packaging"
& $NSIS installer.nsi | Select-Object -Last 6
Pop-Location

# ── 4. MSIX ──────────────────────────────────────────────────────────────────
python -m PyInstaller packaging\disk_occupancy_onedir.spec --noconfirm `
    --distpath build\msix --workpath build\msix-work | Select-Object -Last 3

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

$msixOut = "$Root\dist\installer\DiskOccupancy-$VER.msix"
& "$SDK\makeappx.exe" pack /d "$payload" /p $msixOut /o | Select-Object -Last 2
& "$SDK\signtool.exe" sign /fd SHA256 /f $PFX /p $PFXPW $msixOut

# ── 5. summary ───────────────────────────────────────────────────────────────
Write-Host "`n=== artifacts ($VER) ===" -ForegroundColor Cyan
Get-ChildItem "$Root\dist", "$Root\dist\installer" |
    Where-Object { -not $_.PSIsContainer -and $_.LastWriteTime -gt (Get-Date).AddMinutes(-30) } |
    ForEach-Object { "{0,12:N0}  {1}" -f $_.Length, $_.FullName }
