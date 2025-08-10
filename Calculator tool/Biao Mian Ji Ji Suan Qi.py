import json
import os
import math
from tkinter import Tk, Label, Entry, Button, StringVar, messagebox, ttk

def load_font_config():
    """动态读取字体配置文件"""
    try:
        with open(os.path.join(os.path.dirname(__file__), '../Core/ziti.json'), 'r', encoding='utf-8') as f:
            font_config = json.load(f)
            return font_config.get('family', 'Microsoft YaHei')
    except Exception as e:
        print(f"加载字体配置失败: {e}")
        return 'Microsoft YaHei'

class SurfaceAreaCalculator:
    def __init__(self, master):
        self.master = master
        master.title("多功能表面积计算器")
        
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
        
        # 球体表面积计算器
        self.sphere_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.sphere_frame, text="球体")
        
        Label(self.sphere_frame, text="半径:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.sphere_radius = StringVar()
        Entry(self.sphere_frame, textvariable=self.sphere_radius, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Button(self.sphere_frame, text="计算表面积", command=self.calculate_sphere, font=self.font).grid(row=1, column=0, columnspan=2, pady=10)
        
        # 立方体表面积计算器
        self.cube_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.cube_frame, text="立方体")
        
        Label(self.cube_frame, text="边长:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.cube_side = StringVar()
        Entry(self.cube_frame, textvariable=self.cube_side, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Button(self.cube_frame, text="计算表面积", command=self.calculate_cube, font=self.font).grid(row=1, column=0, columnspan=2, pady=10)
        
        # 三角棱柱表面积计算器
        self.triangular_prism_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.triangular_prism_frame, text="三角棱柱")
        
        # 棱柱类型选择
        Label(self.triangular_prism_frame, text="棱柱类型:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.prism_type = StringVar(value="equilateral")
        ttk.Radiobutton(self.triangular_prism_frame, text="等边三角形", variable=self.prism_type, 
                       value="equilateral").grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(self.triangular_prism_frame, text="直角三角形", variable=self.prism_type, 
                       value="right").grid(row=0, column=2, sticky="w")
        
        # 参数输入
        Label(self.triangular_prism_frame, text="底边长度(b):", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.prism_base = StringVar()
        Entry(self.triangular_prism_frame, textvariable=self.prism_base, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Label(self.triangular_prism_frame, text="三角形高度(h):", font=self.font).grid(row=2, column=0, padx=10, pady=5)
        self.prism_triangle_height = StringVar()
        Entry(self.triangular_prism_frame, textvariable=self.prism_triangle_height, font=self.font).grid(row=2, column=1, padx=10, pady=5)
        
        Label(self.triangular_prism_frame, text="棱柱长度(l):", font=self.font).grid(row=3, column=0, padx=10, pady=5)
        self.prism_length = StringVar()
        Entry(self.triangular_prism_frame, textvariable=self.prism_length, font=self.font).grid(row=3, column=1, padx=10, pady=5)
        
        Button(self.triangular_prism_frame, text="计算表面积", command=self.calculate_triangular_prism, font=self.font).grid(row=4, column=0, columnspan=3, pady=10)
        
        # 圆锥表面积计算器
        self.cone_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.cone_frame, text="圆锥")
        
        # 输入方式选择
        Label(self.cone_frame, text="输入方式:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.cone_input_type = StringVar(value="slant")
        ttk.Radiobutton(self.cone_frame, text="母线长度", variable=self.cone_input_type, 
                       value="slant").grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(self.cone_frame, text="高度", variable=self.cone_input_type, 
                       value="height").grid(row=0, column=2, sticky="w")
        
        # 参数输入
        Label(self.cone_frame, text="底面半径(r):", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.cone_radius = StringVar()
        Entry(self.cone_frame, textvariable=self.cone_radius, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Label(self.cone_frame, text="母线长度/高度:", font=self.font).grid(row=2, column=0, padx=10, pady=5)
        self.cone_slant_or_height = StringVar()
        Entry(self.cone_frame, textvariable=self.cone_slant_or_height, font=self.font).grid(row=2, column=1, padx=10, pady=5)
        
        Button(self.cone_frame, text="计算表面积", command=self.calculate_cone, font=self.font).grid(row=3, column=0, columnspan=3, pady=10)
        Button(self.cone_frame, text="计算侧面积", command=self.calculate_cone_lateral, font=self.font).grid(row=4, column=0, columnspan=3, pady=10)
        
        # 金字塔表面积计算器
        self.pyramid_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.pyramid_frame, text="金字塔")
        
        Label(self.pyramid_frame, text="底面长度:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.pyramid_length = StringVar()
        Entry(self.pyramid_frame, textvariable=self.pyramid_length, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(self.pyramid_frame, text="底面宽度:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.pyramid_width = StringVar()
        Entry(self.pyramid_frame, textvariable=self.pyramid_width, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Label(self.pyramid_frame, text="高度:", font=self.font).grid(row=2, column=0, padx=10, pady=5)
        self.pyramid_height = StringVar()
        Entry(self.pyramid_frame, textvariable=self.pyramid_height, font=self.font).grid(row=2, column=1, padx=10, pady=5)
        
        Button(self.pyramid_frame, text="计算表面积", command=self.calculate_pyramid, font=self.font).grid(row=3, column=0, columnspan=2, pady=10)
        Button(self.pyramid_frame, text="计算侧面积", command=self.calculate_pyramid_lateral, font=self.font).grid(row=4, column=0, columnspan=2, pady=10)
        
        # 结果展示
        self.result_frame = ttk.Frame(master)
        self.result_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        self.result_var = StringVar()
        self.result_label = Label(self.result_frame, textvariable=self.result_var, font=self.font)
        self.result_label.grid(row=0, column=0, padx=10)
    
    def calculate_sphere(self):
        try:
            radius = float(self.sphere_radius.get())
            area = 4 * math.pi * radius ** 2
            self.result_var.set(f"球体表面积: {area:.2f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字", font=self.font)
    
    def calculate_cube(self):
        try:
            side = float(self.cube_side.get())
            area = 6 * side ** 2
            self.result_var.set(f"立方体表面积: {area:.2f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字", font=self.font)
    
    def calculate_triangular_prism(self):
        try:
            base = float(self.prism_base.get())
            triangle_height = float(self.prism_triangle_height.get())
            length = float(self.prism_length.get())
            
            # 计算底面积(三角形面积)
            base_area = base * triangle_height / 2
            
            # 根据棱柱类型计算侧面积
            if self.prism_type.get() == "equilateral":
                # 等边三角形棱柱
                lateral_area = (base * 3) * length
            else:
                # 直角三角形棱柱 (用户提供的公式)
                hypotenuse = math.sqrt(base**2 + triangle_height**2)
                lateral_area = (base + triangle_height + hypotenuse) * length
            
            total_area = 2 * base_area + lateral_area
            self.result_var.set(f"三角棱柱表面积: {total_area:.2f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字", font=self.font)
    
    def calculate_cone(self):
        try:
            radius = float(self.cone_radius.get())
            value = float(self.cone_slant_or_height.get())
            
            base_area = math.pi * radius ** 2
            
            if self.cone_input_type.get() == "slant":
                slant = value
            else:
                # 根据高度计算母线长度
                slant = math.sqrt(radius**2 + value**2)
            
            lateral_area = math.pi * radius * slant
            total_area = base_area + lateral_area
            self.result_var.set(f"圆锥表面积: {total_area:.2f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字", font=self.font)
    
    def calculate_cone_lateral(self):
        try:
            radius = float(self.cone_radius.get())
            value = float(self.cone_slant_or_height.get())
            
            if self.cone_input_type.get() == "slant":
                slant = value
            else:
                # 根据高度计算母线长度
                slant = math.sqrt(radius**2 + value**2)
            
            lateral_area = math.pi * radius * slant
            self.result_var.set(f"圆锥侧面积: {lateral_area:.2f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字", font=self.font)
    
    def calculate_pyramid(self):
        try:
            length = float(self.pyramid_length.get())
            width = float(self.pyramid_width.get())
            height = float(self.pyramid_height.get())
            
            # 计算底面积
            base_area = length * width
            
            # 计算侧面积(2对三角形)
            slant1 = math.sqrt((length / 2) ** 2 + height ** 2)
            slant2 = math.sqrt((width / 2) ** 2 + height ** 2)
            lateral_area = 2 * (length * slant2 / 2) + 2 * (width * slant1 / 2)
            
            total_area = base_area + lateral_area
            self.result_var.set(f"金字塔表面积: {total_area:.2f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字", font=self.font)
    
    def calculate_pyramid_lateral(self):
        try:
            length = float(self.pyramid_length.get())
            width = float(self.pyramid_width.get())
            height = float(self.pyramid_height.get())
            
            # 计算侧面积(2对三角形)
            slant1 = math.sqrt((length / 2) ** 2 + height ** 2)
            slant2 = math.sqrt((width / 2) ** 2 + height ** 2)
            lateral_area = 2 * (length * slant2 / 2) + 2 * (width * slant1 / 2)
            
            self.result_var.set(f"金字塔侧面积: {lateral_area:.2f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字", font=self.font)

if __name__ == "__main__":
    root = Tk()
    app = SurfaceAreaCalculator(root)
    root.mainloop()