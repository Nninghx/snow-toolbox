import tkinter as tk
from tkinter import messagebox

class DivisorCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("因数计算器")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        
        # 设置字体
        self.font = ("Arial", 12)
        
        # 创建界面组件
        self.create_widgets()
    
    def create_widgets(self):
        # 输入框标签
        tk.Label(self.root, text="输入一个正整数:", font=self.font).pack(pady=(10, 5))
        
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
        
        # 因数数量显示
        self.count_label = tk.Label(self.result_frame, text="因数数量: ", font=self.font, anchor="w")
        self.count_label.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        # 滚动条和文本框用于显示所有因数
        scrollbar = tk.Scrollbar(self.result_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.divisors_text = tk.Text(
            self.result_frame, font=self.font, 
            yscrollcommand=scrollbar.set, height=6
        )
        self.divisors_text.pack(fill=tk.BOTH, expand=True, padx=5)
        scrollbar.config(command=self.divisors_text.yview)

    def get_divisors(self, num):
        # 计算并返回所有因数
        divisors = []
        for i in range(1, num + 1):
            if num % i == 0:
                divisors.append(str(i))
        return divisors

    def calculate(self):
        # 获取输入
        input_str = self.input_entry.get().strip()
        
        # 验证输入
        if not input_str:
            messagebox.showerror("错误", "请输入数字!")
            return
        
        try:
            num = int(input_str)
            if num <= 0:
                messagebox.showerror("错误", "请输入正整数!")
                return
            
            # 计算因数
            divisors = self.get_divisors(num)
            self.count_label.config(text=f"因数数量: {len(divisors)}")
            
            # 显示结果
            self.divisors_text.delete(1.0, tk.END)
            self.divisors_text.insert(tk.END, ", ".join(divisors))
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字!")
    
    def clear(self):
        self.input_entry.delete(0, tk.END)
        self.count_label.config(text="因数数量: ")
        self.divisors_text.delete(1.0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = DivisorCalculator(root)
    root.mainloop()