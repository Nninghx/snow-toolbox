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


class TrigonometryApp:
    """三角函数计算器 Flet 应用"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.font_family = APP_FONT_FAMILY

        page.title = "三角函数计算器"
        page.window.width = 780
        page.window.height = 620
        page.window.min_width = 620
        page.window.min_height = 540
        page.padding = 0
        page.bgcolor = ft.Colors.GREY_100
        page.theme = ft.Theme(font_family=self.font_family)

        # 窗口图标由公共基类解析，直接使用
        page.window.icon = APP_ICON_PATH

        # 输入控件
        self.degree_sin = ft.TextField(label="角度值", hint_text="例如 30",
                                          text_size=13, border_radius=8, expand=1)
        self.radian_sin = ft.TextField(label="弧度值", hint_text="例如 1.5708",
                                          text_size=13, border_radius=8, expand=1)

        self.degree_cos = ft.TextField(label="角度值", hint_text="例如 60",
                                          text_size=13, border_radius=8, expand=1)
        self.radian_cos = ft.TextField(label="弧度值", hint_text="例如 1.0472",
                                          text_size=13, border_radius=8, expand=1)

        self.degree_tan = ft.TextField(label="角度值", hint_text="例如 45",
                                          text_size=13, border_radius=8, expand=1)
        self.radian_tan = ft.TextField(label="弧度值", hint_text="例如 0.7854",
                                          text_size=13, border_radius=8, expand=1)

        self.arcsin_input = ft.TextField(label="值 (-1 ~ 1)", text_size=13,
                                             border_radius=8, expand=1)
        self.arccos_input = ft.TextField(label="值 (-1 ~ 1)", text_size=13,
                                             border_radius=8, expand=1)
        self.arctan_input = ft.TextField(label="任意实数", text_size=13,
                                             border_radius=8, expand=1)

        self.output_unit = ft.RadioGroup(
            value="角度",
            content=ft.Row([
                ft.Radio(value="角度", label="角度"),
                ft.Radio(value="弧度", label="弧度"),
            ], spacing=16),
        )

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

    def _btn(self, label, callback, color=ft.Colors.BLUE_600):
        return ft.ElevatedButton(
            label, bgcolor=color, color=ft.Colors.WHITE, on_click=callback,
        )

    def _build_ui(self):
        # 正弦 Tab
        sine_tab = ft.Column([
            ft.Row([
                self.degree_sin,
                self._btn("计算 sin", lambda e: self.calc_sin_from_degree()),
            ], spacing=8),
            ft.Row([
                self.radian_sin,
                self._btn("计算 sin", lambda e: self.calc_sin_from_radian()),
            ], spacing=8),
        ], spacing=10)

        # 余弦 Tab
        cosine_tab = ft.Column([
            ft.Row([
                self.degree_cos,
                self._btn("计算 cos", lambda e: self.calc_cos_from_degree()),
            ], spacing=8),
            ft.Row([
                self.radian_cos,
                self._btn("计算 cos", lambda e: self.calc_cos_from_radian()),
            ], spacing=8),
        ], spacing=10)

        # 正切 Tab
        tangent_tab = ft.Column([
            ft.Row([
                self.degree_tan,
                self._btn("计算 tan", lambda e: self.calc_tan_from_degree()),
            ], spacing=8),
            ft.Row([
                self.radian_tan,
                self._btn("计算 tan", lambda e: self.calc_tan_from_radian()),
            ], spacing=8),
        ], spacing=10)

        # 反三角 Tab
        inverse_tab = ft.Column([
            self.output_unit,
            ft.Row([
                self.arcsin_input,
                self._btn("计算 arcsin", lambda e: self.calc_arcsin()),
            ], spacing=8),
            ft.Row([
                self.arccos_input,
                self._btn("计算 arccos", lambda e: self.calc_arccos()),
            ], spacing=8),
            ft.Row([
                self.arctan_input,
                self._btn("计算 arctan", lambda e: self.calc_arctan()),
            ], spacing=8),
        ], spacing=10)

        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=200,
            height=380,
            tabs=[
                ft.Tab(text="正弦 sin", content=self._pad(sine_tab)),
                ft.Tab(text="余弦 cos", content=self._pad(cosine_tab)),
                ft.Tab(text="正切 tan", content=self._pad(tangent_tab)),
                ft.Tab(text="反三角函数", content=self._pad(inverse_tab)),
            ],
        )
        tabs_card = self._make_card("函数选择", tabs)

        # 结果卡片
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
        self.page.update()

    def _show_error(self, msg):
        self.show_status(msg, success=False)
        self.result_text.value = f"错误: {msg}"
        self.page.update()

    def _get_float(self, field, name):
        text = (field.value or "").strip()
        if not text:
            raise ValueError(f"请输入{name}")
        try:
            return float(text)
        except ValueError:
            raise ValueError(f"{name}格式无效")

    # ----- sin -----
    def calc_sin_from_degree(self):
        try:
            degree = self._get_float(self.degree_sin, "角度值")
            value = math.sin(math.radians(degree))
            self._show_result(f"sin({degree}°) = {value:.6f}")
            self.show_status("计算完成", success=True)
        except ValueError as e:
            self._show_error(str(e))

    def calc_sin_from_radian(self):
        try:
            radian = self._get_float(self.radian_sin, "弧度值")
            value = math.sin(radian)
            self._show_result(f"sin({radian:.4f} rad) = {value:.6f}")
            self.show_status("计算完成", success=True)
        except ValueError as e:
            self._show_error(str(e))

    # ----- cos -----
    def calc_cos_from_degree(self):
        try:
            degree = self._get_float(self.degree_cos, "角度值")
            value = math.cos(math.radians(degree))
            self._show_result(f"cos({degree}°) = {value:.6f}")
            self.show_status("计算完成", success=True)
        except ValueError as e:
            self._show_error(str(e))

    def calc_cos_from_radian(self):
        try:
            radian = self._get_float(self.radian_cos, "弧度值")
            value = math.cos(radian)
            self._show_result(f"cos({radian:.4f} rad) = {value:.6f}")
            self.show_status("计算完成", success=True)
        except ValueError as e:
            self._show_error(str(e))

    # ----- tan -----
    def calc_tan_from_degree(self):
        try:
            degree = self._get_float(self.degree_tan, "角度值")
            if degree % 90 == 0 and degree % 180 != 0:
                raise ValueError("正切值在 90°±180°n 时无定义")
            value = math.tan(math.radians(degree))
            self._show_result(f"tan({degree}°) = {value:.6f}")
            self.show_status("计算完成", success=True)
        except ValueError as e:
            self._show_error(str(e))

    def calc_tan_from_radian(self):
        try:
            radian = self._get_float(self.radian_tan, "弧度值")
            # 判断是否接近 π/2 + nπ
            k = (radian - math.pi / 2) / math.pi
            if abs(k - round(k)) < 1e-9:
                raise ValueError("正切值在 π/2±nπ 时无定义")
            value = math.tan(radian)
            self._show_result(f"tan({radian:.4f} rad) = {value:.6f}")
            self.show_status("计算完成", success=True)
        except ValueError as e:
            self._show_error(str(e))

    # ----- 反三角 -----
    def _format_inverse(self, name, value, radian):
        if self.output_unit.value == "角度":
            return f"{name}({value}) = {math.degrees(radian):.2f}°"
        return f"{name}({value}) = {radian:.4f} rad"

    def calc_arcsin(self):
        try:
            value = self._get_float(self.arcsin_input, "值")
            if value < -1 or value > 1:
                raise ValueError("值必须在 -1 到 1 之间")
            self._show_result(self._format_inverse("arcsin", value, math.asin(value)))
            self.show_status("计算完成", success=True)
        except ValueError as e:
            self._show_error(str(e))

    def calc_arccos(self):
        try:
            value = self._get_float(self.arccos_input, "值")
            if value < -1 or value > 1:
                raise ValueError("值必须在 -1 到 1 之间")
            self._show_result(self._format_inverse("arccos", value, math.acos(value)))
            self.show_status("计算完成", success=True)
        except ValueError as e:
            self._show_error(str(e))

    def calc_arctan(self):
        try:
            value = self._get_float(self.arctan_input, "值")
            self._show_result(self._format_inverse("arctan", value, math.atan(value)))
            self.show_status("计算完成", success=True)
        except ValueError as e:
            self._show_error(str(e))


def main(page: ft.Page):
    TrigonometryApp(page)


if __name__ == "__main__":
    ft.app(target=main)
