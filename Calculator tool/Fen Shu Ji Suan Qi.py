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

def percentage_to_fraction(percentage):
    """将百分比转换为分数"""
    if '%' in percentage:
        percentage = percentage.replace('%', '')
    decimal_num = float(percentage) / 100
    return decimal_to_fraction(decimal_num)

def simplify_fraction(fraction_str):
    """化简分数"""
    try:
        if '/' in fraction_str:
            numerator, denominator = map(int, fraction_str.split('/'))
        else:
            numerator = int(fraction_str)
            denominator = 1
            
        # 约分
        common_divisor = math.gcd(numerator, denominator)
        numerator = numerator // common_divisor
        denominator = denominator // common_divisor
        
        return (numerator, denominator)
    except ValueError:
        raise ValueError("请输入有效的分数(如3/4或5)")

def decimal_to_fraction(decimal_num):
    """将小数转换为分数"""
    tolerance = 1.0E-6
    numerator = 1
    denominator = 1
    
    # 处理负数
    sign = -1 if decimal_num < 0 else 1
    decimal_num = abs(decimal_num)
    
    # 处理整数部分
    integer_part = int(decimal_num)
    decimal_num -= integer_part
    
    if decimal_num < tolerance:
        return (sign * integer_part, 1)
    
    # 连分数算法
    lower_n = 0
    lower_d = 1
    upper_n = 1
    upper_d = 1
    
    while True:
        middle_n = lower_n + upper_n
        middle_d = lower_d + upper_d
        
        if middle_d * (decimal_num + tolerance) < middle_n:
            upper_n = middle_n
            upper_d = middle_d
        elif middle_n < (decimal_num - tolerance) * middle_d:
            lower_n = middle_n
            lower_d = middle_d
        else:
            numerator = middle_n
            denominator = middle_d
            break
    
    numerator = sign * (integer_part * denominator + numerator)
    
    # 约分
    common_divisor = math.gcd(numerator, denominator)
    numerator = numerator // common_divisor
    denominator = denominator // common_divisor
    
    return (numerator, denominator)

class FractionCalculator:
    def __init__(self, master):
        self.master = master
        master.title("多功能分数计算器")
        
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
        
        # 分数化简选项卡
        self.simplify_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.simplify_frame, text="分数化简")
        
        # 分子输入
        Label(self.simplify_frame, text="分子:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.numerator_var = StringVar()
        Entry(self.simplify_frame, textvariable=self.numerator_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        # 分数线
        Label(self.simplify_frame, text="——", font=self.font).grid(row=1, column=0, columnspan=2)
        
        # 分母输入
        Label(self.simplify_frame, text="分母:", font=self.font).grid(row=2, column=0, padx=10, pady=5)
        self.denominator_var = StringVar()
        Entry(self.simplify_frame, textvariable=self.denominator_var, font=self.font).grid(row=2, column=1, padx=10, pady=5)
        
        Button(self.simplify_frame, text="化简", command=self.simplify_fraction, font=self.font).grid(row=3, column=0, columnspan=2, pady=10)
        
        # 小数转分数选项卡
        self.decimal_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.decimal_frame, text="小数转分数")
        
        Label(self.decimal_frame, text="输入小数:", font=self.font).grid(row=0, column=0, padx=10, pady=10)
        self.decimal_var = StringVar()
        Entry(self.decimal_frame, textvariable=self.decimal_var, font=self.font).grid(row=0, column=1, padx=10, pady=10)
        Button(self.decimal_frame, text="转换", command=self.convert_decimal, font=self.font).grid(row=1, column=0, columnspan=2, pady=10)
        
        # 百分比转分数选项卡
        self.percentage_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.percentage_frame, text="百分比转分数")
        
        Label(self.percentage_frame, text="输入百分比:", font=self.font).grid(row=0, column=0, padx=10, pady=10)
        self.percentage_var = StringVar()
        Entry(self.percentage_frame, textvariable=self.percentage_var, font=self.font).grid(row=0, column=1, padx=10, pady=10)
        Button(self.percentage_frame, text="转换", command=self.convert_percentage, font=self.font).grid(row=1, column=0, columnspan=2, pady=10)
        
        # 分数计算选项卡
        self.calculate_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.calculate_frame, text="分数计算")
        
        # 第一个分数 - 上下布局
        Label(self.calculate_frame, text="分数1:", font=self.font).grid(row=0, column=0, padx=10, pady=5, rowspan=2)
        
        # 分子
        self.frac1_num = StringVar()
        Entry(self.calculate_frame, textvariable=self.frac1_num, width=5, font=self.font).grid(row=0, column=1, padx=10)
        
        # 分数线
        Label(self.calculate_frame, text="——", font=self.font).grid(row=1, column=1)
        
        # 分母
        self.frac1_den = StringVar()
        Entry(self.calculate_frame, textvariable=self.frac1_den, width=5, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        # 运算符
        self.operator = StringVar()
        self.operator.set("+")
        OptionMenu(self.calculate_frame, self.operator, "+", "-", "×", "÷").grid(row=0, column=2, rowspan=2, padx=10)
        
        # 第二个分数 - 上下布局
        Label(self.calculate_frame, text="分数2:", font=self.font).grid(row=0, column=3, padx=10, pady=5, rowspan=2)
        
        # 分子
        self.frac2_num = StringVar()
        Entry(self.calculate_frame, textvariable=self.frac2_num, width=5, font=self.font).grid(row=0, column=4, padx=10)
        
        # 分数线
        Label(self.calculate_frame, text="——", font=self.font).grid(row=1, column=4)
        
        # 分母
        self.frac2_den = StringVar()
        Entry(self.calculate_frame, textvariable=self.frac2_den, width=5, font=self.font).grid(row=1, column=4, padx=10, pady=5)
        
        # 计算按钮
        Button(self.calculate_frame, text="计算", command=self.calculate_fractions, font=self.font).grid(row=2, column=0, columnspan=5, pady=10)
        
        # 结果展示框架
        self.result_frame = ttk.Frame(master)
        self.result_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        # 结果标签
        Label(self.result_frame, text="结果:", font=self.font).grid(row=0, column=0, rowspan=2, padx=5)
        
        # 分子显示
        self.result_num_var = StringVar()
        self.result_num_label = Label(self.result_frame, textvariable=self.result_num_var, font=self.font)
        self.result_num_label.grid(row=0, column=1, padx=5)
        
        # 分数线
        self.result_line_label = Label(self.result_frame, text="——", font=self.font)
        self.result_line_label.grid(row=1, column=1)
        
        # 分母显示
        self.result_den_var = StringVar()
        self.result_den_label = Label(self.result_frame, textvariable=self.result_den_var, font=self.font)
        self.result_den_label.grid(row=1, column=1, pady=5)
        
        # 初始隐藏分数线和分母
        self.result_line_label.grid_remove()
        self.result_den_label.grid_remove()
    
    def convert_decimal(self):
        try:
            decimal_num = float(self.decimal_var.get())
            numerator, denominator = decimal_to_fraction(decimal_num)
            self.display_result(numerator, denominator)
        except ValueError:
            messagebox.showerror("错误", "请输入有效的小数", font=self.font)
    
    def convert_percentage(self):
        try:
            percentage = self.percentage_var.get()
            numerator, denominator = percentage_to_fraction(percentage)
            self.display_result(numerator, denominator)
        except ValueError:
            messagebox.showerror("错误", "请输入有效的百分比(如50或50%)", font=self.font)
    
    def simplify_fraction(self):
        try:
            numerator_str = self.numerator_var.get()
            denominator_str = self.denominator_var.get()
            
            if not numerator_str:
                raise ValueError("请输入分子")
                
            numerator = int(numerator_str)
            denominator = int(denominator_str) if denominator_str else 1
            
            if denominator == 0:
                raise ValueError("分母不能为零")
                
            # 约分
            common_divisor = math.gcd(numerator, denominator)
            numerator = numerator // common_divisor
            denominator = denominator // common_divisor
            
            self.display_result(numerator, denominator)
        except ValueError as e:
            messagebox.showerror("错误", str(e), font=self.font)
    
    def calculate_fractions(self):
        try:
            # 获取第一个分数
            num1 = int(self.frac1_num.get())
            den1 = int(self.frac1_den.get()) if self.frac1_den.get() else 1
            if den1 == 0:
                raise ValueError("分数1的分母不能为零")
                
            # 获取第二个分数
            num2 = int(self.frac2_num.get())
            den2 = int(self.frac2_den.get()) if self.frac2_den.get() else 1
            if den2 == 0:
                raise ValueError("分数2的分母不能为零")
                
            # 根据运算符计算
            operator = self.operator.get()
            if operator == "+":
                # 加法: (a*d + b*c)/(b*d)
                numerator = num1 * den2 + num2 * den1
                denominator = den1 * den2
            elif operator == "-":
                # 减法: (a*d - b*c)/(b*d)
                numerator = num1 * den2 - num2 * den1
                denominator = den1 * den2
            elif operator == "×":
                # 乘法: (a*c)/(b*d)
                numerator = num1 * num2
                denominator = den1 * den2
            elif operator == "÷":
                # 除法: (a*d)/(b*c)
                if num2 == 0:
                    raise ValueError("除数不能为零")
                numerator = num1 * den2
                denominator = den1 * num2
            else:
                raise ValueError("无效的运算符")
                
            # 约分
            common_divisor = math.gcd(numerator, denominator)
            numerator = numerator // common_divisor
            denominator = denominator // common_divisor
            
            self.display_result(numerator, denominator)
        except ValueError as e:
            messagebox.showerror("错误", str(e), font=self.font)
    
    def display_result(self, numerator, denominator):
        if denominator == 1:
            # 整数结果显示
            self.result_num_var.set(str(numerator))
            self.result_line_label.grid_remove()
            self.result_den_label.grid_remove()
        else:
            # 分数结果显示
            self.result_num_var.set(str(numerator))
            self.result_den_var.set(str(denominator))
            self.result_line_label.grid()
            self.result_den_label.grid()

if __name__ == "__main__":
    root = Tk()
    app = FractionCalculator(root)
    root.mainloop()