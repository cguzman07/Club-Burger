# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — Club Burger POS
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None
ROOT = Path(SPECPATH).resolve()

datas = [
    (str(ROOT / "assets"), "assets"),
    (str(ROOT / "logo.bmp.png"), "."),
]
binaries = []
hiddenimports = [
    "win32print",
    "win32ui",
    "win32api",
    "pywintypes",
    "pythoncom",
    "PIL",
    "PIL.Image",
    "PIL.ImageWin",
    "PIL.ImageTk",
    "customtkinter",
    "matplotlib",
    "matplotlib.backends.backend_tkagg",
]

tmp_ret = collect_all("customtkinter")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

try:
    tmp_dark = collect_all("darkdetect")
    datas += tmp_dark[0]
    binaries += tmp_dark[1]
    hiddenimports += tmp_dark[2]
except Exception:
    pass

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Club Burger",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "club_burger.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Club Burger",
)
