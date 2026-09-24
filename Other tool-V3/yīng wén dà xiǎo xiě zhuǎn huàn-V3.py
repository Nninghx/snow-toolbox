# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import importlib.util
from pathlib import Path

import flet as ft


def get_project_root():
    """返回项目根目录。"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def _resolve_base_class_path():
    """解析公共基类文件路径，打包后自动使用 .pyc 字节码"""
    base_py = get_project_root() / 'Core' / 'Public base class.py'
    if getattr(sys, 'frozen', False):
        return Path(importlib.util.cache_from_source(str(base_py)))
    return base_py


def run_startup_preflight():
    """执行启动前置检查：加载公共基类并验证字体可用性。"""
    base_file = _resolve_base_class_path()

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
        icon_path = str(base._get_project_root() / 'Image' / 'icon.ico')
        return font_family, icon_path
    finally:
        try:
            if root.winfo_exists():
                root.destroy()
        except Exception:
            pass


APP_FONT_FAMILY, APP_ICON_PATH = run_startup_preflight()


def to_upper(text):
    """转换为全部大写"""
    return text.upper()


def to_lower(text):
    """转换为全部小写"""
    return text.lower()


def to_title(text):
    """首字母大写"""
    return text.title()


def reverse_case(text):
    """大小写反转"""
    return text.swapcase()


class EnglishCaseConverterApp:
    """英文大小写转换 Flet 应用"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.font_family = APP_FONT_FAMILY

        page.title = "英文大小写转换"
        page.window.width = 720
        page.window.height = 640
        page.window.min_width = 560
        page.window.min_height = 520
        page.padding = 0
        page.bgcolor = ft.Colors.GREY_100
        page.theme = ft.Theme(font_family=self.font_family)

        # 窗口图标由公共基类解析，直接使用
        page.window.icon = APP_ICON_PATH

        self.case_mode = ft.RadioGroup(
            value="upper",
            content=ft.Row(
                [
                    ft.Radio(value="upper", label="全部大写"),
                    ft.Radio(value="lower", label="全部小写"),
                    ft.Radio(value="title", label="首字母大写"),
                    ft.Radio(value="reverse", label="大小写反转"),
                ],
                spacing=8,
                wrap=True,
            ),
        )

        self.text_input = ft.TextField(
            label="输入文本",
            multiline=True,
            min_lines=5,
            max_lines=8,
            text_size=13,
            content_padding=ft.padding.all(10),
            border_radius=8,
        )

        self.text_output = ft.TextField(
            label="转换结果",
            multiline=True,
            min_lines=5,
            max_lines=8,
            read_only=True,
            text_size=13,
            content_padding=ft.padding.all(10),
            border_radius=8,
            bgcolor=ft.Colors.GREY_50,
        )

        self.status_text = ft.Text("就绪", size=12, color=ft.Colors.BLUE_GREY_700,
                                    font_family=self.font_family)

        self._build_ui()

    def _make_card(self, title, content):
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=13, weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_GREY_700, font_family=self.font_family),
                content,
            ], spacing=8),
            padding=ft.padding.all(12),
            border_radius=10,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )

    def _build_ui(self):
        input_card = self._make_card("输入", self.text_input)
        mode_card = self._make_card("转换模式", self.case_mode)
        output_card = self._make_card("输出", self.text_output)

        btn_convert = ft.ElevatedButton(
            "转换",
            icon=ft.Icons.SWAP_HORIZ,
            bgcolor=ft.Colors.BLUE_600,
            color=ft.Colors.WHITE,
            on_click=self.on_convert,
        )
        btn_clear = ft.OutlinedButton("清空输入", icon=ft.Icons.CLEAR, on_click=self.on_clear)
        btn_copy = ft.OutlinedButton("复制结果", icon=ft.Icons.COPY, on_click=self.on_copy)

        button_row = ft.Row([btn_convert, btn_clear, btn_copy], spacing=8, wrap=True)

        status_bar = ft.Container(
            content=self.status_text,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            bgcolor=ft.Colors.WHITE,
            border=ft.border.only(top=ft.BorderSide(1, ft.Colors.GREY_200)),
        )

        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        input_card,
                        mode_card,
                        button_row,
                        output_card,
                    ],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
                padding=12,
                expand=True,
            ),
        )
        self.page.add(status_bar)

    def show_status(self, message, success=True):
        self.status_text.value = message
        self.page.snack_bar = ft.SnackBar(
            ft.Text(message, font_family=self.font_family),
            bgcolor=ft.Colors.GREEN if success else ft.Colors.RED,
            open=True,
        )
        self.page.update()

    def on_convert(self, e):
        text = (self.text_input.value or "").strip()
        if not text:
            self.show_status("请先输入文本", success=False)
            return

        mode = self.case_mode.value
        if mode == "upper":
            result = to_upper(text)
        elif mode == "lower":
            result = to_lower(text)
        elif mode == "title":
            result = to_title(text)
        else:
            result = reverse_case(text)

        self.text_output.value = result
        self.show_status("转换完成", success=True)

    def on_clear(self, e):
        self.text_input.value = ""
        self.text_output.value = ""
        self.show_status("已清空", success=True)

    def on_copy(self, e):
        result = (self.text_output.value or "").strip()
        if not result:
            self.show_status("没有可复制的结果", success=False)
            return
        self.page.set_clipboard(result)
        self.show_status("结果已复制到剪贴板", success=True)


def main(page: ft.Page):
    EnglishCaseConverterApp(page)


if __name__ == "__main__":
    ft.app(target=main)
