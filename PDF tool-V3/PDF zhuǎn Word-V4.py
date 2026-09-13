# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import os
import logging
import threading
import importlib.util
from pathlib import Path

import flet as ft

import pdf2docx

# 静默 pdf2docx 内部日志，避免控制台刷屏
try:
    from pdf2docx import settings as _pdf2docx_settings
    if hasattr(_pdf2docx_settings, 'logging_level'):
        _pdf2docx_settings.logging_level = logging.WARNING
except Exception:
    pass

import fitz  # PyMuPDF：pdf2docx 的底层依赖，用于读取页数

from pdf2docx import Converter


def get_project_root():
    """获取项目根目录"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def run_startup_preflight():
    """复用 Core 公共基类执行启动前置流程：授权检查 -> 窗口图标 -> 字体加载；失败时直接报错"""
    base_file = get_project_root() / 'Core' / 'Public base class.py'
    if not base_file.exists():
        raise FileNotFoundError(f"缺少公共基类：{base_file}")

    spec = importlib.util.spec_from_file_location('public_base_class', str(base_file))
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载公共基类：{base_file}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    try:
        base = module.PDFToolBase(root)
        if not root.winfo_exists():
            raise RuntimeError("授权或窗口初始化失败")

        current_font = getattr(base, 'current_font', None)
        if not current_font:
            raise RuntimeError("公共基类未成功加载字体")

        font_family = current_font[0]
        return True, font_family
    except Exception as exc:
        if root.winfo_exists():
            root.destroy()
        raise RuntimeError(f"启动前置检查失败：无法使用项目自带字体。{exc}") from exc
    finally:
        if root.winfo_exists():
            root.destroy()


STARTUP_OK, APP_FONT_FAMILY = run_startup_preflight()
if not STARTUP_OK:
    raise RuntimeError("启动前置检查失败：项目自带字体无法使用")


class PDFToWordApp:
    """PDF转Word：选择 PDF -> 选择保存位置 -> pdf2docx 后台多进程转换"""

    def __init__(self):
        self.page = None
        self.input_file = None
        self.total_pages = 0
        self.processing = False
        self.font_family = APP_FONT_FAMILY

    def build(self, page: ft.Page):
        self.page = page
        page.title = "PDF转Word"
        page.window.width = 660
        page.window.height = 660
        page.window.min_width = 580
        page.window.min_height = 560
        page.window.center()
        page.padding = 16
        page.theme_mode = ft.ThemeMode.LIGHT

        # 设置窗口图标
        icon_path = get_project_root() / 'Image' / 'icon.ico'
        if icon_path.exists():
            page.window.icon = str(icon_path)

        # 文件选择 / 保存对话框
        self.file_picker = ft.FilePicker(on_result=self.on_file_picked)
        self.save_picker = ft.FilePicker(on_result=self.on_save_picked)
        page.overlay.extend([self.file_picker, self.save_picker])

        # PDF 文件卡片
        self.file_text = ft.Text(
            "未选择文件",
            size=13,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
            expand=True,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        file_card = self._make_card(
            "PDF文件",
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.INSERT_DRIVE_FILE, size=18, color=ft.Colors.BLUE_GREY_400),
                            self.file_text,
                            ft.ElevatedButton("选择文件", icon=ft.Icons.UPLOAD_FILE, on_click=self.select_file, height=36),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    ft.Text(
                        "选择要转换的 PDF 文档，转换后保留文本、图片与表格布局",
                        size=12,
                        color=ft.Colors.BLUE_GREY_500,
                        font_family=self.font_family,
                    ),
                ],
                spacing=8,
            ),
        )

        # 使用说明卡片
        note_card = self._make_card(
            "使用说明",
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.INFO_OUTLINE, size=18, color=ft.Colors.BLUE),
                            ft.Text(
                                "1. 选择 PDF 文件\n2. 点击「转换为Word」并选择保存位置\n3. 转换完成后自动打开所在文件夹",
                                size=13,
                                color=ft.Colors.BLUE_GREY_700,
                                font_family=self.font_family,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    ft.Text(
                        "提示：纯扫描/图片型 PDF（无可选文字层）转换结果可能为空白页，请先进行 OCR。",
                        size=12,
                        color=ft.Colors.ORANGE_900,
                        font_family=self.font_family,
                    ),
                ],
                spacing=8,
            ),
        )

        # 进度条与操作按钮
        self.progress = ft.ProgressBar(
            visible=False,
            color=ft.Colors.BLUE,
            bgcolor=ft.Colors.GREY_200,
            bar_height=6,
            border_radius=4,
            expand=True,
        )
        self.progress_text = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)
        self.convert_btn = ft.ElevatedButton(
            "转换为Word",
            icon=ft.Icons.TRANSFORM,
            on_click=self.convert_to_word,
            height=40,
        )

        # 底部状态栏
        self.status_text = ft.Text("就绪", size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)
        self.stats_text = ft.Text(size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)

        page.add(
            ft.Column(
                [
                    # 顶部标题栏
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.DESCRIPTION, size=32, color=ft.Colors.BLUE),
                            ft.Text("PDF转Word", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Divider(thickness=1, opacity=0.3),
                    file_card,
                    note_card,
                    ft.Row(
                        [self.progress, self.progress_text],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Row([self.convert_btn], alignment=ft.MainAxisAlignment.END),
                    # 底部状态栏
                    ft.Container(
                        content=ft.Row(
                            [self.status_text, self.stats_text],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=ft.padding.symmetric(vertical=8, horizontal=12),
                        bgcolor=ft.Colors.BLUE_GREY_50,
                        border_radius=8,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                    ),
                ],
                expand=True,
                spacing=10,
            )
        )

    def _make_card(self, title, content):
        """创建白色圆角卡片（与主程序工具卡片风格一致）"""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        title,
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_GREY_700,
                        font_family=self.font_family,
                    ),
                    content,
                ],
                spacing=8,
            ),
            padding=ft.padding.all(12),
            border_radius=10,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )

    # ---------- 文件选择 ----------
    def select_file(self, e):
        if self.processing:
            return
        self.file_picker.pick_files(
            dialog_title="选择PDF文件",
            allow_multiple=False,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["pdf"],
        )

    def on_file_picked(self, e):
        if not e.files:
            return
        file = e.files[0].path
        if not os.path.exists(file):
            self.show_status("文件不存在", success=False)
            return
        if not file.lower().endswith('.pdf'):
            self.show_status("请选择PDF文件", success=False)
            return
        self.input_file = file
        self.file_text.value = os.path.basename(file)
        self.file_text.color = ft.Colors.BLUE_GREY_900
        self.file_text.tooltip = file
        self._refresh_page_info()
        self.page.update()

    def _refresh_page_info(self):
        """读取并展示 PDF 总页数"""
        try:
            doc = fitz.open(self.input_file)
            try:
                self.total_pages = len(doc)
            finally:
                doc.close()
            self.stats_text.value = f"共 {self.total_pages} 页"
            self.stats_text.color = ft.Colors.BLUE_GREY_700
        except Exception:
            self.total_pages = 0
            self.stats_text.value = ""

    def convert_to_word(self, e):
        """校验输入后弹出保存对话框"""
        if self.processing:
            return
        if not self.input_file:
            self.show_status("请先选择PDF文件", success=False)
            return
        if not os.path.exists(self.input_file):
            self.show_status("PDF文件不存在", success=False)
            return

        base_name = os.path.splitext(os.path.basename(self.input_file))[0]
        self.save_picker.save_file(
            dialog_title="保存Word文档",
            file_name=f"{base_name}.docx",
            allowed_extensions=["docx"],
        )

    def on_save_picked(self, e):
        if not e.path:
            return
        output_path = e.path
        if not output_path.lower().endswith('.docx'):
            output_path += '.docx'

        # 锁定界面并显示转换动画（pdf2docx 无逐页回调，用不确定进度条）
        self.processing = True
        self.convert_btn.disabled = True
        self.progress.value = None  # 不定长动画
        self.progress.visible = True
        self.progress_text.value = "转换中..."
        self.page.update()
        self.show_status("正在准备转换...")

        threading.Thread(
            target=self._do_convert,
            args=(output_path,),
            daemon=True,
        ).start()

    def _do_convert(self, output_path):
        """后台线程：pdf2docx 多进程并行转换"""
        cv = None
        try:
            # 后台线程内创建 Converter，避免阻塞 UI 线程
            cv = Converter(self.input_file)
            total_pages = len(cv.pages)
            self.status_text.value = f"正在转换（共 {total_pages} 页，多进程并行）..."
            self.status_text.update()

            # 优先启用多进程并行转换（pdf2docx 官方加速开关）；
            # 旧版本不支持该参数时自动回退到单进程模式
            try:
                cv.convert(output_path, multi_processing=True, worker_count=4)
            except TypeError:
                cv.convert(output_path)

            self.progress.value = 0
            self.progress.visible = False
            self.progress.update()
            self.show_status(f"转换完成！共 {total_pages} 页")
            self.show_info("成功", f"PDF转Word完成！\n共 {total_pages} 页\n保存到: {output_path}")
            self._open_output_folder(os.path.dirname(output_path))
        except Exception as err:
            message = self._friendly_error(err)
            self.show_status(f"转换失败: {message}", success=False)
        finally:
            if cv is not None:
                try:
                    cv.close()
                except Exception:
                    pass
            self.processing = False
            self.convert_btn.disabled = False
            self.progress.visible = False
            self.progress_text.value = ""
            self.page.update()

    @staticmethod
    def _friendly_error(error: Exception) -> str:
        """将底层异常映射为用户友好的错误提示"""
        message = str(error)
        if "Permission denied" in message:
            return "无法访问输出文件，请确保文件未被其他程序占用且有写入权限。"
        if "not found" in message.lower():
            return "找不到指定的PDF文件，请确保文件路径正确。"
        if "index out of range" in message.lower():
            return "PDF文件格式异常，无法正确读取页面内容。"
        if "memory" in message.lower():
            return "内存不足，请尝试转换较小的PDF文件或关闭其他应用程序后重试。"
        return message

    def _open_output_folder(self, folder_path):
        """在文件资源管理器中打开输出文件夹"""
        try:
            if not folder_path:
                return
            if sys.platform == 'win32':
                os.startfile(folder_path)
            elif sys.platform == 'darwin':
                os.system(f'open "{folder_path}"')
            else:
                os.system(f'xdg-open "{folder_path}"')
        except Exception as err:
            print(f"无法打开输出文件夹: {err}")

    # ---------- 通用 UI 辅助 ----------
    def show_status(self, message: str, success: bool = True):
        """更新状态栏并显示全局提示消息"""
        self.status_text.value = message
        self.page.snack_bar = ft.SnackBar(
            ft.Text(message, font_family=self.font_family),
            bgcolor=ft.Colors.GREEN if success else ft.Colors.RED,
            open=True,
        )
        self.page.update()

    def show_info(self, title: str, message: str):
        """显示结果弹窗"""
        self.page.dialog = ft.AlertDialog(
            title=ft.Text(title, font_family=self.font_family),
            content=ft.Text(message, font_family=self.font_family),
            actions=[ft.TextButton("关闭", on_click=lambda e: self.close_dialog())],
        )
        self.page.dialog.open = True
        self.page.update()

    def close_dialog(self, e=None):
        """关闭当前对话框"""
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()


if __name__ == '__main__':
    app = PDFToWordApp()
    ft.app(target=app.build)
