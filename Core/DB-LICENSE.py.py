"""
许可证检查工具打包脚本
使用 PyInstaller 将 LICENSE.py 打包为可执行文件
"""
import sys
import os
from pathlib import Path

def build_executable():
    """构建可执行文件"""
    import PyInstaller.__main__
    
    # 获取项目根目录和 Core 目录
    project_root = Path(__file__).parent.parent
    core_dir = Path(__file__).parent
    
    # 许可证文件路径
    license_file = project_root / "Image" / "LICENSE.txt"
    
    if not license_file.exists():
        print(f"警告: 未找到许可证文件 {license_file}")
        print("请确保 Image/LICENSE.txt 文件存在")
        return False
    
    # PyInstaller 参数配置
    pyinstaller_args = [
        str(core_dir / "LICENSE.py"),  # 主脚本
        "--name=LICENSE",              # 输出文件名（生成 LICENSE.exe）
        "--onefile",                    # 单文件打包
        "--console",                    # 控制台应用
        "--clean",                      # 清理临时文件
        
        # 包含许可证文件（重要！）
        f"--add-data={license_file};Image",  # Windows 使用分号分隔
        
        # 图标配置
        f"--icon={project_root / 'Image' / 'icon.ico'}",
        
        # 隐藏导入（如果需要）
        "--hidden-import=hashlib",
        "--hidden-import=pathlib",
        
        # 排除不必要的模块以减小体积
        "--exclude-module=tkinter",
        "--exclude-module=PIL",
        "--exclude-module=numpy",
    ]
    
    print("=" * 60)
    print("开始打包许可证检查工具...")
    print("=" * 60)
    print(f"源文件: {core_dir / 'LICENSE.py'}")
    print(f"许可证文件: {license_file}")
    print(f"图标文件: {project_root / 'Image' / 'icon.ico'}")
    print(f"输出目录: {project_root / 'dist'}")
    print("=" * 60)
    
    try:
        PyInstaller.__main__.run(pyinstaller_args)
        print("\n" + "=" * 60)
        print("✓ 打包完成!")
        print(f"可执行文件位置: {project_root / 'dist' / 'LICENSE.exe'}")
        print("=" * 60)
        return True
    except Exception as e:
        print(f"\n✗ 打包失败: {e}")
        return False

def create_spec_file():
    """创建 .spec 配置文件（用于高级定制）"""
    project_root = Path(__file__).parent.parent
    core_dir = Path(__file__).parent
    license_file = project_root / "Image" / "LICENSE.txt"
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{core_dir / "LICENSE.py"}'],
    pathex=[],
    binaries=[],
    datas=[('{license_file}', 'Image')],  # 包含许可证文件
    hiddenimports=['hashlib', 'pathlib'],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=['tkinter', 'PIL', 'numpy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LICENSE',
    icon='{project_root / "Image" / "icon.ico"}',
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
)
'''
    
    spec_path = core_dir / "LICENSE_build.spec"
    with open(spec_path, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"✓ Spec 文件已创建: {spec_path}")
    print(f"使用命令打包: pyinstaller {spec_path}")
    return spec_path

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="许可证检查工具打包脚本")
    parser.add_argument(
        '--spec', 
        action='store_true', 
        help='仅生成 .spec 配置文件，不执行打包'
    )
    
    args = parser.parse_args()
    
    if args.spec:
        create_spec_file()
    else:
        success = build_executable()
        sys.exit(0 if success else 1)
