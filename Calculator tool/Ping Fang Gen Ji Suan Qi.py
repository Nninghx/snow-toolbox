import tkinter as tk
from tkinter import messagebox
import math

class SquareRootCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("平方根计算器")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        
        # 设置字体
        self.font = ("Arial", 12)
        
        # 创建界面组件
        self.create_widgets()
    
    def create_widgets(self):
        # 输入框标签
        tk.Label(self.root, text="输入一个非负数:", font=self.font).pack(pady=(10, 5))
        
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
        
        # 平方根显示
        self.result_label = tk.Label(self.result_frame, text="平方根: ", font=self.font, anchor="w")
        self.result_label.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        # 详细结果显示
        self.details_label = tk.Label(self.result_frame, text="计算过程: ", font=self.font, anchor="w")
        self.details_label.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # 滚动条和文本框用于显示详细信息
        scrollbar = tk.Scrollbar(self.result_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.details_text = tk.Text(
            self.result_frame, font=self.font, 
            yscrollcommand=scrollbar.set, height=6
        )
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5)
        scrollbar.config(command=self.details_text.yview)

    def calculate(self):
        # 获取输入
        input_str = self.input_entry.get().strip()
        
        # 验证输入
        if not input_str:
            messagebox.showerror("错误", "请输入数字!")
            return
        
        try:
            num = float(input_str)
            
            if num < 0:
                messagebox.showerror("错误", "请输入非负数!")
                return
            
            # 计算平方根
            sqrt_value = math.sqrt(num)
            self.result_label.config(text=f"平方根: {sqrt_value:.6f}")
            
            # 显示详细信息
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, f"计算过程:\n")
            self.details_text.insert(tk.END, f"√{num} = {sqrt_value:.6f}\n\n")
            self.details_text.insert(tk.END, f"说明:\n")
            self.details_text.insert(tk.END, f"- 结果保留6位小数\n")
            self.details_text.insert(tk.END, f"- 负数没有实数平方根")
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字!")
    
    def clear(self):
        self.input_entry.delete(0, tk.END)
        self.result_label.config(text="平方根: ")
        self.details_label.config(text="计算过程: ")
        self.details_text.delete(1.0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = SquareRootCalculator(root)
    root.mainloop()