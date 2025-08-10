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

class VolumeCalculator:
    def __init__(self, master):
        self.master = master
        master.title("体积计算器")
        
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
        
        # 主框架
        self.main_frame = ttk.Frame(master)
        self.main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 标题
        Label(self.main_frame, text="体积计算器", font=(font_family, 16, 'bold')).pack(pady=10)
        
        # 几何图形选择按钮框架
        self.shapes_frame = ttk.Frame(self.main_frame)
        self.shapes_frame.pack(fill='x', pady=5)
        
        # 创建形状选择按钮
        shapes = [
            "长方体", "圆柱体", "球体", "金字塔", "直圆柱",
            "立方体", "长方形水箱", "管", "胶囊", "正四棱锥",
            "圆台", "圆锥", "半球", "圆环"
        ]

        # 每行最多6个按钮
        for i in range(0, len(shapes), 6):
            row_frame = ttk.Frame(self.shapes_frame)
            row_frame.pack(fill='x')
            for shape in shapes[i:i+6]:
                btn = Button(row_frame, text=shape, command=lambda s=shape: self.show_shape_ui(s), 
                           font=self.font, width=12)
                btn.pack(side='left', padx=5, pady=2)
        
        # 计算区域框架
        self.calc_frame = ttk.Frame(self.main_frame)
        self.calc_frame.pack(fill='both', expand=True, pady=10)
        
        # 结果展示
        self.result_frame = ttk.Frame(self.main_frame)
        self.result_frame.pack(fill='x', pady=10)
        
        Label(self.result_frame, text="结果:", font=self.font).pack(side='left', padx=5)
        self.result_var = StringVar()
        Label(self.result_frame, textvariable=self.result_var, font=self.font).pack(side='left', padx=5)
        
        # 初始化当前形状UI
        self.current_shape = None
        self.show_shape_ui("长方体")
    
    def setup_cuboid_ui(self, parent):
        """设置长方体体积计算界面"""
        Label(parent, text="长度:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.length_var = StringVar()
        Entry(parent, textvariable=self.length_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="宽度:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.width_var = StringVar()
        Entry(parent, textvariable=self.width_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Label(parent, text="高度:", font=self.font).grid(row=2, column=0, padx=10, pady=5)
        self.height_var = StringVar()
        Entry(parent, textvariable=self.height_var, font=self.font).grid(row=2, column=1, padx=10, pady=5)
        
        Button(parent, text="计算体积", command=self.calculate_cuboid, font=self.font).grid(row=3, column=0, columnspan=2, pady=10)
    
    def setup_cylinder_ui(self, parent):
        """设置圆柱体体积计算界面"""
        Label(parent, text="底面半径:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.radius_var = StringVar()
        Entry(parent, textvariable=self.radius_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="高度:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.cylinder_height_var = StringVar()
        Entry(parent, textvariable=self.cylinder_height_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Button(parent, text="计算体积", command=self.calculate_cylinder, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
    
    def setup_sphere_ui(self, parent):
        """设置球体体积计算界面"""
        Label(parent, text="半径:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.sphere_radius_var = StringVar()
        Entry(parent, textvariable=self.sphere_radius_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Button(parent, text="计算体积", command=self.calculate_sphere, font=self.font).grid(row=1, column=0, columnspan=2, pady=10)
    
    def setup_pyramid_ui(self, parent):
        """设置金字塔体积计算界面"""
        if self.current_shape == "正四棱锥":
            Label(parent, text="底边长度:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
            self.base_side_var = StringVar()
            Entry(parent, textvariable=self.base_side_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        else:
            Label(parent, text="底面积:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
            self.base_area_var = StringVar()
            Entry(parent, textvariable=self.base_area_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="高度:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.square_pyramid_height_var = StringVar()
        Entry(parent, textvariable=self.square_pyramid_height_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        self.pyramid_height_var = self.square_pyramid_height_var  # 保持兼容性
        
        if self.current_shape == "正四棱锥":
            Button(parent, text="计算体积", command=self.calculate_square_pyramid, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
        else:
            Button(parent, text="计算体积", command=self.calculate_pyramid, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
    
    def setup_right_cylinder_ui(self, parent):
        """设置直圆柱体积计算界面"""
        Label(parent, text="底面半径:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.right_radius_var = StringVar()
        Entry(parent, textvariable=self.right_radius_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="高度:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.right_height_var = StringVar()
        Entry(parent, textvariable=self.right_height_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Button(parent, text="计算体积", command=self.calculate_right_cylinder, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
    
    def calculate_cuboid(self):
        """计算长方体体积"""
        try:
            length = float(self.length_var.get())
            width = float(self.width_var.get())
            height = float(self.height_var.get())
            volume = length * width * height
            self.show_result(f"长方体体积: {volume:.2f} 立方单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    
    def calculate_cylinder(self):
        """计算圆柱体体积"""
        try:
            radius = float(self.radius_var.get())
            height = float(self.cylinder_height_var.get())
            volume = math.pi * radius ** 2 * height
            self.show_result(f"圆柱体体积: {volume:.2f} 立方单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    
    def calculate_sphere(self):
        """计算球体体积"""
        try:
            radius = float(self.sphere_radius_var.get())
            volume = (4/3) * math.pi * radius ** 3
            self.show_result(f"球体体积: {volume:.2f} 立方单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    
    def calculate_pyramid(self):
        """计算金字塔体积"""
        try:
            base_area = float(self.base_area_var.get())
            height = float(self.pyramid_height_var.get())
            volume = (1/3) * base_area * height
            self.show_result(f"金字塔体积: {volume:.2f} 立方单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    
    def calculate_right_cylinder(self):
        """计算直圆柱体积"""
        try:
            radius = float(self.right_radius_var.get())
            height = float(self.right_height_var.get())
            volume = math.pi * radius ** 2 * height
            self.show_result(f"直圆柱体积: {volume:.2f} 立方单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    
    def show_result(self, text):
        """显示计算结果"""
        self.result_var.set(text)
        
    def setup_cube_ui(self, parent):
        """设置立方体体积计算界面"""
        Label(parent, text="边长:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.cube_side_var = StringVar()
        Entry(parent, textvariable=self.cube_side_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        Button(parent, text="计算体积", command=self.calculate_cube, font=self.font).grid(row=1, column=0, columnspan=2, pady=10)
    
    def setup_tank_ui(self, parent):
        """设置长方形水箱体积计算界面"""
        Label(parent, text="长度:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.tank_length_var = StringVar()
        Entry(parent, textvariable=self.tank_length_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="宽度:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.tank_width_var = StringVar()
        Entry(parent, textvariable=self.tank_width_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Label(parent, text="高度:", font=self.font).grid(row=2, column=0, padx=10, pady=5)
        self.tank_height_var = StringVar()
        Entry(parent, textvariable=self.tank_height_var, font=self.font).grid(row=2, column=1, padx=10, pady=5)
        
        Label(parent, text="液体高度:", font=self.font).grid(row=3, column=0, padx=10, pady=5)
        self.liquid_height_var = StringVar()
        Entry(parent, textvariable=self.liquid_height_var, font=self.font).grid(row=3, column=1, padx=10, pady=5)
        
        Button(parent, text="计算体积", command=self.calculate_tank, font=self.font).grid(row=4, column=0, columnspan=2, pady=10)
    
    def setup_tube_ui(self, parent):
        """设置管体积计算界面"""
        Label(parent, text="外径:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.outer_diameter_var = StringVar()
        Entry(parent, textvariable=self.outer_diameter_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="内径:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.inner_diameter_var = StringVar()
        Entry(parent, textvariable=self.inner_diameter_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Label(parent, text="长度:", font=self.font).grid(row=2, column=0, padx=10, pady=5)
        self.tube_length_var = StringVar()
        Entry(parent, textvariable=self.tube_length_var, font=self.font).grid(row=2, column=1, padx=10, pady=5)
        
        Button(parent, text="计算体积", command=self.calculate_tube, font=self.font).grid(row=3, column=0, columnspan=2, pady=10)
        
    def setup_capsule_ui(self, parent):
        """设置胶囊体积计算界面"""
        Label(parent, text="半径:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.capsule_radius_var = StringVar()
        Entry(parent, textvariable=self.capsule_radius_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="高度:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.capsule_height_var = StringVar()
        Entry(parent, textvariable=self.capsule_height_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Button(parent, text="计算体积", command=self.calculate_capsule, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
    
    def setup_frustum_ui(self, parent):
        """设置圆台体积计算界面"""
        Label(parent, text="上底半径:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.top_radius_var = StringVar()
        Entry(parent, textvariable=self.top_radius_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="下底半径:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.bottom_radius_var = StringVar()
        Entry(parent, textvariable=self.bottom_radius_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Label(parent, text="高度:", font=self.font).grid(row=2, column=0, padx=10, pady=5)
        self.frustum_height_var = StringVar()
        Entry(parent, textvariable=self.frustum_height_var, font=self.font).grid(row=2, column=1, padx=10, pady=5)
        
        Button(parent, text="计算体积", command=self.calculate_frustum, font=self.font).grid(row=3, column=0, columnspan=2, pady=10)
    
    def setup_cone_ui(self, parent):
        """设置圆锥体积计算界面"""
        Label(parent, text="底面半径:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.cone_radius_var = StringVar()
        Entry(parent, textvariable=self.cone_radius_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="高度:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.cone_height_var = StringVar()
        Entry(parent, textvariable=self.cone_height_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Button(parent, text="计算体积", command=self.calculate_cone, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
    
    def setup_hemisphere_ui(self, parent):
        """设置半球体积计算界面"""
        Label(parent, text="半径:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.hemisphere_radius_var = StringVar()
        Entry(parent, textvariable=self.hemisphere_radius_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Button(parent, text="计算体积", command=self.calculate_hemisphere, font=self.font).grid(row=1, column=0, columnspan=2, pady=10)
    
    def setup_torus_ui(self, parent):
        """设置圆环体积计算界面"""
        Label(parent, text="大半径:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.major_radius_var = StringVar()
        Entry(parent, textvariable=self.major_radius_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="小半径:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.minor_radius_var = StringVar()
        Entry(parent, textvariable=self.minor_radius_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Button(parent, text="计算体积", command=self.calculate_torus, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
    
    def calculate_cube(self):
        """计算立方体体积"""
        try:
            side = float(self.cube_side_var.get())
            volume = side ** 3
            self.show_result(f"立方体体积: {volume:.2f} 立方单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    
    def calculate_tank(self):
        """计算长方形水箱体积"""
        try:
            length = float(self.tank_length_var.get())
            width = float(self.tank_width_var.get())
            liquid_height = float(self.liquid_height_var.get())
            height = float(self.tank_height_var.get())
            
            if liquid_height > height:
                raise ValueError("液体高度不能大于水箱高度")
                
            volume = length * width * liquid_height
            self.show_result(f"水箱液体体积: {volume:.2f} 立方单位")
        except ValueError as e:
            messagebox.showerror("错误", str(e), font=self.font)
    
    def calculate_tube(self):
        """计算管体积"""
        try:
            outer_diameter = float(self.outer_diameter_var.get())
            inner_diameter = float(self.inner_diameter_var.get())
            length = float(self.tube_length_var.get())
            
            if inner_diameter >= outer_diameter:
                raise ValueError("内径必须小于外径")
                
            outer_radius = outer_diameter / 2
            inner_radius = inner_diameter / 2
            volume = math.pi * (outer_radius**2 - inner_radius**2) * length
            self.show_result(f"管体积: {volume:.2f} 立方单位")
        except ValueError as e:
            messagebox.showerror("错误", str(e), font=self.font)
    
    def calculate_capsule(self):
        """计算胶囊体积"""
        try:
            radius = float(self.capsule_radius_var.get())
            height = float(self.capsule_height_var.get())
            
            if height < 2 * radius:
                raise ValueError("高度不能小于直径")
                
            # 胶囊体积 = 圆柱部分 + 两个半球
            cylinder_height = height - 2 * radius
            cylinder_volume = math.pi * radius**2 * cylinder_height
            sphere_volume = (4/3) * math.pi * radius**3
            volume = cylinder_volume + sphere_volume
            self.show_result(f"胶囊体积: {volume:.2f} 立方单位")
        except ValueError as e:
            messagebox.showerror("错误", str(e), font=self.font)
    
    def calculate_square_pyramid(self):
        """计算正四棱锥体积"""
        try:
            base_side = float(self.base_side_var.get())
            height = float(self.square_pyramid_height_var.get())
            volume = (1/3) * base_side**2 * height
            self.show_result(f"正四棱锥体积: {volume:.2f} 立方单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    
    def calculate_frustum(self):
        """计算圆台体积"""
        try:
            top_radius = float(self.top_radius_var.get())
            bottom_radius = float(self.bottom_radius_var.get())
            height = float(self.frustum_height_var.get())
            
            if top_radius <= 0 or bottom_radius <= 0:
                raise ValueError("半径必须大于0")
                
            volume = (1/3) * math.pi * height * (top_radius**2 + bottom_radius**2 + top_radius*bottom_radius)
            self.show_result(f"圆台体积: {volume:.2f} 立方单位")
        except ValueError as e:
            messagebox.showerror("错误", str(e), font=self.font)
    
    def calculate_cone(self):
        """计算圆锥体积"""
        try:
            radius = float(self.cone_radius_var.get())
            height = float(self.cone_height_var.get())
            volume = (1/3) * math.pi * radius**2 * height
            self.show_result(f"圆锥体积: {volume:.2f} 立方单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    
    def calculate_hemisphere(self):
        """计算半球体积"""
        try:
            radius = float(self.hemisphere_radius_var.get())
            volume = (2/3) * math.pi * radius**3
            self.show_result(f"半球体积: {volume:.2f} 立方单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    
    def calculate_torus(self):
        """计算圆环体积"""
        try:
            major_radius = float(self.major_radius_var.get())
            minor_radius = float(self.minor_radius_var.get())
            
            if minor_radius >= major_radius:
                raise ValueError("小半径必须小于大半径")
                
            volume = 2 * math.pi**2 * major_radius * minor_radius**2
            self.show_result(f"圆环体积: {volume:.2f} 立方单位")
        except ValueError as e:
            messagebox.showerror("错误", str(e), font=self.font)
    
    def show_result(self, text):
        """显示计算结果"""
        self.result_var.set(text)
        
    def show_shape_ui(self, shape_name):
        """显示选中的形状计算界面"""
        # 清除之前的计算界面
        for widget in self.calc_frame.winfo_children():
            widget.destroy()
        
        # 根据形状名称创建对应的UI
        if shape_name == "长方体":
            self.setup_cuboid_ui(self.calc_frame)
        elif shape_name == "圆柱体":
            self.setup_cylinder_ui(self.calc_frame)
        elif shape_name == "球体":
            self.setup_sphere_ui(self.calc_frame)
        elif shape_name == "金字塔":
            self.setup_pyramid_ui(self.calc_frame)
        elif shape_name == "直圆柱":
            self.setup_right_cylinder_ui(self.calc_frame)
        elif shape_name == "立方体":
            self.setup_cube_ui(self.calc_frame)
        elif shape_name == "长方形水箱":
            self.setup_tank_ui(self.calc_frame)
        elif shape_name == "管":
            self.setup_tube_ui(self.calc_frame)
        elif shape_name == "胶囊":
            self.setup_capsule_ui(self.calc_frame)
        elif shape_name == "正四棱锥":
            self.setup_pyramid_ui(self.calc_frame)
        elif shape_name == "圆台":
            self.setup_frustum_ui(self.calc_frame)
        elif shape_name == "圆锥":
            self.setup_cone_ui(self.calc_frame)
        elif shape_name == "半球":
            self.setup_hemisphere_ui(self.calc_frame)
        elif shape_name == "圆环":
            self.setup_torus_ui(self.calc_frame)
        
        self.current_shape = shape_name

if __name__ == "__main__":
    root = Tk()
    app = VolumeCalculator(root)
    root.mainloop()