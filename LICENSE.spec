# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['d:\\Users\\ningh\\snow-toolbox-master\\Core\\LICENSE.py'],
    pathex=[],
    binaries=[],
    datas=[('d:\\Users\\ningh\\snow-toolbox-master\\Image\\LICENSE.txt', 'Image')],
    hiddenimports=['hashlib', 'pathlib'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'PIL', 'numpy'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='LICENSE',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['d:\\Users\\ningh\\snow-toolbox-master\\Image\\icon.ico'],
)
