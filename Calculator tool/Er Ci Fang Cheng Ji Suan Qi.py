import tkinter as tk
from tkinter import messagebox
import math

class QuadraticEquationCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("二次方程计算器")
        self.root.geometry("450x400")
        self.root.resizable(False, False)
        
        # 加载并设置字体
        self.font = self.load_font_settings()
        
        # 创建界面组件
        self.create_widgets()

    def load_font_settings(self):
        """从ziti.json加载字体设置，默认返回Arial"""
        import json
        import os
        
        try:
            ziti_path = os.path.join("Core", "ziti.json")
            if os.path.exists(ziti_path):
                with open(ziti_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return (data.get('family', 'Arial'), 12)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return ("Arial", 12)  # 默认字体
    
    def create_widgets(self):
        # 输入框框架
        input_frame = tk.Frame(self.root)
        input_frame.pack(pady=(10, 5))
        
        # 二次项系数(a)输入
        tk.Label(input_frame, text="二次项系数(a):", font=self.font).grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.a_entry = tk.Entry(input_frame, font=self.font, width=15)
        self.a_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # 一次项系数(b)输入
        tk.Label(input_frame, text="一次项系数(b):", font=self.font).grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.b_entry = tk.Entry(input_frame, font=self.font, width=15)
        self.b_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # 常数项(c)输入
        tk.Label(input_frame, text="常数项(c):", font=self.font).grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.c_entry = tk.Entry(input_frame, font=self.font, width=15)
        self.c_entry.grid(row=2, column=1, padx=5, pady=5)
        
        # 按钮框架
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        
        # 计算按钮
        self.calculate_btn = tk.Button(
            button_frame, text="计算", font=self.font, 
            command=self.calculate, bg="#4CAF50", fg="white"
        )
        self.calculate_btn.pack(side=tk.LEFT, padx=5)
        
        # 清除按钮
        self.clear_btn = tk.Button(
            button_frame, text="清除", font=self.font,
            command=self.clear, bg="#f44336", fg="white"
        )
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        # 结果显示区域
        self.result_frame = tk.Frame(self.root, bd=2, relief=tk.GROOVE)
        self.result_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        # 方程显示
        self.equation_label = tk.Label(self.result_frame, text="方程: ", font=self.font, anchor="w")
        self.equation_label.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        # 根显示
        self.roots_label = tk.Label(self.result_frame, text="根: ", font=self.font, anchor="w")
        self.roots_label.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # 滚动条和文本框用于显示详细信息
        scrollbar = tk.Scrollbar(self.result_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.details_text = tk.Text(
            self.result_frame, font=self.font, 
            yscrollcommand=scrollbar.set, height=8
        )
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5)
        scrollbar.config(command=self.details_text.yview)

    def solve_quadratic(self, a, b, c):
        """解二次方程 ax² + bx + c = 0"""
        if a == 0:
            return None, None, "不是二次方程"
        
        discriminant = b**2 - 4*a*c
        if discriminant < 0:
            real_part = -b / (2*a)
            imag_part = math.sqrt(-discriminant) / (2*a)
            return (f"{real_part} + {imag_part}i", 
                    f"{real_part} - {imag_part}i", 
                    "方程有两个共轭复数根")
        elif discriminant == 0:
            root = -b / (2*a)
            return (root, root, "方程有两个相等的实数根")
        else:
            root1 = (-b + math.sqrt(discriminant)) / (2*a)
            root2 = (-b - math.sqrt(discriminant)) / (2*a)
            return (root1, root2, "方程有两个不同的实数根")

    def calculate(self):
        # 获取输入
        a_str = self.a_entry.get().strip()
        b_str = self.b_entry.get().strip()
        c_str = self.c_entry.get().strip()
        
        # 验证输入
        if not a_str or not b_str or not c_str:
            messagebox.showerror("错误", "请输入a、b、c的值!")
            return
        
        try:
            a = float(a_str)
            b = float(b_str)
            c = float(c_str)
            
            # 显示方程
            equation = f"{a}x² + {b}x + {c} = 0"
            self.equation_label.config(text=f"方程: {equation}")
            
            # 解方程
            root1, root2, desc = self.solve_quadratic(a, b, c)
            
            if root1 is None:
                self.roots_label.config(text=f"根: {desc}")
            else:
                self.roots_label.config(text=f"根: x₁ = {root1}, x₂ = {root2}")
            
            # 显示详细信息
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, f"方程: {equation}\n")
            self.details_text.insert(tk.END, f"判别式 Δ = b² - 4ac = {b**2 - 4*a*c}\n")
            self.details_text.insert(tk.END, f"\n{desc}\n")
            
            if root1 is not None:
                if isinstance(root1, str):  # 复数根
                    self.details_text.insert(tk.END, f"x₁ = {root1}\n")
                    self.details_text.insert(tk.END, f"x₂ = {root2}\n")
                else:  # 实数根
                    self.details_text.insert(tk.END, f"求根公式: x = [-b ± √(b²-4ac)] / (2a)\n")
                    self.details_text.insert(tk.END, f"x₁ = [{-b} + √{b**2 - 4*a*c}] / {2*a} = {root1}\n")
                    self.details_text.insert(tk.END, f"x₂ = [{-b} - √{b**2 - 4*a*c}] / {2*a} = {root2}\n")
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字!")
    
    def clear(self):
        self.a_entry.delete(0, tk.END)
        self.b_entry.delete(0, tk.END)
        self.c_entry.delete(0, tk.END)
        self.equation_label.config(text="方程: ")
        self.roots_label.config(text="根: ")
        self.details_text.delete(1.0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = QuadraticEquationCalculator(root)
    root.mainloop()