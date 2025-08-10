import tkinter as tk
from tkinter import messagebox
import os

class BinaryCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("二进制计算器")
        self.root.geometry("500x450")
        self.root.resizable(False, False)
        
        # 设置窗口图标
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "..", "Image", "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"加载图标失败: {e}")
        
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
        
        # 二进制数1输入
        tk.Label(input_frame, text="二进制数1:", font=self.font).grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.binary1_entry = tk.Entry(input_frame, font=self.font, width=20)
        self.binary1_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # 二进制数2输入
        tk.Label(input_frame, text="二进制数2:", font=self.font).grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.binary2_entry = tk.Entry(input_frame, font=self.font, width=20)
        self.binary2_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # 运算选择
        tk.Label(input_frame, text="运算:", font=self.font).grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.operation_var = tk.StringVar(value="AND")
        operations = ["AND", "OR", "XOR", "NOT", "加法", "减法", "左移", "右移"]
        self.operation_menu = tk.OptionMenu(input_frame, self.operation_var, *operations)
        self.operation_menu.config(font=self.font, width=12)
        self.operation_menu.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
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
        
        # 转换按钮
        self.convert_btn = tk.Button(
            button_frame, text="十进制转二进制", font=self.font,
            command=self.decimal_to_binary, bg="#2196F3", fg="white"
        )
        self.convert_btn.pack(side=tk.LEFT, padx=5)
        
        # 结果显示区域
        self.result_frame = tk.Frame(self.root, bd=2, relief=tk.GROOVE)
        self.result_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        # 运算式显示
        self.equation_label = tk.Label(self.result_frame, text="运算式: ", font=self.font, anchor="w")
        self.equation_label.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        # 二进制结果显示
        self.binary_result_label = tk.Label(self.result_frame, text="二进制结果: ", font=self.font, anchor="w")
        self.binary_result_label.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # 十进制结果显示
        self.decimal_result_label = tk.Label(self.result_frame, text="十进制结果: ", font=self.font, anchor="w")
        self.decimal_result_label.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # 滚动条和文本框用于显示详细信息
        scrollbar = tk.Scrollbar(self.result_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.details_text = tk.Text(
            self.result_frame, font=self.font, 
            yscrollcommand=scrollbar.set, height=8
        )
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5)
        scrollbar.config(command=self.details_text.yview)

    def is_valid_binary(self, binary_str):
        """验证是否为有效的二进制字符串"""
        if not binary_str:
            return False
        return all(bit in ('0', '1') for bit in binary_str)

    def binary_to_decimal(self, binary_str):
        """二进制转十进制"""
        return int(binary_str, 2)

    def decimal_to_binary(self):
        """十进制转二进制"""
        decimal_str = tk.simpledialog.askstring("十进制转二进制", "请输入十进制整数:")
        if decimal_str is None:
            return
            
        try:
            decimal = int(decimal_str)
            binary = bin(decimal)[2:]  # 去掉'0b'前缀
            self.binary1_entry.delete(0, tk.END)
            self.binary1_entry.insert(0, binary)
        except ValueError:
            messagebox.showerror("错误", "请输入有效的整数!")

    def calculate(self):
        # 获取输入
        binary1 = self.binary1_entry.get().strip()
        operation = self.operation_var.get()
        
        # 根据运算类型验证输入
        if operation != "NOT":
            binary2 = self.binary2_entry.get().strip()
            if not binary2:
                messagebox.showerror("错误", "请输入二进制数2!")
                return
            if not self.is_valid_binary(binary2):
                messagebox.showerror("错误", "二进制数2包含非法字符!")
                return
        
        if not binary1:
            messagebox.showerror("错误", "请输入二进制数1!")
            return
        if not self.is_valid_binary(binary1):
            messagebox.showerror("错误", "二进制数1包含非法字符!")
            return
        
        try:
            # 转换为十进制
            decimal1 = self.binary_to_decimal(binary1)
            
            if operation != "NOT":
                decimal2 = self.binary_to_decimal(binary2)
            
            # 执行运算
            result_decimal = 0
            details = ""
            
            if operation == "AND":
                result_decimal = decimal1 & decimal2
                details = f"{binary1} AND {binary2}\n= {bin(result_decimal)[2:]}\n\n位运算:\n"
                for i in range(max(len(binary1), len(binary2))):
                    bit1 = binary1[-i-1] if i < len(binary1) else '0'
                    bit2 = binary2[-i-1] if i < len(binary2) else '0'
                    res_bit = '1' if bit1 == '1' and bit2 == '1' else '0'
                    details += f"位{i}: {bit1} & {bit2} = {res_bit}\n"
                    
            elif operation == "OR":
                result_decimal = decimal1 | decimal2
                details = f"{binary1} OR {binary2}\n= {bin(result_decimal)[2:]}\n\n位运算:\n"
                for i in range(max(len(binary1), len(binary2))):
                    bit1 = binary1[-i-1] if i < len(binary1) else '0'
                    bit2 = binary2[-i-1] if i < len(binary2) else '0'
                    res_bit = '1' if bit1 == '1' or bit2 == '1' else '0'
                    details += f"位{i}: {bit1} | {bit2} = {res_bit}\n"
                    
            elif operation == "XOR":
                result_decimal = decimal1 ^ decimal2
                details = f"{binary1} XOR {binary2}\n= {bin(result_decimal)[2:]}\n\n位运算:\n"
                for i in range(max(len(binary1), len(binary2))):
                    bit1 = binary1[-i-1] if i < len(binary1) else '0'
                    bit2 = binary2[-i-1] if i < len(binary2) else '0'
                    res_bit = '1' if bit1 != bit2 else '0'
                    details += f"位{i}: {bit1} ^ {bit2} = {res_bit}\n"
                    
            elif operation == "NOT":
                # 计算补位数
                bits = len(binary1)
                mask = (1 << bits) - 1
                result_decimal = (~decimal1) & mask
                details = f"NOT {binary1}\n= {bin(result_decimal)[2:]}\n\n按位取反:\n"
                for i in range(len(binary1)):
                    bit = binary1[-i-1]
                    res_bit = '0' if bit == '1' else '1'
                    details += f"位{i}: ~{bit} = {res_bit}\n"
                    
            elif operation == "加法":
                result_decimal = decimal1 + decimal2
                details = f"{binary1} + {binary2}\n= {bin(result_decimal)[2:]}\n\n十进制: {decimal1} + {decimal2} = {result_decimal}"
                
            elif operation == "减法":
                result_decimal = decimal1 - decimal2
                details = f"{binary1} - {binary2}\n= {bin(result_decimal)[2:]}\n\n十进制: {decimal1} - {decimal2} = {result_decimal}"
                
            elif operation == "左移":
                result_decimal = decimal1 << decimal2
                details = f"{binary1} << {binary2}\n= {bin(result_decimal)[2:]}\n\n相当于乘以2^{decimal2}: {decimal1} * {2**decimal2} = {result_decimal}"
                
            elif operation == "右移":
                result_decimal = decimal1 >> decimal2
                details = f"{binary1} >> {binary2}\n= {bin(result_decimal)[2:]}\n\n相当于除以2^{decimal2}: {decimal1} / {2**decimal2} = {result_decimal}"
            
            # 显示结果
            result_binary = bin(result_decimal)[2:]
            self.equation_label.config(text=f"运算式: {binary1} {operation} {binary2 if operation != 'NOT' else ''}")
            self.binary_result_label.config(text=f"二进制结果: {result_binary}")
            self.decimal_result_label.config(text=f"十进制结果: {result_decimal}")
            
            # 显示详细信息
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, details)
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的二进制数!")
    
    def clear(self):
        self.binary1_entry.delete(0, tk.END)
        self.binary2_entry.delete(0, tk.END)
        self.operation_var.set("AND")
        self.equation_label.config(text="运算式: ")
        self.binary_result_label.config(text="二进制结果: ")
        self.decimal_result_label.config(text="十进制结果: ")
        self.details_text.delete(1.0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = BinaryCalculator(root)
    root.mainloop()