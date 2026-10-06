#Requires -Version 5.1
<#
.SYNOPSIS
    update-version.ps1 — Windows-native canonical version stamper

.DESCRIPTION
    Windows-native port of Admin-Manual/scripts/versioning/update-version.sh.
    Implements the exact same invariant: MINOR increments unconditionally
    on every invocation. The bump lives INSIDE the stamper.

    This script exists so that agents operating on the Windows host (Windsurf
    native, not WSL) can stamp without bridging to bash. It writes the same
    outputs as the bash stamper: version.txt, version.json, and stamps
    package.json, tauri.conf.json, Cargo.toml, and tauri.properties.

    Lineage: Admin-Manual/scripts/versioning/update-version.sh (the canonical bash
    variant). This is the Windows equivalent — same logic, same invariant,
    same outputs. DO NOT re-derive this logic per project.

.NOTES
    Scheme (BUILD_CONVENTIONS):
      MAJOR = manual milestone (edit version.txt by hand, once per milestone)
      MINOR = auto-bumped UNCONDITIONALLY on every invocation (the heartbeat;
              resets to 0 when MAJOR changes)
      BUILD = epoch-minutes % 100000, 5-digit zero-padded (display only)

      versionName = MAJOR.MINOR.BUILD      e.g. 1.28.06942
      versionCode = MAJOR*100000 + MINOR   (BUILD excluded — Play needs monotonic)

    Canonical file: version.txt (single line). Runtime mirror: version.json.
    release.lock (sourced shell: MAJOR= MINOR= BUILD_NUM=) freezes values so
    multi-artifact releases stamp identical strings; delete to resume bumping.

    Usage:
      pwsh -File scripts/update-version.ps1
      # or from any directory:
      pwsh -File $HOME/Admin-Manual/scripts/versioning/update-version.ps1 -ProjectRoot C:\path\to\project

.PARAMETER ProjectRoot
    Path to the project root (defaults to parent of the script's location,
    matching the bash stamper's `cd "$(dirname "$0")/.."` behavior).

.EXAMPLE
    pwsh -File scripts/update-version.ps1 -ProjectRoot C:\Users\Admin\CascadeProjects\StAndroidsMissal
#>

[CmdletBinding()]
param(
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"

# ── Resolve project root (match bash stamper's cd "$(dirname "$0")/..") ──────
if (-not $ProjectRoot) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path
}
Set-Location $ProjectRoot

# ── Fill these in per project (identifier: no underscores, no hyphens — must ──
# ── equal tauri.conf.json "identifier" / applicationId EXACTLY) ──────────────
$PRODUCT_NAME    = "Disk Occupancy"
$INTERNAL_NAME   = "disk-occupancy"
$PACKAGE_NAME    = "mba.robin.diskoccupancy"

# ── release.lock support (freeze values across multi-artifact release) ───────
$LockFile = Join-Path $ProjectRoot "release.lock"
if (Test-Path $LockFile) {
    Write-Host "[update-version] Using frozen release.lock values"
    Get-Content $LockFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#")) {
            $parts = $line -split '=', 2
            if ($parts.Length -eq 2) {
                $name = $parts[0].Trim()
                $value = $parts[1].Trim()
                Set-Variable -Name $name -Value $value -Scope Script
            }
        }
    }
    # Validate that MAJOR, MINOR, BUILD_NUM were set
    if (-not $MAJOR -or -not $MINOR -or -not $BUILD_NUM) {
        throw "release.lock exists but is missing MAJOR, MINOR, or BUILD_NUM"
    }
} else {
    # ── Read current version from version.txt ────────────────────────────────
    $VersionFile = Join-Path $ProjectRoot "version.txt"
    if (Test-Path $VersionFile) {
        $CurrentVersion = (Get-Content $VersionFile -Raw).Trim()
    } else {
        $CurrentVersion = "1.0.0"
    }

    $VersionParts = $CurrentVersion -split '\.'
    $CURRENT_MAJOR = [int]$VersionParts[0]
    $CURRENT_MINOR = [int]$VersionParts[1]

    $MAJOR     = $CURRENT_MAJOR                        # manual milestone lives in version.txt
    $MINOR     = $CURRENT_MINOR + 1                    # THE heartbeat — never remove
    $BUILD_NUM = [int]([math]::Floor(([DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) / 60) % 100000)
}

$BUILD_PADDED    = "{0:D5}" -f [int]$BUILD_NUM
$DISPLAY_VERSION = "$MAJOR.$MINOR.$BUILD_PADDED"
$VERSION_CODE    = [int]$MAJOR * 100000 + [int]$MINOR

Write-Host "Stamping version: $DISPLAY_VERSION  (versionCode: $VERSION_CODE)"

# ── canonical + runtime mirror ───────────────────────────────────────────────
$VersionTxt = Join-Path $ProjectRoot "version.txt"
Set-Content -Path $VersionTxt -Value $DISPLAY_VERSION -NoNewline

$VersionJson = Join-Path $ProjectRoot "version.json"
$BuildDate = (Get-Date).ToString("o")
$VersionJsonContent = @"
{
  "version": "$DISPLAY_VERSION",
  "versionBase": "$MAJOR.$MINOR",
  "buildNumber": "$BUILD_PADDED",
  "versionCode": $VERSION_CODE,
  "buildDate": "$BuildDate",
  "productName": "$PRODUCT_NAME",
  "internalName": "$INTERNAL_NAME",
  "packageName": "$PACKAGE_NAME"
}
"@
Set-Content -Path $VersionJson -Value $VersionJsonContent

# ── stamp whatever manifests the project has (each guarded, no failures) ─────

# package.json (if jq is available, use it; otherwise use PowerShell)
$PackageJson = Join-Path $ProjectRoot "package.json"
if (Test-Path $PackageJson) {
    $pkg = Get-Content $PackageJson -Raw | ConvertFrom-Json
    $pkg.version = $DISPLAY_VERSION
    $pkg | ConvertTo-Json -Depth 100 | Set-Content $PackageJson
}

# src-tauri/tauri.conf.json
$TauriConf = Join-Path $ProjectRoot "src-tauri/tauri.conf.json"
if (Test-Path $TauriConf) {
    $conf = Get-Content $TauriConf -Raw
    $conf = $conf -replace '"version":\s*"[^"]*"', "`"version`": `"$DISPLAY_VERSION`""
    Set-Content -Path $TauriConf -Value $conf
}

# src-tauri/Cargo.toml (first version = line only)
$CargoToml = Join-Path $ProjectRoot "src-tauri/Cargo.toml"
if (Test-Path $CargoToml) {
    $cargo = Get-Content $CargoToml -Raw
    $cargo = [regex]::Replace($cargo, '(?m)^version\s*=\s*"[^"]*"', "version = `"$DISPLAY_VERSION`"", 1)
    Set-Content -Path $CargoToml -Value $cargo
}

# src-tauri/gen/android/tauri.properties
$AndroidDir = Join-Path $ProjectRoot "src-tauri/gen/android"
if (Test-Path $AndroidDir) {
    $TauriProps = Join-Path $AndroidDir "tauri.properties"
    $PropsContent = @"
tauri.android.versionCode=$VERSION_CODE
tauri.android.versionName=$DISPLAY_VERSION
"@
    Set-Content -Path $TauriProps -Value $PropsContent
}

# ── export for downstream scripts ────────────────────────────────────────────
$env:PROJECT_VERSION = $DISPLAY_VERSION
$env:PROJECT_VERSION_CODE = $VERSION_CODE.ToString()

Write-Host "Done: $DISPLAY_VERSION (versionCode $VERSION_CODE)"
