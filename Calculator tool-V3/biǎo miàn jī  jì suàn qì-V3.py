import json
import os
import math
import subprocess
from pathlib import Path
from tkinter import Tk, Label, Entry, Button, StringVar, messagebox, ttk, PhotoImage
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from fontTools.ttLib import TTFont
    FONTTOOLS_AVAILABLE = True
except ImportError:
    FONTTOOLS_AVAILABLE = False

class SurfaceAreaCalculator:
    def __init__(self, master):
        self.master = master
        
        # 首先检查授权
        if not self.check_license():
            messagebox.showerror(
                "错误", 
                "缺少授权！无法使用！请先获取授权！"
            )
            master.destroy()
            return
        
        master.title("表面积计算器")
        
        # 设置窗口图标
        self.set_window_icon(master)
        
        # 加载字体配置
        self.load_font()
        
        # 创建Notebook选项卡
        self.notebook = ttk.Notebook(master)
        self.notebook.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        
        # 球体表面积计算器
        self.sphere_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.sphere_frame, text="球体")
        
        Label(self.sphere_frame, text="半径:").grid(row=0, column=0, padx=10, pady=5)
        self.sphere_radius = StringVar()
        Entry(self.sphere_frame, textvariable=self.sphere_radius).grid(row=0, column=1, padx=10, pady=5)
        
        Button(self.sphere_frame, text="计算表面积", command=self.calculate_sphere).grid(row=1, column=0, columnspan=2, pady=10)
        
        # 立方体表面积计算器
        self.cube_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.cube_frame, text="立方体")
        
        Label(self.cube_frame, text="边长:").grid(row=0, column=0, padx=10, pady=5)
        self.cube_side = StringVar()
        Entry(self.cube_frame, textvariable=self.cube_side).grid(row=0, column=1, padx=10, pady=5)
        
        Button(self.cube_frame, text="计算表面积", command=self.calculate_cube).grid(row=1, column=0, columnspan=2, pady=10)
        
        # 三角棱柱表面积计算器
        self.triangular_prism_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.triangular_prism_frame, text="三角棱柱")
        
        # 棱柱类型选择
        Label(self.triangular_prism_frame, text="棱柱类型:").grid(row=0, column=0, padx=10, pady=5)
        self.prism_type = StringVar(value="equilateral")
        ttk.Radiobutton(self.triangular_prism_frame, text="等边三角形", variable=self.prism_type, 
                       value="equilateral").grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(self.triangular_prism_frame, text="直角三角形", variable=self.prism_type, 
                       value="right").grid(row=0, column=2, sticky="w")
        
        # 参数输入
        Label(self.triangular_prism_frame, text="底边长度(b):").grid(row=1, column=0, padx=10, pady=5)
        self.prism_base = StringVar()
        Entry(self.triangular_prism_frame, textvariable=self.prism_base).grid(row=1, column=1, padx=10, pady=5)
        
        Label(self.triangular_prism_frame, text="三角形高度(h):").grid(row=2, column=0, padx=10, pady=5)
        self.prism_triangle_height = StringVar()
        Entry(self.triangular_prism_frame, textvariable=self.prism_triangle_height).grid(row=2, column=1, padx=10, pady=5)
        
        Label(self.triangular_prism_frame, text="棱柱长度(l):").grid(row=3, column=0, padx=10, pady=5)
        self.prism_length = StringVar()
        Entry(self.triangular_prism_frame, textvariable=self.prism_length).grid(row=3, column=1, padx=10, pady=5)
        
        Button(self.triangular_prism_frame, text="计算表面积", command=self.calculate_triangular_prism).grid(row=4, column=0, columnspan=3, pady=10)
        
        # 圆锥表面积计算器
        self.cone_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.cone_frame, text="圆锥")
        
        # 输入方式选择
        Label(self.cone_frame, text="输入方式:").grid(row=0, column=0, padx=10, pady=5)
        self.cone_input_type = StringVar(value="slant")
        ttk.Radiobutton(self.cone_frame, text="母线长度", variable=self.cone_input_type, 
                       value="slant").grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(self.cone_frame, text="高度", variable=self.cone_input_type, 
                       value="height").grid(row=0, column=2, sticky="w")
        
        # 参数输入
        Label(self.cone_frame, text="底面半径(r):").grid(row=1, column=0, padx=10, pady=5)
        self.cone_radius = StringVar()
        Entry(self.cone_frame, textvariable=self.cone_radius).grid(row=1, column=1, padx=10, pady=5)
        
        Label(self.cone_frame, text="母线长度/高度:").grid(row=2, column=0, padx=10, pady=5)
        self.cone_slant_or_height = StringVar()
        Entry(self.cone_frame, textvariable=self.cone_slant_or_height).grid(row=2, column=1, padx=10, pady=5)
        
        Button(self.cone_frame, text="计算表面积", command=self.calculate_cone).grid(row=3, column=0, columnspan=3, pady=10)
        Button(self.cone_frame, text="计算侧面积", command=self.calculate_cone_lateral).grid(row=4, column=0, columnspan=3, pady=10)
        
        # 金字塔表面积计算器
        self.pyramid_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.pyramid_frame, text="金字塔")
        
        Label(self.pyramid_frame, text="底面长度:").grid(row=0, column=0, padx=10, pady=5)
        self.pyramid_length = StringVar()
        Entry(self.pyramid_frame, textvariable=self.pyramid_length).grid(row=0, column=1, padx=10, pady=5)
        
        Label(self.pyramid_frame, text="底面宽度:").grid(row=1, column=0, padx=10, pady=5)
        self.pyramid_width = StringVar()
        Entry(self.pyramid_frame, textvariable=self.pyramid_width).grid(row=1, column=1, padx=10, pady=5)
        
        Label(self.pyramid_frame, text="高度:").grid(row=2, column=0, padx=10, pady=5)
        self.pyramid_height = StringVar()
        Entry(self.pyramid_frame, textvariable=self.pyramid_height).grid(row=2, column=1, padx=10, pady=5)
        
        Button(self.pyramid_frame, text="计算表面积", command=self.calculate_pyramid).grid(row=3, column=0, columnspan=2, pady=10)
        Button(self.pyramid_frame, text="计算侧面积", command=self.calculate_pyramid_lateral).grid(row=4, column=0, columnspan=2, pady=10)
        
        # 结果展示
        self.result_frame = ttk.Frame(master)
        self.result_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        self.result_var = StringVar()
        self.result_label = Label(self.result_frame, textvariable=self.result_var)
        self.result_label.grid(row=0, column=0, padx=10)

    def check_license(self):
        """检查开源协议文档是否存在并验证完整性"""
        # 如果通过主程序启动（环境变量已设置），则跳过授权验证
        if os.environ.get('MAIN_APP_AUTHORIZED') == '1':
            return True
        
        try:
            # 验证授权
            PROJECT_ROOT = Path(__file__).resolve().parent.parent
            CORE_DIR = PROJECT_ROOT / "Core"
            license_exe_path = CORE_DIR / "LICENSE.exe"
            if license_exe_path.exists():
                result = subprocess.run(
                    [str(license_exe_path), '--quiet'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.returncode == 0
        except Exception as e:
            print(f"许可证验证异常: {e}")
            return False

    def set_window_icon(self, master):
        """设置应用程序窗口图标"""
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        IMAGE_DIR = PROJECT_ROOT / "Image"
        
        icon_ico_path = IMAGE_DIR / "icon.ico"
        icon_png_path = IMAGE_DIR / "icon.png"

        # Windows系统设置应用ID
        if os.name == 'nt':
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.surface_area_calculator")
            except Exception:
                pass

        # 尝试设置ICO图标
        if icon_ico_path.exists():
            try:
                master.iconbitmap(default=str(icon_ico_path))
            except Exception:
                try:
                    master.iconbitmap(str(icon_ico_path))
                except Exception:
                    pass

        # 尝试设置PNG图标
        if hasattr(master, "iconphoto") and icon_png_path.exists():
            try:
                self.icon_image = PhotoImage(file=str(icon_png_path))
                master.iconphoto(True, self.icon_image)
            except Exception:
                pass

    def load_font(self):
        """从配置文件加载字体设置"""
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        IMAGE_DIR = PROJECT_ROOT / "Image"
        
        font_path = IMAGE_DIR / "AlibabaPuHuiTi-3-55-RegularL3.ttf"
        
        if not font_path.exists():
            messagebox.showerror("错误", f"找不到字体文件：{font_path}")
            self.master.destroy()
            return
        
        # 使用 fonttools 获取字体名称
        tt = TTFont(str(font_path))
        font_name = None
        for record in tt['name'].names:
            if record.nameID == 1:  # Font Family
                font_name = record.toUnicode()
                break
        if not font_name:
            raise RuntimeError(f"无法从字体文件获取字体名称：{font_path}")
        tt.close()
        
        # 使用 Windows API 注册字体
        if os.name == 'nt':
            import ctypes
            GDI32 = ctypes.windll.gdi32
            font_path_str = str(font_path).encode('utf-16-le') + b'\x00'
            GDI32.AddFontResourceW(font_path_str)
            print(f"成功加载自定义字体: {font_path}")
        
        from tkinter import font as tkfont
        self.current_font = (font_name, 12)
        self.master.option_add("*Font", self.current_font)
    
    def calculate_sphere(self):
        try:
            radius = float(self.sphere_radius.get())
            area = 4 * math.pi * radius ** 2
            self.result_var.set(f"球体表面积: {area:.2f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
    
    def calculate_cube(self):
        try:
            side = float(self.cube_side.get())
            area = 6 * side ** 2
            self.result_var.set(f"立方体表面积: {area:.2f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
    
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
            messagebox.showerror("错误", "请输入有效的数字")
    
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
            messagebox.showerror("错误", "请输入有效的数字")
    
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
            messagebox.showerror("错误", "请输入有效的数字")
    
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
            messagebox.showerror("错误", "请输入有效的数字")
    
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
            messagebox.showerror("错误", "请输入有效的数字")

if __name__ == "__main__":
    root = Tk()
    app = SurfaceAreaCalculator(root)
    root.mainloop()