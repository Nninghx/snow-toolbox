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
    "parallelogram": ("平行四边形", [("a", "边 a", "6"), ("b", "边 b", "5")]),
    "rhombus": ("菱形", [("d1", "对角线 d₁", "6"), ("d2", "对角线 d₂", "4")]),
    "triangle": ("三角形", [("s1", "边 a", "3"), ("s2", "边 b", "4"), ("s3", "边 c", "5")]),
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


class PolygonPerimeterApp:
    """多边形周长计算器 Flet 应用"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.font_family = APP_FONT_FAMILY

        page.title = "多边形周长计算器"
        page.window.width = 720
        page.window.height = 780
        page.window.min_width = 560
        page.window.min_height = 620
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
            "周长 = ",
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
        self.result_text.value = "周长 = "
        self.formula_text.value = ""
        self.page.update()

    def on_clear(self, e):
        for f in self.fields.values():
            f.value = ""
        self.result_text.value = "周长 = "
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
        for k in keys:
            v = self._get_value(k)
            if v is None:
                raise ValueError(f"请输入有效的 {SHAPE_CONFIGS[self.shape_dropdown.value][0]} 参数 ({k})")
            vals.append(v)
        return vals if len(vals) > 1 else vals[0]

    def _simpson(self, f, a, b, n=200):
        """辛普森数值积分"""
        if a == b:
            return 0.0
        if n % 2 == 1:
            n += 1
        h = (b - a) / n
        s = f(a) + f(b)
        for i in range(1, n):
            x = a + i * h
            s += (4 if i % 2 == 1 else 2) * f(x)
        return s * h / 3

    def _fmt(self, val):
        if val == int(val):
            return str(int(val))
        return f"{val:.4f}"

    def _show_error(self, msg):
        self.result_text.value = f"错误: {msg}"
        self.formula_text.value = ""
        self.show_status(msg, success=False)

    def _set_result(self, perimeter, formula):
        self.result_text.value = f"周长 = {self._fmt(perimeter)}"
        self.formula_text.value = formula
        self.show_status("计算完成", success=True)

    def calculate(self):
        shape = self.shape_dropdown.value

        if shape == "square":
            a = self._require("a")
            self._set_result(4 * a, (
                f"正方形 边长 a={a}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【周长公式】P = 4a\n"
                f"【计算过程】P = 4 × {a} = {self._fmt(4 * a)}"
            ))

        elif shape == "rectangle":
            a, b = self._require("a", "b")
            self._set_result(2 * (a + b), (
                f"矩形 长 a={a}, 宽 b={b}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【周长公式】P = 2(a + b)\n"
                f"【计算过程】P = 2 × ({a} + {b}) = {self._fmt(2 * (a + b))}"
            ))

        elif shape == "parallelogram":
            a, b = self._require("a", "b")
            self._set_result(2 * (a + b), (
                f"平行四边形 边 a={a}, 边 b={b}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【周长公式】P = 2(a + b)\n"
                f"【计算过程】P = 2 × ({a} + {b}) = {self._fmt(2 * (a + b))}"
            ))

        elif shape == "rhombus":
            d1, d2 = self._require("d1", "d2")
            side = math.sqrt(d1 ** 2 + d2 ** 2) / 2
            self._set_result(4 * side, (
                f"菱形 对角线 d₁={d1}, d₂={d2}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【边长公式】s = √(d₁² + d₂²) / 2 = {self._fmt(side)}\n"
                f"【周长公式】P = 4s = 2√(d₁² + d₂²)"
            ))

        elif shape == "triangle":
            s1, s2, s3 = self._require("s1", "s2", "s3")
            if s1 + s2 <= s3 or s1 + s3 <= s2 or s2 + s3 <= s1:
                raise ValueError("三边无法构成三角形")
            self._set_result(s1 + s2 + s3, (
                f"三角形 三边 a={s1}, b={s2}, c={s3}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【周长公式】P = a + b + c\n"
                f"【计算过程】P = {s1} + {s2} + {s3} = {self._fmt(s1 + s2 + s3)}"
            ))

        elif shape == "right_triangle":
            a, b = self._require("a", "b")
            c = math.sqrt(a ** 2 + b ** 2)
            self._set_result(a + b + c, (
                f"直角三角形 a={a}, b={b}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【勾股定理】c = √(a² + b²) = {self._fmt(c)}\n"
                f"【周长公式】P = a + b + c"
            ))

        elif shape == "equilateral_triangle":
            a = self._require("a")
            self._set_result(3 * a, (
                f"等边三角形 边长 a={a}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【周长公式】P = 3a\n"
                f"【计算过程】P = 3 × {a} = {self._fmt(3 * a)}"
            ))

        elif shape == "circle":
            r = self._require("r")
            self._set_result(2 * math.pi * r, (
                f"圆 半径 r={r}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【周长公式】C = 2πr\n"
                f"【计算过程】C = 2 × π × {r} = {self._fmt(2 * math.pi * r)}"
            ))

        elif shape == "sector":
            r, angle = self._require("r", "angle")
            arc = (angle / 360) * 2 * math.pi * r
            self._set_result(arc + 2 * r, (
                f"扇形 半径 r={r}, 圆心角 θ={angle}°\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【弧长公式】L = (θ / 360) × 2πr = {self._fmt(arc)}\n"
                f"【周长公式】P = L + 2r"
            ))

        elif shape == "annulus":
            R, r = self._require("R", "r")
            if R <= r:
                raise ValueError("外半径必须大于内半径")
            self._set_result(2 * math.pi * (R + r), (
                f"圆环 外半径 R={R}, 内半径 r={r}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【外圆周长】C₁ = 2πR = {self._fmt(2 * math.pi * R)}\n"
                f"【内圆周长】C₂ = 2πr = {self._fmt(2 * math.pi * r)}\n"
                f"【总周长】P = C₁ + C₂ = 2π(R + r)"
            ))

        elif shape == "parabolic_sector":
            w, h = self._require("w", "h")

            def integrand(x):
                dydx = 8 * h * x / (w ** 2)
                return math.sqrt(1 + dydx ** 2)

            arc = 2 * self._simpson(integrand, 0, w / 2)
            self._set_result(w + arc, (
                f"抛物扇形 底宽 w={w}, 高 h={h}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【抛物线方程】y = (4h/w²)x²\n"
                f"【弧长公式】L = ∫√(1 + (dy/dx)²) dx = {self._fmt(arc)}\n"
                f"【周长公式】P = w + L"
            ))

        elif shape == "hyperbolic_sector":
            a, b, t = self._require("a", "b", "t")

            def integrand(u):
                dxdu = a * math.sinh(u)
                dydu = b * math.cosh(u)
                return math.sqrt(dxdu ** 2 + dydu ** 2)

            arc = self._simpson(integrand, 0, t)
            r1 = a
            x2 = a * math.cosh(t)
            y2 = b * math.sinh(t)
            r2 = math.sqrt(x2 ** 2 + y2 ** 2)
            self._set_result(arc + r1 + r2, (
                f"双曲扇形 a={a}, b={b}, t={t}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【参数方程】x = a·cosh(u), y = b·sinh(u)\n"
                f"【弧长】L = {self._fmt(arc)}\n"
                f"【半径】r₁ = {self._fmt(r1)}, r₂ = {self._fmt(r2)}\n"
                f"【周长公式】P = L + r₁ + r₂"
            ))

        elif shape == "elliptic_sector":
            a, b, angle_deg = self._require("a", "b", "angle")
            if angle_deg > 360:
                raise ValueError("参数角不能超过 360°")
            angle_rad = math.radians(angle_deg)

            def integrand(theta):
                dxdt = -a * math.sin(theta)
                dydt = b * math.cos(theta)
                return math.sqrt(dxdt ** 2 + dydt ** 2)

            arc = self._simpson(integrand, 0, angle_rad)
            r1 = a
            x2 = a * math.cos(angle_rad)
            y2 = b * math.sin(angle_rad)
            r2 = math.sqrt(x2 ** 2 + y2 ** 2)
            self._set_result(arc + r1 + r2, (
                f"椭圆扇形 a={a}, b={b}, θ={angle_deg}°\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【参数方程】x = a·cos(θ), y = b·sin(θ)\n"
                f"【弧长】L = {self._fmt(arc)}\n"
                f"【半径】r₁ = {self._fmt(r1)}, r₂ = {self._fmt(r2)}\n"
                f"【周长公式】P = L + r₁ + r₂"
            ))

        elif shape == "ellipse":
            a, b = self._require("a", "b")
            h_val = ((a - b) / (a + b)) ** 2
            perimeter = math.pi * (a + b) * (1 + 3 * h_val / (10 + math.sqrt(4 - 3 * h_val)))
            self._set_result(perimeter, (
                f"椭圆 长半轴 a={a}, 短半轴 b={b}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【拉马努金近似】h = ((a-b)/(a+b))² = {self._fmt(h_val)}\n"
                f"【周长公式】P ≈ π(a+b)(1 + 3h/(10+√(4-3h)))"
            ))


def main(page: ft.Page):
    PolygonPerimeterApp(page)


if __name__ == "__main__":
    ft.app(target=main)
