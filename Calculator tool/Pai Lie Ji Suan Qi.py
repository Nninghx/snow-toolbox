import tkinter as tk
from tkinter import messagebox
import math

class PermutationCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("排列计算器")
        self.root.geometry("400x350")
        self.root.resizable(False, False)
        
        # 设置字体
        self.font = ("Arial", 12)
        
        # 创建界面组件
        self.create_widgets()
    
    def create_widgets(self):
        # 输入框框架
        input_frame = tk.Frame(self.root)
        input_frame.pack(pady=(10, 5))
        
        # 总项目数(n)输入
        tk.Label(input_frame, text="总项目数(n):", font=self.font).grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.n_entry = tk.Entry(input_frame, font=self.font, width=15)
        self.n_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # 排列数(r)输入
        tk.Label(input_frame, text="排列数(r):", font=self.font).grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.r_entry = tk.Entry(input_frame, font=self.font, width=15)
        self.r_entry.grid(row=1, column=1, padx=5, pady=5)
        
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
        
        # 排列数显示
        self.permutation_label = tk.Label(self.result_frame, text="排列数: ", font=self.font, anchor="w")
        self.permutation_label.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        # 滚动条和文本框用于显示详细信息
        scrollbar = tk.Scrollbar(self.result_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.details_text = tk.Text(
            self.result_frame, font=self.font, 
            yscrollcommand=scrollbar.set, height=8
        )
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5)
        scrollbar.config(command=self.details_text.yview)

    def permutation(self, n, r):
        # 计算排列数: nPr = n!/(n-r)!
        if n < r:
            return 0
        return math.perm(n, r)

    def calculate(self):
        # 获取输入
        n_str = self.n_entry.get().strip()
        r_str = self.r_entry.get().strip()
        
        # 验证输入
        if not n_str or not r_str:
            messagebox.showerror("错误", "请输入n和r的值!")
            return
        
        try:
            n = int(n_str)
            r = int(r_str)
            
            if n <= 0 or r <= 0:
                messagebox.showerror("错误", "请输入正整数!")
                return
            
            if n < r:
                messagebox.showerror("错误", "n必须大于或等于r!")
                return
            
            # 计算排列数
            perm = self.permutation(n, r)
            self.permutation_label.config(text=f"排列数: {perm}")
            
            # 显示详细信息
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, f"排列公式: nPr = n!/(n-r)!\n")
            self.details_text.insert(tk.END, f"计算过程: {n}P{r} = {n}!/({n}-{r})! = {perm}\n")
            self.details_text.insert(tk.END, f"\n说明:\n")
            self.details_text.insert(tk.END, f"- 从{n}个不同项目中排列{r}个项目\n")
            self.details_text.insert(tk.END, f"- 考虑项目的顺序\n")
            self.details_text.insert(tk.END, f"- 每个项目只能使用一次")
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的整数!")
        except OverflowError:
            messagebox.showerror("错误", "数字太大，无法计算!")
    
    def clear(self):
        self.n_entry.delete(0, tk.END)
        self.r_entry.delete(0, tk.END)
        self.permutation_label.config(text="排列数: ")
        self.details_text.delete(1.0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = PermutationCalculator(root)
    root.mainloop()