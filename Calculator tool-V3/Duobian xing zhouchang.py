import tkinter as tk
from tkinter import ttk, messagebox
import math


class PolygonPerimeterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("多边形周长计算器")
        self.root.geometry("460x560")
        self.root.resizable(False, False)

        self._setup_styles()
        self._create_ui()

    def _setup_styles(self):
        """配置样式"""
        style = ttk.Style()
        style.theme_use("clam")

        self.colors = {
            "bg": "#f5f7fa",
            "card": "#ffffff",
            "primary": "#4a90d9",
            "success": "#27ae60",
            "text": "#2c3e50",
            "muted": "#7f8c8d",
        }

        self.root.configure(bg=self.colors["bg"])

        style.configure("Title.TLabel",
                        font=("Microsoft YaHei UI", 15, "bold"),
                        foreground=self.colors["primary"],
                        background=self.colors["bg"])

        style.configure("Result.TLabel",
                        font=("Microsoft YaHei UI", 18, "bold"),
                        foreground=self.colors["success"],
                        background=self.colors["bg"])

        style.configure("Formula.TLabel",
                        font=("Microsoft YaHei UI", 9),
                        foreground=self.colors["muted"],
                        background=self.colors["bg"])

        style.configure("TRadiobutton",
                        font=("Microsoft YaHei UI", 10))

        style.configure("TLabel",
                        font=("Microsoft YaHei UI", 10),
                        background=self.colors["bg"])

        style.configure("TLabelframe",
                        background=self.colors["bg"])

        style.configure("TLabelframe.Label",
                        font=("Microsoft YaHei UI", 10, "bold"),
                        foreground=self.colors["text"],
                        background=self.colors["bg"])

    def _create_ui(self):
        """创建界面"""
        # 标题
        ttk.Label(self.root, text="多边形周长计算器",
                  style="Title.TLabel").pack(pady=(15, 10))

        # 图形选择区
        select_frame = ttk.LabelFrame(self.root, text="选择图形", padding=10)
        select_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.shape_var = tk.StringVar(value="square")

        shapes = [
            ("正方形", "square"),
            ("矩形", "rectangle"),
            ("平行四边形", "parallelogram"),
            ("菱形", "rhombus"),
            ("三角形", "triangle"),
            ("直角三角形", "right_triangle"),
            ("等边三角形", "equilateral_triangle"),
            ("圆", "circle"),
            ("扇形", "sector"),
            ("圆环", "annulus"),
            ("抛物扇形", "parabolic_sector"),
            ("双曲扇形", "hyperbolic_sector"),
            ("椭圆扇形", "elliptic_sector"),
            ("椭圆", "ellipse"),
        ]

        rows_data = [shapes[i:i+3] for i in range(0, len(shapes), 3)]
        for i, row_shapes in enumerate(rows_data):
            row = ttk.Frame(select_frame)
            row.pack(fill="x", pady=(0 if i == 0 else 5, 0))
            for text, value in row_shapes:
                ttk.Radiobutton(row, text=text, variable=self.shape_var,
                                value=value, command=self.on_shape_change).pack(
                                    side="left", padx=(0, 15))

        # 参数输入区
        self.input_frame = ttk.LabelFrame(self.root, text="输入参数", padding=15)
        self.input_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # 结果区
        result_frame = ttk.Frame(self.root)
        result_frame.pack(fill="x", padx=20, pady=(0, 5))

        self.result_label = ttk.Label(result_frame, text="周长 = ",
                                      style="Result.TLabel", anchor="center")
        self.result_label.pack(fill="x")

        self.formula_label = ttk.Label(result_frame, text="",
                                       style="Formula.TLabel", anchor="center")
        self.formula_label.pack(fill="x", pady=(2, 0))

        # 计算按钮
        ttk.Button(self.root, text="计 算", command=self.calculate).pack(
            fill="x", padx=20, pady=(5, 15))

        # 初始化输入框
        self.entries = {}
        self._build_inputs("square")

    def _build_inputs(self, shape):
        """根据图形创建对应的输入框"""
        for widget in self.input_frame.winfo_children():
            widget.destroy()
        self.entries.clear()

        configs = {
            "square": [
                ("a", "边长", "5"),
            ],
            "rectangle": [
                ("a", "长", "6"),
                ("b", "宽", "4"),
            ],
            "parallelogram": [
                ("a", "边 a", "6"),
                ("b", "边 b", "5"),
            ],
            "rhombus": [
                ("d1", "对角线 d₁", "6"),
                ("d2", "对角线 d₂", "4"),
            ],
            "triangle": [
                ("s1", "边 a", "3"),
                ("s2", "边 b", "4"),
                ("s3", "边 c", "5"),
            ],
            "right_triangle": [
                ("a", "直角边 a", "3"),
                ("b", "直角边 b", "4"),
            ],
            "equilateral_triangle": [
                ("a", "边长", "5"),
            ],
            "circle": [
                ("r", "半径 r", "5"),
            ],
            "sector": [
                ("r", "半径 r", "5"),
                ("angle", "圆心角 (°)", "90"),
            ],
            "annulus": [
                ("R", "外半径 R", "6"),
                ("r", "内半径 r", "3"),
            ],
            "parabolic_sector": [
                ("w", "底宽 w", "6"),
                ("h", "高 h", "4"),
            ],
            "hyperbolic_sector": [
                ("a", "参数 a", "3"),
                ("b", "参数 b", "2"),
                ("t", "双曲角 t", "1.5"),
            ],
            "elliptic_sector": [
                ("a", "长半轴 a", "5"),
                ("b", "短半轴 b", "3"),
                ("angle", "参数角 θ (°)", "60"),
            ],
            "ellipse": [
                ("a", "长半轴 a", "5"),
                ("b", "短半轴 b", "3"),
            ],
        }

        params = configs[shape]
        for i, (key, label, default) in enumerate(params):
            row = ttk.Frame(self.input_frame)
            row.pack(fill="x", pady=(0, 8))

            ttk.Label(row, text=f"{label}:", width=12, anchor="e").pack(
                side="left", padx=(0, 5))

            entry = ttk.Entry(row, width=15)
            entry.insert(0, default)
            entry.pack(side="left")
            entry.bind("<Return>", lambda e: self.calculate())

            self.entries[key] = entry

    def on_shape_change(self):
        """切换图形时重建输入框"""
        self._build_inputs(self.shape_var.get())
        self.result_label.config(text="周长 = ")
        self.formula_label.config(text="")

    def _get_value(self, key):
        """获取输入值"""
        try:
            val = float(self.entries[key].get())
            if val <= 0:
                raise ValueError
            return val
        except (ValueError, KeyError):
            return None

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

    def calculate(self):
        """计算周长"""
        shape = self.shape_var.get()

        if shape == "square":
            a = self._get_value("a")
            if a is None:
                return self._show_error("请输入有效的边长")
            perimeter = 4 * a
            self.result_label.config(text=f"周长 = {self._fmt(perimeter)}")
            self.formula_label.config(text=(
                f"正方形 边长 a={a}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【周长公式】P = 4a"
            ))

        elif shape == "rectangle":
            a = self._get_value("a")
            b = self._get_value("b")
            if a is None or b is None:
                return self._show_error("请输入有效的长和宽")
            perimeter = 2 * (a + b)
            self.result_label.config(text=f"周长 = {self._fmt(perimeter)}")
            self.formula_label.config(text=(
                f"矩形 长 a={a}, 宽 b={b}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【周长公式】P = 2(a + b)"
            ))

        elif shape == "parallelogram":
            a = self._get_value("a")
            b = self._get_value("b")
            if a is None or b is None:
                return self._show_error("请输入有效的边长")
            perimeter = 2 * (a + b)
            self.result_label.config(text=f"周长 = {self._fmt(perimeter)}")
            self.formula_label.config(text=(
                f"平行四边形 边 a={a}, 边 b={b}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【周长公式】P = 2(a + b)"
            ))

        elif shape == "rhombus":
            d1 = self._get_value("d1")
            d2 = self._get_value("d2")
            if d1 is None or d2 is None:
                return self._show_error("请输入有效的对角线长度")
            side = math.sqrt(d1**2 + d2**2) / 2
            perimeter = 4 * side
            self.result_label.config(text=f"周长 = {self._fmt(perimeter)}")
            self.formula_label.config(text=(
                f"菱形 对角线 d₁={d1}, d₂={d2}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【边长公式】s = √(d₁² + d₂²) / 2\n"
                f"【周长公式】P = 4s = 2√(d₁² + d₂²)"
            ))

        elif shape == "triangle":
            s1 = self._get_value("s1")
            s2 = self._get_value("s2")
            s3 = self._get_value("s3")
            if s1 is None or s2 is None or s3 is None:
                return self._show_error("请输入三边长度")
            if s1 + s2 <= s3 or s1 + s3 <= s2 or s2 + s3 <= s1:
                return self._show_error("三边无法构成三角形")
            perimeter = s1 + s2 + s3
            self.result_label.config(text=f"周长 = {self._fmt(perimeter)}")
            self.formula_label.config(text=(
                f"三角形 三边 a={s1}, b={s2}, c={s3}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【周长公式】P = a + b + c"
            ))

        elif shape == "right_triangle":
            a = self._get_value("a")
            b = self._get_value("b")
            if a is None or b is None:
                return self._show_error("请输入有效的直角边长度")
            c = math.sqrt(a**2 + b**2)
            perimeter = a + b + c
            self.result_label.config(text=f"周长 = {self._fmt(perimeter)}")
            self.formula_label.config(text=(
                f"直角三角形 a={a}, b={b}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【勾股定理】c = √(a² + b²)\n"
                f"【周长公式】P = a + b + c = a + b + √(a² + b²)"
            ))

        elif shape == "equilateral_triangle":
            a = self._get_value("a")
            if a is None:
                return self._show_error("请输入有效的边长")
            perimeter = 3 * a
            self.result_label.config(text=f"周长 = {self._fmt(perimeter)}")
            self.formula_label.config(text=(
                f"等边三角形 边长 a={a}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【周长公式】P = 3a"
            ))

        elif shape == "circle":
            r = self._get_value("r")
            if r is None:
                return self._show_error("请输入有效的半径")
            perimeter = 2 * math.pi * r
            self.result_label.config(text=f"周长 = {self._fmt(perimeter)}")
            self.formula_label.config(text=(
                f"圆 半径 r={r}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【周长公式】C = 2πr"
            ))

        elif shape == "sector":
            r = self._get_value("r")
            angle = self._get_value("angle")
            if r is None or angle is None:
                return self._show_error("请输入有效的半径和圆心角")
            arc = (angle / 360) * 2 * math.pi * r
            perimeter = arc + 2 * r
            self.result_label.config(text=f"周长 = {self._fmt(perimeter)}")
            self.formula_label.config(text=(
                f"扇形 半径 r={r}, 圆心角 θ={angle}°\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【弧长公式】L = (θ / 360) × 2πr\n"
                f"【周长公式】P = L + 2r"
            ))

        elif shape == "annulus":
            R = self._get_value("R")
            r = self._get_value("r")
            if R is None or r is None:
                return self._show_error("请输入有效的半径")
            if R <= r:
                return self._show_error("外半径必须大于内半径")
            outer_c = 2 * math.pi * R
            inner_c = 2 * math.pi * r
            perimeter = outer_c + inner_c
            self.result_label.config(text=f"周长 = {self._fmt(perimeter)}")
            self.formula_label.config(text=(
                f"圆环 外半径 R={R}, 内半径 r={r}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【外圆周长】C₁ = 2πR\n"
                f"【内圆周长】C₂ = 2πr\n"
                f"【总周长】P = C₁ + C₂ = 2π(R + r)"
            ))

        elif shape == "parabolic_sector":
            w = self._get_value("w")
            h = self._get_value("h")
            if w is None or h is None:
                return self._show_error("请输入有效的底宽和高")
            # 抛物线弧长：y = (4h/w²)x², x ∈ [-w/2, w/2]
            # dy/dx = 8hx/w²
            # arc = ∫√(1 + (8hx/w²)²) dx, 利用对称性 = 2 × ∫[0, w/2]
            def integrand(x):
                dydx = 8 * h * x / (w ** 2)
                return math.sqrt(1 + dydx ** 2)
            arc = 2 * self._simpson(integrand, 0, w / 2)
            perimeter = w + arc
            self.result_label.config(text=f"周长 = {self._fmt(perimeter)}")
            self.formula_label.config(text=(
                f"抛物扇形 底宽 w={w}, 高 h={h}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【抛物线方程】y = (4h/w²)x²\n"
                f"【弧长公式】L = ∫√(1 + (dy/dx)²) dx\n"
                f"【周长公式】P = w + L"
            ))

        elif shape == "hyperbolic_sector":
            a = self._get_value("a")
            b = self._get_value("b")
            t = self._get_value("t")
            if a is None or b is None or t is None:
                return self._show_error("请输入有效的参数")
            # 双曲线弧长：x=a·cosh(u), y=b·sinh(u), u ∈ [0, t]
            # dx/du = a·sinh(u), dy/du = b·cosh(u)
            def integrand(u):
                dxdu = a * math.sinh(u)
                dydu = b * math.cosh(u)
                return math.sqrt(dxdu ** 2 + dydu ** 2)
            arc = self._simpson(integrand, 0, t)
            # 两条直线段：从原点到 (a, 0) 和从原点到 (a·cosh(t), b·sinh(t))
            r1 = a  # 到 (a·cosh(0), b·sinh(0)) = (a, 0)
            x2 = a * math.cosh(t)
            y2 = b * math.sinh(t)
            r2 = math.sqrt(x2 ** 2 + y2 ** 2)
            perimeter = arc + r1 + r2
            self.result_label.config(text=f"周长 = {self._fmt(perimeter)}")
            self.formula_label.config(text=(
                f"双曲扇形 a={a}, b={b}, t={t}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【参数方程】x = a·cosh(u), y = b·sinh(u)\n"
                f"【弧长公式】L = ∫√((dx/du)² + (dy/du)²) du\n"
                f"【周长公式】P = L + r₁ + r₂"
            ))

        elif shape == "elliptic_sector":
            a = self._get_value("a")
            b = self._get_value("b")
            angle_deg = self._get_value("angle")
            if a is None or b is None or angle_deg is None:
                return self._show_error("请输入有效的参数")
            if angle_deg > 360:
                return self._show_error("参数角不能超过360°")
            # 椭圆弧长：x=a·cos(θ), y=b·sin(θ)
            # dx/dθ = -a·sin(θ), dy/dθ = b·cos(θ)
            angle_rad = math.radians(angle_deg)
            def integrand(theta):
                dxdt = -a * math.sin(theta)
                dydt = b * math.cos(theta)
                return math.sqrt(dxdt ** 2 + dydt ** 2)
            arc = self._simpson(integrand, 0, angle_rad)
            # 两条半径：从原点到 (a, 0) 和从原点到椭圆上的点
            r1 = a  # 到 (a·cos(0), b·sin(0)) = (a, 0)
            x2 = a * math.cos(angle_rad)
            y2 = b * math.sin(angle_rad)
            r2 = math.sqrt(x2 ** 2 + y2 ** 2)
            perimeter = arc + r1 + r2
            self.result_label.config(text=f"周长 = {self._fmt(perimeter)}")
            self.formula_label.config(text=(
                f"椭圆扇形 a={a}, b={b}, θ={angle_deg}°\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【参数方程】x = a·cos(θ), y = b·sin(θ)\n"
                f"【弧长公式】L = ∫√((dx/dθ)² + (dy/dθ)²) dθ\n"
                f"【周长公式】P = L + r₁ + r₂"
            ))

        elif shape == "ellipse":
            a = self._get_value("a")
            b = self._get_value("b")
            if a is None or b is None:
                return self._show_error("请输入有效的半轴长度")
            # 拉马努金近似公式
            h_val = ((a - b) / (a + b)) ** 2
            perimeter = math.pi * (a + b) * (1 + 3 * h_val / (10 + math.sqrt(4 - 3 * h_val)))
            self.result_label.config(text=f"周长 = {self._fmt(perimeter)}")
            self.formula_label.config(text=(
                f"椭圆 长半轴 a={a}, 短半轴 b={b}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【拉马努金近似】h = ((a-b)/(a+b))²\n"
                f"【周长公式】P ≈ π(a+b)(1 + 3h/(10+√(4-3h)))"
            ))

    def _fmt(self, val):
        """格式化数字：整数不显示小数位"""
        if val == int(val):
            return str(int(val))
        return f"{val:.4f}"

    def _show_error(self, msg):
        messagebox.showwarning("输入错误", msg)


if __name__ == "__main__":
    root = tk.Tk()
    app = PolygonPerimeterApp(root)
    root.mainloop()
