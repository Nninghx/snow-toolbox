import json
import os
import math
from tkinter import Tk, Label, Entry, Button, StringVar, messagebox, ttk, OptionMenu

def load_font_config():
    """动态读取字体配置文件"""
    try:
        with open(os.path.join(os.path.dirname(__file__), '../Core/ziti.json'), 'r', encoding='utf-8') as f:
            font_config = json.load(f)
            return font_config.get('family', 'Microsoft YaHei')
    except Exception as e:
        print(f"加载字体配置失败: {e}")
        return 'Microsoft YaHei'

class PerimeterCalculator:
    def __init__(self, master):
        self.master = master
        master.title("多功能周长计算器")
        
        # 设置窗口图标
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "..", "Image", "icon.ico")
            if os.path.exists(icon_path):
                master.iconbitmap(icon_path)
        except Exception as e:
            print(f"加载图标失败: {e}")
        
        # 加载字体配置
        font_family = load_font_config()
        self.font = (font_family, 12)
        
        # 创建Notebook选项卡
        self.notebook = ttk.Notebook(master)
        self.notebook.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        
        # 长方形周长计算器
        self.rectangle_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.rectangle_frame, text="长方形")
        
        Label(self.rectangle_frame, text="长度:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.rect_length = StringVar()
        Entry(self.rectangle_frame, textvariable=self.rect_length, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(self.rectangle_frame, text="宽度:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.rect_width = StringVar()
        Entry(self.rectangle_frame, textvariable=self.rect_width, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Button(self.rectangle_frame, text="计算周长", command=self.calculate_rectangle, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
        
        # 圆形周长计算器
        self.circle_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.circle_frame, text="圆形")
        
        Label(self.circle_frame, text="半径:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.circle_radius = StringVar()
        Entry(self.circle_frame, textvariable=self.circle_radius, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Button(self.circle_frame, text="计算周长", command=self.calculate_circle, font=self.font).grid(row=1, column=0, columnspan=2, pady=10)
        
        # 正方形周长计算器
        self.square_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.square_frame, text="正方形")
        
        Label(self.square_frame, text="边长:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.square_side = StringVar()
        Entry(self.square_frame, textvariable=self.square_side, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Button(self.square_frame, text="计算周长", command=self.calculate_square, font=self.font).grid(row=1, column=0, columnspan=2, pady=10)
        
        # 八边形周长计算器
        self.octagon_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.octagon_frame, text="八边形")
        
        Label(self.octagon_frame, text="边长:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.octagon_side = StringVar()
        Entry(self.octagon_frame, textvariable=self.octagon_side, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Button(self.octagon_frame, text="计算周长", command=self.calculate_octagon, font=self.font).grid(row=1, column=0, columnspan=2, pady=10)
        
        # 等腰三角形周长计算器
        self.triangle_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.triangle_frame, text="等腰三角形")
        
        Label(self.triangle_frame, text="底边:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.triangle_base = StringVar()
        Entry(self.triangle_frame, textvariable=self.triangle_base, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(self.triangle_frame, text="腰长:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.triangle_side = StringVar()
        Entry(self.triangle_frame, textvariable=self.triangle_side, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Button(self.triangle_frame, text="计算周长", command=self.calculate_triangle, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
        
        # 斜边和周长计算器
        self.hypotenuse_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.hypotenuse_frame, text="斜边计算")
        
        Label(self.hypotenuse_frame, text="直角边1:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.hypotenuse_a = StringVar()
        Entry(self.hypotenuse_frame, textvariable=self.hypotenuse_a, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(self.hypotenuse_frame, text="直角边2:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.hypotenuse_b = StringVar()
        Entry(self.hypotenuse_frame, textvariable=self.hypotenuse_b, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Button(self.hypotenuse_frame, text="计算斜边", command=self.calculate_hypotenuse, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
        
        # 结果展示
        self.result_frame = ttk.Frame(master)
        self.result_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        self.result_var = StringVar()
        self.result_label = Label(self.result_frame, textvariable=self.result_var, font=self.font)
        self.result_label.grid(row=0, column=0, padx=10)
    
    def calculate_rectangle(self):
        try:
            length = float(self.rect_length.get())
            width = float(self.rect_width.get())
            perimeter = 2 * (length + width)
            self.result_var.set(f"长方形周长: {perimeter:.2f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字", font=self.font)
    
    def calculate_circle(self):
        try:
            radius = float(self.circle_radius.get())
            perimeter = 2 * math.pi * radius
            self.result_var.set(f"圆周长: {perimeter:.2f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字", font=self.font)
    
    def calculate_square(self):
        try:
            side = float(self.square_side.get())
            perimeter = 4 * side
            self.result_var.set(f"正方形周长: {perimeter:.2f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字", font=self.font)
    
    def calculate_octagon(self):
        try:
            side = float(self.octagon_side.get())
            perimeter = 8 * side
            self.result_var.set(f"八边形周长: {perimeter:.2f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字", font=self.font)
    
    def calculate_triangle(self):
        try:
            base = float(self.triangle_base.get())
            side = float(self.triangle_side.get())
            perimeter = base + 2 * side
            self.result_var.set(f"等腰三角形周长: {perimeter:.2f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字", font=self.font)
    
    def calculate_hypotenuse(self):
        try:
            a = float(self.hypotenuse_a.get())
            b = float(self.hypotenuse_b.get())
            hypotenuse = math.sqrt(a**2 + b**2)
            perimeter = a + b + hypotenuse
            self.result_var.set(f"斜边: {hypotenuse:.2f}\n三角形周长: {perimeter:.2f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字", font=self.font)

if __name__ == "__main__":
    root = Tk()
    app = PerimeterCalculator(root)
    root.mainloop()