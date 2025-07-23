import tkinter as tk
from tkinter import messagebox
import math

class NthRootCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("N次方根计算器")
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
        
        # 底数输入
        tk.Label(input_frame, text="底数:", font=self.font).grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.base_entry = tk.Entry(input_frame, font=self.font, width=15)
        self.base_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # 根指数输入
        tk.Label(input_frame, text="根指数(N):", font=self.font).grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.root_entry = tk.Entry(input_frame, font=self.font, width=15)
        self.root_entry.grid(row=1, column=1, padx=5, pady=5)
        
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
        
        # 运算式显示
        self.equation_label = tk.Label(self.result_frame, text="运算式: ", font=self.font, anchor="w")
        self.equation_label.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        # 结果显示
        self.result_label = tk.Label(self.result_frame, text="计算结果: ", font=self.font, anchor="w")
        self.result_label.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # 滚动条和文本框用于显示详细信息
        scrollbar = tk.Scrollbar(self.result_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.details_text = tk.Text(
            self.result_frame, font=self.font, 
            yscrollcommand=scrollbar.set, height=8
        )
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5)
        scrollbar.config(command=self.details_text.yview)

    def calculate_nth_root(self, base, n):
        """计算N次方根"""
        if n == 0:
            return None, "根指数不能为零"
        if n % 2 == 0 and base < 0:
            return None, "负数不能开偶次方根"
        
        # 处理负数的奇次方根
        if base < 0 and n % 2 != 0:
            return -((-base) ** (1/n)), None
        
        return base ** (1/n), None

    def calculate(self):
        # 获取输入
        base_str = self.base_entry.get().strip()
        root_str = self.root_entry.get().strip()
        
        # 验证输入
        if not base_str or not root_str:
            messagebox.showerror("错误", "请输入底数和根指数!")
            return
        
        try:
            base = float(base_str)
            n = float(root_str)
            
            if n == int(n):
                n = int(n)  # 如果是整数，转换为整数显示
            
            # 计算N次方根
            result, error = self.calculate_nth_root(base, n)
            
            if error:
                self.equation_label.config(text=f"运算式: {base} 的 {n} 次方根")
                self.result_label.config(text=f"计算结果: {error}")
                self.details_text.delete(1.0, tk.END)
                self.details_text.insert(tk.END, f"错误: {error}")
                return
            
            # 显示结果
            self.equation_label.config(text=f"运算式: {base} 的 {n} 次方根")
            self.result_label.config(text=f"计算结果: {result}")
            
            # 显示详细信息
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, f"计算 {base} 的 {n} 次方根:\n")
            
            if n == 2:
                self.details_text.insert(tk.END, f"√{base} = {result}\n")
            elif n == 3:
                self.details_text.insert(tk.END, f"³√{base} = {result}\n")
            else:
                self.details_text.insert(tk.END, f"{n}√{base} = {result}\n")
            
            self.details_text.insert(tk.END, f"\n验证:\n")
            self.details_text.insert(tk.END, f"{result}^{n} = {result**n}\n")
            
            # 显示更多小数位
            self.details_text.insert(tk.END, f"\n精确值:\n")
            self.details_text.insert(tk.END, f"{result:.15f}\n")
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字!")
    
    def clear(self):
        self.base_entry.delete(0, tk.END)
        self.root_entry.delete(0, tk.END)
        self.equation_label.config(text="运算式: ")
        self.result_label.config(text="计算结果: ")
        self.details_text.delete(1.0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = NthRootCalculator(root)
    root.mainloop()