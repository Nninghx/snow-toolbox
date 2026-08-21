# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

"""
项目公共基类
提供窗口图标设置、授权验证、字体加载等通用功能
"""

import os
import subprocess
import tkinter as tk
from tkinter import messagebox
from pathlib import Path


class PDFToolBase:
    """PDF工具基类，提供通用的初始化功能"""

    def __init__(self, root):
        """基础初始化：授权检查 -> 窗口图标 -> 字体加载"""
        self.root = root

        if not self.check_license():
            messagebox.showerror(
                "错误",
                "缺少授权！无法使用！请先获取授权！\n"
            )
            root.destroy()
            return

        self.set_window_icon()
        self.load_font()

    def _get_project_root(self):
        """获取项目根目录"""
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parent.parent

    def set_window_icon(self):
        """设置应用程序窗口图标"""
        project_root = self._get_project_root()
        image_dir = project_root / "Image"

        icon_ico_path = image_dir / "icon.ico"
        icon_png_path = image_dir / "icon.png"

        # Windows系统设置应用ID
        if os.name == 'nt':
            try:
                import ctypes
                app_id = f"snow_toolbox_master.{self.__class__.__name__}"
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
            except Exception:
                pass

        # 尝试设置ICO图标
        if icon_ico_path.exists():
            try:
                self.root.iconbitmap(default=str(icon_ico_path))
            except Exception:
                try:
                    self.root.iconbitmap(str(icon_ico_path))
                except Exception:
                    pass

        # 尝试设置PNG图标
        if hasattr(self.root, "iconphoto") and icon_png_path.exists():
            try:
                self._icon_image = tk.PhotoImage(file=str(icon_png_path))
                self.root.iconphoto(True, self._icon_image)
            except Exception:
                pass

    def check_license(self):
        """检查授权验证"""
        # 如果通过主程序启动（环境变量已设置），则跳过授权验证
        if os.environ.get('MAIN_APP_AUTHORIZED') == '1':
            return True

        try:
            project_root = self._get_project_root()
            core_dir = project_root / "Core"
            license_exe_path = core_dir / "LICENSE.exe"
            if license_exe_path.exists():
                result = subprocess.run(
                    [str(license_exe_path), '--quiet'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.returncode == 0
        except Exception as e:
            print(f"许可证验证异常: {e}")
            return False

    def load_font(self):
        """通过 FontManager 加载字体"""
        project_root = self._get_project_root()
        
        # 确保项目根目录在 sys.path 中（支持独立运行）
        root_str = str(project_root)
        if root_str not in sys.path:
            sys.path.insert(0, root_str)
        
        from Core.FontManager import FontManager

        font_path = project_root / "Image" / "AlibabaPuHuiTi-3-55-RegularL3.ttf"

        if not font_path.exists():
            print(f"警告: 找不到字体文件: {font_path}，使用系统默认字体")

        self.current_font = FontManager.apply_to_root(self.root, 10)

    def apply_font_to_widgets(self, widgets=None):
        """为指定控件列表应用字体"""
        if widgets is None:
            return
        for widget in widgets:
            try:
                if isinstance(widget, (tk.Label, tk.Button, tk.Radiobutton, tk.Entry)):
                    widget.config(font=(self.current_font[0], 10))
                elif isinstance(widget, tk.LabelFrame):
                    widget.config(font=(self.current_font[0], 10, "bold"))
            except Exception:
                continue
