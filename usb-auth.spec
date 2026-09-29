# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for the single-file Windows executable.

    python -m PyInstaller --noconfirm usb-auth.spec
    -> dist/USB-Authentication-Tool.exe

Notes
-----
* pywin32 is imported *inside* functions by auth.py, driveletter.py and eject.py
  (so the pure logic stays importable everywhere), which means PyInstaller cannot
  discover it statically - hence the explicit hidden imports below. win32timezone
  is pulled in indirectly by the win32com module loader.
* The build is a console application on purpose: the log stream is how an
  operator diagnoses a device that was rejected.
* authfile.example.txt and README.md are bundled so the executable folder is
  self-documenting. The live authfile.txt is created next to the .exe on first
  run (see config.app_dir) and is never bundled.
"""

APP_NAME = "USB-Authentication-Tool"
ENTRY_POINT = "main.py"

HIDDEN_IMPORTS = [
    "win32api",
    "win32file",
    "win32com",
    "win32com.client",
    "win32timezone",
    "pywintypes",
    "pythoncom",
]

DATAS = [
    ("authfile.example.txt", "."),
    ("README.md", "."),
]

a = Analysis(
    [ENTRY_POINT],
    pathex=[],
    binaries=[],
    datas=DATAS,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "ruff"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # point this at an .ico if you add one
)
