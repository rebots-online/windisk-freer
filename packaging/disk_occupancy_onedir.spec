# PyInstaller spec — ONEDIR windowed build, payload for MSIX/Store packaging.
# Build: pyinstaller packaging\disk_occupancy_onedir.spec --clean --noconfirm
# Output: dist\DiskOccupancy\  (folder, not single exe — MSIX packs loose files)
a = Analysis(
    ['../disk_occupancy.py'],
    pathex=['..', 'C:/Users/Admin/tools/licensing'],
    binaries=[],
    datas=[('../version.txt', '.')],
    hiddenimports=['send2trash', 'rlmc_license', 'cryptography'],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'numpy', 'pandas', 'matplotlib'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DiskOccupancy',
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=None,
    version='version_info.txt',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='DiskOccupancy',
)
