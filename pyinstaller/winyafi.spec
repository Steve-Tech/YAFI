# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = [('LpcCrOSEC.bin', '.')]
datas += collect_data_files('yafi')


a = Analysis(
    ['winyafi.py'],
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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='winyafi',
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
    uac_admin=True,
)
