import json
import os
import math
import subprocess
from pathlib import Path
from tkinter import Tk, Label, Entry, Button, StringVar, messagebox, ttk, OptionMenu
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

class TrigonometryCalculator:
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
        
        master.title("三角函数计算器")
        
        # 设置窗口图标
        self.set_window_icon(master)
        
        # 加载字体配置
        self.load_font()
        
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
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.trigonometry_calculator")
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
                self.icon_image = tk.PhotoImage(file=str(icon_png_path))
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

if __name__ == "__main__":
    root = Tk()
    app = TrigonometryCalculator(root)
    root.mainloop()
