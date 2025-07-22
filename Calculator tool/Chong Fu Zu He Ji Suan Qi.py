import tkinter as tk
from tkinter import messagebox
import math

class CombinationCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("重复组合计算器")
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
            # 注意路径可能需要根据实际位置调整
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
        
        # 物品类型总数(n)输入
        tk.Label(input_frame, text="物品类型总数(n):", font=self.font).grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.n_entry = tk.Entry(input_frame, font=self.font, width=15)
        self.n_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # 选择数量(r)输入
        tk.Label(input_frame, text="选择数量(r):", font=self.font).grid(row=1, column=0, padx=5, pady=5, sticky="e")
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
        
        # 组合数显示
        self.combination_label = tk.Label(self.result_frame, text="组合数: ", font=self.font, anchor="w")
        self.combination_label.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        # 组合示例显示
        self.example_label = tk.Label(self.result_frame, text="示例组合: ", font=self.font, anchor="w")
        self.example_label.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # 滚动条和文本框用于显示详细信息
        scrollbar = tk.Scrollbar(self.result_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.details_text = tk.Text(
            self.result_frame, font=self.font, 
            yscrollcommand=scrollbar.set, height=8
        )
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5)
        scrollbar.config(command=self.details_text.yview)

    def combination_with_repetition(self, n, r):
        # 计算重复组合数: C(n+r-1, r)
        if n == 0 or r == 0:
            return 0
        return math.comb(n + r - 1, r)

    def generate_example(self, n, r):
        # 生成简单的组合示例
        if n <= 0 or r <= 0:
            return ""
        
        # 简单示例：用字母A,B,C...表示不同类型物品
        letters = [chr(ord('A') + i) for i in range(min(n, 26))]
        if n > 26:
            letters += [f"Item{i+1}" for i in range(26, n)]
        
        # 返回一个示例组合
        return ", ".join([letters[0]] * r)

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
            
            # 计算组合数
            comb = self.combination_with_repetition(n, r)
            self.combination_label.config(text=f"组合数: {comb}")
            
            # 生成示例组合
            example = self.generate_example(n, r)
            self.example_label.config(text=f"示例组合: {example}")
            
            # 显示详细信息
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, f"重复组合公式: C(n+r-1, r)\n")
            self.details_text.insert(tk.END, f"计算过程: C({n}+{r}-1, {r}) = C({n+r-1}, {r}) = {comb}\n")
            self.details_text.insert(tk.END, f"\n说明:\n")
            self.details_text.insert(tk.END, f"- 从{n}种不同类型物品中选择{r}个\n")
            self.details_text.insert(tk.END, f"- 允许重复选择同类型物品\n")
            self.details_text.insert(tk.END, f"- 不考虑选择的顺序")
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的整数!")
        except OverflowError:
            messagebox.showerror("错误", "数字太大，无法计算!")
    
    def clear(self):
        self.n_entry.delete(0, tk.END)
        self.r_entry.delete(0, tk.END)
        self.combination_label.config(text="组合数: ")
        self.example_label.config(text="示例组合: ")
        self.details_text.delete(1.0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = CombinationCalculator(root)
    root.mainloop()