import json
import os
import math
import subprocess
import sys
from pathlib import Path
import tkinter as tk
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

class AverageCalculator:
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
        
        master.title("代数计算器")
        
        # 设置窗口图标
        self.set_window_icon(master)
        
        # 加载字体配置
        self.load_font()
        
        # 创建Notebook选项卡
        self.notebook = ttk.Notebook(master)
        self.notebook.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        
        # 简单平均值计算选项卡
        self.simple_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.simple_frame, text="平均值计算")
        
        # 数字输入区域
        Label(self.simple_frame, text="输入数字(用空格分隔):").grid(row=0, column=0, padx=10, pady=5)
        self.numbers_var = StringVar()
        Entry(self.simple_frame, textvariable=self.numbers_var, width=30).grid(row=0, column=1, padx=10, pady=5)
        
        Button(self.simple_frame, text="计算", command=self.calculate_simple_average).grid(row=1, column=0, columnspan=2, pady=10)
        
        # 指数计算选项卡
        self.exponent_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.exponent_frame, text="指数计算")
        
        # 底数输入
        Label(self.exponent_frame, text="底数:").grid(row=0, column=0, padx=5, pady=5)
        self.base_var = StringVar()
        Entry(self.exponent_frame, textvariable=self.base_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        # 指数输入
        Label(self.exponent_frame, text="指数:").grid(row=1, column=0, padx=5, pady=5)
        self.power_var = StringVar()
        Entry(self.exponent_frame, textvariable=self.power_var, width=10).grid(row=1, column=1, padx=5, pady=5)
        
        Button(self.exponent_frame, text="计算", command=self.calculate_exponent).grid(row=2, column=0, columnspan=2, pady=10)
        
        # 比例计算选项卡
        self.ratio_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.ratio_frame, text="比例计算")
        
        # 比例输入区域
        Label(self.ratio_frame, text="a:").grid(row=0, column=0, padx=5, pady=5)
        self.a_var = StringVar()
        Entry(self.ratio_frame, textvariable=self.a_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        Label(self.ratio_frame, text=":").grid(row=0, column=2)
        
        Label(self.ratio_frame, text="b:").grid(row=0, column=3, padx=5, pady=5)
        self.b_var = StringVar()
        Entry(self.ratio_frame, textvariable=self.b_var, width=10).grid(row=0, column=4, padx=5, pady=5)
        
        Label(self.ratio_frame, text="=").grid(row=0, column=5)
        
        Label(self.ratio_frame, text="c:").grid(row=0, column=6, padx=5, pady=5)
        self.c_var = StringVar()
        Entry(self.ratio_frame, textvariable=self.c_var, width=10).grid(row=0, column=7, padx=5, pady=5)
        
        Label(self.ratio_frame, text=":").grid(row=0, column=8)
        
        Label(self.ratio_frame, text="d:").grid(row=0, column=9, padx=5, pady=5)
        self.d_var = StringVar()
        Entry(self.ratio_frame, textvariable=self.d_var, width=10).grid(row=0, column=10, padx=5, pady=5)
        
        Button(self.ratio_frame, text="计算", command=self.calculate_ratio).grid(row=1, column=0, columnspan=11, pady=10)
        
        # 最小公倍数计算选项卡
        self.lcm_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.lcm_frame, text="最小公倍数")
        
        Label(self.lcm_frame, text="输入数字(用空格分隔):").grid(row=0, column=0, padx=10, pady=5)
        self.lcm_numbers_var = StringVar()
        Entry(self.lcm_frame, textvariable=self.lcm_numbers_var, width=30).grid(row=0, column=1, padx=10, pady=5)
        
        Button(self.lcm_frame, text="计算", command=self.calculate_lcm).grid(row=1, column=0, columnspan=2, pady=10)
        
        # 最大公因数计算选项卡
        self.gcd_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.gcd_frame, text="最大公因数")
        
        Label(self.gcd_frame, text="输入数字(用空格分隔):").grid(row=0, column=0, padx=10, pady=5)
        self.gcd_numbers_var = StringVar()
        Entry(self.gcd_frame, textvariable=self.gcd_numbers_var, width=30).grid(row=0, column=1, padx=10, pady=5)
        
        Button(self.gcd_frame, text="计算", command=self.calculate_gcd).grid(row=1, column=0, columnspan=2, pady=10)
        
        # 对数计算选项卡
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="对数计算")
        
        # 数字输入
        Label(self.log_frame, text="数字:").grid(row=0, column=0, padx=5, pady=5)
        self.log_number_var = StringVar()
        Entry(self.log_frame, textvariable=self.log_number_var, width=15).grid(row=0, column=1, padx=5, pady=5)
        
        # 底数输入
        Label(self.log_frame, text="底数:").grid(row=1, column=0, padx=5, pady=5)
        self.log_base_var = StringVar()
        Entry(self.log_frame, textvariable=self.log_base_var, width=15).grid(row=1, column=1, padx=5, pady=5)
        
        Button(self.log_frame, text="计算", command=self.calculate_log).grid(row=2, column=0, columnspan=2, pady=5)
        
        # 自然对数计算选项卡
        self.ln_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.ln_frame, text="自然对数")
        
        # 数字输入
        Label(self.ln_frame, text="输入正数:").grid(row=0, column=0, padx=5, pady=5)
        self.ln_number_var = StringVar()
        Entry(self.ln_frame, textvariable=self.ln_number_var, width=15).grid(row=0, column=1, padx=5, pady=5)
        
        Button(self.ln_frame, text="计算", command=self.calculate_ln).grid(row=1, column=0, columnspan=2, pady=5)
        
        # 反对数计算选项卡
        self.antilog_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.antilog_frame, text="反对数计算")
        
        # 数字输入
        Label(self.antilog_frame, text="输入数字:").grid(row=0, column=0, padx=5, pady=5)
        self.antilog_number_var = StringVar()
        Entry(self.antilog_frame, textvariable=self.antilog_number_var, width=15).grid(row=0, column=1, padx=5, pady=5)
        
        # 底数选择
        Label(self.antilog_frame, text="选择底数:").grid(row=1, column=0, padx=5, pady=5)
        self.antilog_base_var = StringVar(value="10")
        ttk.Combobox(self.antilog_frame, textvariable=self.antilog_base_var, 
                    values=["10", "e", "2"], state="readonly", width=12).grid(row=1, column=1, padx=5, pady=5)
        
        Button(self.antilog_frame, text="计算", command=self.calculate_antilog).grid(row=2, column=0, columnspan=2, pady=5)
        
        # 结果展示框架
        self.result_frame = ttk.Frame(master)
        self.result_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        # 结果标签
        Label(self.result_frame, text="结果:").grid(row=0, column=0, padx=5)
        
        # 结果显示
        self.result_var = StringVar()
        self.result_label = Label(self.result_frame, textvariable=self.result_var)
        self.result_label.grid(row=0, column=1, padx=5)

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
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.algebra_calculator")
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
    
    def calculate_simple_average(self):
        try:
            numbers_str = self.numbers_var.get()
            if not numbers_str:
                raise ValueError("请输入数字")
                
            numbers = [float(num) for num in numbers_str.split()]
            average = sum(numbers) / len(numbers)
            
            self.result_var.set(f"{average:.4f}")
        except ValueError as e:
            messagebox.showerror("错误", str(e))
    
    def calculate_lcm(self):
        """计算最小公倍数"""
        try:
            numbers_str = self.lcm_numbers_var.get()
            if not numbers_str:
                raise ValueError("请输入数字")
                
            numbers = [int(num) for num in numbers_str.split()]
            if len(numbers) < 2:
                raise ValueError("至少需要输入两个数字")
                
            if any(num <= 0 for num in numbers):
                raise ValueError("数字必须为正整数")
                
            def gcd(a, b):
                """计算最大公约数"""
                while b:
                    a, b = b, a % b
                return a
                
            def lcm(a, b):
                """计算两个数的最小公倍数"""
                return a * b // gcd(a, b)
                
            current_lcm = numbers[0]
            for num in numbers[1:]:
                current_lcm = lcm(current_lcm, num)
                
            self.result_var.set(f"最小公倍数: {current_lcm}")
        except ValueError as e:
            messagebox.showerror("错误", str(e))
            
    def calculate_ratio(self):
        """计算比例中的未知值 a:b = c:d"""
        try:
            # 获取输入值
            a = self.a_var.get()
            b = self.b_var.get()
            c = self.c_var.get()
            d = self.d_var.get()
            
            # 统计空值的数量
            empty_count = sum(1 for x in [a, b, c, d] if not x)
            
            if empty_count != 1:
                raise ValueError("必须且只能留空一个值")
                
            # 转换非空值为浮点数
            values = []
            for val in [a, b, c, d]:
                if val:
                    try:
                        values.append(float(val))
                    except ValueError:
                        raise ValueError("请输入有效的数字")
                else:
                    values.append(None)
            
            a_val, b_val, c_val, d_val = values
            
            # 计算未知值
            if a_val is None:
                result = (b_val * c_val) / d_val
                self.a_var.set(f"{result:.4f}")
                self.result_var.set(f"计算结果: a = {result:.4f}")
            elif b_val is None:
                result = (a_val * d_val) / c_val
                self.b_var.set(f"{result:.4f}")
                self.result_var.set(f"计算结果: b = {result:.4f}")
            elif c_val is None:
                result = (a_val * d_val) / b_val
                self.c_var.set(f"{result:.4f}")
                self.result_var.set(f"计算结果: c = {result:.4f}")
            elif d_val is None:
                result = (b_val * c_val) / a_val
                self.d_var.set(f"{result:.4f}")
                self.result_var.set(f"计算结果: d = {result:.4f}")
                
        except ValueError as e:
            messagebox.showerror("错误", str(e))
        except ZeroDivisionError:
            messagebox.showerror("错误", "除数不能为零")
            
    def calculate_exponent(self):
        """计算指数 a^b"""
        try:
            base = self.base_var.get()
            power = self.power_var.get()
            
            if not base or not power:
                raise ValueError("请输入底数和指数")
                
            base_num = float(base)
            power_num = float(power)
            
            result = base_num ** power_num
            self.result_var.set(f"{base_num}^{power_num} = {result:.6g}")
            
        except ValueError as e:
            messagebox.showerror("错误", str(e))
            
    def calculate_gcd(self):
        """计算最大公因数"""
        try:
            numbers_str = self.gcd_numbers_var.get()
            if not numbers_str:
                raise ValueError("请输入数字")
                
            numbers = [int(num) for num in numbers_str.split()]
            if len(numbers) < 2:
                raise ValueError("至少需要输入两个数字")
                
            if any(num <= 0 for num in numbers):
                raise ValueError("数字必须为正整数")
                
            def gcd(a, b):
                """计算两个数的最大公约数"""
                while b:
                    a, b = b, a % b
                return a
                
            current_gcd = numbers[0]
            for num in numbers[1:]:
                current_gcd = gcd(current_gcd, num)
                
            self.result_var.set(f"最大公因数: {current_gcd}")
        except ValueError as e:
            messagebox.showerror("错误", str(e))
            
    def calculate_log(self):
        """计算对数"""
        try:
            number = self.log_number_var.get()
            base = self.log_base_var.get()
            
            if not number or not base:
                raise ValueError("请输入数字和底数")
                
            number_val = float(number)
            base_val = float(base)
            
            if number_val <= 0:
                raise ValueError("数字必须大于0")
            if base_val <= 0 or base_val == 1:
                raise ValueError("底数必须大于0且不等于1")
                
            result = math.log(number_val, base_val)
            self.result_var.set(f"log{base_val}({number_val}) = {result:.6g}")
            
        except ValueError as e:
            messagebox.showerror("错误", str(e))
            
    def calculate_ln(self):
        """计算自然对数"""
        try:
            number = self.ln_number_var.get()
            
            if not number:
                raise ValueError("请输入数字")
                
            number_val = float(number)
            
            if number_val <= 0:
                raise ValueError("数字必须大于0")
                
            result = math.log(number_val)
            self.result_var.set(f"ln({number_val}) = {result:.6g}")
            
        except ValueError as e:
            messagebox.showerror("错误", str(e))
            
    def calculate_antilog(self):
        """计算反对数"""
        try:
            number = self.antilog_number_var.get()
            base = self.antilog_base_var.get()
            
            if not number:
                raise ValueError("请输入数字")
                
            number_val = float(number)
            
            if base == "10":
                result = 10 ** number_val
                self.result_var.set(f"antilog₁₀({number_val}) = {result:.6g}")
            elif base == "e":
                result = math.exp(number_val)
                self.result_var.set(f"antilogₑ({number_val}) = {result:.6g}")
            elif base == "2":
                result = 2 ** number_val
                self.result_var.set(f"antilog₂({number_val}) = {result:.6g}")
                
        except ValueError as e:
            messagebox.showerror("错误", str(e))

if __name__ == "__main__":
    root = Tk()
    app = AverageCalculator(root)
    root.mainloop()