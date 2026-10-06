# CHECKLIST — disk-occupancy tool

- ✅ PySide6 GUI: drive buttons (all fixed disks incl. P:), size-sorted
  folder tree (Name/Size/%/Files), squarified treemap, scan progress,
  denied-count reporting.
- ✅ Delete → Recycle Bin (send2trash), permanent-delete fallback prompt,
  sizes re-rolled up the ancestor chain without rescan.
- ✅ Context menu: Open in Explorer / Copy path / Delete. Rescan / Stop /
  Scan-folder controls. Reparse points skipped (no junction loops).
- ✅ Verified offscreen: scan rollup correct, remove_subtree decrements
  ancestors incl. root, treemap emits rects.
- Launch: `pythonw C:\Users\Admin\tools\disk-occupancy\disk_occupancy.py [path]`
- ✅ Commercialization scaffold: PyInstaller onefile windowed build
  (`packaging/disk_occupancy.spec`), version resource, Inno Setup
  installer script. Exe verified launching at `packaging/dist/`.
- ✅ In-house licensing (PRLD1 Ed25519 offline keys, convention shared
  via `tools/licensing/`): `keygen.py` issues, vendored `prl_licensing.py`
  verifies. Free = scan/view, Pro = delete (gated). License dialog in
  toolbar, key persisted in HKCU\Software\DiskOccupancy, optional
  machine binding via MachineGuid hash. Verified: valid/tampered/
  expired/wrong-product/wrong-machine/registry roundtrip.
- Pending commercialization: real .ico, Authenticode cert, LICENSE.txt +
  Qt LGPL notice, purchase flow (webhook → keygen issue → email key).

## Session 2026-10-05 — git init + UI compliance

- ✅ git init (master), origin = github.com/rebots-online/windisk-freer,
  initial commit, push. Ignore __pycache__, *.bak, .codegraph/,
  packaging/build/ + unstamped exe (CC12: unstamped binaries must not be
  tracked; CC13: no GitHub LFS).
- ✅ Menubar compliance (RobinsAI CLAUDE spec §Standard Menu Structure):
  File | Edit | View | Help; License + About under Help; About shows
  Copyright + License + Version+Build; status bar bottom-right shows
  v<version.txt> (CC7). Commit `v0.1.53003: ` prefixed (CC9) + push.
- ✅ Splash compliance: name + v<version.txt> + copyright + init line.
  Committed + pushed.

Future: $MFT raw-read mode (WizTree method, admin required) for
seconds-not-minutes full-disk scans.

## Session 2026-10-05 — root dist/ build + installers + README

- [X] PyInstaller onefile build to ROOT `dist/` via
  `python -m PyInstaller packaging\disk_occupancy.spec --distpath dist
  --workpath build`; `dist/DiskOccupancy.exe` produced (exit 0, 52 MB).
  ⚠ An offscreen "does it start" launch was run here — that was an
  ad-hoc smoke test, PROHIBITED per KStore
  memory/01a10b4b-4e4c-8001-bc8a-ad0a8521310c. It is NOT valid
  verification; the claim is retracted.
- [ ] OWED: rubric-delineated verification of the three deliverables
  (exe, NSIS setup, MSIX) executed with screencast/screenshot evidence
  recorded — required by the verification policy; not yet performed.

### Additions later same session

- ✅ `license.key` at root: machine-bound Pro key (machine hash
  `30dce8d28a055e53`, perpetual, robin@local) issued via
  `tools/licensing/keygen.py`; `.gitignore`d with `*.lic`.
- ✅ `license.key` auto-activation: `_find_license_key_file` +
  `_auto_activate` — reads key file beside exe (frozen) or script (dev)
  when registry has no license; copies the key into HKCU on first run.
- ✅ License dialog QR (segno, pure-python): licensed → QR of the key
  (carry to mobile); unlicensed → `RLMC-PURCHASE|diskoccupancy|
  machine=<hash>` payload for Biddlr billing scan. Graceful no-QR
  fallback on ImportError. `segno` added to both spec hiddenimports.
- ✅ All three artifacts rebuilt with the feature (exe 55 MB; NSIS
  setup; MSIX repacked + re-signed). `dist/DiskOccupancy.exe.old` is a
  leftover of a still-running older exe (rename-succeeded, delete
  pending on process exit).
- [X] Checkbox select-per-row + selected-for-deletion tally
  implemented: `Node.check` tri-state, cascade up/down in TreeModel,
  `effective_checked()` dedups covered descendants, `selChanged` signal
  drives status-bar tally + toolbar "Delete selected (N)" button;
  context menu Mark/Unmark + Delete selected; single-click behavior is
  config item `clickMode` (check|navigate) via QSettings
  HKCU\Software\RobinsAI\DiskOccupancy + Edit-menu toggle. Compiles;
  rubric-evidenced run still owed (see above).
- ✅ NSIS installer → `dist/installer/Disk Occupancy-0.1.53003-setup.exe`
  (52 MB, lzma). installer.nsi updated: APPVERSION=0.1.53003, exe from
  `..\dist`, output `..\dist\installer`. Created root `LICENSE.txt`
  (proprietary EULA, required by MUI license page) +
  `LICENSE-Qt-LGPL.txt` (LGPL notice).
- ✅ MSIX/Store installer → `dist/installer/DiskOccupancy-0.1.53003.msix`
  (55 MB): onedir payload via `disk_occupancy_onedir.spec` to
  `build/msix`, placeholder Assets rendered by
  `scripts/make-msix-assets-d20261005.py`, manifest identity set to
  `RobinCheung.DiskOccupancy`/`CN=DiskOccupancy` (Partner Center values
  still needed for real Store submission), self-signed dev cert
  `build/msix-cert/` (thumbprint 99C5…A575), packed with makeappx,
  signed with signtool SHA256. `.cer` copied to dist/installer for
  sideload trust.
- ✅ Root `README.md`: features, run-from-source, all three build
  recipes, Store-submission notes, layout, license pointers.
- ✅ `.gitignore`: added root `dist/` + `build/` (CC12: unstamped
  binaries not tracked).
- Note: git-bash MSYS mangles `/d` `/p` flags for makeappx/signtool —
  must prefix `MSYS_NO_PATHCONV=1` (or invoke via powershell -Command).

## Session 2026-10-05 (cont.) — build-time version stamping

- ✅ Canonical Admin-Manual stamper ported into repo:
  `scripts/update-version.ps1` (verbatim port, product vars filled:
  Disk Occupancy / disk-occupancy / mba.robin.diskoccupancy). MINOR
  auto-bumps every run; BUILD = epoch-minutes % 100000. Operator rejected
  manual version edits ("never manually version; the build number would
  be a lie") — version.txt is now written ONLY by the stamper.
- ✅ Milestone edit: `version.txt` → `1.0.53003` (the one sanctioned
  manual act — MAJOR can't be 0). First stamp produced `1.1.54313`
  (versionCode 100001); `version.json` mirror written.
- ✅ `packaging/installer.nsi`: APPVERSION now `!define /file
  ..\version.txt` (self-stamping; `/D` override still possible).
- ✅ `packaging/appxmanifest.xml`: Identity/@Version is a stamped
  output — `scripts/build-release.ps1` rewrites it in the staged copy at
  pack time (4-part `<major>.<minor>.<build>.0`).
- ✅ `scripts/build-release.ps1` orchestrates the full pipeline:
  stamp → PyInstaller onefile → NSIS → onedir → stage+stamp manifest →
  makeappx → signtool. Ran end-to-end: `dist\DiskOccupancy.exe` (55 MB),
  `Disk Occupancy-1.1.54313-setup.exe`, `DiskOccupancy-1.1.54313.msix`
  (dev-signed). Stale 0.1.53003 artifacts + `.exe.old` removed.
- ⚠ Pitfall recorded in script: PS `-replace` is case-insensitive —
  naive `Version=` regex mangled the XML declaration AND `Get-Content`
  default encoding mangled the em-dash; use `[System.IO.File]` + a
  scoped `(<Identity[^>]*?Version=")` pattern + `${1}` braces.
- [X] "Can't delete" root-caused + fixed (PENDING SIGNOFF — see
  DOCS/ARCHITECTURE.md AD-2): P: is NTFS Fixed with NO `$RECYCLE.BIN`, so
  `send2trash`/`IFileOperation` fails unconditionally while `rmdir`
  works. Fix: `_has_recycle_bin` probe → no-bin volumes go straight to a
  "delete PERMANENTLY" confirm; batch delete gets the permanent fallback
  it was missing; items failing both stay checked and are reported.
  Compiles; NOT yet rebuilt — holding for operator signoff on AD-2 +
  AD-6 artifact-naming deviation before `build-release.ps1` runs.
- [ ] AD-10 (proposed, needs signoff): delete becomes two persisted
  QSettings — `deleteMode` (permanent|auto|recycle|shred, default
  `permanent` — recycle frees no space; auto = recycle iff
  `$RECYCLE.BIN` exists) and `deleteEngine`
  (robomirror|ifileop|memwalk|py, default `robomirror` = `robocopy
  /MIR /MT:32` from an empty dir — the Windows rsync-class answer and
  the fastest native tree wipe); `shred` zero-fills then deletes via
  engine (SSD caveat documented); optional persisted `retrim` toggle
  runs `defrag <drive>: /L` post-batch (admin-only — NTFS already
  TRIMs at unlink, so it's opt-in). Edit-menu "Delete method" submenu.
  Failed items stay checked, reported.
