import tkinter as tk
from tkinter import messagebox
import math

class DivisorCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("最小公倍数计算器")
        self.root.geometry("400x300")
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
        # 输入框标签
        tk.Label(self.root, text="输入数字(使用空格分隔):", font=self.font).pack(pady=(10, 5))
        
        # 输入框
        self.input_entry = tk.Entry(self.root, font=self.font, width=30)
        self.input_entry.pack(pady=5)
        
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
        
        # 最小公倍数显示
        self.sum_label = tk.Label(self.result_frame, text="最小公倍数: ", font=self.font, anchor="w")
        self.sum_label.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        # 乘数结果显示
        self.divisors_label = tk.Label(self.result_frame, text="乘数结果: ", font=self.font, anchor="w")
        self.divisors_label.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # 滚动条和文本框用于显示所有因数
        scrollbar = tk.Scrollbar(self.result_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.divisors_text = tk.Text(
            self.result_frame, font=self.font, 
            yscrollcommand=scrollbar.set, height=6
        )
        self.divisors_text.pack(fill=tk.BOTH, expand=True, padx=5)
        scrollbar.config(command=self.divisors_text.yview)
    
    def lcm(self, numbers):
        # 计算最小公倍数
        lcm_value = numbers[0]
        for num in numbers[1:]:
            lcm_value = lcm_value * num // math.gcd(lcm_value, num)
        return lcm_value

    def calculate(self):
        # 获取输入
        input_str = self.input_entry.get().strip()
        
        # 验证输入
        if not input_str:
            messagebox.showerror("错误", "请输入数字!")
            return
        
        try:
            # 分割输入的数字
            numbers = []
            for num in input_str.replace(", ", "").split():
                numbers.append(int(num))
            
            # 计算最小公倍数
            lcm_value = self.lcm(numbers)
            self.sum_label.config(text=f"最小公倍数: {lcm_value}")
            
            # 计算每个数字的乘数
            multipliers = []
            for num in numbers:
                multiplier = lcm_value // num
                multipliers.append(f"{num} × {multiplier} = {lcm_value}")
            
            # 显示结果
            self.divisors_text.delete(1.0, tk.END)
            self.divisors_text.insert(tk.END, "\n".join(multipliers))
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字!")
    
    def clear(self):
        self.input_entry.delete(0, tk.END)
        self.sum_label.config(text="和值: ")
        self.divisors_label.config(text="因数: ")
        self.divisors_text.delete(1.0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = DivisorCalculator(root)
    root.mainloop()