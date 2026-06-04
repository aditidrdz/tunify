# PyInstaller spec file for Tunify - builds a single Tunify.exe
#
# Build with:
#     pyinstaller Tunify.spec --clean --noconfirm
#
# Output: dist/Tunify.exe  (single file, no Python install required to run)

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Bundle Flask templates, static files, and yt-dlp's extractor data.
datas = []
datas += [("templates", "templates")]
datas += [("static", "static")]
datas += collect_data_files("yt_dlp")
datas += collect_data_files("certifi")  # SSL CA bundle (used by urllib/requests)

# yt-dlp lazy-imports extractors, so PyInstaller can miss them.
hiddenimports = []
hiddenimports += collect_submodules("yt_dlp.extractor")
hiddenimports += collect_submodules("yt_dlp.downloader")
hiddenimports += collect_submodules("yt_dlp.postprocessor")

a = Analysis(
    ["launch.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim some heavy modules we don't use.
        "tkinter",
        "test",
        "unittest",
        "pydoc",
        "doctest",
        "playwright",
        "pyinstaller",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Tunify",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,           # UPX can confuse Windows Defender; skip.
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,        # Keep console so users see startup messages + errors.
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
