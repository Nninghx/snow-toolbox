# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import math
from pathlib import Path
from tkinter import Tk, Label, Entry, Button, StringVar, messagebox, ttk, OptionMenu

# 导入公共基类
import importlib.util
_base_spec = importlib.util.spec_from_file_location(
    "public_base_class",
    Path(__file__).resolve().parent.parent / "Core" / "Public base class.py"
)
_base_module = importlib.util.module_from_spec(_base_spec)
_base_spec.loader.exec_module(_base_module)
PDFToolBase = _base_module.PDFToolBase
del _base_spec, _base_module

class TrigonometryCalculator(PDFToolBase):
    def __init__(self, master):
        super().__init__(master)
        if not master.winfo_exists():
            return
        self.master = master
        
        master.title("三角函数计算器")
        
        # 创建Notebook选项卡
        self.notebook = ttk.Notebook(master)
        self.notebook.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        
        # 正弦计算选项卡
        self.sine_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.sine_frame, text="正弦计算")
        
        # 角度转正弦值
        Label(self.sine_frame, text="角度转正弦:").grid(row=0, column=0, padx=10, pady=5)
        self.degree_sin_var = StringVar()
        Entry(self.sine_frame, textvariable=self.degree_sin_var).grid(row=0, column=1, padx=10, pady=5)
        Button(self.sine_frame, text="计算", command=self.calculate_sin_from_degree).grid(row=0, column=2, padx=5)
        
        # 弧度转正弦值
        Label(self.sine_frame, text="弧度转正弦:").grid(row=1, column=0, padx=10, pady=5)
        self.radian_sin_var = StringVar()
        Entry(self.sine_frame, textvariable=self.radian_sin_var).grid(row=1, column=1, padx=10, pady=5)
        Button(self.sine_frame, text="计算", command=self.calculate_sin_from_radian).grid(row=1, column=2, padx=5)
        
        # 余弦计算选项卡
        self.cosine_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.cosine_frame, text="余弦计算")
        
        # 角度转余弦值
        Label(self.cosine_frame, text="角度转余弦:").grid(row=0, column=0, padx=10, pady=5)
        self.degree_cos_var = StringVar()
        Entry(self.cosine_frame, textvariable=self.degree_cos_var).grid(row=0, column=1, padx=10, pady=5)
        Button(self.cosine_frame, text="计算", command=self.calculate_cos_from_degree).grid(row=0, column=2, padx=5)
        
        # 弧度转余弦值
        Label(self.cosine_frame, text="弧度转余弦:").grid(row=1, column=0, padx=10, pady=5)
        self.radian_cos_var = StringVar()
        Entry(self.cosine_frame, textvariable=self.radian_cos_var).grid(row=1, column=1, padx=10, pady=5)
        Button(self.cosine_frame, text="计算", command=self.calculate_cos_from_radian).grid(row=1, column=2, padx=5)
        
        # 正切计算选项卡
        self.tangent_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tangent_frame, text="正切计算")
        
        # 角度转正切值
        Label(self.tangent_frame, text="角度转正切:").grid(row=0, column=0, padx=10, pady=5)
        self.degree_tan_var = StringVar()
        Entry(self.tangent_frame, textvariable=self.degree_tan_var).grid(row=0, column=1, padx=10, pady=5)
        Button(self.tangent_frame, text="计算", command=self.calculate_tan_from_degree).grid(row=0, column=2, padx=5)
        
        # 弧度转正切值
        Label(self.tangent_frame, text="弧度转正切:").grid(row=1, column=0, padx=10, pady=5)
        self.radian_tan_var = StringVar()
        Entry(self.tangent_frame, textvariable=self.radian_tan_var).grid(row=1, column=1, padx=10, pady=5)
        Button(self.tangent_frame, text="计算", command=self.calculate_tan_from_radian).grid(row=1, column=2, padx=5)
        
        # 反三角函数选项卡
        self.inverse_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.inverse_frame, text="反三角函数")
        
        # 输出单位选择
        Label(self.inverse_frame, text="输出单位:").grid(row=0, column=0, padx=10, pady=5)
        self.output_unit = StringVar()
        self.output_unit.set("角度")
        OptionMenu(self.inverse_frame, self.output_unit, "角度", "弧度").grid(row=0, column=1, padx=10, pady=5)
        
        # 反正弦计算
        Label(self.inverse_frame, text="反正弦:").grid(row=1, column=0, padx=10, pady=5)
        self.arcsin_var = StringVar()
        Entry(self.inverse_frame, textvariable=self.arcsin_var).grid(row=1, column=1, padx=10, pady=5)
        Button(self.inverse_frame, text="计算", command=self.calculate_arcsin).grid(row=1, column=2, padx=5)
        
        # 反余弦计算
        Label(self.inverse_frame, text="反余弦:").grid(row=2, column=0, padx=10, pady=5)
        self.arccos_var = StringVar()
        Entry(self.inverse_frame, textvariable=self.arccos_var).grid(row=2, column=1, padx=10, pady=5)
        Button(self.inverse_frame, text="计算", command=self.calculate_arccos).grid(row=2, column=2, padx=5)
        
        # 反正切计算
        Label(self.inverse_frame, text="反正切:").grid(row=3, column=0, padx=10, pady=5)
        self.arctan_var = StringVar()
        Entry(self.inverse_frame, textvariable=self.arctan_var).grid(row=3, column=1, padx=10, pady=5)
        Button(self.inverse_frame, text="计算", command=self.calculate_arctan).grid(row=3, column=2, padx=5)
        
        
        # 结果展示
        self.result_frame = ttk.Frame(master)
        self.result_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        Label(self.result_frame, text="结果:").grid(row=0, column=0, padx=5)
        self.result_var = StringVar()
        Label(self.result_frame, textvariable=self.result_var).grid(row=0, column=1, padx=5)
    
    def calculate_sin_from_degree(self):
        try:
            degree = float(self.degree_sin_var.get())
            radian = math.radians(degree)
            value = math.sin(radian)
            self.show_result(f"sin({degree}°) = {value:.6f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的角度值")
    
    def calculate_sin_from_radian(self):
        try:
            radian = float(self.radian_sin_var.get())
            value = math.sin(radian)
            self.show_result(f"sin({radian:.4f} rad) = {value:.6f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的弧度值")
    
    def calculate_cos_from_degree(self):
        try:
            degree = float(self.degree_cos_var.get())
            radian = math.radians(degree)
            value = math.cos(radian)
            self.show_result(f"cos({degree}°) = {value:.6f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的角度值")
    
    def calculate_cos_from_radian(self):
        try:
            radian = float(self.radian_cos_var.get())
            value = math.cos(radian)
            self.show_result(f"cos({radian:.4f} rad) = {value:.6f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的弧度值")
    
    def calculate_tan_from_degree(self):
        try:
            degree = float(self.degree_tan_var.get())
            if degree % 90 == 0 and degree % 180 != 0:
                raise ValueError("正切值在90°±180°n时无定义")
            radian = math.radians(degree)
            value = math.tan(radian)
            self.show_result(f"tan({degree}°) = {value:.6f}")
        except ValueError as e:
            messagebox.showerror("错误", str(e))
    
    def calculate_tan_from_radian(self):
        try:
            radian = float(self.radian_tan_var.get())
            if (radian - math.pi/2) % math.pi == 0:
                raise ValueError("正切值在π/2±nπ时无定义")
            value = math.tan(radian)
            self.show_result(f"tan({radian:.4f} rad) = {value:.6f}")
        except ValueError as e:
            messagebox.showerror("错误", str(e))
    
    def calculate_arcsin(self):
        try:
            value = float(self.arcsin_var.get())
            if value < -1 or value > 1:
                raise ValueError("值必须在-1到1之间")
            radian = math.asin(value)
            self.show_inverse_result("arcsin", value, radian)
        except ValueError as e:
            messagebox.showerror("错误", str(e))
    
    def calculate_arccos(self):
        try:
            value = float(self.arccos_var.get())
            if value < -1 or value > 1:
                raise ValueError("值必须在-1到1之间")
            radian = math.acos(value)
            self.show_inverse_result("arccos", value, radian)
        except ValueError as e:
            messagebox.showerror("错误", str(e))
    
    def calculate_arctan(self):
        try:
            value = float(self.arctan_var.get())
            radian = math.atan(value)
            self.show_inverse_result("arctan", value, radian)
        except ValueError as e:
            messagebox.showerror("错误", str(e))
    
    def show_result(self, text):
        """显示计算结果"""
        if not hasattr(self, 'result_var'):
            self.result_frame = ttk.Frame(self.master)
            self.result_frame.grid(row=2, column=0, columnspan=3, pady=10)
            self.result_var = StringVar()
            Label(self.result_frame, textvariable=self.result_var).pack()
        self.result_var.set(text)
    
    def show_inverse_result(self, func_name, value, radian):
        """显示反三角函数结果"""
        if self.output_unit.get() == "角度":
            degree = math.degrees(radian)
            self.show_result(f"{func_name}({value}) = {degree:.2f}°")
        else:
            self.show_result(f"{func_name}({value}) = {radian:.4f} rad")

if __name__ == "__main__":
    root = Tk()
    app = TrigonometryCalculator(root)
    root.mainloop()
