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

class PerimeterCalculator:
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
        
        master.title("周长计算器")
        
        # 设置窗口图标
        self.set_window_icon(master)
        
        # 加载字体配置
        self.load_font()
        
        # 创建Notebook选项卡
        self.notebook = ttk.Notebook(master)
        self.notebook.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        
        # 长方形周长计算器
        self.rectangle_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.rectangle_frame, text="长方形")
        
        Label(self.rectangle_frame, text="长度:").grid(row=0, column=0, padx=10, pady=5)
        self.rect_length = StringVar()
        Entry(self.rectangle_frame, textvariable=self.rect_length).grid(row=0, column=1, padx=10, pady=5)
        
        Label(self.rectangle_frame, text="宽度:").grid(row=1, column=0, padx=10, pady=5)
        self.rect_width = StringVar()
        Entry(self.rectangle_frame, textvariable=self.rect_width).grid(row=1, column=1, padx=10, pady=5)
        
        Button(self.rectangle_frame, text="计算周长", command=self.calculate_rectangle).grid(row=2, column=0, columnspan=2, pady=10)
        
        # 圆形周长计算器
        self.circle_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.circle_frame, text="圆形")
        
        Label(self.circle_frame, text="半径:").grid(row=0, column=0, padx=10, pady=5)
        self.circle_radius = StringVar()
        Entry(self.circle_frame, textvariable=self.circle_radius).grid(row=0, column=1, padx=10, pady=5)
        
        Button(self.circle_frame, text="计算周长", command=self.calculate_circle).grid(row=1, column=0, columnspan=2, pady=10)
        
        # 正方形周长计算器
        self.square_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.square_frame, text="正方形")
        
        Label(self.square_frame, text="边长:").grid(row=0, column=0, padx=10, pady=5)
        self.square_side = StringVar()
        Entry(self.square_frame, textvariable=self.square_side).grid(row=0, column=1, padx=10, pady=5)
        
        Button(self.square_frame, text="计算周长", command=self.calculate_square).grid(row=1, column=0, columnspan=2, pady=10)
        
        # 八边形周长计算器
        self.octagon_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.octagon_frame, text="八边形")
        
        Label(self.octagon_frame, text="边长:").grid(row=0, column=0, padx=10, pady=5)
        self.octagon_side = StringVar()
        Entry(self.octagon_frame, textvariable=self.octagon_side).grid(row=0, column=1, padx=10, pady=5)
        
        Button(self.octagon_frame, text="计算周长", command=self.calculate_octagon).grid(row=1, column=0, columnspan=2, pady=10)
        
        # 等腰三角形周长计算器
        self.triangle_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.triangle_frame, text="等腰三角形")
        
        Label(self.triangle_frame, text="底边:").grid(row=0, column=0, padx=10, pady=5)
        self.triangle_base = StringVar()
        Entry(self.triangle_frame, textvariable=self.triangle_base).grid(row=0, column=1, padx=10, pady=5)
        
        Label(self.triangle_frame, text="腰长:").grid(row=1, column=0, padx=10, pady=5)
        self.triangle_side = StringVar()
        Entry(self.triangle_frame, textvariable=self.triangle_side).grid(row=1, column=1, padx=10, pady=5)
        
        Button(self.triangle_frame, text="计算周长", command=self.calculate_triangle).grid(row=2, column=0, columnspan=2, pady=10)
        
        # 斜边和周长计算器
        self.hypotenuse_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.hypotenuse_frame, text="斜边计算")
        
        Label(self.hypotenuse_frame, text="直角边1:").grid(row=0, column=0, padx=10, pady=5)
        self.hypotenuse_a = StringVar()
        Entry(self.hypotenuse_frame, textvariable=self.hypotenuse_a).grid(row=0, column=1, padx=10, pady=5)
        
        Label(self.hypotenuse_frame, text="直角边2:").grid(row=1, column=0, padx=10, pady=5)
        self.hypotenuse_b = StringVar()
        Entry(self.hypotenuse_frame, textvariable=self.hypotenuse_b).grid(row=1, column=1, padx=10, pady=5)
        
        Button(self.hypotenuse_frame, text="计算斜边", command=self.calculate_hypotenuse).grid(row=2, column=0, columnspan=2, pady=10)
        
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
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.perimeter_calculator")
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
    
    def calculate_rectangle(self):
        try:
            length = float(self.rect_length.get())
            width = float(self.rect_width.get())
            perimeter = 2 * (length + width)
            self.result_var.set(f"长方形周长: {perimeter:.2f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
    
    def calculate_circle(self):
        try:
            radius = float(self.circle_radius.get())
            perimeter = 2 * math.pi * radius
            self.result_var.set(f"圆周长: {perimeter:.2f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
    
    def calculate_square(self):
        try:
            side = float(self.square_side.get())
            perimeter = 4 * side
            self.result_var.set(f"正方形周长: {perimeter:.2f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
    
    def calculate_octagon(self):
        try:
            side = float(self.octagon_side.get())
            perimeter = 8 * side
            self.result_var.set(f"八边形周长: {perimeter:.2f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
    
    def calculate_triangle(self):
        try:
            base = float(self.triangle_base.get())
            side = float(self.triangle_side.get())
            perimeter = base + 2 * side
            self.result_var.set(f"等腰三角形周长: {perimeter:.2f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
    
    def calculate_hypotenuse(self):
        try:
            a = float(self.hypotenuse_a.get())
            b = float(self.hypotenuse_b.get())
            hypotenuse = math.sqrt(a**2 + b**2)
            perimeter = a + b + hypotenuse
            self.result_var.set(f"斜边: {hypotenuse:.2f}\n三角形周长: {perimeter:.2f}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")

if __name__ == "__main__":
    root = Tk()
    app = PerimeterCalculator(root)
    root.mainloop()
