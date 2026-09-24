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


# ============================================================================
# PDF 内文字绘制用的项目自带字体（两套互补字库）
#   Regular  ：常用字库，含常用汉字(0x4E00-0x9FFF)/ASCII/中文标点
#   RegularL3：生僻字补充库，含康熙部首与 CJK 扩展 B+ 生僻字，不含常用字
# 两套字体族名相同（Alibaba PuHuiTi 3.0），供 reportlab/fitz 逐字形混排使用。
# ============================================================================
FONT_REGULAR_NAME = "AlibabaPuHuiTi-3-55-Regular.ttf"
FONT_RARE_NAME = "AlibabaPuHuiTi-3-55-RegularL3.ttf"

# 角色标识：调用方按角色映射到自己在 reportlab/fitz 中注册的字体
FONT_ROLE_REGULAR = "regular"
FONT_ROLE_RARE = "rare"


def get_project_root_path():
    """获取项目根目录（模块级，供非 PDFToolBase 实例的调用方复用，兼容打包模式）"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def get_pdf_text_font_paths():
    """返回 PDF 内文字绘制可用的项目自带字体：[(role, Path), ...]，常用库在前、生僻库在后。

    常用库 Regular 为必需，缺失即报错（不静默降级、不回退系统字体）；
    生僻库 RegularL3 为可选增强，缺失时仅跳过（不影响常用文字渲染）。
    """
    image_dir = get_project_root_path() / "Image"
    regular = image_dir / FONT_REGULAR_NAME
    if not regular.exists():
        raise FileNotFoundError(f"项目自带字体不存在：{regular}")
    paths = [(FONT_ROLE_REGULAR, regular)]
    rare = image_dir / FONT_RARE_NAME
    if rare.exists():
        paths.append((FONT_ROLE_RARE, rare))
    return paths


class PdfTextFontMixer:
    """按字形覆盖把文本切成 [(role, substring), ...]，供 reportlab/fitz 逐段切换字体绘制。

    规则：逐字优先用常用库 Regular；Regular 没有的生僻字用 L3；两者都无覆盖则归入常用库
    （由渲染端映射为 .notdef）。cmap 懒加载并缓存，纯 GUI 工具不会触发字体解析开销。
    """

    def __init__(self, font_paths=None):
        # font_paths: [(role, Path), ...]，默认取项目自带两套字体
        self._font_paths = list(font_paths) if font_paths is not None else get_pdf_text_font_paths()
        self._cmaps = None  # 懒加载缓存：[(role, set(codepoints)), ...]

    @property
    def font_paths(self):
        """当前参与混排的字体：[(role, Path), ...]，供调用方逐一注册到 reportlab/fitz"""
        return list(self._font_paths)

    def _load_cmaps(self):
        if self._cmaps is not None:
            return self._cmaps
        from fontTools.ttLib import TTFont
        cmaps = []
        for role, path in self._font_paths:
            tt = TTFont(str(path))
            best = None
            for table in tt['cmap'].tables:
                if table.isUnicode() and (best is None or len(table.cmap) > len(best.cmap)):
                    best = table
            cmaps.append((role, set(best.cmap.keys()) if best is not None else set()))
            tt.close()
        self._cmaps = cmaps
        return self._cmaps

    def role_for_char(self, ch):
        """返回单个字符应使用的字体角色（常用库优先，其次生僻库，都无则常用库）"""
        code = ord(ch)
        for role, cmap in self._load_cmaps():
            if code in cmap:
                return role
        return self._font_paths[0][0]

    def split(self, text):
        """把 text 切成 [(role, substring), ...]，相邻同角色字符合并为一段"""
        runs = []
        for ch in text:
            role = self.role_for_char(ch)
            if runs and runs[-1][0] == role:
                runs[-1] = (role, runs[-1][1] + ch)
            else:
                runs.append((role, ch))
        return runs


class PDFToolBase:

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
            # PyInstaller 打包后资源文件位于 _internal/ 子目录（sys._MEIPASS）
            return Path(sys._MEIPASS)
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
        """加载自定义字体并应用到根窗口；失败时直接抛错，不允许回退到 Arial"""
        project_root = self._get_project_root()
        font_path = project_root / "Image" / FONT_REGULAR_NAME

        if not font_path.exists():
            raise FileNotFoundError(f"项目自带字体不存在：{font_path}")

        try:
            from fontTools.ttLib import TTFont

            # 解析字体名称表获取字体族名称
            tt = TTFont(str(font_path))
            font_family = 'Arial'
            for record in tt['name'].names:
                if record.nameID == 1:  # Font Family
                    font_family = record.toUnicode()
                    break
            tt.close()

            # 使用 Windows API 注册字体
            if os.name == 'nt':
                import ctypes
                font_path_str = str(font_path).encode('utf-16-le') + b'\x00'
                ctypes.windll.gdi32.AddFontResourceW(font_path_str)
        except Exception as e:
            raise RuntimeError(f"无法加载项目自带字体：{font_path}，错误：{e}") from e

        self.root.option_add("*Font", (font_family, 10))
        self.current_font = (font_family, 10)

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
