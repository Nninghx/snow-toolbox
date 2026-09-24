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


class SurfaceAreaApp:
    """表面积计算器 Flet 应用"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.font_family = APP_FONT_FAMILY

        page.title = "表面积计算器"
        page.window.width = 820
        page.window.height = 680
        page.window.min_width = 640
        page.window.min_height = 560
        page.padding = 0
        page.bgcolor = ft.Colors.GREY_100
        page.theme = ft.Theme(font_family=self.font_family)

        # 窗口图标由公共基类解析，直接使用
        page.window.icon = APP_ICON_PATH

        # 球体
        self.sphere_radius = ft.TextField(label="半径 r", text_size=13,
                                              border_radius=8)
        # 立方体
        self.cube_side = ft.TextField(label="边长 a", text_size=13,
                                          border_radius=8)
        # 三角棱柱
        self.prism_type = ft.RadioGroup(
            value="equilateral",
            content=ft.Row([
                ft.Radio(value="equilateral", label="等边三角形"),
                ft.Radio(value="right", label="直角三角形"),
            ], spacing=12),
        )
        self.prism_base = ft.TextField(label="底边长度 b", text_size=13,
                                            border_radius=8)
        self.prism_triangle_height = ft.TextField(label="三角形高度 h",
                                                      text_size=13, border_radius=8)
        self.prism_length = ft.TextField(label="棱柱长度 l", text_size=13,
                                              border_radius=8)
        # 圆锥
        self.cone_input_type = ft.RadioGroup(
            value="slant",
            content=ft.Row([
                ft.Radio(value="slant", label="母线长度"),
                ft.Radio(value="height", label="高度"),
            ], spacing=12),
        )
        self.cone_radius = ft.TextField(label="底面半径 r", text_size=13,
                                            border_radius=8)
        self.cone_slant_or_height = ft.TextField(label="母线/高度",
                                                      text_size=13, border_radius=8)
        # 金字塔
        self.pyramid_length = ft.TextField(label="底面长度", text_size=13,
                                                border_radius=8)
        self.pyramid_width = ft.TextField(label="底面宽度", text_size=13,
                                               border_radius=8)
        self.pyramid_height = ft.TextField(label="高度", text_size=13,
                                                border_radius=8)

        # 结果
        self.result_text = ft.Text(
            "结果将显示在这里",
            size=16, weight=ft.FontWeight.BOLD,
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
        sphere_tab = ft.Column([
            self.sphere_radius,
            ft.Row([self._btn("计算表面积", self.calc_sphere)],
                     alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=10)

        cube_tab = ft.Column([
            self.cube_side,
            ft.Row([self._btn("计算表面积", self.calc_cube)],
                     alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=10)

        prism_tab = ft.Column([
            self.prism_type,
            self.prism_base,
            self.prism_triangle_height,
            self.prism_length,
            ft.Row([self._btn("计算表面积", self.calc_triangular_prism)],
                     alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=10)

        cone_tab = ft.Column([
            self.cone_input_type,
            self.cone_radius,
            self.cone_slant_or_height,
            ft.Row([
                self._btn("计算表面积", self.calc_cone),
                self._btn("计算侧面积", self.calc_cone_lateral),
            ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=10)

        pyramid_tab = ft.Column([
            self.pyramid_length,
            self.pyramid_width,
            self.pyramid_height,
            ft.Row([
                self._btn("计算表面积", self.calc_pyramid),
                self._btn("计算侧面积", self.calc_pyramid_lateral),
            ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=10)

        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=200,
            height=420,
            tabs=[
                ft.Tab(text="球体", content=self._pad(sphere_tab)),
                ft.Tab(text="立方体", content=self._pad(cube_tab)),
                ft.Tab(text="三角棱柱", content=self._pad(prism_tab)),
                ft.Tab(text="圆锥", content=self._pad(cone_tab)),
                ft.Tab(text="金字塔", content=self._pad(pyramid_tab)),
            ],
        )
        tabs_card = self._make_card("几何体选择", tabs)

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

    def _get_float(self, field, name):
        text = (field.value or "").strip()
        if not text:
            raise ValueError(f"请输入{name}")
        try:
            value = float(text)
        except ValueError:
            raise ValueError(f"{name}格式无效")
        if value < 0:
            raise ValueError(f"{name}不能为负数")
        return value

    # ----- 球体 -----
    def calc_sphere(self, e):
        try:
            r = self._get_float(self.sphere_radius, "半径")
            area = 4 * math.pi * r ** 2
            self._show_result(f"球体表面积 = 4πr² = {area:.4f}")
        except ValueError as ex:
            self._show_error(str(ex))

    # ----- 立方体 -----
    def calc_cube(self, e):
        try:
            a = self._get_float(self.cube_side, "边长")
            area = 6 * a ** 2
            self._show_result(f"立方体表面积 = 6a² = {area:.4f}")
        except ValueError as ex:
            self._show_error(str(ex))

    # ----- 三角棱柱 -----
    def calc_triangular_prism(self, e):
        try:
            b = self._get_float(self.prism_base, "底边长度")
            h = self._get_float(self.prism_triangle_height, "三角形高度")
            l = self._get_float(self.prism_length, "棱柱长度")

            base_area = b * h / 2
            if self.prism_type.value == "equilateral":
                lateral_area = (b * 3) * l
            else:
                hypotenuse = math.sqrt(b ** 2 + h ** 2)
                lateral_area = (b + h + hypotenuse) * l
            total = 2 * base_area + lateral_area
            self._show_result(
                f"三角棱柱表面积 = {total:.4f}\n"
                f"（底面积 {base_area:.4f} × 2 + 侧面积 {lateral_area:.4f}）"
            )
        except ValueError as ex:
            self._show_error(str(ex))

    # ----- 圆锥 -----
    def _cone_slant(self, r, value):
        if self.cone_input_type.value == "slant":
            if value < r:
                raise ValueError("母线长度必须不小于底面半径")
            return value
        return math.sqrt(r ** 2 + value ** 2)

    def calc_cone(self, e):
        try:
            r = self._get_float(self.cone_radius, "底面半径")
            value = self._get_float(self.cone_slant_or_height, "母线/高度")
            slant = self._cone_slant(r, value)
            base_area = math.pi * r ** 2
            lateral = math.pi * r * slant
            total = base_area + lateral
            self._show_result(
                f"圆锥表面积 = πr² + πrl = {total:.4f}\n"
                f"（底面积 {base_area:.4f} + 侧面积 {lateral:.4f}, 母线 l={slant:.4f}）"
            )
        except ValueError as ex:
            self._show_error(str(ex))

    def calc_cone_lateral(self, e):
        try:
            r = self._get_float(self.cone_radius, "底面半径")
            value = self._get_float(self.cone_slant_or_height, "母线/高度")
            slant = self._cone_slant(r, value)
            lateral = math.pi * r * slant
            self._show_result(f"圆锥侧面积 = πrl = {lateral:.4f}（母线 l={slant:.4f}）")
        except ValueError as ex:
            self._show_error(str(ex))

    # ----- 金字塔 -----
    def _pyramid_slants(self, length, width, height):
        slant1 = math.sqrt((length / 2) ** 2 + height ** 2)
        slant2 = math.sqrt((width / 2) ** 2 + height ** 2)
        return slant1, slant2

    def calc_pyramid(self, e):
        try:
            l = self._get_float(self.pyramid_length, "底面长度")
            w = self._get_float(self.pyramid_width, "底面宽度")
            h = self._get_float(self.pyramid_height, "高度")
            base_area = l * w
            slant1, slant2 = self._pyramid_slants(l, w, h)
            lateral = 2 * (l * slant2 / 2) + 2 * (w * slant1 / 2)
            total = base_area + lateral
            self._show_result(
                f"金字塔表面积 = {total:.4f}\n"
                f"（底面积 {base_area:.4f} + 侧面积 {lateral:.4f}）"
            )
        except ValueError as ex:
            self._show_error(str(ex))

    def calc_pyramid_lateral(self, e):
        try:
            l = self._get_float(self.pyramid_length, "底面长度")
            w = self._get_float(self.pyramid_width, "底面宽度")
            h = self._get_float(self.pyramid_height, "高度")
            slant1, slant2 = self._pyramid_slants(l, w, h)
            lateral = 2 * (l * slant2 / 2) + 2 * (w * slant1 / 2)
            self._show_result(f"金字塔侧面积 = {lateral:.4f}")
        except ValueError as ex:
            self._show_error(str(ex))


def main(page: ft.Page):
    SurfaceAreaApp(page)


if __name__ == "__main__":
    ft.app(target=main)
