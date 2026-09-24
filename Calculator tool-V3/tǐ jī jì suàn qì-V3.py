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


# 每个形状的参数定义：(key, label, hint)
SHAPE_CONFIGS = {
    "长方体": [("length", "长度", ""), ("width", "宽度", ""), ("height", "高度", "")],
    "圆柱体": [("radius", "底面半径", ""), ("height", "高度", "")],
    "球体": [("radius", "半径", "")],
    "金字塔": [("base_area", "底面积", ""), ("height", "高度", "")],
    "直圆柱": [("radius", "底面半径", ""), ("height", "高度", "")],
    "立方体": [("side", "边长", "")],
    "长方形水箱": [
        ("length", "长度", ""), ("width", "宽度", ""),
        ("height", "水箱高度", ""), ("liquid_height", "液体高度", ""),
    ],
    "管": [
        ("outer_diameter", "外径", ""), ("inner_diameter", "内径", ""),
        ("length", "长度", ""),
    ],
    "胶囊": [("radius", "半径", ""), ("height", "总高度", "")],
    "正四棱锥": [("base_side", "底边长度", ""), ("height", "高度", "")],
    "圆台": [
        ("top_radius", "上底半径", ""), ("bottom_radius", "下底半径", ""),
        ("height", "高度", ""),
    ],
    "圆锥": [("radius", "底面半径", ""), ("height", "高度", "")],
    "半球": [("radius", "半径", "")],
    "圆环": [("major_radius", "大半径 R", ""), ("minor_radius", "小半径 r", "")],
}

SHAPE_NAMES = list(SHAPE_CONFIGS.keys())


class VolumeCalculatorApp:
    """体积计算器 Flet 应用"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.font_family = APP_FONT_FAMILY

        page.title = "体积计算器"
        page.window.width = 820
        page.window.height = 720
        page.window.min_width = 640
        page.window.min_height = 600
        page.padding = 0
        page.bgcolor = ft.Colors.GREY_100
        page.theme = ft.Theme(font_family=self.font_family)

        # 窗口图标由公共基类解析，直接使用
        page.window.icon = APP_ICON_PATH

        self.shape_dropdown = ft.Dropdown(
            label="几何形状",
            value="长方体",
            options=[ft.dropdown.Option(name) for name in SHAPE_NAMES],
            text_size=13,
            border_radius=8,
            width=260,
            on_change=self.on_shape_change,
        )

        self.inputs_container = ft.Column(spacing=8)
        self.fields = {}

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
        self._rebuild_inputs("长方体")

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
        btn_calc = ft.ElevatedButton(
            "计算体积", icon=ft.Icons.CALCULATE,
            bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE,
            on_click=self.on_calculate,
        )
        btn_clear = ft.OutlinedButton("清空", icon=ft.Icons.CLEAR,
                                         on_click=self.on_clear)

        select_card = self._make_card(
            "选择形状",
            ft.Column([
                self.shape_dropdown,
                self.inputs_container,
                ft.Row([btn_calc, btn_clear], spacing=8),
            ], spacing=10),
        )

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
                    [select_card, result_card],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
                padding=12,
                expand=True,
            ),
        )
        self.page.add(status_bar)

    def _rebuild_inputs(self, shape):
        """重建当前形状的输入框"""
        self.inputs_container.controls.clear()
        self.fields.clear()
        for key, label, hint in SHAPE_CONFIGS[shape]:
            field = ft.TextField(
                label=label,
                hint_text=hint,
                text_size=13,
                content_padding=ft.padding.all(10),
                border_radius=8,
            )
            self.fields[key] = field
            self.inputs_container.controls.append(field)
        self.page.update()

    def on_shape_change(self, e):
        self._rebuild_inputs(self.shape_dropdown.value)
        self.result_text.value = "结果将显示在这里"
        self.page.update()

    def on_clear(self, e):
        for f in self.fields.values():
            f.value = ""
        self.result_text.value = "结果将显示在这里"
        self.page.update()
        self.show_status("已清空", success=True)

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

    def _get_float(self, key, name=None, positive=True):
        field = self.fields.get(key)
        if field is None:
            raise ValueError(f"缺少参数 {key}")
        text = (field.value or "").strip()
        label = name or field.label or key
        if not text:
            raise ValueError(f"请输入{label}")
        try:
            value = float(text)
        except ValueError:
            raise ValueError(f"{label}格式无效")
        if positive and value <= 0:
            raise ValueError(f"{label}必须大于 0")
        return value

    # ----- 各形状计算 -----
    def _calc_shape(self, shape):
        if shape == "长方体":
            l = self._get_float("length")
            w = self._get_float("width")
            h = self._get_float("height")
            return l * w * h, f"长方体 V = lwh = {l}×{w}×{h}"

        if shape == "圆柱体":
            r = self._get_float("radius")
            h = self._get_float("height")
            return math.pi * r ** 2 * h, f"圆柱体 V = πr²h"

        if shape == "球体":
            r = self._get_float("radius")
            return (4 / 3) * math.pi * r ** 3, "球体 V = (4/3)πr³"

        if shape == "金字塔":
            base_area = self._get_float("base_area")
            h = self._get_float("height")
            return (1 / 3) * base_area * h, "金字塔 V = (1/3) × 底面积 × 高"

        if shape == "直圆柱":
            r = self._get_float("radius")
            h = self._get_float("height")
            return math.pi * r ** 2 * h, "直圆柱 V = πr²h"

        if shape == "立方体":
            a = self._get_float("side")
            return a ** 3, f"立方体 V = a³ = {a}³"

        if shape == "长方形水箱":
            l = self._get_float("length")
            w = self._get_float("width")
            h = self._get_float("height")
            lh = self._get_float("liquid_height", positive=False)
            if lh < 0:
                raise ValueError("液体高度不能为负")
            if lh > h:
                raise ValueError("液体高度不能大于水箱高度")
            return l * w * lh, "水箱液体 V = l × w × 液体高度"

        if shape == "管":
            outer = self._get_float("outer_diameter")
            inner = self._get_float("inner_diameter")
            length = self._get_float("length")
            if inner >= outer:
                raise ValueError("内径必须小于外径")
            outer_r = outer / 2
            inner_r = inner / 2
            return math.pi * (outer_r ** 2 - inner_r ** 2) * length, \
                "管 V = π(R² - r²)l"

        if shape == "胶囊":
            r = self._get_float("radius")
            h = self._get_float("height")
            if h < 2 * r:
                raise ValueError("总高度不能小于直径 (2r)")
            cyl_h = h - 2 * r
            cyl_v = math.pi * r ** 2 * cyl_h
            sphere_v = (4 / 3) * math.pi * r ** 3
            return cyl_v + sphere_v, "胶囊 V = 圆柱部分 + 完整球体"

        if shape == "正四棱锥":
            a = self._get_float("base_side")
            h = self._get_float("height")
            return (1 / 3) * a ** 2 * h, f"正四棱锥 V = (1/3)a²h"

        if shape == "圆台":
            r1 = self._get_float("top_radius")
            r2 = self._get_float("bottom_radius")
            h = self._get_float("height")
            return (1 / 3) * math.pi * h * (r1 ** 2 + r2 ** 2 + r1 * r2), \
                "圆台 V = (1/3)πh(R² + r² + Rr)"

        if shape == "圆锥":
            r = self._get_float("radius")
            h = self._get_float("height")
            return (1 / 3) * math.pi * r ** 2 * h, "圆锥 V = (1/3)πr²h"

        if shape == "半球":
            r = self._get_float("radius")
            return (2 / 3) * math.pi * r ** 3, "半球 V = (2/3)πr³"

        if shape == "圆环":
            R = self._get_float("major_radius")
            r = self._get_float("minor_radius")
            if r >= R:
                raise ValueError("小半径必须小于大半径")
            return 2 * math.pi ** 2 * R * r ** 2, "圆环 V = 2π²Rr²"

        raise ValueError(f"未知形状: {shape}")

    def on_calculate(self, e):
        shape = self.shape_dropdown.value
        try:
            volume, formula = self._calc_shape(shape)
            self._show_result(f"{formula}\n{shape}体积 = {volume:.4f} 立方单位")
        except ValueError as ex:
            self._show_error(str(ex))
        except Exception as ex:
            self._show_error(f"计算出错: {ex}")


def main(page: ft.Page):
    VolumeCalculatorApp(page)


if __name__ == "__main__":
    ft.app(target=main)
