# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import sys
import shutil
import subprocess
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent

# 打包配置
APP_NAME = "snow-toolbox"
MAIN_SCRIPT = "San Yuan Gong Ju_V3-0-0.py"
VERSION = "3.0.0"

# 子工具目录和文件
TOOLS = {
    "Audio tool": ["Yin Pin Ti Qu VV3-0-0.py"],
    
}

# 资源目录
RESOURCE_DIRS = ["Core", "Image"]

# 隐藏导入模块
HIDDEN_IMPORTS = [
    "flet",
    "flet.core",
]


def clean_build():
    """清理之前的构建文件"""
    dirs_to_clean = ["build", "dist"]
    for d in dirs_to_clean:
        path = PROJECT_ROOT / d
        if path.exists():
            print(f"清理 {d}/ 目录...")
            shutil.rmtree(path)


def build_spec_file():
    """生成 PyInstaller spec 文件"""
    
    # 收集所有数据文件
    datas = []
    
    # 添加资源目录
    for res_dir in RESOURCE_DIRS:
        res_path = PROJECT_ROOT / res_dir
        if res_path.exists():
            datas.append((str(res_path), res_dir))
    
    # 添加子工具目录
    for tool_dir, tool_files in TOOLS.items():
        tool_path = PROJECT_ROOT / tool_dir
        if tool_path.exists():
            datas.append((str(tool_path), tool_dir))
    
    # 数据文件字符串 - 使用正斜杠或双反斜杠避免转义问题
    datas_str = ",\n            ".join([f'("{src.replace(chr(92), chr(92)+chr(92))}", "{dst}")' for src, dst in datas])
    
    # 隐藏导入字符串
    hidden_imports_str = ",\n    ".join([f'"{mod}"' for mod in HIDDEN_IMPORTS])
    
    spec_content = f'''# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# 项目根目录 - SPECPATH 是 spec 文件所在目录,不需要 .parent
project_root = Path(SPECPATH)

# 应用名称和版本
app_name = "{APP_NAME}"
version = "{VERSION}"

# 主脚本
main_script = "{MAIN_SCRIPT}"

# 数据文件: (源路径, 目标目录)
datas = [
    {datas_str}
]

# 隐藏导入
hiddenimports = [
    {hidden_imports_str}
]

# 分析主脚本
a = Analysis(
    [main_script],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
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
'''
    
    spec_file = PROJECT_ROOT / f"{APP_NAME}.spec"
    with open(spec_file, "w", encoding="utf-8") as f:
        f.write(spec_content)
    
    print(f"已生成 spec 文件: {spec_file}")
    return spec_file


def run_pyinstaller(spec_file):
    """运行 PyInstaller 打包"""
    cmd = ["pyinstaller", str(spec_file), "--clean"]
    print(f"执行命令: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    
    if result.returncode != 0:
        print("打包失败!")
        return False
    
    print("打包成功!")
    return True


def main():
    print("=" * 50)
    print(f"{APP_NAME} 打包脚本 v{VERSION}")
    print("=" * 50)
    
    # 检查 PyInstaller 是否安装
    try:
        subprocess.run(["pyinstaller", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("错误: PyInstaller 未安装!")
        print("请运行: pip install pyinstaller")
        sys.exit(1)
    
    # 检查主脚本是否存在
    if not (PROJECT_ROOT / MAIN_SCRIPT).exists():
        print(f"错误: 主脚本 {MAIN_SCRIPT} 不存在!")
        sys.exit(1)
    
    # 清理旧构建
    clean_build()
    
    # 生成 spec 文件
    spec_file = build_spec_file()
    
    # 运行打包
    if run_pyinstaller(spec_file):
        output_dir = PROJECT_ROOT / "dist" / APP_NAME
        print(f"\\n打包完成!")
        print(f"输出目录: {output_dir}")
        print(f"可执行文件: {output_dir / APP_NAME}.exe")


if __name__ == "__main__":
    main()
