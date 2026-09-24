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


class AlgebraCalculatorApp:
    """代数计算器 Flet 应用"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.font_family = APP_FONT_FAMILY

        page.title = "代数计算器"
        page.window.width = 860
        page.window.height = 680
        page.window.min_width = 680
        page.window.min_height = 560
        page.padding = 0
        page.bgcolor = ft.Colors.GREY_100
        page.theme = ft.Theme(font_family=self.font_family)

        # 窗口图标由公共基类解析，直接使用
        page.window.icon = APP_ICON_PATH

        # 平均值
        self.avg_input = ft.TextField(
            label="数字（空格分隔）", hint_text="例如 1 2 3 4 5",
            text_size=13, border_radius=8, expand=1,
        )

        # 指数
        self.exp_base = ft.TextField(label="底数", text_size=13,
                                        border_radius=8, expand=1)
        self.exp_power = ft.TextField(label="指数", text_size=13,
                                         border_radius=8, expand=1)

        # 比例
        self.ratio_a = ft.TextField(label="a", text_size=13,
                                       border_radius=8, expand=1)
        self.ratio_b = ft.TextField(label="b", text_size=13,
                                       border_radius=8, expand=1)
        self.ratio_c = ft.TextField(label="c", text_size=13,
                                       border_radius=8, expand=1)
        self.ratio_d = ft.TextField(label="d", text_size=13,
                                       border_radius=8, expand=1)

        # LCM/GCD
        self.lcm_input = ft.TextField(
            label="数字（空格分隔）", hint_text="例如 4 6 8",
            text_size=13, border_radius=8, expand=1,
        )
        self.gcd_input = ft.TextField(
            label="数字（空格分隔）", hint_text="例如 12 18 24",
            text_size=13, border_radius=8, expand=1,
        )

        # 对数
        self.log_number = ft.TextField(label="数字", text_size=13,
                                          border_radius=8, expand=1)
        self.log_base = ft.TextField(label="底数", text_size=13,
                                        border_radius=8, expand=1)

        # 自然对数
        self.ln_input = ft.TextField(label="输入正数", text_size=13,
                                        border_radius=8, expand=1)

        # 反对数
        self.antilog_input = ft.TextField(label="输入数字", text_size=13,
                                              border_radius=8, expand=1)
        self.antilog_base = ft.Dropdown(
            label="底数", value="10",
            options=[ft.dropdown.Option(x) for x in ["10", "e", "2"]],
            text_size=13, border_radius=8, width=140,
        )

        # 结果
        self.result_text = ft.Text(
            "结果将显示在这里",
            size=15, weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_GREY_800,
            text_align=ft.TextAlign.CENTER,
            font_family=self.font_family,
            selectable=True,
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

    def _btn(self, label, callback):
        return ft.ElevatedButton(
            label, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE,
            on_click=callback,
        )

    def _pad(self, content):
        return ft.Container(content=content, padding=ft.padding.all(8))

    def _build_ui(self):
        avg_tab = ft.Row([self.avg_input, self._btn("计算", self.calc_average)],
                            spacing=8)

        exp_tab = ft.Row([self.exp_base, self.exp_power,
                             self._btn("计算", self.calc_exponent)], spacing=8)

        ratio_tab = ft.Row([
            self.ratio_a,
            ft.Text(":", size=16, font_family=self.font_family),
            self.ratio_b,
            ft.Text("=", size=16, font_family=self.font_family),
            self.ratio_c,
            ft.Text(":", size=16, font_family=self.font_family),
            self.ratio_d,
            self._btn("计算", self.calc_ratio),
        ], spacing=8)

        lcm_tab = ft.Row([self.lcm_input, self._btn("计算 LCM", self.calc_lcm)],
                             spacing=8)
        gcd_tab = ft.Row([self.gcd_input, self._btn("计算 GCD", self.calc_gcd)],
                             spacing=8)

        log_tab = ft.Row([self.log_number, self.log_base,
                             self._btn("计算", self.calc_log)], spacing=8)
        ln_tab = ft.Row([self.ln_input, self._btn("计算 ln", self.calc_ln)],
                            spacing=8)
        antilog_tab = ft.Row([self.antilog_input, self.antilog_base,
                                 self._btn("计算", self.calc_antilog)], spacing=8)

        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=200,
            height=340,
            scrollable=True,
            tabs=[
                ft.Tab(text="平均值", content=self._pad(avg_tab)),
                ft.Tab(text="指数", content=self._pad(exp_tab)),
                ft.Tab(text="比例 a:b=c:d", content=self._pad(ratio_tab)),
                ft.Tab(text="最小公倍数", content=self._pad(lcm_tab)),
                ft.Tab(text="最大公因数", content=self._pad(gcd_tab)),
                ft.Tab(text="对数", content=self._pad(log_tab)),
                ft.Tab(text="自然对数", content=self._pad(ln_tab)),
                ft.Tab(text="反对数", content=self._pad(antilog_tab)),
            ],
        )
        tabs_card = self._make_card("计算类型", tabs)

        result_container = ft.Container(
            content=self.result_text,
            padding=ft.padding.all(18),
            border_radius=8,
            bgcolor=ft.Colors.BLUE_GREY_50,
            alignment=ft.alignment.center,
        )
        result_card = self._make_card("计算结果", result_container)

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

    def show_status(self, message, success=True):
        self.status_text.value = message
        self.page.snack_bar = ft.SnackBar(
            ft.Text(message, font_family=self.font_family),
            bgcolor=ft.Colors.GREEN if success else ft.Colors.RED,
            open=True,
        )
        self.page.update()

    def _show_result(self, text):
        self.result_text.value = text
        self.show_status("计算完成", success=True)

    def _show_error(self, msg):
        self.result_text.value = f"错误: {msg}"
        self.show_status(msg, success=False)

    # ----- 平均值 -----
    def calc_average(self, e):
        try:
            text = (self.avg_input.value or "").strip()
            if not text:
                raise ValueError("请输入数字")
            numbers = [float(x) for x in text.split()]
            if not numbers:
                raise ValueError("请输入数字")
            average = sum(numbers) / len(numbers)
            self._show_result(f"平均值 = {average:.4f}（共 {len(numbers)} 个数字）")
        except ValueError as ex:
            self._show_error(str(ex))

    # ----- 指数 -----
    def calc_exponent(self, e):
        try:
            base_str = (self.exp_base.value or "").strip()
            power_str = (self.exp_power.value or "").strip()
            if not base_str or not power_str:
                raise ValueError("请输入底数和指数")
            base = float(base_str)
            power = float(power_str)
            result = base ** power
            self._show_result(f"{base}^{power} = {result:.6g}")
        except ValueError as ex:
            self._show_error(str(ex))

    # ----- 比例 -----
    def calc_ratio(self, e):
        try:
            values_str = [
                (self.ratio_a.value or "").strip(),
                (self.ratio_b.value or "").strip(),
                (self.ratio_c.value or "").strip(),
                (self.ratio_d.value or "").strip(),
            ]
            empty_count = sum(1 for x in values_str if not x)
            if empty_count != 1:
                raise ValueError("必须且只能留空一个值")

            values = []
            for val in values_str:
                if val:
                    try:
                        values.append(float(val))
                    except ValueError:
                        raise ValueError("请输入有效的数字")
                else:
                    values.append(None)

            a, b, c, d = values

            if a is None:
                if d == 0:
                    raise ValueError("除数不能为零")
                result = (b * c) / d
                self.ratio_a.value = f"{result:.4f}"
                self._show_result(f"计算结果: a = {result:.4f}")
            elif b is None:
                if c == 0:
                    raise ValueError("除数不能为零")
                result = (a * d) / c
                self.ratio_b.value = f"{result:.4f}"
                self._show_result(f"计算结果: b = {result:.4f}")
            elif c is None:
                if b == 0:
                    raise ValueError("除数不能为零")
                result = (a * d) / b
                self.ratio_c.value = f"{result:.4f}"
                self._show_result(f"计算结果: c = {result:.4f}")
            elif d is None:
                if a == 0:
                    raise ValueError("除数不能为零")
                result = (b * c) / a
                self.ratio_d.value = f"{result:.4f}"
                self._show_result(f"计算结果: d = {result:.4f}")
        except ValueError as ex:
            self._show_error(str(ex))

    # ----- LCM -----
    def calc_lcm(self, e):
        try:
            text = (self.lcm_input.value or "").strip()
            if not text:
                raise ValueError("请输入数字")
            numbers = [int(x) for x in text.split()]
            if len(numbers) < 2:
                raise ValueError("至少需要输入两个数字")
            if any(n <= 0 for n in numbers):
                raise ValueError("数字必须为正整数")

            def lcm(a, b):
                return a * b // math.gcd(a, b)

            current = numbers[0]
            for n in numbers[1:]:
                current = lcm(current, n)
            self._show_result(f"最小公倍数 LCM = {current}")
        except ValueError as ex:
            self._show_error(str(ex))

    # ----- GCD -----
    def calc_gcd(self, e):
        try:
            text = (self.gcd_input.value or "").strip()
            if not text:
                raise ValueError("请输入数字")
            numbers = [int(x) for x in text.split()]
            if len(numbers) < 2:
                raise ValueError("至少需要输入两个数字")
            if any(n <= 0 for n in numbers):
                raise ValueError("数字必须为正整数")

            current = numbers[0]
            for n in numbers[1:]:
                current = math.gcd(current, n)
            self._show_result(f"最大公因数 GCD = {current}")
        except ValueError as ex:
            self._show_error(str(ex))

    # ----- 对数 -----
    def calc_log(self, e):
        try:
            num_str = (self.log_number.value or "").strip()
            base_str = (self.log_base.value or "").strip()
            if not num_str or not base_str:
                raise ValueError("请输入数字和底数")
            num = float(num_str)
            base = float(base_str)
            if num <= 0:
                raise ValueError("数字必须大于 0")
            if base <= 0 or base == 1:
                raise ValueError("底数必须大于 0 且不等于 1")
            result = math.log(num, base)
            self._show_result(f"log{base}({num}) = {result:.6g}")
        except ValueError as ex:
            self._show_error(str(ex))

    # ----- 自然对数 -----
    def calc_ln(self, e):
        try:
            text = (self.ln_input.value or "").strip()
            if not text:
                raise ValueError("请输入数字")
            num = float(text)
            if num <= 0:
                raise ValueError("数字必须大于 0")
            result = math.log(num)
            self._show_result(f"ln({num}) = {result:.6g}")
        except ValueError as ex:
            self._show_error(str(ex))

    # ----- 反对数 -----
    def calc_antilog(self, e):
        try:
            text = (self.antilog_input.value or "").strip()
            if not text:
                raise ValueError("请输入数字")
            num = float(text)
            base = self.antilog_base.value
            if base == "10":
                result = 10 ** num
                self._show_result(f"antilog₁₀({num}) = {result:.6g}")
            elif base == "e":
                result = math.exp(num)
                self._show_result(f"antilogₑ({num}) = {result:.6g}")
            elif base == "2":
                result = 2 ** num
                self._show_result(f"antilog₂({num}) = {result:.6g}")
        except ValueError as ex:
            self._show_error(str(ex))
        except OverflowError:
            self._show_error("结果溢出，请减小输入值")


def main(page: ft.Page):
    AlgebraCalculatorApp(page)


if __name__ == "__main__":
    ft.app(target=main)
