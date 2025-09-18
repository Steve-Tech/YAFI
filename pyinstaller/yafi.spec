# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--onefile", action="store_true")
options = parser.parse_args()

datas = [('LpcCrOSEC.bin', '.')] if os.name == 'nt' and os.path.exists('LpcCrOSEC.bin') else []
datas += collect_data_files('yafi')

a = Analysis(
    ['entrypoint.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['cros_ec_python'],
    hookspath=[],
    hooksconfig={"gi":{"module-versions": {"Gtk": "4.0"}}},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

if options.onefile:
    splash = Splash(
      'splash.png',
      binaries=a.binaries,
      datas=a.datas,
      text_pos=(4, 480),
      # Text doesn't scale on Linux, but does on Windows
      text_size=12 if os.name == 'nt' else 6,
      minify_script=True,
      always_on_top=True,
  )

exe_args = (
    [
        a.scripts,
        a.binaries,
        a.datas,
        splash,
        splash.binaries,
    ]
    if options.onefile
    else [a.scripts]
)

exe = EXE(
    pyz,
    *exe_args,
    exclude_binaries=not options.onefile,
    name='YAFI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['yafi.ico'],
)

if not options.onefile:
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='YAFI',
    )
