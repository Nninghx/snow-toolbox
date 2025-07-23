import tkinter as tk
from tkinter import messagebox
import math

class FractionSimplifier:
    def __init__(self, root):
        self.root = root
        self.root.title("分数化简计算器")
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
        
        # 分子输入
        tk.Label(input_frame, text="分子:", font=self.font).grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.numerator_entry = tk.Entry(input_frame, font=self.font, width=15)
        self.numerator_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # 分母输入
        tk.Label(input_frame, text="分母:", font=self.font).grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.denominator_entry = tk.Entry(input_frame, font=self.font, width=15)
        self.denominator_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # 按钮框架
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        
        # 化简按钮
        self.simplify_btn = tk.Button(
            button_frame, text="化简", font=self.font, 
            command=self.simplify, bg="#4CAF50", fg="white"
        )
        self.simplify_btn.pack(side=tk.LEFT, padx=5)
        
        # 清除按钮
        self.clear_btn = tk.Button(
            button_frame, text="清除", font=self.font,
            command=self.clear, bg="#f44336", fg="white"
        )
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        # 结果显示区域
        self.result_frame = tk.Frame(self.root, bd=2, relief=tk.GROOVE)
        self.result_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        # 原始分数显示
        self.original_label = tk.Label(self.result_frame, text="原始分数: ", font=self.font, anchor="w")
        self.original_label.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        # 化简结果显示
        self.simplified_label = tk.Label(self.result_frame, text="化简结果: ", font=self.font, anchor="w")
        self.simplified_label.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # 滚动条和文本框用于显示详细信息
        scrollbar = tk.Scrollbar(self.result_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.details_text = tk.Text(
            self.result_frame, font=self.font, 
            yscrollcommand=scrollbar.set, height=8
        )
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5)
        scrollbar.config(command=self.details_text.yview)

    def gcd(self, a, b):
        """计算最大公约数"""
        a, b = abs(a), abs(b)
        while b:
            a, b = b, a % b
        return a

    def simplify_fraction(self, numerator, denominator):
        """化简分数"""
        if denominator == 0:
            return None, None, "分母不能为零"
        
        common_divisor = self.gcd(numerator, denominator)
        simplified_num = numerator // common_divisor
        simplified_den = denominator // common_divisor
        
        # 处理分母为负数的情况
        if simplified_den < 0:
            simplified_num *= -1
            simplified_den *= -1
            
        return simplified_num, simplified_den, common_divisor

    def simplify(self):
        # 获取输入
        numerator_str = self.numerator_entry.get().strip()
        denominator_str = self.denominator_entry.get().strip()
        
        # 验证输入
        if not numerator_str or not denominator_str:
            messagebox.showerror("错误", "请输入分子和分母!")
            return
        
        try:
            numerator = int(numerator_str)
            denominator = int(denominator_str)
            
            # 显示原始分数
            self.original_label.config(text=f"原始分数: {numerator}/{denominator}")
            
            # 化简分数
            simplified_num, simplified_den, common_divisor = self.simplify_fraction(numerator, denominator)
            
            if simplified_num is None:
                self.simplified_label.config(text=f"化简结果: {common_divisor}")
            else:
                if simplified_den == 1:
                    self.simplified_label.config(text=f"化简结果: {simplified_num}")
                else:
                    self.simplified_label.config(text=f"化简结果: {simplified_num}/{simplified_den}")
            
            # 显示详细信息
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, f"原始分数: {numerator}/{denominator}\n")
            
            if simplified_num is not None:
                self.details_text.insert(tk.END, f"最大公约数(GCD): {common_divisor}\n")
                self.details_text.insert(tk.END, f"\n化简过程:\n")
                self.details_text.insert(tk.END, f"{numerator} ÷ {common_divisor} = {simplified_num}\n")
                self.details_text.insert(tk.END, f"{denominator} ÷ {common_divisor} = {simplified_den}\n")
                
                if simplified_den == 1:
                    self.details_text.insert(tk.END, f"\n最终结果: {simplified_num} (整数)\n")
                else:
                    self.details_text.insert(tk.END, f"\n最终结果: {simplified_num}/{simplified_den}\n")
            else:
                self.details_text.insert(tk.END, f"\n错误: {common_divisor}\n")
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的整数!")
    
    def clear(self):
        self.numerator_entry.delete(0, tk.END)
        self.denominator_entry.delete(0, tk.END)
        self.original_label.config(text="原始分数: ")
        self.simplified_label.config(text="化简结果: ")
        self.details_text.delete(1.0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = FractionSimplifier(root)
    root.mainloop()