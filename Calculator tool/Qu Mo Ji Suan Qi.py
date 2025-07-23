import tkinter as tk
from tkinter import messagebox

class ModuloCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("取模计算器")
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
        
        # 被除数输入
        tk.Label(input_frame, text="被除数:", font=self.font).grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.dividend_entry = tk.Entry(input_frame, font=self.font, width=15)
        self.dividend_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # 除数输入
        tk.Label(input_frame, text="除数:", font=self.font).grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.divisor_entry = tk.Entry(input_frame, font=self.font, width=15)
        self.divisor_entry.grid(row=1, column=1, padx=5, pady=5)
        
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
        self.result_label = tk.Label(self.result_frame, text="取模结果: ", font=self.font, anchor="w")
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

    def calculate_modulo(self, dividend, divisor):
        """计算取模运算"""
        if divisor == 0:
            return None, "除数不能为零"
        
        remainder = dividend % divisor
        quotient = dividend // divisor
        return remainder, quotient

    def calculate(self):
        # 获取输入
        dividend_str = self.dividend_entry.get().strip()
        divisor_str = self.divisor_entry.get().strip()
        
        # 验证输入
        if not dividend_str or not divisor_str:
            messagebox.showerror("错误", "请输入被除数和除数!")
            return
        
        try:
            dividend = int(dividend_str)
            divisor = int(divisor_str)
            
            # 计算取模
            remainder, quotient = self.calculate_modulo(dividend, divisor)
            
            if remainder is None:
                self.equation_label.config(text=f"运算式: {dividend} mod {divisor}")
                self.result_label.config(text=f"取模结果: {quotient}")
            else:
                self.equation_label.config(text=f"运算式: {dividend} mod {divisor}")
                self.result_label.config(text=f"取模结果: {remainder}")
            
            # 显示详细信息
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, f"运算式: {dividend} mod {divisor}\n")
            
            if remainder is not None:
                self.details_text.insert(tk.END, f"\n计算过程:\n")
                self.details_text.insert(tk.END, f"1. 计算商: {dividend} ÷ {divisor} = {quotient}\n")
                self.details_text.insert(tk.END, f"2. 计算余数: {dividend} - ({divisor} × {quotient}) = {remainder}\n")
                self.details_text.insert(tk.END, f"\n最终结果: {remainder}\n")
            else:
                self.details_text.insert(tk.END, f"\n错误: {quotient}\n")
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的整数!")
    
    def clear(self):
        self.dividend_entry.delete(0, tk.END)
        self.divisor_entry.delete(0, tk.END)
        self.equation_label.config(text="运算式: ")
        self.result_label.config(text="取模结果: ")
        self.details_text.delete(1.0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = ModuloCalculator(root)
    root.mainloop()