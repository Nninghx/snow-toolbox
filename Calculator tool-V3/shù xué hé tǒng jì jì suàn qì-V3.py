import json
import os
import math
import subprocess
from pathlib import Path
from tkinter import Tk, Label, Entry, Button, StringVar, messagebox, ttk, OptionMenu
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from fontTools.ttLib import TTFont
    FONTTOOLS_AVAILABLE = True
except ImportError:
    FONTTOOLS_AVAILABLE = False

class MathStatisticsCalculator:
    def __init__(self, master):
        self.master = master
        
        # 首先检查授权
        if not self.check_license():
            messagebox.showerror(
                "错误", 
                "缺少授权！无法使用！请先获取授权！"
            )
            master.destroy()
            return
        
        master.title("数学和统计计算器")
        
        # 设置窗口图标
        self.set_window_icon(master)
        
        # 加载字体配置
        self.load_font()
        
        # 创建Notebook选项卡
        self.notebook = ttk.Notebook(master)
        self.notebook.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        
        # 根计算选项卡
        self.root_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.root_frame, text="根计算")
        
        # 根计算类型选择
        Label(self.root_frame, text="根类型:").grid(row=0, column=0, padx=5, pady=5)
        self.root_type = StringVar()
        self.root_type.set("平方根")
        OptionMenu(self.root_frame, self.root_type, "平方根", "立方根", "N次方根").grid(row=0, column=1, padx=5)
        
        # 输入值和N值
        Label(self.root_frame, text="数值:").grid(row=1, column=0, padx=5, pady=5)
        self.value_var = StringVar()
        Entry(self.root_frame, textvariable=self.value_var, width=8).grid(row=1, column=1, padx=5)
        
        Label(self.root_frame, text="N(次方根):").grid(row=1, column=2, padx=5)
        self.nth_var = StringVar()
        Entry(self.root_frame, textvariable=self.nth_var, width=8, state='disabled').grid(row=1, column=3, padx=5)
        
        Button(self.root_frame, text="计算", command=self.calculate_root).grid(row=1, column=4, padx=10)
        
        # 绑定根类型变化事件
        self.root_type.trace_add('write', self.update_root_ui)
        
        # 二次方程计算选项卡
        self.quadratic_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.quadratic_frame, text="二次方程")
        
        # 二次方程系数输入
        Label(self.quadratic_frame, text="a:").grid(row=0, column=0, padx=5, pady=5)
        self.a_var = StringVar()
        Entry(self.quadratic_frame, textvariable=self.a_var, width=8).grid(row=0, column=1, padx=5)
        
        Label(self.quadratic_frame, text="b:").grid(row=0, column=2, padx=5)
        self.b_var = StringVar()
        Entry(self.quadratic_frame, textvariable=self.b_var, width=8).grid(row=0, column=3, padx=5)
        
        Label(self.quadratic_frame, text="c:").grid(row=0, column=4, padx=5)
        self.c_var = StringVar()
        Entry(self.quadratic_frame, textvariable=self.c_var, width=8).grid(row=0, column=5, padx=5)
        
        Button(self.quadratic_frame, text="求解", command=self.solve_quadratic).grid(row=0, column=6, padx=10)
        
        # 四舍五入计算选项卡
        self.rounding_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.rounding_frame, text="四舍五入")
        
        # 数值和位数输入
        Label(self.rounding_frame, text="数值:").grid(row=0, column=0, padx=5, pady=5)
        self.round_value_var = StringVar()
        Entry(self.rounding_frame, textvariable=self.round_value_var).grid(row=0, column=1, padx=5)
        
        Label(self.rounding_frame, text="小数位数:").grid(row=0, column=2, padx=5)
        self.decimal_places_var = StringVar()
        Entry(self.rounding_frame, textvariable=self.decimal_places_var, width=5).grid(row=0, column=3, padx=5)
        
        Button(self.rounding_frame, text="计算", command=self.calculate_rounding).grid(row=0, column=4, padx=10)
        
        # 取模计算选项卡
        self.modulo_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.modulo_frame, text="取模计算")
        
        # 被除数和除数输入
        Label(self.modulo_frame, text="被除数:").grid(row=0, column=0, padx=5, pady=5)
        self.dividend_var = StringVar()
        Entry(self.modulo_frame, textvariable=self.dividend_var).grid(row=0, column=1, padx=5)
        
        Label(self.modulo_frame, text="除数:").grid(row=0, column=2, padx=5)
        self.divisor_var = StringVar()
        Entry(self.modulo_frame, textvariable=self.divisor_var).grid(row=0, column=3, padx=5)
        
        Button(self.modulo_frame, text="计算", command=self.calculate_modulo).grid(row=0, column=4, padx=10)
        
        # 组合排列计算选项卡
        self.combination_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.combination_frame, text="组合排列")
        
        # 组合排列类型选择
        Label(self.combination_frame, text="计算类型:").grid(row=0, column=0, padx=5, pady=5)
        self.comb_type = StringVar()
        self.comb_type.set("组合")
        OptionMenu(self.combination_frame, self.comb_type, "组合", "排列", "重复组合", "重复排列").grid(row=0, column=1, padx=5)
        
        # 输入n和k
        Label(self.combination_frame, text="n:").grid(row=1, column=0, padx=5, pady=5)
        self.n_var = StringVar()
        Entry(self.combination_frame, textvariable=self.n_var, width=8).grid(row=1, column=1, padx=5)
        
        Label(self.combination_frame, text="k:").grid(row=1, column=2, padx=5)
        self.k_var = StringVar()
        Entry(self.combination_frame, textvariable=self.k_var, width=8).grid(row=1, column=3, padx=5)
        
        Button(self.combination_frame, text="计算", command=self.calculate_combination).grid(row=1, column=4, padx=10)
        
        # 结果展示
        self.result_frame = ttk.Frame(master)
        self.result_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        Label(self.result_frame, text="结果:").grid(row=0, column=0, padx=5)
        self.result_var = StringVar()
        Label(self.result_frame, textvariable=self.result_var).grid(row=0, column=1, padx=5)
    
    def check_license(self):
        """检查开源协议文档是否存在并验证完整性"""
        # 如果通过主程序启动（环境变量已设置），则跳过授权验证
        if os.environ.get('MAIN_APP_AUTHORIZED') == '1':
            return True
        
        try:
            # 验证授权
            PROJECT_ROOT = Path(__file__).resolve().parent.parent
            CORE_DIR = PROJECT_ROOT / "Core"
            license_exe_path = CORE_DIR / "LICENSE.exe"
            if license_exe_path.exists():
                result = subprocess.run(
                    [str(license_exe_path), '--quiet'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.returncode == 0
        except Exception as e:
            print(f"许可证验证异常: {e}")
            return False

    def set_window_icon(self, master):
        """设置应用程序窗口图标"""
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        IMAGE_DIR = PROJECT_ROOT / "Image"
        
        icon_ico_path = IMAGE_DIR / "icon.ico"
        icon_png_path = IMAGE_DIR / "icon.png"

        # Windows系统设置应用ID
        if os.name == 'nt':
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.math_statistics_calculator")
            except Exception:
                pass

        # 尝试设置ICO图标
        if icon_ico_path.exists():
            try:
                master.iconbitmap(default=str(icon_ico_path))
            except Exception:
                try:
                    master.iconbitmap(str(icon_ico_path))
                except Exception:
                    pass

        # 尝试设置PNG图标
        if hasattr(master, "iconphoto") and icon_png_path.exists():
            try:
                self.icon_image = tk.PhotoImage(file=str(icon_png_path))
                master.iconphoto(True, self.icon_image)
            except Exception:
                pass

    def load_font(self):
        """从配置文件加载字体设置"""
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        IMAGE_DIR = PROJECT_ROOT / "Image"
        
        font_path = IMAGE_DIR / "AlibabaPuHuiTi-3-55-RegularL3.ttf"
        
        if not font_path.exists():
            messagebox.showerror("错误", f"找不到字体文件：{font_path}")
            self.master.destroy()
            return
        
        # 使用 fonttools 获取字体名称
        tt = TTFont(str(font_path))
        font_name = None
        for record in tt['name'].names:
            if record.nameID == 1:  # Font Family
                font_name = record.toUnicode()
                break
        if not font_name:
            raise RuntimeError(f"无法从字体文件获取字体名称：{font_path}")
        tt.close()
        
        # 使用 Windows API 注册字体
        if os.name == 'nt':
            import ctypes
            GDI32 = ctypes.windll.gdi32
            font_path_str = str(font_path).encode('utf-16-le') + b'\x00'
            GDI32.AddFontResourceW(font_path_str)
            print(f"成功加载自定义字体: {font_path}")
        
        from tkinter import font as tkfont
        self.current_font = (font_name, 12)
        self.master.option_add("*Font", self.current_font)
    
    def update_root_ui(self, *args):
        """根据选择的根类型更新UI"""
        if self.root_type.get() == "N次方根":
            self.nth_var.set("")
            Entry(self.root_frame, textvariable=self.nth_var, state='normal').grid(row=1, column=3, padx=5)
        else:
            self.nth_var.set("")
            Entry(self.root_frame, textvariable=self.nth_var, state='disabled').grid(row=1, column=3, padx=5)
    
    def calculate_root(self):
        """计算各种根"""
        try:
            value = float(self.value_var.get())
            root_type = self.root_type.get()
            
            if root_type == "平方根":
                if value < 0:
                    raise ValueError("负数没有实数平方根")
                result = math.sqrt(value)
                self.show_result(f"√{value} = {result:.6f}")
            elif root_type == "立方根":
                result = value ** (1/3)
                self.show_result(f"³√{value} = {result:.6f}")
            elif root_type == "N次方根":
                n = float(self.nth_var.get())
                if n == 0:
                    raise ValueError("N不能为0")
                if value < 0 and n % 2 == 0:
                    raise ValueError("负数的偶数次方根没有实数解")
                result = value ** (1/n)
                self.show_result(f"{n}√{value} = {result:.6f}")
        except ValueError as e:
            messagebox.showerror("错误", str(e))
    
    def show_result(self, text):
        """显示计算结果"""
        self.result_var.set(text)
    
    def solve_quadratic(self):
        """解二次方程 ax² + bx + c = 0"""
        try:
            a = float(self.a_var.get())
            b = float(self.b_var.get())
            c = float(self.c_var.get())
            
            if a == 0:
                raise ValueError("a不能为0")
            
            discriminant = b**2 - 4*a*c
            if discriminant > 0:
                x1 = (-b + math.sqrt(discriminant)) / (2*a)
                x2 = (-b - math.sqrt(discriminant)) / (2*a)
                self.show_result(f"解: x₁ = {x1:.6f}, x₂ = {x2:.6f}")
            elif discriminant == 0:
                x = -b / (2*a)
                self.show_result(f"解: x = {x:.6f} (重根)")
            else:
                real_part = -b / (2*a)
                imaginary_part = math.sqrt(abs(discriminant)) / (2*a)
                self.show_result(f"解: x₁ = {real_part:.6f}+{imaginary_part:.6f}i, x₂ = {real_part:.6f}-{imaginary_part:.6f}i")
        except ValueError as e:
            messagebox.showerror("错误", str(e))
    
    def factorial(self, n):
        """计算阶乘"""
        if n < 0:
            raise ValueError("阶乘数不能为负")
        return math.factorial(n)
    
    def calculate_rounding(self):
        """四舍五入计算"""
        try:
            value = float(self.round_value_var.get())
            decimal_places = int(self.decimal_places_var.get())
            if decimal_places < 0:
                raise ValueError("小数位数不能为负数")
            rounded = round(value, decimal_places)
            self.show_result(f"{value} 四舍五入到 {decimal_places} 位小数: {rounded}")
        except ValueError as e:
            messagebox.showerror("错误", str(e))
    
    def calculate_modulo(self):
        """取模计算"""
        try:
            dividend = float(self.dividend_var.get())
            divisor = float(self.divisor_var.get())
            if divisor == 0:
                raise ValueError("除数不能为0")
            result = dividend % divisor
            self.show_result(f"{dividend} mod {divisor} = {result}")
        except ValueError as e:
            messagebox.showerror("错误", str(e))
    
    def calculate_combination(self):
        """计算组合或排列"""
        try:
            n = int(self.n_var.get())
            k = int(self.k_var.get())
            comb_type = self.comb_type.get()
            
            if n < 0 or k < 0:
                raise ValueError("n和k必须为非负整数")
            
            if comb_type == "组合":
                if k > n:
                    raise ValueError("k不能大于n")
                result = self.factorial(n) // (self.factorial(k) * self.factorial(n - k))
                self.show_result(f"C({n},{k}) = {result}")
            elif comb_type == "排列":
                if k > n:
                    raise ValueError("k不能大于n")
                result = self.factorial(n) // self.factorial(n - k)
                self.show_result(f"P({n},{k}) = {result}")
            elif comb_type == "重复组合":
                result = self.factorial(n + k - 1) // (self.factorial(k) * self.factorial(n - 1))
                self.show_result(f"H({n},{k}) = {result}")
            elif comb_type == "重复排列":
                result = n ** k
                self.show_result(f"π({n},{k}) = {result}")
        except ValueError as e:
            messagebox.showerror("错误", str(e))

if __name__ == "__main__":
    root = Tk()
    app = MathStatisticsCalculator(root)
    root.mainloop()
