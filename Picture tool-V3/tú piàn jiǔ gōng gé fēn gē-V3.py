# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

from PIL import Image
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
from pathlib import Path
from fontTools.ttLib import TTFont


class ImageSplitterApp:
    def __init__(self, root):
        """初始化应用界面和配置"""
        # 首先检查开源协议文档是否存在并验证完整性
        if not self.check_license():
            messagebox.showerror(
                "错误", 
                "缺少授权！无法使用！请先获取授权！\n"
            )
            root.destroy()
            return
        
        self.root = root
        self.root.title("图片九宫格分割")
        
        # 设置窗口图标、加载字体并构建UI
        self.set_window_icon()
        self.load_font()
        self.build_ui()

    def set_window_icon(self):
        """设置应用程序窗口图标"""
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        IMAGE_DIR = PROJECT_ROOT / "Image"
        
        icon_ico_path = IMAGE_DIR / "icon.ico"
        icon_png_path = IMAGE_DIR / "icon.png"

        # Windows系统设置应用ID
        if os.name == 'nt':
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.ImageSplitterApp")
            except Exception:
                pass

        # 尝试设置ICO图标
        if icon_ico_path.exists():
            try:
                self.root.iconbitmap(default=str(icon_ico_path))
            except Exception:
                try:
                    self.root.iconbitmap(str(icon_ico_path))
                except Exception:
                    pass

        # 尝试设置PNG图标
        if hasattr(self.root, "iconphoto") and icon_png_path.exists():
            try:
                self.icon_image = tk.PhotoImage(file=str(icon_png_path))
                self.root.iconphoto(True, self.icon_image)
            except Exception:
                pass

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

    def load_font(self):
        """从配置文件加载字体设置"""
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        IMAGE_DIR = PROJECT_ROOT / "Image"
        
        font_path = IMAGE_DIR / "AlibabaPuHuiTi-3-55-RegularL3.ttf"
        
        if not font_path.exists():
            messagebox.showerror("错误", f"找不到字体文件：{font_path}")
            self.root.destroy()
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
        self.current_font = (font_name, 10)
        self.root.option_add("*Font", self.current_font)

    def build_ui(self):
        """构建用户界面"""
        # 输入图片
        tk.Label(self.root, text="输入图片:", font=(self.current_font[0], 10)).grid(row=0, column=0, padx=5, pady=5)
        self.input_entry = tk.Entry(self.root, width=40, font=(self.current_font[0], 10))
        self.input_entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Button(self.root, text="浏览...", command=self.browse_input, font=(self.current_font[0], 10)).grid(row=0, column=2, padx=5, pady=5)
        
        # 输出目录
        tk.Label(self.root, text="输出目录:", font=(self.current_font[0], 10)).grid(row=1, column=0, padx=5, pady=5)
        self.output_entry = tk.Entry(self.root, width=40, font=(self.current_font[0], 10))
        self.output_entry.grid(row=1, column=1, padx=5, pady=5)
        tk.Button(self.root, text="浏览...", command=self.browse_output, font=(self.current_font[0], 10)).grid(row=1, column=2, padx=5, pady=5)
        
        # 进度条
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=300, mode="determinate")
        self.progress.grid(row=2, column=0, columnspan=3, padx=5, pady=10)
        
        # 分割按钮
        tk.Button(self.root, text="开始分割", command=self.start_split, font=(self.current_font[0], 10)).grid(row=3, column=0, columnspan=3, pady=10)
        
    def browse_input(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif")]
        )
        if filepath:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, filepath)
    
    def browse_output(self):
        dirpath = filedialog.askdirectory()
        if dirpath:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, dirpath)
    
    def start_split(self):
        input_path = self.input_entry.get()
        output_dir = self.output_entry.get()
        
        if not input_path or not output_dir:
            messagebox.showerror("错误", "请选择输入图片和输出目录")
            return
        
        try:
            self.progress["value"] = 0
            self.root.update()
            
            # 获取输入文件名(不带扩展名)
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            # 创建子文件夹路径
            save_dir = os.path.join(output_dir, base_name + "_split")
            
            # 确保输出目录存在
            os.makedirs(save_dir, exist_ok=True)
            
            # 打开图片
            with Image.open(input_path) as img:
                width, height = img.size
                
                # 计算每个小块的尺寸
                tile_width = width // 3
                tile_height = height // 3
                
                # 分割图片
                total = 9
                for i in range(3):
                    for j in range(3):
                        left = j * tile_width
                        upper = i * tile_height
                        right = left + tile_width
                        lower = upper + tile_height
                        
                        # 裁剪图片
                        tile = img.crop((left, upper, right, lower))
                        
                        # 保存小块
                        tile.save(os.path.join(save_dir, f'{base_name}_tile_{i}_{j}.png'))
                        
                        # 更新进度
                        self.progress["value"] = ((i * 3) + j + 1) / total * 100
                        self.root.update()
            
            messagebox.showinfo("完成", f"图片已成功分割为9份，保存在 {save_dir}")
            self.progress["value"] = 0
        
        except Exception as e:
            messagebox.showerror("错误", f"处理图片时出错: {e}")
            self.progress["value"] = 0


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageSplitterApp(root)
    root.mainloop()
