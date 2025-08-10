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

class MathStatisticsCalculator:
    def __init__(self, master):
        self.master = master
        master.title("数学和统计计算器")
        
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
        
        # 根计算选项卡
        self.root_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.root_frame, text="根计算")
        
        # 根计算类型选择
        Label(self.root_frame, text="根类型:", font=self.font).grid(row=0, column=0, padx=5, pady=5)
        self.root_type = StringVar()
        self.root_type.set("平方根")
        OptionMenu(self.root_frame, self.root_type, "平方根", "立方根", "N次方根").grid(row=0, column=1, padx=5)
        
        # 输入值和N值
        Label(self.root_frame, text="数值:", font=self.font).grid(row=1, column=0, padx=5, pady=5)
        self.value_var = StringVar()
        Entry(self.root_frame, textvariable=self.value_var, font=self.font, width=8).grid(row=1, column=1, padx=5)
        
        Label(self.root_frame, text="N(次方根):", font=self.font).grid(row=1, column=2, padx=5)
        self.nth_var = StringVar()
        Entry(self.root_frame, textvariable=self.nth_var, font=self.font, width=8, state='disabled').grid(row=1, column=3, padx=5)
        
        Button(self.root_frame, text="计算", command=self.calculate_root, font=self.font).grid(row=1, column=4, padx=10)
        
        # 绑定根类型变化事件
        self.root_type.trace_add('write', self.update_root_ui)
        
        # 二次方程计算选项卡
        self.quadratic_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.quadratic_frame, text="二次方程")
        
        # 二次方程系数输入
        Label(self.quadratic_frame, text="a:", font=self.font).grid(row=0, column=0, padx=5, pady=5)
        self.a_var = StringVar()
        Entry(self.quadratic_frame, textvariable=self.a_var, font=self.font, width=8).grid(row=0, column=1, padx=5)
        
        Label(self.quadratic_frame, text="b:", font=self.font).grid(row=0, column=2, padx=5)
        self.b_var = StringVar()
        Entry(self.quadratic_frame, textvariable=self.b_var, font=self.font, width=8).grid(row=0, column=3, padx=5)
        
        Label(self.quadratic_frame, text="c:", font=self.font).grid(row=0, column=4, padx=5)
        self.c_var = StringVar()
        Entry(self.quadratic_frame, textvariable=self.c_var, font=self.font, width=8).grid(row=0, column=5, padx=5)
        
        Button(self.quadratic_frame, text="求解", command=self.solve_quadratic, font=self.font).grid(row=0, column=6, padx=10)
        
        # 四舍五入计算选项卡
        self.rounding_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.rounding_frame, text="四舍五入")
        
        # 数值和位数输入
        Label(self.rounding_frame, text="数值:", font=self.font).grid(row=0, column=0, padx=5, pady=5)
        self.round_value_var = StringVar()
        Entry(self.rounding_frame, textvariable=self.round_value_var, font=self.font).grid(row=0, column=1, padx=5)
        
        Label(self.rounding_frame, text="小数位数:", font=self.font).grid(row=0, column=2, padx=5)
        self.decimal_places_var = StringVar()
        Entry(self.rounding_frame, textvariable=self.decimal_places_var, font=self.font, width=5).grid(row=0, column=3, padx=5)
        
        Button(self.rounding_frame, text="计算", command=self.calculate_rounding, font=self.font).grid(row=0, column=4, padx=10)
        
        # 取模计算选项卡
        self.modulo_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.modulo_frame, text="取模计算")
        
        # 被除数和除数输入
        Label(self.modulo_frame, text="被除数:", font=self.font).grid(row=0, column=0, padx=5, pady=5)
        self.dividend_var = StringVar()
        Entry(self.modulo_frame, textvariable=self.dividend_var, font=self.font).grid(row=0, column=1, padx=5)
        
        Label(self.modulo_frame, text="除数:", font=self.font).grid(row=0, column=2, padx=5)
        self.divisor_var = StringVar()
        Entry(self.modulo_frame, textvariable=self.divisor_var, font=self.font).grid(row=0, column=3, padx=5)
        
        Button(self.modulo_frame, text="计算", command=self.calculate_modulo, font=self.font).grid(row=0, column=4, padx=10)
        
        # 组合排列计算选项卡
        self.combination_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.combination_frame, text="组合排列")
        
        # 组合排列类型选择
        Label(self.combination_frame, text="计算类型:", font=self.font).grid(row=0, column=0, padx=5, pady=5)
        self.comb_type = StringVar()
        self.comb_type.set("组合")
        OptionMenu(self.combination_frame, self.comb_type, "组合", "排列", "重复组合", "重复排列").grid(row=0, column=1, padx=5)
        
        # 输入n和k
        Label(self.combination_frame, text="n:", font=self.font).grid(row=1, column=0, padx=5, pady=5)
        self.n_var = StringVar()
        Entry(self.combination_frame, textvariable=self.n_var, font=self.font, width=8).grid(row=1, column=1, padx=5)
        
        Label(self.combination_frame, text="k:", font=self.font).grid(row=1, column=2, padx=5)
        self.k_var = StringVar()
        Entry(self.combination_frame, textvariable=self.k_var, font=self.font, width=8).grid(row=1, column=3, padx=5)
        
        Button(self.combination_frame, text="计算", command=self.calculate_combination, font=self.font).grid(row=1, column=4, padx=10)
        
        # 结果展示
        self.result_frame = ttk.Frame(master)
        self.result_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        Label(self.result_frame, text="结果:", font=self.font).grid(row=0, column=0, padx=5)
        self.result_var = StringVar()
        Label(self.result_frame, textvariable=self.result_var, font=self.font).grid(row=0, column=1, padx=5)
    
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
            messagebox.showerror("错误", str(e), font=self.font)
    
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
            messagebox.showerror("错误", str(e), font=self.font)
    
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
            messagebox.showerror("错误", str(e), font=self.font)
    
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
            messagebox.showerror("错误", str(e), font=self.font)
    
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
            messagebox.showerror("错误", str(e), font=self.font)

if __name__ == "__main__":
    root = Tk()
    app = MathStatisticsCalculator(root)
    root.mainloop()