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


OPERATIONS = ["AND", "OR", "XOR", "NOT", "加法", "减法", "左移", "右移"]


class BinaryCalculatorApp:
    """二进制计算器 Flet 应用"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.font_family = APP_FONT_FAMILY

        page.title = "二进制计算器"
        page.window.width = 720
        page.window.height = 720
        page.window.min_width = 560
        page.window.min_height = 600
        page.padding = 0
        page.bgcolor = ft.Colors.GREY_100
        page.theme = ft.Theme(font_family=self.font_family)

        # 窗口图标由公共基类解析，直接使用
        page.window.icon = APP_ICON_PATH

        self.binary1_field = ft.TextField(
            label="二进制数1",
            hint_text="只允许 0/1",
            text_size=13,
            content_padding=ft.padding.all(10),
            border_radius=8,
        )
        self.binary2_field = ft.TextField(
            label="二进制数2",
            hint_text="NOT 运算时可留空",
            text_size=13,
            content_padding=ft.padding.all(10),
            border_radius=8,
        )
        self.operation_dropdown = ft.Dropdown(
            label="运算",
            value="AND",
            options=[ft.dropdown.Option(op) for op in OPERATIONS],
            text_size=13,
            border_radius=8,
            width=200,
        )

        self.equation_text = ft.Text("运算式: ", size=13, font_family=self.font_family,
                                       color=ft.Colors.BLUE_GREY_800, selectable=True)
        self.binary_result_text = ft.Text("二进制结果: ", size=13,
                                            font_family=self.font_family,
                                            color=ft.Colors.BLUE_GREY_800, selectable=True)
        self.decimal_result_text = ft.Text("十进制结果: ", size=13,
                                             font_family=self.font_family,
                                             color=ft.Colors.BLUE_GREY_800, selectable=True)
        self.details_view = ft.TextField(
            label="详细信息",
            multiline=True,
            min_lines=6,
            max_lines=10,
            read_only=True,
            text_size=12,
            text_style=ft.TextStyle(font_family="Consolas", size=12),
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
        input_card = self._make_card(
            "输入",
            ft.Column([self.binary1_field, self.binary2_field, self.operation_dropdown],
                       spacing=8),
        )

        btn_calc = ft.ElevatedButton(
            "计算", icon=ft.Icons.CALCULATE,
            bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE,
            on_click=self.on_calculate,
        )
        btn_clear = ft.OutlinedButton("清除", icon=ft.Icons.CLEAR, on_click=self.on_clear)
        btn_dec2bin = ft.OutlinedButton(
            "十进制转二进制", icon=ft.Icons.SWAP_HORIZ, on_click=self.on_dec2bin,
        )
        button_row = ft.Row([btn_calc, btn_clear, btn_dec2bin], spacing=8, wrap=True)

        result_card = self._make_card(
            "运算结果",
            ft.Column([
                self.equation_text,
                self.binary_result_text,
                self.decimal_result_text,
                self.details_view,
            ], spacing=6),
        )

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

    def is_valid_binary(self, s):
        return bool(s) and all(bit in ('0', '1') for bit in s)

    def binary_to_decimal(self, s):
        return int(s, 2)

    def on_clear(self, e):
        self.binary1_field.value = ""
        self.binary2_field.value = ""
        self.operation_dropdown.value = "AND"
        self.equation_text.value = "运算式: "
        self.binary_result_text.value = "二进制结果: "
        self.decimal_result_text.value = "十进制结果: "
        self.details_view.value = ""
        self.page.update()
        self.show_status("已清空", success=True)

    def on_dec2bin(self, e):
        """弹出对话框，输入十进制整数，转换为二进制填入 binary1"""
        dec_field = ft.TextField(label="十进制整数", autofocus=True,
                                   text_size=13, border_radius=8)

        def do_close(_e):
            self.page.dialog.open = False
            self.page.update()

        def do_convert(_e):
            text = (dec_field.value or "").strip()
            try:
                dec = int(text)
                binary = bin(dec)[2:] if dec >= 0 else "-" + bin(-dec)[2:]
                self.binary1_field.value = binary.lstrip("-")
                self.page.dialog.open = False
                self.page.update()
                self.show_status(f"{dec} → {binary}", success=True)
            except ValueError:
                self.show_status("请输入有效的整数", success=False)

        self.page.dialog = ft.AlertDialog(
            title=ft.Text("十进制转二进制", font_family=self.font_family),
            content=ft.Column([dec_field], tight=True, spacing=8),
            actions=[
                ft.TextButton("取消", on_click=do_close),
                ft.ElevatedButton("转换", bgcolor=ft.Colors.BLUE_600,
                                     color=ft.Colors.WHITE, on_click=do_convert),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog.open = True
        self.page.update()

    def on_calculate(self, e):
        binary1 = (self.binary1_field.value or "").strip()
        binary2 = (self.binary2_field.value or "").strip()
        operation = self.operation_dropdown.value

        if not binary1:
            self.show_status("请输入二进制数1", success=False)
            return
        if not self.is_valid_binary(binary1):
            self.show_status("二进制数1包含非法字符（仅允许 0/1）", success=False)
            return
        if operation != "NOT":
            if not binary2:
                self.show_status("请输入二进制数2", success=False)
                return
            if not self.is_valid_binary(binary2):
                self.show_status("二进制数2包含非法字符（仅允许 0/1）", success=False)
                return

        try:
            decimal1 = self.binary_to_decimal(binary1)
            decimal2 = self.binary_to_decimal(binary2) if operation != "NOT" else 0

            result_decimal = 0
            details = ""

            if operation == "AND":
                result_decimal = decimal1 & decimal2
                details = f"{binary1} AND {binary2}\n= {bin(result_decimal)[2:]}\n\n位运算:\n"
                for i in range(max(len(binary1), len(binary2))):
                    bit1 = binary1[-i - 1] if i < len(binary1) else '0'
                    bit2 = binary2[-i - 1] if i < len(binary2) else '0'
                    res_bit = '1' if bit1 == '1' and bit2 == '1' else '0'
                    details += f"位{i}: {bit1} & {bit2} = {res_bit}\n"

            elif operation == "OR":
                result_decimal = decimal1 | decimal2
                details = f"{binary1} OR {binary2}\n= {bin(result_decimal)[2:]}\n\n位运算:\n"
                for i in range(max(len(binary1), len(binary2))):
                    bit1 = binary1[-i - 1] if i < len(binary1) else '0'
                    bit2 = binary2[-i - 1] if i < len(binary2) else '0'
                    res_bit = '1' if bit1 == '1' or bit2 == '1' else '0'
                    details += f"位{i}: {bit1} | {bit2} = {res_bit}\n"

            elif operation == "XOR":
                result_decimal = decimal1 ^ decimal2
                details = f"{binary1} XOR {binary2}\n= {bin(result_decimal)[2:]}\n\n位运算:\n"
                for i in range(max(len(binary1), len(binary2))):
                    bit1 = binary1[-i - 1] if i < len(binary1) else '0'
                    bit2 = binary2[-i - 1] if i < len(binary2) else '0'
                    res_bit = '1' if bit1 != bit2 else '0'
                    details += f"位{i}: {bit1} ^ {bit2} = {res_bit}\n"

            elif operation == "NOT":
                bits = len(binary1)
                mask = (1 << bits) - 1
                result_decimal = (~decimal1) & mask
                details = f"NOT {binary1}\n= {bin(result_decimal)[2:]}\n\n按位取反:\n"
                for i in range(len(binary1)):
                    bit = binary1[-i - 1]
                    res_bit = '0' if bit == '1' else '1'
                    details += f"位{i}: ~{bit} = {res_bit}\n"

            elif operation == "加法":
                result_decimal = decimal1 + decimal2
                details = (f"{binary1} + {binary2}\n= {bin(result_decimal)[2:]}\n\n"
                            f"十进制: {decimal1} + {decimal2} = {result_decimal}")

            elif operation == "减法":
                result_decimal = decimal1 - decimal2
                if result_decimal < 0:
                    details = (f"{binary1} - {binary2}\n= 负数（{result_decimal}），"
                                f"二进制显示为绝对值\n= {bin(abs(result_decimal))[2:]}\n\n"
                                f"十进制: {decimal1} - {decimal2} = {result_decimal}")
                else:
                    details = (f"{binary1} - {binary2}\n= {bin(result_decimal)[2:]}\n\n"
                                f"十进制: {decimal1} - {decimal2} = {result_decimal}")

            elif operation == "左移":
                result_decimal = decimal1 << decimal2
                details = (f"{binary1} << {binary2}\n= {bin(result_decimal)[2:]}\n\n"
                            f"相当于乘以 2^{decimal2}: "
                            f"{decimal1} * {2 ** decimal2} = {result_decimal}")

            elif operation == "右移":
                result_decimal = decimal1 >> decimal2
                details = (f"{binary1} >> {binary2}\n= {bin(result_decimal)[2:]}\n\n"
                            f"相当于除以 2^{decimal2}: "
                            f"{decimal1} / {2 ** decimal2} = {result_decimal}")

            # 显示结果
            if result_decimal < 0:
                result_binary = "-" + bin(abs(result_decimal))[2:]
            else:
                result_binary = bin(result_decimal)[2:]

            self.equation_text.value = (
                f"运算式: {binary1} {operation} "
                f"{binary2 if operation != 'NOT' else ''}".strip()
            )
            self.binary_result_text.value = f"二进制结果: {result_binary}"
            self.decimal_result_text.value = f"十进制结果: {result_decimal}"
            self.details_view.value = details
            self.page.update()
            self.show_status("计算完成", success=True)

        except ValueError:
            self.show_status("请输入有效的二进制数", success=False)
        except Exception as ex:
            self.show_status(f"计算出错: {ex}", success=False)


def main(page: ft.Page):
    BinaryCalculatorApp(page)


if __name__ == "__main__":
    ft.app(target=main)
