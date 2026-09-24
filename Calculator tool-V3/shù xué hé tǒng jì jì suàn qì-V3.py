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


class MathStatisticsApp:
    """数学和统计计算器 Flet 应用"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.font_family = APP_FONT_FAMILY

        page.title = "数学和统计计算器"
        page.window.width = 820
        page.window.height = 680
        page.window.min_width = 640
        page.window.min_height = 560
        page.padding = 0
        page.bgcolor = ft.Colors.GREY_100
        page.theme = ft.Theme(font_family=self.font_family)

        # 窗口图标由公共基类解析，直接使用
        page.window.icon = APP_ICON_PATH

        # 根计算
        self.root_type = ft.Dropdown(
            label="根类型", value="平方根",
            options=[ft.dropdown.Option(x) for x in ["平方根", "立方根", "N次方根"]],
            text_size=13, border_radius=8, width=160,
            on_change=self._on_root_type_change,
        )
        self.root_value = ft.TextField(label="数值", text_size=13,
                                           border_radius=8, expand=1)
        self.root_n = ft.TextField(label="N (次方根)", text_size=13,
                                       border_radius=8, width=140, disabled=True)

        # 二次方程
        self.quad_a = ft.TextField(label="a", text_size=13, border_radius=8, expand=1)
        self.quad_b = ft.TextField(label="b", text_size=13, border_radius=8, expand=1)
        self.quad_c = ft.TextField(label="c", text_size=13, border_radius=8, expand=1)

        # 四舍五入
        self.round_value = ft.TextField(label="数值", text_size=13,
                                            border_radius=8, expand=1)
        self.round_places = ft.TextField(label="小数位数", text_size=13,
                                              border_radius=8, width=140)

        # 取模
        self.mod_dividend = ft.TextField(label="被除数", text_size=13,
                                              border_radius=8, expand=1)
        self.mod_divisor = ft.TextField(label="除数", text_size=13,
                                             border_radius=8, expand=1)

        # 组合排列
        self.comb_type = ft.Dropdown(
            label="计算类型", value="组合",
            options=[ft.dropdown.Option(x)
                        for x in ["组合", "排列", "重复组合", "重复排列"]],
            text_size=13, border_radius=8, width=160,
        )
        self.comb_n = ft.TextField(label="n", text_size=13, border_radius=8, expand=1)
        self.comb_k = ft.TextField(label="k", text_size=13, border_radius=8, expand=1)

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

    def _build_ui(self):
        # 根计算
        root_row = ft.Row([self.root_type, self.root_value, self.root_n,
                            self._btn("计算", self.calc_root)], spacing=8)

        # 二次方程
        quad_row = ft.Row([self.quad_a, self.quad_b, self.quad_c,
                            self._btn("求解", self.solve_quadratic)], spacing=8)

        # 四舍五入
        round_row = ft.Row([self.round_value, self.round_places,
                              self._btn("计算", self.calc_round)], spacing=8)

        # 取模
        mod_row = ft.Row([self.mod_dividend, self.mod_divisor,
                            self._btn("计算", self.calc_mod)], spacing=8)

        # 组合排列
        comb_row = ft.Row([self.comb_type, self.comb_n, self.comb_k,
                             self._btn("计算", self.calc_comb)], spacing=8)

        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=200,
            height=340,
            tabs=[
                ft.Tab(text="根计算", content=self._pad(root_row)),
                ft.Tab(text="二次方程", content=self._pad(quad_row)),
                ft.Tab(text="四舍五入", content=self._pad(round_row)),
                ft.Tab(text="取模", content=self._pad(mod_row)),
                ft.Tab(text="组合排列", content=self._pad(comb_row)),
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

    def _show_result(self, text):
        self.result_text.value = text
        self.show_status("计算完成", success=True)

    def _show_error(self, msg):
        self.result_text.value = f"错误: {msg}"
        self.show_status(msg, success=False)

    def _on_root_type_change(self, e):
        self.root_n.disabled = (self.root_type.value != "N次方根")
        if self.root_n.disabled:
            self.root_n.value = ""
        self.page.update()

    def _get_float(self, field, name):
        text = (field.value or "").strip()
        if not text:
            raise ValueError(f"请输入{name}")
        return float(text)

    # ----- 根 -----
    def calc_root(self, e):
        try:
            value = self._get_float(self.root_value, "数值")
            root_type = self.root_type.value

            if root_type == "平方根":
                if value < 0:
                    raise ValueError("负数没有实数平方根")
                result = math.sqrt(value)
                self._show_result(f"√{value} = {result:.6f}")
            elif root_type == "立方根":
                if value < 0:
                    result = -((-value) ** (1 / 3))
                else:
                    result = value ** (1 / 3)
                self._show_result(f"³√{value} = {result:.6f}")
            elif root_type == "N次方根":
                n = self._get_float(self.root_n, "N")
                if n == 0:
                    raise ValueError("N 不能为 0")
                if value < 0 and int(n) % 2 == 0:
                    raise ValueError("负数的偶数次方根没有实数解")
                if value < 0:
                    result = -((-value) ** (1 / n))
                else:
                    result = value ** (1 / n)
                self._show_result(f"{n}√{value} = {result:.6f}")
        except ValueError as ex:
            self._show_error(str(ex))

    # ----- 二次方程 -----
    def solve_quadratic(self, e):
        try:
            a = self._get_float(self.quad_a, "a")
            b = self._get_float(self.quad_b, "b")
            c = self._get_float(self.quad_c, "c")

            if a == 0:
                raise ValueError("a 不能为 0")

            discriminant = b ** 2 - 4 * a * c
            if discriminant > 0:
                x1 = (-b + math.sqrt(discriminant)) / (2 * a)
                x2 = (-b - math.sqrt(discriminant)) / (2 * a)
                self._show_result(f"解: x₁ = {x1:.6f}, x₂ = {x2:.6f}")
            elif discriminant == 0:
                x = -b / (2 * a)
                self._show_result(f"解: x = {x:.6f} (重根)")
            else:
                real = -b / (2 * a)
                imag = math.sqrt(abs(discriminant)) / (2 * a)
                self._show_result(
                    f"解: x₁ = {real:.6f}+{imag:.6f}i, x₂ = {real:.6f}-{imag:.6f}i"
                )
        except ValueError as ex:
            self._show_error(str(ex))

    # ----- 四舍五入 -----
    def calc_round(self, e):
        try:
            value = self._get_float(self.round_value, "数值")
            places_str = (self.round_places.value or "").strip()
            if not places_str:
                raise ValueError("请输入小数位数")
            places = int(places_str)
            if places < 0:
                raise ValueError("小数位数不能为负数")
            rounded = round(value, places)
            self._show_result(f"{value} 四舍五入到 {places} 位小数: {rounded}")
        except ValueError as ex:
            self._show_error(str(ex))

    # ----- 取模 -----
    def calc_mod(self, e):
        try:
            dividend = self._get_float(self.mod_dividend, "被除数")
            divisor = self._get_float(self.mod_divisor, "除数")
            if divisor == 0:
                raise ValueError("除数不能为 0")
            result = dividend % divisor
            self._show_result(f"{dividend} mod {divisor} = {result}")
        except ValueError as ex:
            self._show_error(str(ex))

    # ----- 组合排列 -----
    def calc_comb(self, e):
        try:
            n_str = (self.comb_n.value or "").strip()
            k_str = (self.comb_k.value or "").strip()
            if not n_str or not k_str:
                raise ValueError("请输入 n 和 k")
            n = int(n_str)
            k = int(k_str)
            comb_type = self.comb_type.value

            if n < 0 or k < 0:
                raise ValueError("n 和 k 必须为非负整数")

            if comb_type == "组合":
                if k > n:
                    raise ValueError("k 不能大于 n")
                result = math.factorial(n) // (
                        math.factorial(k) * math.factorial(n - k)
                )
                self._show_result(f"C({n},{k}) = {result}")
            elif comb_type == "排列":
                if k > n:
                    raise ValueError("k 不能大于 n")
                result = math.factorial(n) // math.factorial(n - k)
                self._show_result(f"P({n},{k}) = {result}")
            elif comb_type == "重复组合":
                if n == 0:
                    raise ValueError("n 不能为 0")
                result = math.factorial(n + k - 1) // (
                        math.factorial(k) * math.factorial(n - 1)
                )
                self._show_result(f"H({n},{k}) = {result}")
            elif comb_type == "重复排列":
                result = n ** k
                self._show_result(f"π({n},{k}) = {result}")
        except ValueError as ex:
            self._show_error(str(ex))


def main(page: ft.Page):
    MathStatisticsApp(page)


if __name__ == "__main__":
    ft.app(target=main)
