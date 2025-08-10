import json
import os
import math
from tkinter import Tk, Label, Entry, Button, StringVar, messagebox, ttk, OptionMenu

def load_font_config():
    """动态读取字体配置文件"""
    try:
        with open(os.path.join(os.path.dirname(__file__), '../Core/ziti.json'), 'r', encoding='utf-8') as f:
            font_config = json.load(f)
            return font_config.get('family', 'Microsoft YaHei')
    except Exception as e:
        print(f"加载字体配置失败: {e}")
        return 'Microsoft YaHei'

class AverageCalculator:
    def __init__(self, master):
        self.master = master
        master.title("多功能代数计算器")

        # 设置窗口图标
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "..", "Image", "icon.ico")
            if os.path.exists(icon_path):
                master.iconbitmap(icon_path)
        except Exception as e:
            print(f"加载图标失败: {e}")

        # 加载字体配置
        font_family = load_font_config()
        self.font = (font_family, 12)
        
        # 创建Notebook选项卡
        self.notebook = ttk.Notebook(master)
        self.notebook.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        
        # 简单平均值计算选项卡
        self.simple_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.simple_frame, text="平均值计算")
        
        # 数字输入区域
        Label(self.simple_frame, text="输入数字(用空格分隔):", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.numbers_var = StringVar()
        Entry(self.simple_frame, textvariable=self.numbers_var, font=self.font, width=30).grid(row=0, column=1, padx=10, pady=5)
        
        Button(self.simple_frame, text="计算", command=self.calculate_simple_average, font=self.font).grid(row=1, column=0, columnspan=2, pady=10)
        # 指数计算选项卡
        self.exponent_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.exponent_frame, text="指数计算")
        
        # 底数输入
        Label(self.exponent_frame, text="底数:", font=self.font).grid(row=0, column=0, padx=5, pady=5)
        self.base_var = StringVar()
        Entry(self.exponent_frame, textvariable=self.base_var, font=self.font, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        # 指数输入
        Label(self.exponent_frame, text="指数:", font=self.font).grid(row=1, column=0, padx=5, pady=5)
        self.power_var = StringVar()
        Entry(self.exponent_frame, textvariable=self.power_var, font=self.font, width=10).grid(row=1, column=1, padx=5, pady=5)
        
        Button(self.exponent_frame, text="计算", command=self.calculate_exponent, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
        
        # 比例计算选项卡
        self.ratio_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.ratio_frame, text="比例计算")
        
        # 比例输入区域
        Label(self.ratio_frame, text="a:", font=self.font).grid(row=0, column=0, padx=5, pady=5)
        self.a_var = StringVar()
        Entry(self.ratio_frame, textvariable=self.a_var, font=self.font, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        Label(self.ratio_frame, text=":", font=self.font).grid(row=0, column=2)
        
        Label(self.ratio_frame, text="b:", font=self.font).grid(row=0, column=3, padx=5, pady=5)
        self.b_var = StringVar()
        Entry(self.ratio_frame, textvariable=self.b_var, font=self.font, width=10).grid(row=0, column=4, padx=5, pady=5)
        
        Label(self.ratio_frame, text="=", font=self.font).grid(row=0, column=5, padx=5)
        
        Label(self.ratio_frame, text="c:", font=self.font).grid(row=0, column=6, padx=5, pady=5)
        self.c_var = StringVar()
        Entry(self.ratio_frame, textvariable=self.c_var, font=self.font, width=10).grid(row=0, column=7, padx=5, pady=5)
        
        Label(self.ratio_frame, text=":", font=self.font).grid(row=0, column=8)
        
        Label(self.ratio_frame, text="d:", font=self.font).grid(row=0, column=9, padx=5, pady=5)
        self.d_var = StringVar()
        Entry(self.ratio_frame, textvariable=self.d_var, font=self.font, width=10).grid(row=0, column=10, padx=5, pady=5)
        
        Button(self.ratio_frame, text="计算", command=self.calculate_ratio, font=self.font).grid(row=1, column=0, columnspan=11, pady=10)
        
        # 最小公倍数计算选项卡
        self.lcm_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.lcm_frame, text="最小公倍数")
        
        Label(self.lcm_frame, text="输入数字(用空格分隔):", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.lcm_numbers_var = StringVar()
        Entry(self.lcm_frame, textvariable=self.lcm_numbers_var, font=self.font, width=30).grid(row=0, column=1, padx=10, pady=5)
        
        Button(self.lcm_frame, text="计算", command=self.calculate_lcm, font=self.font).grid(row=1, column=0, columnspan=2, pady=10)
        
        # 底数输入
        Label(self.exponent_frame, text="底数:", font=self.font).grid(row=0, column=0, padx=5, pady=5)
        self.base_var = StringVar()
        Entry(self.exponent_frame, textvariable=self.base_var, font=self.font, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        # 指数输入
        Label(self.exponent_frame, text="指数:", font=self.font).grid(row=1, column=0, padx=5, pady=5)
        self.power_var = StringVar()
        Entry(self.exponent_frame, textvariable=self.power_var, font=self.font, width=10).grid(row=1, column=1, padx=5, pady=5)
        
        Button(self.exponent_frame, text="计算", command=self.calculate_exponent, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
        
        # 最大公因数计算选项卡
        self.gcd_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.gcd_frame, text="最大公因数")
        
        Label(self.gcd_frame, text="输入数字(用空格分隔):", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.gcd_numbers_var = StringVar()
        Entry(self.gcd_frame, textvariable=self.gcd_numbers_var, font=self.font, width=30).grid(row=0, column=1, padx=10, pady=5)
        
        Button(self.gcd_frame, text="计算", command=self.calculate_gcd, font=self.font).grid(row=1, column=0, columnspan=2, pady=10)
        
        # 对数计算选项卡
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="对数计算")
        
        # 数字输入
        Label(self.log_frame, text="数字:", font=self.font).grid(row=0, column=0, padx=5, pady=5)
        self.log_number_var = StringVar()
        Entry(self.log_frame, textvariable=self.log_number_var, font=self.font, width=15).grid(row=0, column=1, padx=5, pady=5)
        
        # 底数输入
        Label(self.log_frame, text="底数:", font=self.font).grid(row=1, column=0, padx=5, pady=5)
        self.log_base_var = StringVar()
        Entry(self.log_frame, textvariable=self.log_base_var, font=self.font, width=15).grid(row=1, column=1, padx=5, pady=5)
        
        Button(self.log_frame, text="计算", command=self.calculate_log, font=self.font).grid(row=2, column=0, columnspan=2, pady=5)
        
        # 自然对数计算选项卡
        self.ln_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.ln_frame, text="自然对数")
        
        # 数字输入
        Label(self.ln_frame, text="输入正数:", font=self.font).grid(row=0, column=0, padx=5, pady=5)
        self.ln_number_var = StringVar()
        Entry(self.ln_frame, textvariable=self.ln_number_var, font=self.font, width=15).grid(row=0, column=1, padx=5, pady=5)
        
        Button(self.ln_frame, text="计算", command=self.calculate_ln, font=self.font).grid(row=1, column=0, columnspan=2, pady=5)
        
        # 反对数计算选项卡
        self.antilog_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.antilog_frame, text="反对数计算")
        
        # 数字输入
        Label(self.antilog_frame, text="输入数字:", font=self.font).grid(row=0, column=0, padx=5, pady=5)
        self.antilog_number_var = StringVar()
        Entry(self.antilog_frame, textvariable=self.antilog_number_var, font=self.font, width=15).grid(row=0, column=1, padx=5, pady=5)
        
        # 底数选择
        Label(self.antilog_frame, text="选择底数:", font=self.font).grid(row=1, column=0, padx=5, pady=5)
        self.antilog_base_var = StringVar(value="10")
        ttk.Combobox(self.antilog_frame, textvariable=self.antilog_base_var, 
                    values=["10", "e", "2"], state="readonly", width=12).grid(row=1, column=1, padx=5, pady=5)
        
        Button(self.antilog_frame, text="计算", command=self.calculate_antilog, font=self.font).grid(row=2, column=0, columnspan=2, pady=5)
        
        # 结果展示框架
        self.result_frame = ttk.Frame(master)
        self.result_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        # 结果标签
        Label(self.result_frame, text="结果:", font=self.font).grid(row=0, column=0, padx=5)
        
        # 结果显示
        self.result_var = StringVar()
        self.result_label = Label(self.result_frame, textvariable=self.result_var, font=self.font)
        self.result_label.grid(row=0, column=1, padx=5)
    
    def calculate_simple_average(self):
        try:
            numbers_str = self.numbers_var.get()
            if not numbers_str:
                raise ValueError("请输入数字")
                
            numbers = [float(num) for num in numbers_str.split()]
            average = sum(numbers) / len(numbers)
            
            self.result_var.set(f"{average:.4f}")
        except ValueError as e:
            messagebox.showerror("错误", str(e), font=self.font)
    
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
            messagebox.showerror("错误", str(e), font=self.font)
            
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
            messagebox.showerror("错误", str(e), font=self.font)
        except ZeroDivisionError:
            messagebox.showerror("错误", "除数不能为零", font=self.font)
            
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
            messagebox.showerror("错误", str(e), font=self.font)
            
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
            messagebox.showerror("错误", str(e), font=self.font)
            
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
            messagebox.showerror("错误", str(e), font=self.font)
            
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
            messagebox.showerror("错误", str(e), font=self.font)
            
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
            messagebox.showerror("错误", str(e), font=self.font)

if __name__ == "__main__":
    root = Tk()
    app = AverageCalculator(root)
    root.mainloop()