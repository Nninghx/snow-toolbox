# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import math
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


def decimal_to_fraction(decimal_num):
    """将小数转换为分数（连分数算法）"""
    tolerance = 1.0E-6
    sign = -1 if decimal_num < 0 else 1
    decimal_num = abs(decimal_num)

    integer_part = int(decimal_num)
    decimal_num -= integer_part

    if decimal_num < tolerance:
        return (sign * integer_part, 1)

    lower_n, lower_d = 0, 1
    upper_n, upper_d = 1, 1

    while True:
        middle_n = lower_n + upper_n
        middle_d = lower_d + upper_d

        if middle_d * (decimal_num + tolerance) < middle_n:
            upper_n, upper_d = middle_n, middle_d
        elif middle_n < (decimal_num - tolerance) * middle_d:
            lower_n, lower_d = middle_n, middle_d
        else:
            numerator = middle_n
            denominator = middle_d
            break

    numerator = sign * (integer_part * denominator + numerator)

    common = math.gcd(numerator, denominator)
    return (numerator // common, denominator // common)


def percentage_to_fraction(percentage):
    """将百分比转换为分数"""
    if isinstance(percentage, str) and '%' in percentage:
        percentage = percentage.replace('%', '')
    decimal_num = float(percentage) / 100
    return decimal_to_fraction(decimal_num)


class FractionCalculatorApp:
    """分数计算器 Flet 应用"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.font_family = APP_FONT_FAMILY

        page.title = "分数计算器"
        page.window.width = 780
        page.window.height = 660
        page.window.min_width = 620
        page.window.min_height = 560
        page.padding = 0
        page.bgcolor = ft.Colors.GREY_100
        page.theme = ft.Theme(font_family=self.font_family)

        # 窗口图标由公共基类解析，直接使用
        page.window.icon = APP_ICON_PATH

        # 分数化简
        self.simp_num = ft.TextField(label="分子", text_size=13,
                                        border_radius=8, expand=1)
        self.simp_den = ft.TextField(label="分母（可留空表示 1）", text_size=13,
                                        border_radius=8, expand=1)

        # 小数转分数
        self.decimal_input = ft.TextField(label="输入小数", text_size=13,
                                              border_radius=8, expand=1)

        # 百分比转分数
        self.percentage_input = ft.TextField(label="输入百分比",
                                                hint_text="如 50 或 50%",
                                                text_size=13,
                                                border_radius=8, expand=1)

        # 分数计算
        self.frac1_num = ft.TextField(label="分数1 分子", text_size=13,
                                          border_radius=8, expand=1)
        self.frac1_den = ft.TextField(label="分数1 分母", text_size=13,
                                          border_radius=8, expand=1)
        self.operator = ft.Dropdown(
            label="运算符", value="+",
            options=[ft.dropdown.Option(x) for x in ["+", "-", "×", "÷"]],
            text_size=13, border_radius=8, width=110,
        )
        self.frac2_num = ft.TextField(label="分数2 分子", text_size=13,
                                          border_radius=8, expand=1)
        self.frac2_den = ft.TextField(label="分数2 分母", text_size=13,
                                          border_radius=8, expand=1)

        # 结果展示
        self.result_num_text = ft.Text("", size=22, weight=ft.FontWeight.BOLD,
                                           color=ft.Colors.BLUE_GREY_800,
                                           font_family=self.font_family,
                                           text_align=ft.TextAlign.CENTER,
                                           selectable=True)
        self.result_line_text = ft.Text("━━━━", size=18,
                                           color=ft.Colors.BLUE_GREY_800,
                                           font_family=self.font_family,
                                           text_align=ft.TextAlign.CENTER,
                                           visible=False)
        self.result_den_text = ft.Text("", size=22, weight=ft.FontWeight.BOLD,
                                           color=ft.Colors.BLUE_GREY_800,
                                           font_family=self.font_family,
                                           text_align=ft.TextAlign.CENTER,
                                           selectable=True)
        self.result_description = ft.Text("", size=12,
                                              color=ft.Colors.BLUE_GREY_600,
                                              font_family=self.font_family,
                                              text_align=ft.TextAlign.CENTER)

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

    def _btn(self, label, callback):
        return ft.ElevatedButton(
            label, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE,
            on_click=callback,
        )

    def _build_ui(self):
        # 分数化简
        simplify_tab = ft.Column([
            ft.Row([self.simp_num, self.simp_den], spacing=8),
            ft.Row([self._btn("化简", self.on_simplify)], alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=10)

        # 小数转分数
        decimal_tab = ft.Column([
            self.decimal_input,
            ft.Row([self._btn("转换", self.on_decimal)],
                     alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=10)

        # 百分比转分数
        percentage_tab = ft.Column([
            self.percentage_input,
            ft.Row([self._btn("转换", self.on_percentage)],
                     alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=10)

        # 分数计算
        calc_tab = ft.Column([
            ft.Row([
                ft.Column([self.frac1_num, self.frac1_den], spacing=4, expand=2),
                self.operator,
                ft.Column([self.frac2_num, self.frac2_den], spacing=4, expand=2),
            ], spacing=8),
            ft.Row([self._btn("计算", self.on_calculate)],
                     alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=10)

        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=200,
            height=380,
            tabs=[
                ft.Tab(text="分数化简", content=self._pad(simplify_tab)),
                ft.Tab(text="小数转分数", content=self._pad(decimal_tab)),
                ft.Tab(text="百分比转分数", content=self._pad(percentage_tab)),
                ft.Tab(text="分数计算", content=self._pad(calc_tab)),
            ],
        )
        tabs_card = self._make_card("计算类型", tabs)

        result_card = self._make_card(
            "结果",
            ft.Container(
                content=ft.Column([
                    self.result_num_text,
                    self.result_line_text,
                    self.result_den_text,
                    ft.Divider(height=8, color=ft.Colors.TRANSPARENT),
                    self.result_description,
                ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.all(16),
                border_radius=8,
                bgcolor=ft.Colors.BLUE_GREY_50,
                alignment=ft.alignment.center,
            ),
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
                    [tabs_card, result_card],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
                padding=12,
                expand=True,
            ),
        )
        self.page.add(status_bar)

    def _pad(self, content):
        return ft.Container(content=content, padding=ft.padding.all(8))

    def show_status(self, message, success=True):
        self.status_text.value = message
        self.page.snack_bar = ft.SnackBar(
            ft.Text(message, font_family=self.font_family),
            bgcolor=ft.Colors.GREEN if success else ft.Colors.RED,
            open=True,
        )
        self.page.update()

    def display_result(self, numerator, denominator, description=""):
        if denominator == 1:
            self.result_num_text.value = str(numerator)
            self.result_line_text.visible = False
            self.result_den_text.value = ""
            self.result_den_text.visible = False
        else:
            self.result_num_text.value = str(numerator)
            self.result_line_text.visible = True
            self.result_den_text.value = str(denominator)
            self.result_den_text.visible = True
        self.result_description.value = description
        self.page.update()
        self.show_status("计算完成", success=True)

    def _show_error(self, msg):
        self.result_num_text.value = "错误"
        self.result_line_text.visible = False
        self.result_den_text.visible = False
        self.result_description.value = msg
        self.page.update()
        self.show_status(msg, success=False)

    # ----- 分数化简 -----
    def on_simplify(self, e):
        try:
            num_str = (self.simp_num.value or "").strip()
            den_str = (self.simp_den.value or "").strip()

            if not num_str:
                raise ValueError("请输入分子")

            numerator = int(num_str)
            denominator = int(den_str) if den_str else 1

            if denominator == 0:
                raise ValueError("分母不能为零")

            common = math.gcd(numerator, denominator)
            n = numerator // common
            d = denominator // common
            # 保持分母为正
            if d < 0:
                n, d = -n, -d
            self.display_result(n, d, f"{numerator}/{denominator} 化简为最简分数")
        except ValueError as ex:
            self._show_error(str(ex))

    # ----- 小数转分数 -----
    def on_decimal(self, e):
        try:
            text = (self.decimal_input.value or "").strip()
            if not text:
                raise ValueError("请输入小数")
            decimal_num = float(text)
            n, d = decimal_to_fraction(decimal_num)
            self.display_result(n, d, f"{decimal_num} ≈ {n}/{d}")
        except ValueError as ex:
            self._show_error("请输入有效的小数" if not str(ex) else str(ex))

    # ----- 百分比转分数 -----
    def on_percentage(self, e):
        try:
            text = (self.percentage_input.value or "").strip()
            if not text:
                raise ValueError("请输入百分比")
            n, d = percentage_to_fraction(text)
            self.display_result(n, d, f"{text} ≈ {n}/{d}")
        except ValueError as ex:
            self._show_error("请输入有效的百分比（如 50 或 50%）")

    # ----- 分数四则运算 -----
    def on_calculate(self, e):
        try:
            num1_str = (self.frac1_num.value or "").strip()
            den1_str = (self.frac1_den.value or "").strip()
            num2_str = (self.frac2_num.value or "").strip()
            den2_str = (self.frac2_den.value or "").strip()

            if not num1_str or not num2_str:
                raise ValueError("请输入两个分数的分子")

            num1 = int(num1_str)
            den1 = int(den1_str) if den1_str else 1
            num2 = int(num2_str)
            den2 = int(den2_str) if den2_str else 1

            if den1 == 0:
                raise ValueError("分数1的分母不能为零")
            if den2 == 0:
                raise ValueError("分数2的分母不能为零")

            op = self.operator.value
            if op == "+":
                numerator = num1 * den2 + num2 * den1
                denominator = den1 * den2
                formula = f"({num1}×{den2} + {num2}×{den1}) / ({den1}×{den2})"
            elif op == "-":
                numerator = num1 * den2 - num2 * den1
                denominator = den1 * den2
                formula = f"({num1}×{den2} - {num2}×{den1}) / ({den1}×{den2})"
            elif op == "×":
                numerator = num1 * num2
                denominator = den1 * den2
                formula = f"({num1}×{num2}) / ({den1}×{den2})"
            elif op == "÷":
                if num2 == 0:
                    raise ValueError("除数分子不能为零")
                numerator = num1 * den2
                denominator = den1 * num2
                formula = f"({num1}×{den2}) / ({den1}×{num2})"
            else:
                raise ValueError("无效的运算符")

            if denominator == 0:
                raise ValueError("结果分母为零，运算无效")

            common = math.gcd(numerator, denominator)
            n = numerator // common
            d = denominator // common
            if d < 0:
                n, d = -n, -d

            self.display_result(
                n, d,
                f"{num1}/{den1} {op} {num2}/{den2} = {formula} = {n}/{d}"
            )
        except ValueError as ex:
            self._show_error(str(ex))


def main(page: ft.Page):
    FractionCalculatorApp(page)


if __name__ == "__main__":
    ft.app(target=main)
