import tkinter as tk
from tkinter import messagebox

class RoundingCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("四舍五入计算器")
        self.root.geometry("400x350")
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
        
        # 数字输入
        tk.Label(input_frame, text="输入数字:", font=self.font).grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.number_entry = tk.Entry(input_frame, font=self.font, width=15)
        self.number_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # 小数点位数输入
        tk.Label(input_frame, text="保留小数位:", font=self.font).grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.decimal_entry = tk.Entry(input_frame, font=self.font, width=15)
        self.decimal_entry.grid(row=1, column=1, padx=5, pady=5)
        
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
        
        # 结果标签
        self.result_label = tk.Label(self.result_frame, text="四舍五入结果: ", font=self.font, anchor="w")
        self.result_label.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        # 滚动条和文本框用于显示详细信息
        scrollbar = tk.Scrollbar(self.result_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.details_text = tk.Text(
            self.result_frame, font=self.font, 
            yscrollcommand=scrollbar.set, height=8
        )
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5)
        scrollbar.config(command=self.details_text.yview)

    def calculate(self):
        # 获取输入
        number_str = self.number_entry.get().strip()
        decimal_str = self.decimal_entry.get().strip()
        
        # 验证输入
        if not number_str or not decimal_str:
            messagebox.showerror("错误", "请输入数字和保留小数位数!")
            return
        
        try:
            number = float(number_str)
            decimal = int(decimal_str)
            
            if decimal < 0:
                messagebox.showerror("错误", "小数位数不能为负数!")
                return
            
            # 四舍五入计算
            rounded = round(number, decimal)
            self.result_label.config(text=f"四舍五入结果: {rounded}")
            
            # 显示详细信息
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, f"原始数字: {number}\n")
            self.details_text.insert(tk.END, f"保留小数位数: {decimal}\n")
            self.details_text.insert(tk.END, f"\n计算过程:\n")
            self.details_text.insert(tk.END, f"- 找到第{decimal+1}位小数\n")
            self.details_text.insert(tk.END, f"- 根据该位数值决定舍入\n")
            self.details_text.insert(tk.END, f"- 最终结果: {rounded}")
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字!")
    
    def clear(self):
        self.number_entry.delete(0, tk.END)
        self.decimal_entry.delete(0, tk.END)
        self.result_label.config(text="四舍五入结果: ")
        self.details_text.delete(1.0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = RoundingCalculator(root)
    root.mainloop()