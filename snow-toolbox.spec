# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# 项目根目录 - SPECPATH 是 spec 文件所在目录,不需要 .parent
project_root = Path(SPECPATH)

# 应用名称和版本
app_name = "snow-toolbox"
version = "3.0.0"

# 主脚本
main_script = "San Yuan Gong Ju_V3-0-0.py"

# 数据文件: (源路径, 目标目录)
datas = [
    ("D:\\Users\\ningh\\snow-toolbox-master\\Core", "Core"),
            ("D:\\Users\\ningh\\snow-toolbox-master\\Image", "Image"),
            ("D:\\Users\\ningh\\snow-toolbox-master\\Audio tool", "Audio tool"),
            ("D:\\Users\\ningh\\snow-toolbox-master\\File tool", "File tool")
]

# 隐藏导入
hiddenimports = [
    "flet",
    "flet.core"
]

# 分析主脚本
a = Analysis(
    [main_script],
    pathex=[str(project_root)],
    binaries=[],
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
    name=app_name,
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
    icon=str(project_root / "Image" / "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=app_name,
)
