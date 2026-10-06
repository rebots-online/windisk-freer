# PyInstaller spec — single-file, windowed (no console) commercial build.
# Build: pyinstaller packaging\disk_occupancy.spec --clean --noconfirm
a = Analysis(
    ['../disk_occupancy.py'],
    pathex=['..', 'C:/Users/Admin/tools/licensing'],
    binaries=[],
    datas=[('../version.txt', '.')],
    hiddenimports=['send2trash', 'rlmc_license', 'cryptography', 'segno'],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'numpy', 'pandas', 'matplotlib'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DiskOccupancy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,            # GUI subsystem — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=None,                # set 'app.ico' here once a real icon exists
    version='version_info.txt',
    uac_admin=False,          # no manifest elevation; denied dirs are reported
)
