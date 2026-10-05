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

- [ ] git init (master), origin = github.com/rebots-online/windisk-freer,
  initial commit, push. Ignore __pycache__, *.bak, .codegraph/,
  packaging/build/ + unstamped exe (CC12: unstamped binaries must not be
  tracked; CC13: no GitHub LFS).
- [ ] Menubar compliance (RobinsAI CLAUDE spec §Standard Menu Structure):
  File | Edit | View | Help; License + About under Help; About shows
  Copyright + License + Version+Build; status bar bottom-right shows
  v<version.txt> (CC7). Commit `v0.1.53003: ` prefixed (CC9) + push.
- [ ] Splash compliance: name + v<version.txt> + copyright line.
  Commit + push.

Future: $MFT raw-read mode (WizTree method, admin required) for
seconds-not-minutes full-disk scans.
