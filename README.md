# Disk Occupancy

WinDirStat-style disk-space analyzer and cleaner for Windows. PySide6 GUI
with drive buttons for every fixed disk, a size-sorted folder tree
(Name / Size / % of parent / file count), a squarified treemap, and
delete-to-Recycle-Bin cleanup.

Freemium: scanning and viewing are free; deleting files through the app
requires a Pro license key (offline Ed25519 keys, verified by the
in-house `rlmc_license` module).

## Run from source

```
pip install PySide6 send2trash cryptography segno
pythonw disk_occupancy.py [path]
```

`[path]` optionally pre-selects the folder to scan. Reparse points and
junctions are counted as zero-size leaves (no double-counting, no loops).
Folders that can't be read are reported as a denied count — no admin
rights needed for normal scans.

## Features

- Drive buttons for all fixed disks; rescan / stop / scan-folder controls
- Folder tree sorted by size with % of parent and file counts
- Squarified treemap visualization
- Context menu: Open in Explorer, Copy path, Mark/Unmark for deletion,
  Delete, Delete selected
- Checkboxes on every folder/file row (tri-state cascade); status bar
  shows a de-duplicated selected-for-deletion tally; toolbar + Edit menu
  + context menu offer "Delete selected"
- Single-click behavior is a config item (Edit → "Single-click marks
  for deletion", persisted via QSettings): mark-for-deletion vs
  navigate/expand
- Delete sends to Recycle Bin (send2trash) with permanent-delete
  fallback prompt; sizes re-roll up ancestors without a rescan
- License dialog under Help; key persisted in
  `HKCU\Software\DiskOccupancy`, optional machine binding
- License dialog shows a QR code: the license key when activated, or a
  `RLMC-PURCHASE|<product>|machine=<hash>` payload when not — for
  Biddlr billing and mobile activation
- `license.key` beside the exe (or the script, in dev) auto-activates on
  startup if no license is registered

## Versioning

Version is **build-time stamped, never hand-edited** (Admin-Manual
convention, `scripts/update-version.ps1` — port of the canonical bash
stamper):

- `MAJOR.MINOR.BUILD` — MAJOR is the milestone (the one sanctioned manual
  edit to `version.txt`); MINOR auto-bumps on *every* stamp; BUILD is
  epoch-minutes % 100000 (display only).
- Canonical file: `version.txt`; runtime mirror: `version.json`.
- `installer.nsi` reads `version.txt` itself (`!define /file`); the MSIX
  `Identity/@Version` is rewritten in the staged manifest at pack time.
  Both are stamped outputs — don't edit them.
- `release.lock` (`MAJOR= MINOR= BUILD_NUM=`) freezes values across a
  multi-artifact release; delete to resume bumping.

## Build

The full release pipeline is one command — it stamps the version, then
builds all four deliverables **flat into `dist/`** (the tracked release
surface — it is never cleared; each version's artifacts accumulate):

```
powershell -File scripts\build-release.ps1
```

Artifacts (AD-6 slug-first names):

| Artifact | File |
|---|---|
| Standalone exe | `dist\windisk-freer-v<ver>-win64.exe` |
| NSIS installer | `dist\windisk-freer-v<ver>-win64-nsis.exe` |
| MSI installer | `dist\windisk-freer-v<ver>-win64.msi` |
| MSIX (Store) | `dist\windisk-freer-v<ver>-win64.msix` |

Intermediates (`build\onefile`, `build\msix`, `build\msix-work`) stay in
the gitignored `build/` dir. MSI requires WiX (`dotnet tool install -g
wix`; the script passes `--acceptEula` — accepts the WiX OSMF EULA per
invocation, see wixtoolset.org/osmf).

### NSIS details

Per-user install to `%LOCALAPPDATA%\Programs` (no UAC), Add/Remove
Programs entry, desktop + Start Menu shortcuts, uninstaller.

### MSIX (Microsoft Store) details

The pipeline stages `packaging\appxmanifest.xml` (version stamped into
`Identity/@Version`) + `build\msix-assets\*.png` + licenses onto the
onedir payload, then `makeappx pack` + `signtool sign` →
`dist\windisk-freer-v<ver>-win64.msix`.

The included manifest uses `runFullTrust` (desktop bridge) so packaged
scans keep working. For **sideloading**, the MSIX is signed with the dev
cert `build\msix-cert\DiskOccupancy-dev.cer` — install that cert into
*Trusted People* on the target machine first
(`Import-Certificate -CertStoreLocation Cert:\LocalMachine\TrustedPeople`).

For **Store submission**: reserve the app in Partner Center, then replace
`Identity/@Name` and `Identity/@Publisher` in
`packaging\appxmanifest.xml` with the Partner Center values, rebuild, and
let Partner Center sign. The generated PNGs in
`scripts\make-msix-assets-d20261005.py` are placeholders — commission
real branded art first.

## Layout

| Path | Purpose |
|---|---|
| `disk_occupancy.py` | entire application (single file) |
| `version.txt` | canonical version, stamped by `scripts/update-version.ps1` |
| `packaging/` | PyInstaller specs, NSIS + Inno scripts, MSIX manifest |
| `scripts/` | asset generation and maintenance scripts |
| `DOCS/ARCHITECTURE.md` | design notes |
| `dist/` | build output: exe + installers (gitignored) |

## License

Proprietary — see `LICENSE.txt`. Qt/PySide6 components under LGPLv3 —
see `LICENSE-Qt-LGPL.txt`.
