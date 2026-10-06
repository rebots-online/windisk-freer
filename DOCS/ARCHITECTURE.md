# REMINDER FROM OPERATOR: 
 
 - always follow the central dev dogma, kstore reminder directives, and Admin-Manual
 - Step 1: Propose a new @DOCS/ARCHITECTURE.md and open in editor for operator signoff
 - Step 2: transform the approved ARCHITECTURE.md -> recipe in the form of a CHECKLIST.md comprising self-contained four-state [ ] Tasks sufficiently-detailed that a coding subagent does not need to examine the codebase to code it, then present in editor for operator signoff; 
 - your turn is not complete until all kstore reminders in in context injected during this turn have been resolved

# windisk-freer — Architecture

- **Product**: Disk Occupancy — WinDirStat-style per-disk, per-folder space
  occupancy GUI with select-to-delete.
- **Repo**: `github.com/rebots-online/windisk-freer` (code-only; no LFS per CC13)
- **Stack**: Python 3.13, PySide6, `send2trash`, vendored `rlmc_license`
  (in-house RLMC1 Ed25519 offline licensing, shared convention via
  `~/tools/licensing/`).
- **Version scheme**: `MAJOR.MINOR.BUILD` (CC2/CC7). MAJOR ≥ 1 — `0.x` is
  noncompliant. MAJOR is a manual milestone; MINOR auto-bumps on every stamper
  run; BUILD = `epoch_minutes % 100000`, zero-padded 5 digits.
- **Adopted conventions**: CC2, CC7, CC9, CC12, CC13; standard windowed-app
  menu structure `File | Edit | View | Help` with About under Help
  (Copyright + License + Version+Build); version bottom-right of status bar;
  runtime identity overridable via `.env` (see AD-7).

## 1. Phase I feature manifest

Shipped and closed:

1. Drive buttons for every fixed disk (`fixed_drives`).
2. Size-sorted folder tree: Name / Size / % / Files (`TreeModel`, `Node`).
3. Squarified treemap visualization (`Treemap`, `squarify`).
4. Progress + denied-count reporting (`Scanner` signals, status bar).
5. Delete → Recycle Bin where the volume supports it; permanent delete
   with explicit confirm elsewhere (`Main._delete`,
   `Main._delete_permanent_prompt`, `Main._has_recycle_bin`), size
   re-rollup without rescan (`TreeModel.remove_subtree`).
6. Context menu: Open in Explorer / Copy path / Mark for deletion /
   Delete / Delete selected (`Main._menu`).
7. Offline licensing gate: Free = scan/view, Pro = delete
   (`LICENSING`, `Main._license_dialog`, `Main._activate`).
8. Splash + compliant version surfaces (`main`, `app_version`,
   `Main._build_menus`, `Main._about`).
9. PyInstaller packaging scaffold (`packaging/disk_occupancy.spec`,
   `disk_occupancy_onedir.spec`); `scripts/build-release.ps1` runs the
   full stamp→exe→NSIS→MSIX pipeline.
10. Tri-state checkboxes on every folder/file row; cascade up/down
    (`TreeModel.setData`); de-duplicated selected-for-deletion tally in
    the status bar; `Delete selected` in toolbar/Edit/context menu.
11. Single-click behavior is a persisted config item
    (`QSettings` `clickMode` = `check`/`navigate`, Edit-menu toggle).
12. License dialog renders a QR (`segno`): the key when licensed, else a
    `RLMC-PURCHASE|<product>|machine=<hash>` payload for Biddlr/mobile.
13. `license.key` beside the exe (or script, in dev) auto-activates on
    startup when no license is registered (`Main._auto_activate`).

## 2. Data flow

```
startup: main() -> QApplication(DARK_STYLE) -> QSplashScreen(name +
         v<version.txt> + copyright + init line) -> Main -> argv[1] scan?

scan:    Main.scan(path) -> Scanner(QThread) iterative os.scandir DFS
         (reparse points = zero-size leaves, no junction loops)
         -> Node tree + _rollup() size/file-count aggregation
         -> finished_scan -> TreeModel.set_root + Treemap.set_root

select:  QTreeView selection <-> Treemap rects (bidirectional highlight);
         checkboxes (tri-state cascade in TreeModel.setData) -> status-bar
         tally via selChanged signal

delete:  context menu / Edit menu / toolbar -> Main._delete /
         Main._delete_selected_set -> Pro gate (LICENSING.is_pro) ->
         _has_recycle_bin(path)? -> send2trash (recyclable) or direct
         rmtree/os.remove (no-bin volume e.g. P:) -> recycle failure ->
         _delete_permanent_prompt (shared, batch-aware) ->
         TreeModel.remove_subtree -> Treemap refresh

license: Help -> License… -> _license_dialog (machine_hash shown for
         machine-bound issuance) -> LICENSING.save(key) validates
         signature/product/expiry -> persists HKCU\Software\DiskOccupancy
```

## 3. Entity table — `disk_occupancy.py`

| Entity | Type | file:line | Role | Signature / fields |
|---|---|---|---|---|
| `_load_env()` | fn | :19 | loads `.env` overrides (script dir, `_MEIPASS`, frozen exe dir); `setdefault`, never clobbers real env | `-> None` |
| `APP_NAME` | const | :~30 | display name; `os.environ.get("WINDISK_APP_NAME", "Disk Occupancy")` | str |
| `PRODUCT_ID` | const | :~31 | license product id; `os.environ.get("WINDISK_PRODUCT_ID", "diskoccupancy")` | str |
| `PUBLIC_KEY_B64` | const | :~32 | Ed25519 public key verifying RLMC1 keys | str |
| `LICENSING` | instance | :~33 | license facade | `rlmc_license.Licensing(PRODUCT_ID, PUBLIC_KEY_B64, reg_key=r"Software\DiskOccupancy")` — `.load() .save(key) .clear() .is_pro` |
| `app_version()` | fn | :~45 | CC7 display version = `v` + `version.txt`; `_MEIPASS`/script-dir lookup | `-> str` ("v0.0.00000" floor) |
| `HIDDEN` | const | :~54 | reserved excluded-dir names (defined; currently unconsumed) | set[str] |
| `Node` | dataclass | :~59 | scanned tree node | `name, path, is_dir, size, nfiles, children, parent, denied, check`; `row() -> int` |
| `human(n)` | fn | :~73 | byte-size formatter | `int -> "12.3 MB"` |
| `Scanner` | QThread | :~81 | background scandir walker | `progress(str,int,int)`, `finished_scan(object,int)`; `run()`, `_stop`; `@staticmethod _rollup(node)` |
| `TreeModel` | QAbstractItemModel | :~152 | tree datasource | `COLS=("Name","Size","%","Files")`; `set_root`, `remove_subtree`, `index_for`, `setData` (CheckStateRole tri-state cascade), `effective_checked` (topmost-checked dedup), `selChanged` signal + required model API |
| `squarify()` | fn | :~238 | slice-dice treemap layout | `(children,x,y,w,h,out,depth)`; depth<3, top 25 children per level |
| `PALETTE` | const | :~262 | treemap colors | list[str] ×10 |
| `Treemap` | QWidget | :~266 | painted treemap | `clicked=Signal(object)`; `set_root`, `set_selected`, `paintEvent`, `mousePressEvent`; top 200 rects |
| `fixed_drives()` | fn | :~323 | enumerate DRIVE_FIXED via `GetLogicalDrives`/`GetDriveTypeW` | `-> list[str]` (fallback `["C:\\"]`) |
| `Main` | QMainWindow | :~335 | application window | see §3.1 |
| `DARK_STYLE` | const | :~627 | Qt stylesheet | str |
| `main()` | fn | :~655 | entry: app, splash, window, argv path | `-> None` |

### 3.1 `Main` methods

| Method | Role |
|---|---|
| `__init__`, `_build_ui` | window, toolbar (drive buttons, Scan folder…/Rescan/Stop), tree+treemap splitter, status bar (status, progress, tier, version bottom-right) |
| `_build_menus` | `File`(Scan folder…, Exit) `Edit`(Copy path, Delete) `View`(Rescan, Stop, Expand/Collapse all) `Help`(License…, About) |
| `_selected_node`, `_copy_selected_path`, `_delete_selected` | Edit-menu plumbing onto current tree selection |
| `_about` | About dialog: name + `v<version.txt>`, license row, Qt component row, copyright |
| `_update_tier`, `_license_dialog`, `_activate` | license status, entry/activation, machine-id copy |
| `scan`, `stop`, `rescan`, `pick_folder`, `_scanned` | scan lifecycle |
| `_menu`, `_open`, `_tree_sel`, `_map_sel`, `_delete` | context menu, explorer open, selection sync, gated single delete |
| `_delete_selected_set`, `_delete_permanent_prompt`, `_has_recycle_bin` | batch delete of checked items; shared permanent-delete confirm; `$RECYCLE.BIN` volume probe |
| `_clicked`, `_toggle_click_mode`, `_update_sel_label` | single-click behavior (`check`/`navigate`, QSettings `clickMode`), status-bar selected tally |
| `_auto_activate`, `_find_license_key_file` | `license.key` startup activation when registry has no license |

## 4. Non-source entities

| Entity | Path | Role |
|---|---|---|
| `rlmc_license` | `~/tools/licensing/rlmc_license.py` (outside repo; `sys.path` insert) | RLMC1 Ed25519 verify + HKCU persistence + `machine_hash()` |
| `version.txt` | repo root | canonical `MAJOR.MINOR.BUILD`, one line; only writer = `scripts/update-version.ps1` |
| `version.json` | repo root | generated runtime mirror (version, versionCode, buildDate, productName, internalName, packageName) |
| `scripts/update-version.ps1` | `scripts/` | canonical stamper — verbatim port of `~/Admin-Manual/scripts/versioning/update-version.ps1`; MINOR heartbeat inside the stamper; `release.lock` freeze support |
| `scripts/build-release.ps1` | `scripts/` | release pipeline: stamp → onefile exe → NSIS → onedir → stage+stamp MSIX manifest → makeappx → signtool |
| `scripts/make-msix-assets-d20261005.py` | `scripts/` | placeholder MSIX tile/logo PNG generator |
| `license.key` | repo root (gitignored) | machine-bound Pro key for this machine; auto-activated at startup |
| `.env` | repo root (gitignored) | runtime overrides `WINDISK_APP_NAME`, `WINDISK_PRODUCT_ID` |
| `.env.example` | repo root (tracked) | documented template of the above |
| `verify-licensing.py` | repo root | offscreen verifier: CC7 string, license roundtrip, menu structure |
| `packaging/disk_occupancy.spec` | `packaging/` | PyInstaller onefile windowed spec → `packaging/dist/` |
| `packaging/installer.{iss,nsi}`, `appxmanifest.xml`, `version_info.txt`, `disk_occupancy_onedir.spec` | `packaging/` | installer/metadata scaffold |
| `dist/` | repo root (TRACKED, flat, never cleared) | release artifacts, slug-first `windisk-freer-v<ver>-win64-<tech>.<ext>` (exe/nsis/msi/msix); sole binary surface |

## 5. Decisions

- **AD-1** PySide6 + `os.scandir` (no admin required); reparse points counted
  as zero-size leaves to prevent junction loops and double-counting.
- **AD-2** Delete semantics: delete mode/engine are persisted user
  settings (AD-10) — default `permanent`/`robomirror` for speed and
  actual space reclamation; `recycle`/`auto`/`shred` selectable.
  `auto` uses `$RECYCLE.BIN` presence (`_has_recycle_bin`) to pick
  recycle-vs-permanent — no-bin volumes (e.g. `P:`) never attempt the
  recycle call that fails unconditionally. A permanent delete always
  asks once before running (first-use "cannot be undone" confirm).
  Failed items stay checked and are reported, never silently dropped.
  No elevation: admin ≠ TrustedInstaller and the operator rejected an
  elevated helper.
- **AD-3** Licensing: offline Ed25519 (RLMC1), no network; Free = scan/view,
  Pro = delete; key persisted in `HKCU\Software\DiskOccupancy`; optional
  machine binding via `machine_hash`.
- **AD-4** Versioning is scripted, never manual: `scripts/update-version.ps1`
  is the only writer of `version.txt`/`version.json`; MAJOR milestone edits
  land in `version.txt` by hand, then the stamper runs. `0.x` noncompliant.
  `installer.nsi` APPVERSION comes from `!define /file ..\version.txt`;
  the MSIX `Identity/@Version` is rewritten in the staged manifest copy at
  pack time — both are stamped outputs, never hand-edited.
- **AD-5** Standard menubar `File | Edit | View | Help`; About carries
  copyright + license + version+build; `v<version.txt>` bottom-right of
  status bar and on the splash (CC7 — nothing appended).
- **AD-6** Release artifacts: repo-root `dist/` is FLAT and NEVER
  CLEARED — no subfolders, no temp dirs, no pruning; each release's
  artifacts accumulate as the release history. Filenames are slug-first
  `windisk-freer-v<MAJOR.MINOR.BUILD>-win64-<tech>.<ext>`:
  `-win64.exe` (standalone), `-win64-nsis.exe` (NSIS),
  `-win64.msi` (WiX 7 via dotnet tool, cab embedded via
  `MediaTemplate/@EmbedCab`, `-pdbtype none`), `-win64.msix`
  (makeappx + signtool). Installer-tech qualifier is mandatory.
  Intermediates live only in `build/` (gitignored disposable zone:
  `onefile/`, `msix/`, `msix-work/`).
- **AD-8** Selection model: `Node.check` tri-state; cascade down sets the
  whole subtree, cascade up resolves ancestors to
  Checked/PartiallyChecked/Unchecked; `effective_checked()` returns
  topmost-checked nodes only so tallies and deletes never double-count.
- **AD-9** Single-click behavior is a user config item
  (`QSettings` `clickMode`, `check`|`navigate`), toggled from the Edit
  menu; clicking the checkbox glyph always toggles regardless of mode.
- **AD-10** (PROPOSED — pending signoff) Delete is two orthogonal,
  persisted settings (`QSettings` under `HKCU\Software\RobinsAI\
  DiskOccupancy`), exposed as an Edit-menu "Delete method" submenu:

  *Method* (`deleteMode`, default `permanent` — the tool exists for
  speed and space reclamation; recycle merely relocates bytes into
  `$RECYCLE.BIN` on the same volume and frees nothing until emptied;
  Explorer already covers the recycle use-case):
  - `permanent` — straight unlink via the configured engine;
  - `auto` — recycle if the volume has `$RECYCLE.BIN`, else permanent
    (kept for cautious users);
  - `recycle` — `send2trash`/`IFileOperation`+`FOFX_RECYCLEONDELETE`;
  - `shred` — zero-fill each file (`shredPasses`, default 1) then
    delete. Caveat recorded: on SSD/flash, overwriting is advisory at
    best (wear-leveling, overprovisioned cells) — true erasure needs
    `cipher /w` or crypto-erase; the option is labeled accordingly.

  *Post-delete TRIM* (`retrim`, persisted toggle, default off):
  NTFS already TRIMs freed clusters at unlink time when
  `DisableDeleteNotify=0` (default), so deletes auto-TRIM; this toggle
  adds a full-volume `defrag <drive>: /L` retrim once per affected
  drive after a batch — requires elevation, so the option is disabled
  unless the process is admin. Documented as mostly-redundant for
  deletes; useful after large shred passes.

  *Engine* for permanent/shred (`deleteEngine`, default `robomirror`):
  - `robomirror` — `robocopy <empty> <target> /MIR /MT:32 /NFL /NDL
    /NJH /NJS /NP` then remove the emptied root: the fastest native
    tree wipe on Windows (multithreaded, one process, no per-file
    Python overhead). Same mechanism as the rsync-style question —
    robocopy IS the Windows rsync-class tool; no external dep needed.
  - `ifileop` — `IFileOperation.DeleteItem` batch *without*
    `FOFX_RECYCLEONDELETE`: one `PerformOperations` for the whole
    selection, real per-item errors via progress sink, clears
    read-only attrs that `rmtree` chokes on; pywin32 already bundled.
  - `memwalk` — bottom-up `os.unlink`/`os.rmdir` over the in-memory
    `Node` tree; zero re-enumeration; ENOTEMPTY (post-scan additions)
    falls back to `rmtree` for the residue.
  - `py` — `shutil.rmtree`/`os.remove`; slowest, always-available
    fallback; engines degrade to it on failure.

  Failure policy unchanged: items failing the chosen path stay checked
  and are reported; never silently dropped.

  Rejected: archive-bit mark-then-sweep (`attrib +A`, `del /a:a`,
  `robocopy /IA:A`) — a real Windows idiom but built for incremental
  backups (`xcopy /m`); redundant with the in-memory checkbox model.
  Rejected (SUPERSEDED by AD-11, operator-directed 2026-10-06):
  elevated delete helper for the ordinary-delete path — admin ≠
  TrustedInstaller and it was the wrong fix for the no-recycle-bin
  failure class. Session elevation returns in AD-11 as an opt-in for
  system-owned targets where it IS required.
- **AD-7** Runtime identity override via `.env` (`WINDISK_APP_NAME`,
  `WINDISK_PRODUCT_ID`) — loaded by `_load_env()` before constants bind;
  `.env` gitignored, `.env.example` committed.

- **AD-11** (PROPOSED — pending signoff) Windows.old + system space
  reclaim: a "System Reclaim" surface (Tools menu) listing detected
  reclaimable categories with sizes, checkboxes, and one Reclaim
  button. Pro-gated (it is a delete-class operation, AD-3).

  *Elevation foundation (persisted default drives UAC timing).*
  System-owned targets cannot be deleted unelevated —
  `Windows.old`, `C:\Windows\Temp`, SoftwareDistribution, WinSxS,
  hiberfil all require admin, and the silent/automated cleanup
  handlers require it too. `allowElevate` is a persisted Settings
  checkbox AND the override of the per-session rule:

  - `allowElevate` ON (persisted): at launch the app treats the
    setting as the checked-box gesture — UAC fires immediately at
    startup, the elevated channel is established once, and every
    privileged op runs silently for the session. The user never
    re-checks anything; the setting IS the standing consent.
  - `allowElevate` OFF/never set: checking the box mid-session
    fires UAC at that moment (consent and elevation are the same
    gesture); declined UAC reverts the box. Ops needing admin
    while unchecked are marked "needs administrator", not blocked
    silently.

  Mechanism: a single cached elevated channel per session —
  primary = elevated `IFileOperation`/`ShellExecute` via the COM
  elevation moniker
  (`Elevation:Administrator!new:{3AD05575-8857-4850-9277-11B85BDB8E09}`);
  fallback = a persistent `runas` helper process (same exe,
  `--elevated-worker`, named-pipe job/result protocol, random
  pipe name). Windows mandates one UAC per elevation event — the
  persisted setting controls WHEN it fires (launch vs. checkbox
  click), never how many times Windows asks. Admin still ≠
  TrustedInstaller — the tier list below is ordered so the OS's own
  handlers (which carry the right ownership/ACL logic) run first.

  *Windows.old (`C:\Windows.old`, plus upgrade remnants
  `$Windows.~BT`, `$Windows.~WS`, `C:\ESD\Windows`) — three tiers:*
  - Tier 1 (default): hand off to Microsoft's own handler —
    `cleanmgr.exe /AUTOCLEAN` elevated (silent, removes Previous
    Windows Installation + related handlers) or the `SilentCleanup`
    scheduled task. Correct ACL/ownership handling by definition;
    headless; also sweeps other upgrade leftovers.
  - Tier 2 (fallback when Tier 1 reports nothing removed):
    elevated brute force — `takeown /f <path> /r /d y` +
    `icacls <path> /reset /t /c /q` then the configured delete
    engine (robomirror). Explicitly labeled "slow, deep ACL churn —
    last resort"; progress + cancel required (~200k-file trees).
  - Tier 3 (always): open the sanctioned UI —
    `ms-settings:storagesense` / interactive `cleanmgr` — if
    automation fails outright. Never silently no-op.
  - Confirmation states plainly: deleting Windows.old permanently
    removes the option to roll back the last Windows upgrade (the
    OS would auto-delete it ~10 days post-upgrade anyway).

  *Other reclaim categories (flat list, per-row size + badge):*
  - Recycle bins, all fixed drives — `SHEmptyRecycleBin`;
    unelevated for the caller's own items. Badge: safe.
  - `%TEMP%` + `C:\Windows\Temp` — delete engine; Windows\Temp
    needs the elevated channel. Badge: safe / admin.
  - `C:\Windows\SoftwareDistribution\Download` (Update cache) —
    elevated; stop `wuauserv` first, restart after. Badge: admin.
  - Delivery Optimization cache — elevated. Badge: admin.
  - Memory dumps (`MEMORY.DMP`, `Minidump\`) — elevated. Badge:
    safe after admin.
  - WinSxS component cleanup — `Dism.exe /online /Cleanup-Image
    /StartComponentCleanup`, elevated; optional `/ResetBase`
    checkbox with warning that installed updates become
    uninstallable (permanent). Badge: admin + caution.
  - Hibernation — `powercfg /h off`, elevated; functional change:
    disables hibernate AND Fast Startup; checkbox off by default
    with the consequence stated in the row. Badge: functional
    change.
  - Rejected: pagefile resizing/deletion — performance
    destabilisation risk vastly outweighs the reclaim.

  *Detection/sizing:* on drive load, probe the fixed well-known
  paths above; sizes come from the existing scandir walk —
  ACL-denied subtrees report a `>=` lower bound rather than a fake
  exact figure. Windows.old rows that need admin to size are
  marked "size unknown until elevated".

  *Failure policy unchanged (AD-2/AD-10):* per-category result
  reported; failed rows stay checked; UAC-declined is a stated
  outcome, not a crash.

## 6. Outstanding

- Real `.ico`, Authenticode signing, purchase flow (webhook → keygen →
  email). `LICENSE.txt` + `LICENSE-Qt-LGPL.txt` done and shipped in
  NSIS/MSIX.
- MSIX uses dev identity `RobinCheung.DiskOccupancy`/`CN=DiskOccupancy` —
  Partner Center values required for actual Store submission.
- Future: `$MFT` raw-read mode (WizTree method, admin required).
