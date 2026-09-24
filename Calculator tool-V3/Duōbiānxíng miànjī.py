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


# 图形配置：key -> (显示名, [(参数键, 标签, 默认值), ...])
SHAPE_CONFIGS = {
    "square": ("正方形", [("a", "边长", "5")]),
    "rectangle": ("矩形", [("a", "长", "6"), ("b", "宽", "4")]),
    "parallelogram": ("平行四边形", [("a", "底", "6"), ("h", "高", "4")]),
    "rhombus": ("菱形", [("d1", "对角线 d₁", "6"), ("d2", "对角线 d₂", "4")]),
    # 三角形：既可用 底×高，也可用三边（海伦公式），二选一
    "triangle": ("三角形", [
        ("a", "底 (可选)", ""),
        ("h", "高 (可选)", ""),
        ("s1", "边 a (海伦公式)", "3"),
        ("s2", "边 b (海伦公式)", "4"),
        ("s3", "边 c (海伦公式)", "5"),
    ]),
    "right_triangle": ("直角三角形", [("a", "直角边 a", "3"), ("b", "直角边 b", "4")]),
    "equilateral_triangle": ("等边三角形", [("a", "边长", "5")]),
    "circle": ("圆", [("r", "半径 r", "5")]),
    "sector": ("扇形", [("r", "半径 r", "5"), ("angle", "圆心角 (°)", "90")]),
    "annulus": ("圆环", [("R", "外半径 R", "6"), ("r", "内半径 r", "3")]),
    "parabolic_sector": ("抛物扇形", [("w", "底宽 w", "6"), ("h", "高 h", "4")]),
    "hyperbolic_sector": ("双曲扇形", [("a", "参数 a", "3"), ("b", "参数 b", "2"), ("t", "双曲角 t", "1.5")]),
    "elliptic_sector": ("椭圆扇形", [("a", "长半轴 a", "5"), ("b", "短半轴 b", "3"), ("angle", "参数角 θ (°)", "60")]),
    "ellipse": ("椭圆", [("a", "长半轴 a", "5"), ("b", "短半轴 b", "3")]),
}

SHAPE_KEYS = list(SHAPE_CONFIGS.keys())


class PolygonAreaApp:
    """多边形面积计算器 Flet 应用"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.font_family = APP_FONT_FAMILY

        page.title = "多边形面积计算器"
        page.window.width = 720
        page.window.height = 800
        page.window.min_width = 560
        page.window.min_height = 640
        page.padding = 0
        page.bgcolor = ft.Colors.GREY_100
        page.theme = ft.Theme(font_family=self.font_family)

        # 窗口图标由公共基类解析，直接使用
        page.window.icon = APP_ICON_PATH

        self.shape_dropdown = ft.Dropdown(
            label="选择图形",
            value="square",
            options=[ft.dropdown.Option(k, SHAPE_CONFIGS[k][0]) for k in SHAPE_KEYS],
            text_size=13,
            border_radius=8,
            on_change=self.on_shape_change,
        )

        self.inputs_container = ft.Column(spacing=8)
        self.fields = {}

        self.result_text = ft.Text(
            "面积 = ",
            size=22, weight=ft.FontWeight.BOLD,
            color=ft.Colors.GREEN_700,
            text_align=ft.TextAlign.CENTER,
            font_family=self.font_family,
            selectable=True,
        )
        self.formula_text = ft.Text(
            "",
            size=12,
            color=ft.Colors.BLUE_GREY_700,
            text_align=ft.TextAlign.CENTER,
            font_family="Consolas",
            selectable=True,
        )

        self.status_text = ft.Text("就绪", size=12, color=ft.Colors.BLUE_GREY_700,
                                    font_family=self.font_family)

        self._build_ui()
        self._rebuild_inputs("square")

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
            "计 算", icon=ft.Icons.CALCULATE,
            bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE,
            on_click=self.on_calculate, expand=True,
        )
        btn_clear = ft.OutlinedButton("清空", icon=ft.Icons.CLEAR,
                                         on_click=self.on_clear)

        select_card = self._make_card(
            "选择图形",
            ft.Column([self.shape_dropdown, self.inputs_container], spacing=10),
        )

        result_container = ft.Container(
            content=ft.Column([self.result_text, self.formula_text], spacing=8,
                              horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.all(14),
            border_radius=8,
            bgcolor=ft.Colors.BLUE_GREY_50,
        )
        result_card = self._make_card("计算结果", result_container)

        action_row = ft.Row([btn_calc, btn_clear], spacing=8)

        status_bar = ft.Container(
            content=self.status_text,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            bgcolor=ft.Colors.WHITE,
            border=ft.border.only(top=ft.BorderSide(1, ft.Colors.GREY_200)),
        )

        self.page.add(
            ft.Container(
                content=ft.Column(
                    [select_card, result_card, action_row],
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
        self.inputs_container.controls.clear()
        self.fields.clear()
        _, params = SHAPE_CONFIGS[shape]
        for key, label, default in params:
            field = ft.TextField(
                label=label,
                value=default,
                text_size=13,
                content_padding=ft.padding.all(10),
                border_radius=8,
                on_submit=lambda e: self.on_calculate(e),
            )
            self.fields[key] = field
            self.inputs_container.controls.append(field)
        self.page.update()

    def on_shape_change(self, e):
        self._rebuild_inputs(self.shape_dropdown.value)
        self.result_text.value = "面积 = "
        self.formula_text.value = ""
        self.page.update()

    def on_clear(self, e):
        for f in self.fields.values():
            f.value = ""
        self.result_text.value = "面积 = "
        self.formula_text.value = ""
        self.page.update()
        self.show_status("已清空", success=True)

    def on_calculate(self, e):
        try:
            self.calculate()
        except ValueError as ex:
            self._show_error(str(ex))
        except Exception as ex:
            self._show_error(f"计算失败: {ex}")

    def show_status(self, message, success=True):
        self.status_text.value = message
        self.page.snack_bar = ft.SnackBar(
            ft.Text(message, font_family=self.font_family),
            bgcolor=ft.Colors.GREEN if success else ft.Colors.RED,
            open=True,
        )
        self.page.update()

    def _get_value(self, key):
        field = self.fields.get(key)
        if field is None:
            return None
        text = (field.value or "").strip()
        if not text:
            return None
        try:
            val = float(text)
        except ValueError:
            return None
        if val <= 0:
            return None
        return val

    def _require(self, *keys):
        vals = []
        shape_name = SHAPE_CONFIGS[self.shape_dropdown.value][0]
        for k in keys:
            v = self._get_value(k)
            if v is None:
                raise ValueError(f"请输入有效的 {shape_name} 参数 ({k})")
            vals.append(v)
        return vals if len(vals) > 1 else vals[0]

    def _fmt(self, val):
        if val == int(val):
            return str(int(val))
        return f"{val:.4f}"

    def _show_error(self, msg):
        self.result_text.value = f"错误: {msg}"
        self.formula_text.value = ""
        self.show_status(msg, success=False)

    def _set_result(self, area, formula):
        self.result_text.value = f"面积 = {self._fmt(area)}"
        self.formula_text.value = formula
        self.show_status("计算完成", success=True)

    def calculate(self):
        shape = self.shape_dropdown.value

        if shape == "square":
            a = self._require("a")
            area = a * a
            self._set_result(area, (
                f"正方形 边长 a={a}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【面积公式】A = a²\n"
                f"【计算过程】A = {a}² = {self._fmt(area)}"
            ))

        elif shape == "rectangle":
            a, b = self._require("a", "b")
            area = a * b
            self._set_result(area, (
                f"矩形 长 a={a}, 宽 b={b}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【面积公式】A = a × b\n"
                f"【计算过程】A = {a} × {b} = {self._fmt(area)}"
            ))

        elif shape == "parallelogram":
            a, h = self._require("a", "h")
            area = a * h
            self._set_result(area, (
                f"平行四边形 底 a={a}, 高 h={h}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【面积公式】A = 底 × 高\n"
                f"【计算过程】A = {a} × {h} = {self._fmt(area)}"
            ))

        elif shape == "rhombus":
            d1, d2 = self._require("d1", "d2")
            area = (d1 * d2) / 2
            self._set_result(area, (
                f"菱形 对角线 d₁={d1}, d₂={d2}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【面积公式】A = (d₁ × d₂) / 2\n"
                f"【计算过程】A = ({d1} × {d2}) / 2 = {self._fmt(area)}"
            ))

        elif shape == "triangle":
            # 优先尝试 底 × 高
            a = self._get_value("a")
            h = self._get_value("h")
            if a is not None and h is not None:
                area = (a * h) / 2
                self._set_result(area, (
                    f"三角形 底 a={a}, 高 h={h}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"【面积公式】A = (底 × 高) / 2\n"
                    f"【计算过程】A = ({a} × {h}) / 2 = {self._fmt(area)}"
                ))
                return

            # 尝试海伦公式
            s1 = self._get_value("s1")
            s2 = self._get_value("s2")
            s3 = self._get_value("s3")
            if s1 is not None and s2 is not None and s3 is not None:
                if s1 + s2 <= s3 or s1 + s3 <= s2 or s2 + s3 <= s1:
                    raise ValueError("三边无法构成三角形")
                s = (s1 + s2 + s3) / 2
                area = math.sqrt(s * (s - s1) * (s - s2) * (s - s3))
                self._set_result(area, (
                    f"三角形 三边 a={s1}, b={s2}, c={s3}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"【海伦公式】A = √(s(s-a)(s-b)(s-c))\n"
                    f"【半周长】s = (a+b+c)/2 = ({s1}+{s2}+{s3})/2 = {self._fmt(s)}\n"
                    f"【计算过程】A = √({self._fmt(s)}×{self._fmt(s - s1)}×{self._fmt(s - s2)}×{self._fmt(s - s3)}) = {self._fmt(area)}"
                ))
                return

            raise ValueError("请输入底和高，或三边长度")

        elif shape == "right_triangle":
            a, b = self._require("a", "b")
            c = math.sqrt(a ** 2 + b ** 2)
            area = (a * b) / 2
            h = (a * b) / c
            p = (a ** 2) / c
            q = (b ** 2) / c
            alpha = math.degrees(math.atan(a / b))
            beta = math.degrees(math.atan(b / a))
            self._set_result(area, (
                f"直角三角形 a={a}, b={b}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【勾股定理】斜边 c = √(a²+b²) = {self._fmt(c)}\n"
                f"【高】h = ab/c = {self._fmt(h)}\n"
                f"【欧几里得关系】h² = p·q = {self._fmt(p)} × {self._fmt(q)} = {self._fmt(p * q)}\n"
                f"【边角关系】α = {alpha:.2f}°, β = {beta:.2f}°\n"
                f"【面积公式】A = (a × b) / 2"
            ))

        elif shape == "equilateral_triangle":
            a = self._require("a")
            area = (math.sqrt(3) / 4) * a ** 2
            self._set_result(area, (
                f"等边三角形 边长 a={a}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【面积公式】A = (√3 / 4) × a²\n"
                f"【计算过程】A = (√3 / 4) × {a}² = {self._fmt(area)}"
            ))

        elif shape == "circle":
            r = self._require("r")
            area = math.pi * r ** 2
            self._set_result(area, (
                f"圆 半径 r={r}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【面积公式】A = π × r²\n"
                f"【计算过程】A = π × {r}² = {self._fmt(area)}"
            ))

        elif shape == "sector":
            r, angle = self._require("r", "angle")
            area = (angle / 360) * math.pi * r ** 2
            arc = (angle / 360) * 2 * math.pi * r
            self._set_result(area, (
                f"扇形 半径 r={r}, 圆心角 θ={angle}°\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【面积公式】A = (θ / 360) × π × r²\n"
                f"【计算过程】A = ({angle}/360) × π × {r}² = {self._fmt(area)}\n"
                f"【弧长公式】L = (θ / 360) × 2πr = {self._fmt(arc)}"
            ))

        elif shape == "annulus":
            R, r = self._require("R", "r")
            if R <= r:
                raise ValueError("外半径必须大于内半径")
            area = math.pi * (R ** 2 - r ** 2)
            self._set_result(area, (
                f"圆环 外半径 R={R}, 内半径 r={r}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【面积公式】A = π × (R² - r²)\n"
                f"【计算过程】A = π × ({R}² - {r}²) = π × {self._fmt(R ** 2 - r ** 2)} = {self._fmt(area)}"
            ))

        elif shape == "parabolic_sector":
            w, h = self._require("w", "h")
            area = (2 / 3) * w * h
            self._set_result(area, (
                f"抛物扇形 底宽 w={w}, 高 h={h}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【面积公式】A = (2/3) × w × h\n"
                f"【计算过程】A = (2/3) × {w} × {h} = {self._fmt(area)}"
            ))

        elif shape == "hyperbolic_sector":
            a, b, t = self._require("a", "b", "t")
            area = (a * b / 2) * t
            x = a * math.cosh(t)
            y = b * math.sinh(t)
            self._set_result(area, (
                f"双曲扇形 a={a}, b={b}, t={t}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【参数方程】x = a·cosh(u), y = b·sinh(u)\n"
                f"【面积公式】A = (a·b / 2) × t\n"
                f"【计算过程】A = ({a}×{b} / 2) × {t} = {self._fmt(area)}\n"
                f"【终点坐标】({self._fmt(x)}, {self._fmt(y)})"
            ))

        elif shape == "elliptic_sector":
            a, b, angle_deg = self._require("a", "b", "angle")
            if angle_deg > 360:
                raise ValueError("参数角不能超过 360°")
            angle_rad = math.radians(angle_deg)
            area = (a * b / 2) * angle_rad
            x = a * math.cos(angle_rad)
            y = b * math.sin(angle_rad)
            self._set_result(area, (
                f"椭圆扇形 a={a}, b={b}, θ={angle_deg}°\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【参数方程】x = a·cos(θ), y = b·sin(θ)\n"
                f"【面积公式】A = (a·b / 2) × θ\n"
                f"【计算过程】A = ({a}×{b} / 2) × {self._fmt(angle_rad)} = {self._fmt(area)}\n"
                f"【终点坐标】({self._fmt(x)}, {self._fmt(y)})"
            ))

        elif shape == "ellipse":
            a, b = self._require("a", "b")
            area = math.pi * a * b
            self._set_result(area, (
                f"椭圆 长半轴 a={a}, 短半轴 b={b}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【面积公式】A = π × a × b\n"
                f"【计算过程】A = π × {a} × {b} = {self._fmt(area)}"
            ))


def main(page: ft.Page):
    PolygonAreaApp(page)


if __name__ == "__main__":
    ft.app(target=main)
