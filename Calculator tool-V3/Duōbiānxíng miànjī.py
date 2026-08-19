
import tkinter as tk
from tkinter import ttk, messagebox
import math


class PolygonAreaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("多边形面积计算器")
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
        ttk.Label(self.root, text="多边形面积计算器",
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

        self.result_label = ttk.Label(result_frame, text="面积 = ",
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
        # 清空旧输入
        for widget in self.input_frame.winfo_children():
            widget.destroy()
        self.entries.clear()

        # 各图形的参数定义
        configs = {
            "square": [
                ("a", "边长", "5"),
            ],
            "rectangle": [
                ("a", "长", "6"),
                ("b", "宽", "4"),
            ],
            "parallelogram": [
                ("a", "底", "6"),
                ("h", "高", "4"),
            ],
            "rhombus": [
                ("d1", "对角线 d₁", "6"),
                ("d2", "对角线 d₂", "4"),
            ],
            "triangle": [
                ("a", "底", "6"),
                ("h", "高", "4"),
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

        # 三角形额外加一个海伦公式选项
        if shape == "triangle":
            sep = ttk.Separator(self.input_frame, orient="horizontal")
            sep.pack(fill="x", pady=8)

            heron_frame = ttk.Frame(self.input_frame)
            heron_frame.pack(fill="x")

            ttk.Label(heron_frame, text="或使用三边 (海伦公式):",
                      foreground=self.colors["muted"]).pack(anchor="w", pady=(0, 5))

            hrow = ttk.Frame(heron_frame)
            hrow.pack(fill="x")

            for key, label, default in [("s1", "a", "3"), ("s2", "b", "4"), ("s3", "c", "5")]:
                ttk.Label(hrow, text=f"{label}=").pack(side="left", padx=(5, 2))
                entry = ttk.Entry(hrow, width=6)
                entry.insert(0, default)
                entry.pack(side="left", padx=(0, 8))
                entry.bind("<Return>", lambda e: self.calculate())
                self.entries[key] = entry

    def on_shape_change(self):
        """切换图形时重建输入框"""
        self._build_inputs(self.shape_var.get())
        self.result_label.config(text="面积 = ")
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

    def calculate(self):
        """计算面积"""
        shape = self.shape_var.get()

        if shape == "square":
            a = self._get_value("a")
            if a is None:
                return self._show_error("请输入有效的边长")
            area = a * a
            self.result_label.config(text=f"面积 = {self._fmt(area)}")
            self.formula_label.config(text=(
                f"正方形 边长 a={a}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【面积公式】A = a²\n"
                f"【计算过程】A = {a}² = {self._fmt(area)}"
            ))

        elif shape == "rectangle":
            a = self._get_value("a")
            b = self._get_value("b")
            if a is None or b is None:
                return self._show_error("请输入有效的长和宽")
            area = a * b
            self.result_label.config(text=f"面积 = {self._fmt(area)}")
            self.formula_label.config(text=(
                f"矩形 长 a={a}, 宽 b={b}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【面积公式】A = a × b\n"
                f"【计算过程】A = {a} × {b} = {self._fmt(area)}"
            ))

        elif shape == "parallelogram":
            a = self._get_value("a")
            h = self._get_value("h")
            if a is None or h is None:
                return self._show_error("请输入有效的底和高")
            area = a * h
            self.result_label.config(text=f"面积 = {self._fmt(area)}")
            self.formula_label.config(text=(
                f"平行四边形 底 a={a}, 高 h={h}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【面积公式】A = 底 × 高\n"
                f"【计算过程】A = {a} × {h} = {self._fmt(area)}"
            ))

        elif shape == "rhombus":
            d1 = self._get_value("d1")
            d2 = self._get_value("d2")
            if d1 is None or d2 is None:
                return self._show_error("请输入有效的对角线长度")
            area = (d1 * d2) / 2
            self.result_label.config(text=f"面积 = {self._fmt(area)}")
            self.formula_label.config(text=(
                f"菱形 对角线 d₁={d1}, d₂={d2}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【面积公式】A = (d₁ × d₂) / 2\n"
                f"【计算过程】A = ({d1} × {d2}) / 2 = {self._fmt(area)}"
            ))

        elif shape == "triangle":
            # 优先尝试底×高
            a = self._get_value("a")
            h = self._get_value("h")
            if a is not None and h is not None:
                area = (a * h) / 2
                self.result_label.config(text=f"面积 = {self._fmt(area)}")
                self.formula_label.config(text=(
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
                    return self._show_error("三边无法构成三角形")
                s = (s1 + s2 + s3) / 2
                area = math.sqrt(s * (s - s1) * (s - s2) * (s - s3))
                self.result_label.config(text=f"面积 = {self._fmt(area)}")
                self.formula_label.config(text=(
                    f"三角形 三边 a={s1}, b={s2}, c={s3}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"【海伦公式】A = √(s(s-a)(s-b)(s-c))\n"
                    f"【半周长】s = (a+b+c)/2 = ({s1}+{s2}+{s3})/2 = {s}\n"
                    f"【计算过程】A = √({s}×{s-s1}×{s-s2}×{s-s3}) = {self._fmt(area)}"
                ))
                return

            self._show_error("请输入底和高，或三边长度")

        elif shape == "right_triangle":
            a = self._get_value("a")
            b = self._get_value("b")
            if a is None or b is None:
                return self._show_error("请输入有效的直角边长度")
            
            # 勾股定理：斜边 c = √(a² + b²)
            c = math.sqrt(a ** 2 + b ** 2)
            
            # 面积
            area = (a * b) / 2
            
            # 高 h（欧几里得关系）：h = ab/c
            h = (a * b) / c
            
            # 斜边被高分成的两段：p = a²/c, q = b²/c
            p = (a ** 2) / c
            q = (b ** 2) / c
            
            # 角度（弧度转角度）
            alpha = math.degrees(math.atan(a / b))  # 角A（对边为a）
            beta = math.degrees(math.atan(b / a))   # 角B（对边为b）
            
            # 显示结果
            result_text = f"面积 = {area:.4f}"
            self.result_label.config(text=result_text)
            
            # 显示详细信息
            detail = (
                f"直角三角形 a={a}, b={b}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【勾股定理】斜边 c = √(a²+b²) = {c:.4f}\n"
                f"【高】h = ab/c = {h:.4f}\n"
                f"【欧几里得关系】h² = p·q = {p:.4f} × {q:.4f} = {p*q:.4f}\n"
                f"【边角关系】α = {alpha:.2f}°, β = {beta:.2f}°\n"
                f"【面积公式】A = (a × b) / 2"
            )
            self.formula_label.config(text=detail)

        elif shape == "equilateral_triangle":
            a = self._get_value("a")
            if a is None:
                return self._show_error("请输入有效的边长")
            area = (math.sqrt(3) / 4) * a ** 2
            self.result_label.config(text=f"面积 = {self._fmt(area)}")
            self.formula_label.config(text=(
                f"等边三角形 边长 a={a}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【面积公式】A = (√3 / 4) × a²\n"
                f"【计算过程】A = (√3 / 4) × {a}² = {self._fmt(area)}"
            ))

        elif shape == "circle":
            r = self._get_value("r")
            if r is None:
                return self._show_error("请输入有效的半径")
            area = math.pi * r ** 2
            self.result_label.config(text=f"面积 = {self._fmt(area)}")
            self.formula_label.config(text=(
                f"圆 半径 r={r}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【面积公式】A = π × r²\n"
                f"【计算过程】A = π × {r}² = {self._fmt(area)}"
            ))

        elif shape == "sector":
            r = self._get_value("r")
            angle = self._get_value("angle")
            if r is None or angle is None:
                return self._show_error("请输入有效的半径和圆心角")
            area = (angle / 360) * math.pi * r ** 2
            # 弧长
            arc = (angle / 360) * 2 * math.pi * r
            self.result_label.config(text=f"面积 = {self._fmt(area)}")
            self.formula_label.config(text=(
                f"扇形 半径 r={r}, 圆心角 θ={angle}°\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【面积公式】A = (θ / 360) × π × r²\n"
                f"【计算过程】A = ({angle}/360) × π × {r}² = {self._fmt(area)}\n"
                f"【弧长公式】L = (θ / 360) × 2πr = {self._fmt(arc)}"
            ))

        elif shape == "annulus":
            R = self._get_value("R")
            r = self._get_value("r")
            if R is None or r is None:
                return self._show_error("请输入有效的半径")
            if R <= r:
                return self._show_error("外半径必须大于内半径")
            area = math.pi * (R ** 2 - r ** 2)
            self.result_label.config(text=f"面积 = {self._fmt(area)}")
            self.formula_label.config(text=(
                f"圆环 外半径 R={R}, 内半径 r={r}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【面积公式】A = π × (R² - r²)\n"
                f"【计算过程】A = π × ({R}² - {r}²) = π × {R**2 - r**2} = {self._fmt(area)}"
            ))

        elif shape == "parabolic_sector":
            w = self._get_value("w")
            h = self._get_value("h")
            if w is None or h is None:
                return self._show_error("请输入有效的底宽和高")
            # 抛物线弓形面积 = (2/3) × 底宽 × 高
            area = (2 / 3) * w * h
            self.result_label.config(text=f"面积 = {self._fmt(area)}")
            self.formula_label.config(text=(
                f"抛物扇形 底宽 w={w}, 高 h={h}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【面积公式】A = (2/3) × w × h\n"
                f"【计算过程】A = (2/3) × {w} × {h} = {self._fmt(area)}"
            ))

        elif shape == "hyperbolic_sector":
            a = self._get_value("a")
            b = self._get_value("b")
            t = self._get_value("t")
            if a is None or b is None or t is None:
                return self._show_error("请输入有效的参数")
            # 双曲线 x=a·cosh(u), y=b·sinh(u) 从 u=0 到 u=t 的扇形面积
            # A = (ab/2) × t
            area = (a * b / 2) * t
            # 对应的双曲线上的点
            x = a * math.cosh(t)
            y = b * math.sinh(t)
            self.result_label.config(text=f"面积 = {self._fmt(area)}")
            self.formula_label.config(text=(
                f"双曲扇形 a={a}, b={b}, t={t}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【参数方程】x = a·cosh(u), y = b·sinh(u)\n"
                f"【面积公式】A = (a·b / 2) × t\n"
                f"【计算过程】A = ({a}×{b} / 2) × {t} = {self._fmt(area)}\n"
                f"【终点坐标】({self._fmt(x)}, {self._fmt(y)})"
            ))

        elif shape == "elliptic_sector":
            a = self._get_value("a")
            b = self._get_value("b")
            angle_deg = self._get_value("angle")
            if a is None or b is None or angle_deg is None:
                return self._show_error("请输入有效的参数")
            if angle_deg > 360:
                return self._show_error("参数角不能超过360°")
            # 椭圆参数方程: x=a·cos(θ), y=b·sin(θ)
            # 从参数角 0 到 θ 的扇形面积 = (ab/2) × θ (弧度)
            angle_rad = math.radians(angle_deg)
            area = (a * b / 2) * angle_rad
            # 对应的椭圆上的点
            x = a * math.cos(angle_rad)
            y = b * math.sin(angle_rad)
            self.result_label.config(text=f"面积 = {self._fmt(area)}")
            self.formula_label.config(text=(
                f"椭圆扇形 a={a}, b={b}, θ={angle_deg}°\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【参数方程】x = a·cos(θ), y = b·sin(θ)\n"
                f"【面积公式】A = (a·b / 2) × θ\n"
                f"【计算过程】A = ({a}×{b} / 2) × {self._fmt(angle_rad)} = {self._fmt(area)}\n"
                f"【终点坐标】({self._fmt(x)}, {self._fmt(y)})"
            ))

        elif shape == "ellipse":
            a = self._get_value("a")
            b = self._get_value("b")
            if a is None or b is None:
                return self._show_error("请输入有效的半轴长度")
            area = math.pi * a * b
            self.result_label.config(text=f"面积 = {self._fmt(area)}")
            self.formula_label.config(text=(
                f"椭圆 长半轴 a={a}, 短半轴 b={b}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"【面积公式】A = π × a × b\n"
                f"【计算过程】A = π × {a} × {b} = {self._fmt(area)}"
            ))

    def _fmt(self, val):
        """格式化数字：整数不显示小数位"""
        if val == int(val):
            return str(int(val))
        return f"{val:.4f}"

    def _show_result(self, area, desc, formula):
        """显示结果"""
        # 格式化：整数不显示小数位
        if area == int(area):
            area_text = str(int(area))
        else:
            area_text = f"{area:.4f}"

        self.result_label.config(text=f"面积 = {area_text}")
        self.formula_label.config(text=f"{desc}  |  {formula}")

    def _show_error(self, msg):
        messagebox.showwarning("输入错误", msg)


if __name__ == "__main__":
    root = tk.Tk()
    app = PolygonAreaApp(root)
    root.mainloop()
