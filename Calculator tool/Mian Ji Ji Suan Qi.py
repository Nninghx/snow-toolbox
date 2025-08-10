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

class AreaCalculator:
    def __init__(self, master):
        self.master = master
        master.title("面积计算器")
        
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
        Label(self.main_frame, text="面积计算器", font=(font_family, 16, 'bold')).pack(pady=10)
        
        # 几何图形选择按钮框架
        self.shapes_frame = ttk.Frame(self.main_frame)
        self.shapes_frame.pack(fill='x', pady=5)
        # 创建形状选择按钮
        shapes = [
            "圆面积", "长方形面积", "椭圆面积", "梯形面积", "平行四边形面积", 
            "菱形面积", "等腰三角形面积", "风筝形面积", "圆台面积", "球体表面积",
            "立方体表面积", "土地面积", "四边形面积", "正八边形面积", "正多边形面积",
            "圆环面积", "圆柱体表面积", "三角棱柱表面积", "圆锥侧面积", "圆锥底面积",
            "金字塔表面积", "金字塔侧面积", "正方形面积", "三角形面积"
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
        self.show_shape_ui("圆面积")
    
    def setup_circle_ui(self, parent):
        """设置圆面积计算界面"""
        Label(parent, text="半径:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.radius_var = StringVar()
        Entry(parent, textvariable=self.radius_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Button(parent, text="计算面积", command=self.calculate_circle, font=self.font).grid(row=1, column=0, columnspan=2, pady=10)
    
    def setup_rectangle_ui(self, parent):
        """设置长方形面积计算界面"""
        Label(parent, text="长度:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.length_var = StringVar()
        Entry(parent, textvariable=self.length_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="宽度:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.width_var = StringVar()
        Entry(parent, textvariable=self.width_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Button(parent, text="计算面积", command=self.calculate_rectangle, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
    
    def setup_ellipse_ui(self, parent):
        """设置椭圆面积面积面积计算界面"""
        Label(parent, text="长半轴:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.major_axis_var = StringVar()
        Entry(parent, textvariable=self.major_axis_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="短半轴:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.minor_axis_var = StringVar()
        Entry(parent, textvariable=self.minor_axis_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Button(parent, text="计算面积", command=self.calculate_ellipse, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
    
    def calculate_circle(self):
        """计算圆面积"""
        try:
            radius = float(self.radius_var.get())
            area = math.pi * radius ** 2
            self.show_result(f"圆面积: {area:.2f} 平方单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    
    def calculate_rectangle(self):
        """计算长方形面积"""
        try:
            length = float(self.length_var.get())
            width = float(self.width_var.get())
            area = length * width
            self.show_result(f"长方形面积: {area:.2f} 平方单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    
    def calculate_ellipse(self):
        """计算椭圆面积面积面积"""
        try:
            major_axis = float(self.major_axis_var.get())
            minor_axis = float(self.minor_axis_var.get())
            area = math.pi * major_axis * minor_axis
            self.show_result(f"椭圆面积: {area:.2f} 平方单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    
    def show_result(self, text):
        """显示计算结果"""
        self.result_var.set(text)
    
    def setup_trapezoid_ui(self, parent):
        """设置梯形面积计算界面"""
        Label(parent, text="上底:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.top_base_var = StringVar()
        Entry(parent, textvariable=self.top_base_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="下底:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.bottom_base_var = StringVar()
        Entry(parent, textvariable=self.bottom_base_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Label(parent, text="高度:", font=self.font).grid(row=2, column=0, padx=10, pady=5)
        self.trapezoid_height_var = StringVar()
        Entry(parent, textvariable=self.trapezoid_height_var, font=self.font).grid(row=2, column=1, padx=10, pady=5)
        
        Button(parent, text="计算面积", command=self.calculate_trapezoid, font=self.font).grid(row=3, column=0, columnspan=2, pady=10)
    def setup_parallelogram_ui(self, parent):
        """设置平行四边形面积计算界面"""
        Label(parent, text="底边:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.parallelogram_base_var = StringVar()
        Entry(parent, textvariable=self.parallelogram_base_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="高度:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.parallelogram_height_var = StringVar()
        Entry(parent, textvariable=self.parallelogram_height_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Button(parent, text="计算面积", command=self.calculate_parallelogram, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
    
    def setup_rhombus_ui(self, parent):
        """设置菱形面积计算界面"""
        Label(parent, text="对角线1:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.diagonal1_var = StringVar()
        Entry(parent, textvariable=self.diagonal1_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="对角线2:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.diagonal2_var = StringVar()
        Entry(parent, textvariable=self.diagonal2_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Button(parent, text="计算面积", command=self.calculate_rhombus, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
    
    def setup_isosceles_triangle_ui(self, parent):
        """设置等腰三角形面积计算界面"""
        Label(parent, text="底边:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.triangle_base_var = StringVar()
        Entry(parent, textvariable=self.triangle_base_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="高度:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.triangle_height_var = StringVar()
        Entry(parent, textvariable=self.triangle_height_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Button(parent, text="计算面积", command=self.calculate_isosceles_triangle, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
    
    def setup_kite_ui(self, parent):
        """设置风筝面积计算界面"""
        Label(parent, text="对角线1:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.kite_diagonal1_var = StringVar()
        Entry(parent, textvariable=self.kite_diagonal1_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="对角线2:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.kite_diagonal2_var = StringVar()
        Entry(parent, textvariable=self.kite_diagonal2_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Button(parent, text="计算面积", command=self.calculate_kite, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
    
    def setup_frustum_area_ui(self, parent):
        """设置圆台面积计算界面"""
        Label(parent, text="上底半径:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.frustum_top_radius_var = StringVar()
        Entry(parent, textvariable=self.frustum_top_radius_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="下底半径:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.frustum_bottom_radius_var = StringVar()
        Entry(parent, textvariable=self.frustum_bottom_radius_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Label(parent, text="高度:", font=self.font).grid(row=2, column=0, padx=10, pady=5)
        self.frustum_height_var = StringVar()
        Entry(parent, textvariable=self.frustum_height_var, font=self.font).grid(row=2, column=1, padx=10, pady=5)
        
        Button(parent, text="计算面积", command=self.calculate_frustum_area, font=self.font).grid(row=3, column=0, columnspan=2, pady=10)
    def setup_sphere_surface_ui(self, parent):
        """设置球体表面积计算界面"""
        Label(parent, text="半径:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.sphere_radius_var = StringVar()
        Entry(parent, textvariable=self.sphere_radius_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Button(parent, text="计算面积", command=self.calculate_sphere_surface, font=self.font).grid(row=1, column=0, columnspan=2, pady=10)
    
    def setup_cube_surface_ui(self, parent):
        """设置立方体表面积计算界面"""
        Label(parent, text="边长:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.cube_side_var = StringVar()
        Entry(parent, textvariable=self.cube_side_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Button(parent, text="计算面积", command=self.calculate_cube_surface, font=self.font).grid(row=1, column=0, columnspan=2, pady=10)
    
    def setup_land_area_ui(self, parent):
        """设置土地面积计算界面"""
        Label(parent, text="长度(米):", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.land_length_var = StringVar()
        Entry(parent, textvariable=self.land_length_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="宽度(米):", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.land_width_var = StringVar()
        Entry(parent, textvariable=self.land_width_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Button(parent, text="计算面积", command=self.calculate_land_area, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
    
    def calculate_trapezoid(self):
        """计算梯形面积"""
        try:
            top = float(self.top_base_var.get())
            bottom = float(self.bottom_base_var.get())
            height = float(self.trapezoid_height_var.get())
            area = (top + bottom) * height / 2
            self.show_result(f"梯形面积: {area:.2f} 平方单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    
    def calculate_parallelogram(self):
        """计算平行四边形面积"""
        try:
            base = float(self.parallelogram_base_var.get())
            height = float(self.parallelogram_height_var.get())
            area = base * height
            self.show_result(f"平行四边形面积: {area:.2f} 平方单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    
    def calculate_rhombus(self):
        """计算菱形面积"""
        try:
            d1 = float(self.diagonal1_var.get())
            d2 = float(self.diagonal2_var.get())
            area = d1 * d2 / 2
            self.show_result(f"菱形面积: {area:.2f} 平方单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    
    def calculate_isosceles_triangle(self):
        """计算等腰三角形面积"""
        try:
            base = float(self.triangle_base_var.get())
            height = float(self.triangle_height_var.get())
            area = base * height / 2
            self.show_result(f"等腰三角形面积: {area:.2f} 平方单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    
    def calculate_kite(self):
        """计算风筝形面积"""
        try:
            d1 = float(self.kite_diagonal1_var.get())
            d2 = float(self.kite_diagonal2_var.get())
            area = d1 * d2 / 2
            self.show_result(f"风筝形面积: {area:.2f} 平方单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    
    def calculate_frustum_area(self):
        """计算圆台面积"""
        try:
            r1 = float(self.frustum_top_radius_var.get())
            r2 = float(self.frustum_bottom_radius_var.get())
            h = float(self.frustum_height_var.get())
            l = math.sqrt((r2 - r1)**2 + h**2)  # 斜高
            lateral_area = math.pi * (r1 + r2) * l
            base_area = math.pi * (r1**2 + r2**2)
            total_area = lateral_area + base_area
            self.show_result(f"圆台表面积: {total_area:.2f} 平方单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    
    def calculate_sphere_surface(self):
        """计算球体表面积"""
        try:
            r = float(self.sphere_radius_var.get())
            area = 4 * math.pi * r**2
            self.show_result(f"球体表面积: {area:.2f} 平方单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    
    def calculate_cube_surface(self):
        """计算立方体表面积"""
        try:
            side = float(self.cube_side_var.get())
            area = 6 * side**2
            self.show_result(f"立方体表面积: {area:.2f} 平方单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    
    def calculate_land_area(self):
        """计算土地面积"""
        try:
            length = float(self.land_length_var.get())
            width = float(self.land_width_var.get())
            area_m2 = length * width
            area_mu = area_m2 / 666.67  # 1亩≈666.67平方米
            self.show_result(f"土地面积: {area_m2:.2f} 平方米 ({area_mu:.4f} 亩)")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    def setup_octagon_ui(self, parent):
        """设置正八边形面积计算界面"""
        Label(parent, text="边长:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.octagon_side_var = StringVar()
        Entry(parent, textvariable=self.octagon_side_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Button(parent, text="计算面积", command=self.calculate_octagon, font=self.font).grid(row=1, column=0, columnspan=2, pady=10)
    
    def calculate_octagon(self):
        """计算正八边形面积"""
        try:
            side = float(self.octagon_side_var.get())
            area = 2 * (1 + math.sqrt(2)) * side**2
            self.show_result(f"正八边形面积: {area:.2f} 平方单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    
    def setup_quadrilateral_ui(self, parent):
        """设置四边形面积计算界面"""
        Label(parent, text="边a:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.quad_side_a_var = StringVar()
        Entry(parent, textvariable=self.quad_side_a_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="边b:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.quad_side_b_var = StringVar()
        Entry(parent, textvariable=self.quad_side_b_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Label(parent, text="边c:", font=self.font).grid(row=2, column=0, padx=10, pady=5)
        self.quad_side_c_var = StringVar()
        Entry(parent, textvariable=self.quad_side_c_var, font=self.font).grid(row=2, column=1, padx=10, pady=5)
        
        Label(parent, text="边d:", font=self.font).grid(row=3, column=0, padx=10, pady=5)
        self.quad_side_d_var = StringVar()
        Entry(parent, textvariable=self.quad_side_d_var, font=self.font).grid(row=3, column=1, padx=10, pady=5)
        
        Button(parent, text="计算面积", command=self.calculate_quadrilateral, font=self.font).grid(row=4, column=0, columnspan=2, pady=10)
    
    def calculate_quadrilateral(self):
        """计算四边形面积(基于边长)"""
        try:
            a = float(self.quad_side_a_var.get())
            b = float(self.quad_side_b_var.get())
            c = float(self.quad_side_c_var.get())
            d = float(self.quad_side_d_var.get())
            s = (a + b + c + d) / 2
            area = math.sqrt((s - a) * (s - b) * (s - c) * (s - d))
            self.show_result(f"四边形面积: {area:.2f} 平方单位")
        except ValueError as e:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    
    def calculate_octagon(self):
        """计算正八边形面积"""
        try:
            side = float(self.octagon_side_var.get())
            area = 2 * (1 + math.sqrt(2)) * side**2
            self.show_result(f"正八边形面积: {area:.2f} 平方单位")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值", font=self.font)
    def setup_regular_polygon_ui(self, parent):
        """设置正多边形面积计算界面"""
        Label(parent, text="边数:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.polygon_sides_var = StringVar()
        Entry(parent, textvariable=self.polygon_sides_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="边长:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.polygon_side_length_var = StringVar()
        Entry(parent, textvariable=self.polygon_side_length_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Button(parent, text="计算面积", command=self.calculate_regular_polygon, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
    
    def setup_annulus_ui(self, parent):
        """设置圆环面积计算界面"""
        Label(parent, text="外半径:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.annulus_outer_var = StringVar()
        Entry(parent, textvariable=self.annulus_outer_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="内半径:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.annulus_inner_var = StringVar()
        Entry(parent, textvariable=self.annulus_inner_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Button(parent, text="计算面积", command=self.calculate_annulus, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
    
    def setup_cylinder_ui(self, parent):
        """设置圆柱体表面积计算界面"""
        Label(parent, text="半径:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.cylinder_radius_var = StringVar()
        Entry(parent, textvariable=self.cylinder_radius_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="高度:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.cylinder_height_var = StringVar()
        Entry(parent, textvariable=self.cylinder_height_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Button(parent, text="计算表面积", command=self.calculate_cylinder, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
    
    def calculate_regular_polygon(self):
        """计算正多边形面积"""
        try:
            n = int(self.polygon_sides_var.get())
            s = float(self.polygon_side_length_var.get())
            if n < 3:
                raise ValueError("边数必须大于等于3")
            area = (n * s**2) / (4 * math.tan(math.pi / n))
            self.show_result(f"正{n}边形面积: {area:.2f} 平方单位")
        except ValueError as e:
            messagebox.showerror("错误", str(e) if str(e) else "请输入有效的数值", font=self.font)
    
    def calculate_annulus(self):
        """计算圆环面积"""
        try:
            R = float(self.annulus_outer_var.get())
            r = float(self.annulus_inner_var.get())
            if R <= r:
                raise ValueError("外半径必须大于内半径")
            area = math.pi * (R**2 - r**2)
            self.show_result(f"圆环面积: {area:.2f} 平方单位")
        except ValueError as e:
            messagebox.showerror("错误", str(e) if str(e) else "请输入有效的数值", font=self.font)
        self.cylinder_height_var = StringVar()
        Entry(parent, textvariable=self.cylinder_height_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Button(parent, text="计算表面积", command=self.calculate_cylinder, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
    
    def setup_triangular_prism_ui(self, parent):
        """设置三角棱柱表面积计算界面"""
        Label(parent, text="底面边长a:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.prism_side_a_var = StringVar()
        Entry(parent, textvariable=self.prism_side_a_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="底面边长b:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.prism_side_b_var = StringVar()
        Entry(parent, textvariable=self.prism_side_b_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Label(parent, text="底面边长c:", font=self.font).grid(row=2, column=0, padx=10, pady=5)
        self.prism_side_c_var = StringVar()
        Entry(parent, textvariable=self.prism_side_c_var, font=self.font).grid(row=2, column=1, padx=10, pady=5)
        
        Label(parent, text="高度:", font=self.font).grid(row=3, column=0, padx=10, pady=5)
        self.prism_height_var = StringVar()
        Entry(parent, textvariable=self.prism_height_var, font=self.font).grid(row=3, column=1, padx=10, pady=5)
        
        Button(parent, text="计算表面积", command=self.calculate_triangular_prism, font=self.font).grid(row=4, column=0, columnspan=2, pady=10)
    
    def calculate_cylinder(self):
        """计算圆柱体表面积"""
        try:
            radius = float(self.cylinder_radius_var.get())
            height = float(self.cylinder_height_var.get())
            base_area = math.pi * radius**2
            lateral_area = 2 * math.pi * radius * height
            total_area = 2 * base_area + lateral_area
            self.show_result(f"圆柱体表面积: {total_area:.2f} 平方单位")
        except ValueError as e:
            messagebox.showerror("错误", str(e) if str(e) else "请输入有效的数值", font=self.font)
    
    def calculate_triangular_prism(self):
        """计算三角棱柱表面积"""
        try:
            a = float(self.prism_side_a_var.get())
            b = float(self.prism_side_b_var.get())
            c = float(self.prism_side_c_var.get())
            h = float(self.prism_height_var.get())
            
            # 计算底面积(海伦公式)
            s = (a + b + c) / 2
            base_area = math.sqrt(s * (s - a) * (s - b) * (s - c))
            
            # 计算侧面积
            lateral_area = (a + b + c) * h
            
            total_area = 2 * base_area + lateral_area
            self.show_result(f"三角棱柱表面积: {total_area:.2f} 平方单位")
        except ValueError as e:
            messagebox.showerror("错误", str(e) if str(e) else "请输入有效的数值", font=self.font)
    def setup_cone_lateral_ui(self, parent):
        """设置圆锥侧面积计算界面"""
        Label(parent, text="底面半径:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.cone_lateral_radius_var = StringVar()
        Entry(parent, textvariable=self.cone_lateral_radius_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="高度:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.cone_lateral_height_var = StringVar()
        Entry(parent, textvariable=self.cone_lateral_height_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Button(parent, text="计算侧面积", command=self.calculate_cone_lateral, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
    def setup_cone_base_ui(self, parent):
        """设置圆锥底面积计算界面"""
        Label(parent, text="底面半径:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.cone_base_radius_var = StringVar()
        Entry(parent, textvariable=self.cone_base_radius_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Button(parent, text="计算底面积", command=self.calculate_cone_base, font=self.font).grid(row=1, column=0, columnspan=2, pady=10)
    def setup_pyramid_surface_ui(self, parent):
        """设置金字塔表面积计算界面"""
        Label(parent, text="长度:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.pyramid_length_var = StringVar()
        Entry(parent, textvariable=self.pyramid_length_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="宽度:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.pyramid_width_var = StringVar()
        Entry(parent, textvariable=self.pyramid_width_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Label(parent, text="高度:", font=self.font).grid(row=2, column=0, padx=10, pady=5)
        self.pyramid_height_var = StringVar()
        Entry(parent, textvariable=self.pyramid_height_var, font=self.font).grid(row=2, column=1, padx=10, pady=5)
        
        Button(parent, text="计算表面积", command=self.calculate_pyramid_surface, font=self.font).grid(row=3, column=0, columnspan=2, pady=10)
    
    def setup_pyramid_lateral_ui(self, parent):
        """设置金字塔侧面积计算界面"""
        Label(parent, text="长度:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.pyramid_length_var = StringVar()
        Entry(parent, textvariable=self.pyramid_length_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="宽度:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.pyramid_width_var = StringVar()
        Entry(parent, textvariable=self.pyramid_width_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Label(parent, text="高度:", font=self.font).grid(row=2, column=0, padx=10, pady=5)
        self.pyramid_height_var = StringVar()
        Entry(parent, textvariable=self.pyramid_height_var, font=self.font).grid(row=2, column=1, padx=10, pady=5)
        
        Button(parent, text="计算侧面积", command=self.calculate_pyramid_lateral, font=self.font).grid(row=3, column=0, columnspan=2, pady=10)
    
    def calculate_cone_lateral(self):
        """计算圆锥侧面积"""
        try:
            cone_radius = float(self.cone_lateral_radius_var.get())
            height = float(self.cone_lateral_height_var.get())
            slant_height = math.sqrt(cone_radius**2 + height**2)
            area = math.pi * cone_radius * slant_height
            self.show_result(f"圆锥侧面积: {area:.2f} 平方单位")
        except ValueError as e:
            messagebox.showerror("错误", str(e) if str(e) else "请输入有效的数值", font=self.font)
    
    def calculate_cone_base(self):
        """计算圆锥底面积"""
        try:
            r = float(self.cone_base_radius_var.get())
            area = math.pi * r**2
            self.show_result(f"圆锥底面积: {area:.2f} 平方单位")
        except ValueError as e:
            messagebox.showerror("错误", str(e) if str(e) else "请输入有效的数值", font=self.font)
    
    def calculate_pyramid_surface(self):
        """计算金字塔表面积"""
        try:
            l = float(self.pyramid_length_var.get())  # 底面长度
            w = float(self.pyramid_width_var.get())  # 底面宽度
            h = float(self.pyramid_height_var.get())  # 高度
            
            # 计算表面积公式: A = lw + l√(h² + w²/4) + w√(h² + l²/4)
            base_area = l * w
            term1 = l * math.sqrt(h**2 + (w**2)/4)
            term2 = w * math.sqrt(h**2 + (l**2)/4)
            total_area = base_area + term1 + term2
            
            self.show_result(f"金字塔表面积: {total_area:.2f} 平方单位")
        except ValueError as e:
            messagebox.showerror("错误", str(e) if str(e) else "请输入有效的数值", font=self.font)
    
    def calculate_pyramid_lateral(self):
        """计算金字塔侧面积"""
        try:
            l = float(self.pyramid_length_var.get())  # 底面长度
            w = float(self.pyramid_width_var.get())  # 底面宽度
            h = float(self.pyramid_height_var.get())  # 高度
            
            # 计算侧面积公式: A = l * √(h² + w²/4) + w * √(h² + l²/4)
            term1 = l * math.sqrt(h**2 + (w**2)/4)
            term2 = w * math.sqrt(h**2 + (l**2)/4)
            area = term1 + term2
            
            self.show_result(f"金字塔侧面积: {area:.2f} 平方单位")
        except ValueError as e:
            messagebox.showerror("错误", str(e) if str(e) else "请输入有效的数值", font=self.font)
    def setup_square_ui(self, parent):
        """设置正方形面积计算界面"""
        Label(parent, text="边长:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.square_side_var = StringVar()
        Entry(parent, textvariable=self.square_side_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Button(parent, text="计算面积", command=self.calculate_square, font=self.font).grid(row=1, column=0, columnspan=2, pady=10)
    
    def setup_triangle_ui(self, parent):
        """设置三角形面积计算界面"""
        Label(parent, text="底边:", font=self.font).grid(row=0, column=0, padx=10, pady=5)
        self.triangle_base_var = StringVar()
        Entry(parent, textvariable=self.triangle_base_var, font=self.font).grid(row=0, column=1, padx=10, pady=5)
        
        Label(parent, text="高度:", font=self.font).grid(row=1, column=0, padx=10, pady=5)
        self.triangle_height_var = StringVar()
        Entry(parent, textvariable=self.triangle_height_var, font=self.font).grid(row=1, column=1, padx=10, pady=5)
        
        Button(parent, text="计算面积", command=self.calculate_triangle, font=self.font).grid(row=2, column=0, columnspan=2, pady=10)
    
    def calculate_square(self):
        """计算正方形面积"""
        try:
            side = float(self.square_side_var.get())
            area = side ** 2
            self.show_result(f"正方形面积: {area:.2f} 平方单位")
        except ValueError as e:
            messagebox.showerror("错误", str(e) if str(e) else "请输入有效的数值", font=self.font)
    
    def calculate_triangle(self):
        """计算三角形面积"""
        try:
            base = float(self.triangle_base_var.get())
            height = float(self.triangle_height_var.get())
            area = base * height / 2
            self.show_result(f"三角形面积: {area:.2f} 平方单位")
        except ValueError as e:
            messagebox.showerror("错误", str(e) if str(e) else "请输入有效的数值", font=self.font)
    
    def show_shape_ui(self, shape_name):
        """显示选中的形状计算界面"""
        # 清除之前的计算界面
        for widget in self.calc_frame.winfo_children():
            widget.destroy()
        
        # 根据形状名称创建对应的UI
        if shape_name == "圆面积":
            self.setup_circle_ui(self.calc_frame)
        elif shape_name == "长方形面积":
            self.setup_rectangle_ui(self.calc_frame)
        elif shape_name == "椭圆面积":
            self.setup_ellipse_ui(self.calc_frame)
        elif shape_name == "梯形面积":
            self.setup_trapezoid_ui(self.calc_frame)
        elif shape_name == "平行四边形面积":
            self.setup_parallelogram_ui(self.calc_frame)
        elif shape_name == "菱形面积":
            self.setup_rhombus_ui(self.calc_frame)
        elif shape_name == "等腰三角形面积":
            self.setup_isosceles_triangle_ui(self.calc_frame)
        elif shape_name == "风筝形面积":
            self.setup_kite_ui(self.calc_frame)
        elif shape_name == "圆台面积":
            self.setup_frustum_area_ui(self.calc_frame)
        elif shape_name == "球体表面积":
            self.setup_sphere_surface_ui(self.calc_frame)
        elif shape_name == "立方体表面积":
            self.setup_cube_surface_ui(self.calc_frame)
        elif shape_name == "土地面积":
            self.setup_land_area_ui(self.calc_frame)
        elif shape_name == "四边形面积":
            self.setup_quadrilateral_ui(self.calc_frame)
        elif shape_name == "正八边形面积":
            self.setup_octagon_ui(self.calc_frame)
        elif shape_name == "正多边形面积":
            self.setup_regular_polygon_ui(self.calc_frame)
        elif shape_name == "圆环面积":
            self.setup_annulus_ui(self.calc_frame)
        elif shape_name == "圆柱体表面积":
            self.setup_cylinder_ui(self.calc_frame)
        elif shape_name == "三角棱柱表面积":
            self.setup_triangular_prism_ui(self.calc_frame)
        elif shape_name == "圆锥侧面积":
            self.setup_cone_lateral_ui(self.calc_frame)
        elif shape_name == "圆锥底面积":
            self.setup_cone_base_ui(self.calc_frame)
        elif shape_name == "金字塔表面积":
            self.setup_pyramid_surface_ui(self.calc_frame)
        elif shape_name == "金字塔侧面积":
            self.setup_pyramid_lateral_ui(self.calc_frame)
        elif shape_name == "正方形面积":
            self.setup_square_ui(self.calc_frame)
        elif shape_name == "三角形面积":
            self.setup_triangle_ui(self.calc_frame)
        
        self.current_shape = shape_name

if __name__ == "__main__":
    root = Tk()
    app = AreaCalculator(root)
    root.mainloop()