# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import re
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


class RMBConverter:
    """数字小写转中文大写转换器"""

    NUM_MAP = {
        '0': '零', '1': '壹', '2': '贰', '3': '叁', '4': '肆',
        '5': '伍', '6': '陆', '7': '柒', '8': '捌', '9': '玖'
    }
    INT_UNITS = ['', '拾', '佰', '仟']
    BIG_UNITS = ['', '万', '亿', '兆', '京', '垓']
    DECIMAL_UNITS = ['角', '分', '厘', '毫', '丝', '忽', '微']

    def validate_input(self, num_str):
        """验证输入是否有效"""
        if not num_str:
            return None
        pattern = r'^\d{1,30}(\.\d{1,7})?$'
        if not re.match(pattern, num_str):
            return "请输入正确的数字格式（小数点后最多7位）"
        parts = num_str.split('.')
        int_part = parts[0].lstrip('0')
        if len(int_part) > 21:
            return "整数部分超过21位，请输入更小的数字"
        return None

    def convert_integer_part(self, int_str):
        """转换整数部分"""
        int_str = int_str.lstrip('0')
        if not int_str:
            return '零'
        if len(int_str) > 21:
            int_str = int_str[-21:]

        groups = []
        length = len(int_str)
        for i in range(0, length, 4):
            start = max(0, length - i - 4)
            end = length - i
            groups.insert(0, int_str[start:end])

        result = []
        for i, group in enumerate(groups):
            if group == '0' * len(group) and i < len(groups) - 1:
                if any(g != '0' * len(g) for g in groups[i + 1:]):
                    if not (result and result[-1] == '零'):
                        result.append('零')
                continue

            group_result = []
            has_zero = False
            last_non_zero = None

            for j, digit in enumerate(group):
                unit_index = len(group) - j - 1
                if digit == '0':
                    has_zero = True
                else:
                    if has_zero and group_result:
                        group_result.append('零')
                    group_result.append(self.NUM_MAP[digit])
                    if unit_index > 0:
                        group_result.append(self.INT_UNITS[unit_index])
                    last_non_zero = digit
                    has_zero = False

            if has_zero and last_non_zero is not None:
                group_result.append('零')

            if group_result:
                result.extend(group_result)
                big_unit_index = len(groups) - i - 1
                if big_unit_index < len(self.BIG_UNITS):
                    result.append(self.BIG_UNITS[big_unit_index])

        return ''.join(result) if result else '零'

    def convert_decimal_part(self, decimal_str):
        """转换小数部分"""
        result = []
        decimal_str = (decimal_str + '0' * 7)[:7]

        last_non_zero = -1
        for i in range(len(decimal_str) - 1, -1, -1):
            if decimal_str[i] != '0':
                last_non_zero = i
                break

        for i, digit in enumerate(decimal_str[:last_non_zero + 1]):
            if digit != '0':
                result.append(self.NUM_MAP[digit])
                result.append(self.DECIMAL_UNITS[i])
            elif result and result[-1] not in self.DECIMAL_UNITS:
                result.append('零')

        return ''.join(result)

    def convert(self, num_str):
        """转换数字为中文大写"""
        try:
            parts = num_str.split('.')
            integer_part = parts[0]
            decimal_part = parts[1] if len(parts) > 1 else ''

            result = []
            int_result = self.convert_integer_part(integer_part)
            if int_result:
                result.append(int_result)
                result.append('元')

            dec_result = self.convert_decimal_part(decimal_part)
            if dec_result:
                result.append(dec_result)
            elif int_result:
                result.append('整')

            return ''.join(result)
        except Exception as e:
            return f'转换错误：{str(e)}'


class RMBConverterApp:
    """数字小写转大写 Flet 应用"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.font_family = APP_FONT_FAMILY
        self.converter = RMBConverter()

        page.title = "数字小写转大写"
        page.window.width = 820
        page.window.height = 640
        page.window.min_width = 640
        page.window.min_height = 520
        page.padding = 0
        page.bgcolor = ft.Colors.GREY_100
        page.theme = ft.Theme(font_family=self.font_family)

        # 窗口图标由公共基类解析，直接使用
        page.window.icon = APP_ICON_PATH

        self.input_field = ft.TextField(
            label="请输入金额",
            hint_text="例如：1234.56",
            text_size=14,
            content_padding=ft.padding.all(10),
            border_radius=8,
            on_change=self.on_input_change,
            autofocus=True,
        )

        self.result_field = ft.TextField(
            label="转换结果",
            multiline=True,
            min_lines=6,
            max_lines=10,
            read_only=True,
            text_size=16,
            content_padding=ft.padding.all(12),
            border_radius=8,
            bgcolor=ft.Colors.GREY_50,
        )

        self.status_text = ft.Text("支持范围：整数最多21位（到垓），小数最多7位（到微）",
                                    size=12, color=ft.Colors.BLUE_GREY_700,
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
        input_card = self._make_card("输入金额", self.input_field)
        result_card = self._make_card("转换结果", self.result_field)

        btn_clear = ft.OutlinedButton("清除", icon=ft.Icons.CLEAR, on_click=self.on_clear)
        btn_copy = ft.ElevatedButton(
            "复制结果",
            icon=ft.Icons.COPY,
            bgcolor=ft.Colors.BLUE_600,
            color=ft.Colors.WHITE,
            on_click=self.on_copy,
        )
        button_row = ft.Row([btn_clear, btn_copy], spacing=8)

        status_bar = ft.Container(
            content=self.status_text,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            bgcolor=ft.Colors.WHITE,
            border=ft.border.only(top=ft.BorderSide(1, ft.Colors.GREY_200)),
        )

        self.page.add(
            ft.Container(
                content=ft.Column(
                    [input_card, button_row, result_card],
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

    def on_input_change(self, e):
        text = (self.input_field.value or "").strip()
        if not text:
            self.result_field.value = ""
            self.page.update()
            return

        error_msg = self.converter.validate_input(text)
        if error_msg is None:
            try:
                self.result_field.value = self.converter.convert(text)
            except Exception as e:
                self.result_field.value = f"转换出错：{e}"
        else:
            self.result_field.value = error_msg
        self.page.update()

    def on_clear(self, e):
        self.input_field.value = ""
        self.result_field.value = ""
        self.show_status("已清空", success=True)

    def on_copy(self, e):
        result = (self.result_field.value or "").strip()
        if not result:
            self.show_status("没有可复制的结果", success=False)
            return
        self.page.set_clipboard(result)
        self.show_status("结果已复制到剪贴板", success=True)


def main(page: ft.Page):
    RMBConverterApp(page)


if __name__ == "__main__":
    ft.app(target=main)
