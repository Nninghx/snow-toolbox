import os
import sys
import subprocess
from pathlib import Path
import json
import tkinter as tk
from tkinter import font, filedialog, messagebox
from fontTools.ttLib import TTFont


class EmptyFolderCleaner:
    def __init__(self, root):
        # 首先检查授权
        if not self.check_license():
            messagebox.showerror(
                "错误", 
                "缺少授权！无法使用！请先获取授权！\n"
            )
            root.destroy()
            return
        
        self.root = root
        self.setup_ui()
        
    def check_license(self):
        """检查授权验证"""
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
    
    def set_window_icon(self):
        """设置应用程序窗口图标"""
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        IMAGE_DIR = PROJECT_ROOT / "Image"
        
        icon_ico_path = IMAGE_DIR / "icon.ico"
        icon_png_path = IMAGE_DIR / "icon.png"

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
        
        self.current_font = (font_name, 10)
        self.root.option_add("*Font", self.current_font)
        
    def setup_ui(self):
        # 设置窗口图标和加载字体
        self.set_window_icon()
        self.load_font()
        
        self.root.title("空文件夹清理工具")
        self.root.geometry("400x200")
        
        tk.Label(self.root, text="选择要清理的目录:").pack(pady=10)
        
        self.path_var = tk.StringVar()
        tk.Entry(self.root, textvariable=self.path_var, width=40).pack()
        
        tk.Button(self.root, text="浏览", command=self.browse_directory).pack(pady=5)
        tk.Button(self.root, text="清理空文件夹", command=self.clean_empty_folders).pack(pady=10)
        
    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.path_var.set(directory)
            
    def clean_empty_folders(self):
        target_dir = self.path_var.get()
        if not target_dir:
            messagebox.showerror("错误", "请先选择目录")
            return
            
        try:
            count = self._remove_empty_folders(target_dir)
            messagebox.showinfo("完成", f"已删除 {count} 个空文件夹")
        except Exception as e:
            messagebox.showerror("错误", str(e))
            
    def _remove_empty_folders(self, folder):
        count = 0
        for root, dirs, files in os.walk(folder, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        count += 1
                except Exception:
                    continue
        return count

if __name__ == "__main__":
    # Windows系统设置应用ID（必须在创建窗口之前）
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.EmptyFolderCleaner")
        except Exception:
            pass
    
    root = tk.Tk()
    app = EmptyFolderCleaner(root)
    root.mainloop()