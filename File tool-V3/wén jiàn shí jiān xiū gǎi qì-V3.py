import os
import sys
import time
import random
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import threading
from fontTools.ttLib import TTFont


class TimeModifierApp:
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
        self.root.title("文件时间修改器")
        self.root.geometry("800x450")
        self.root.resizable(True, True)
        
        # 设置窗口图标和加载字体
        self.set_window_icon()
        self.load_font()
        
        # 设置样式
        style = ttk.Style()
        style.configure('TButton', padding=5)
        style.configure('Header.TLabel', font=(self.current_font[0], 12, 'bold'))
        
        # 主框架
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 文件/文件夹选择区域
        selection_frame = ttk.LabelFrame(main_frame, text="选择目标", padding="10")
        selection_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(selection_frame, text="路径:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(selection_frame, textvariable=self.path_var, width=60)
        self.path_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        ttk.Button(selection_frame, text="浏览文件", command=self.browse_file).grid(row=0, column=2, padx=2)
        ttk.Button(selection_frame, text="浏览文件夹", command=self.browse_folder).grid(row=0, column=3, padx=2)
        
        # 时间设置区域
        time_frame = ttk.LabelFrame(main_frame, text="时间设置", padding="10")
        time_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 创建时间
        ttk.Label(time_frame, text="创建时间:", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, pady=5)
        self.create_time_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        create_time_frame = ttk.Frame(time_frame)
        create_time_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Entry(create_time_frame, textvariable=self.create_time_var, width=20).pack(side=tk.LEFT, padx=2)
        ttk.Button(create_time_frame, text="现在", command=lambda: self.set_current_time(self.create_time_var)).pack(side=tk.LEFT, padx=2)
        ttk.Button(create_time_frame, text="随机", command=lambda: self.set_random_time(self.create_time_var)).pack(side=tk.LEFT, padx=2)
        
        # 修改时间
        ttk.Label(time_frame, text="修改时间:", style='Header.TLabel').grid(row=1, column=0, sticky=tk.W, pady=5)
        self.modify_time_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        modify_time_frame = ttk.Frame(time_frame)
        modify_time_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Entry(modify_time_frame, textvariable=self.modify_time_var, width=20).pack(side=tk.LEFT, padx=2)
        ttk.Button(modify_time_frame, text="现在", command=lambda: self.set_current_time(self.modify_time_var)).pack(side=tk.LEFT, padx=2)
        ttk.Button(modify_time_frame, text="随机", command=lambda: self.set_random_time(self.modify_time_var)).pack(side=tk.LEFT, padx=2)
        
        # 访问时间
        ttk.Label(time_frame, text="访问时间:", style='Header.TLabel').grid(row=2, column=0, sticky=tk.W, pady=5)
        self.access_time_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        access_time_frame = ttk.Frame(time_frame)
        access_time_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Entry(access_time_frame, textvariable=self.access_time_var, width=20).pack(side=tk.LEFT, padx=2)
        ttk.Button(access_time_frame, text="现在", command=lambda: self.set_current_time(self.access_time_var)).pack(side=tk.LEFT, padx=2)
        ttk.Button(access_time_frame, text="随机", command=lambda: self.set_random_time(self.access_time_var)).pack(side=tk.LEFT, padx=2)
        
        # 选项区域
        options_frame = ttk.LabelFrame(main_frame, text="选项", padding="10")
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.recursive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="递归处理子文件夹（仅文件夹模式）", variable=self.recursive_var).grid(row=0, column=0, sticky=tk.W, padx=5)
        
        self.apply_create_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="应用创建时间", variable=self.apply_create_var).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        self.apply_modify_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="应用修改时间", variable=self.apply_modify_var).grid(row=0, column=2, sticky=tk.W, padx=5)
        
        self.apply_access_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="应用访问时间", variable=self.apply_access_var).grid(row=0, column=3, sticky=tk.W, padx=5)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="开始修改", command=self.start_modification, style='TButton').pack(side=tk.LEFT, padx=5)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
    
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
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.TimeModifierApp")
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
        # 定义项目根目录和图片目录
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
    
    def browse_file(self):
        """浏览选择文件"""
        file_path = filedialog.askopenfilename(title="选择文件")
        if file_path:
            self.path_var.set(file_path)
    
    def browse_folder(self):
        """浏览选择文件夹"""
        folder_path = filedialog.askdirectory(title="选择文件夹")
        if folder_path:
            self.path_var.set(folder_path)
    
    def set_current_time(self, var):
        """设置为当前时间"""
        var.set(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    def set_random_time(self, var):
        """设置为随机时间(前后一年内)"""
        # 生成过去或未来一年内的随机时间
        random_offset = random.randint(-31536000, 31536000)  # ±1年的秒数
        random_time = datetime.fromtimestamp(time.time() + random_offset)
        var.set(random_time.strftime("%Y-%m-%d %H:%M:%S"))
    
    def validate_time_format(self, time_str):
        """验证时间格式"""
        try:
            datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            return True
        except ValueError:
            return False
    
    def parse_time(self, time_str):
        """解析时间字符串为时间戳"""
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return dt.timestamp()
    
    def modify_single_file(self, file_path, create_time, modify_time, access_time):
        """修改单个文件的时间属性"""
        try:
            # Windows系统使用os.utime修改访问和修改时间
            if self.apply_access_var.get() or self.apply_modify_var.get():
                atime = access_time if self.apply_access_var.get() else os.stat(file_path).st_atime
                mtime = modify_time if self.apply_modify_var.get() else os.stat(file_path).st_mtime
                os.utime(file_path, (atime, mtime))
            
            # Windows系统创建时间需要使用win32api或subprocess调用powershell
            if self.apply_create_var.get():
                import subprocess
                create_time_str = datetime.fromtimestamp(create_time).strftime("%Y-%m-%dT%H:%M:%S")
                cmd = f'powershell -Command "(Get-Item \'{file_path}\').CreationTime=\'{create_time_str}\'"'
                subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            return True, "成功"
        except Exception as e:
            return False, str(e)
    
    def process_files(self, path, create_time, modify_time, access_time):
        """处理文件或文件夹"""
        results = {"success": 0, "failed": 0, "total": 0}
        
        if os.path.isfile(path):
            # 处理单个文件
            results["total"] = 1
            success, msg = self.modify_single_file(path, create_time, modify_time, access_time)
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1
        
        elif os.path.isdir(path):
            # 处理文件夹
            if self.recursive_var.get():
                # 递归处理
                for root, dirs, files in os.walk(path):
                    for name in files:
                        file_path = os.path.join(root, name)
                        results["total"] += 1
                        success, msg = self.modify_single_file(file_path, create_time, modify_time, access_time)
                        if success:
                            results["success"] += 1
                        else:
                            results["failed"] += 1
                    
                    # 如果需要也修改文件夹本身的时间
                    if self.apply_create_var.get() or self.apply_modify_var.get() or self.apply_access_var.get():
                        results["total"] += 1
                        success, msg = self.modify_single_file(root, create_time, modify_time, access_time)
                        if success:
                            results["success"] += 1
                        else:
                            results["failed"] += 1
            else:
                # 仅处理顶层文件
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    if os.path.isfile(item_path):
                        results["total"] += 1
                        success, msg = self.modify_single_file(item_path, create_time, modify_time, access_time)
                        if success:
                            results["success"] += 1
                        else:
                            results["failed"] += 1
        
        return results
    
    def start_modification(self):
        """开始修改"""
        path = self.path_var.get().strip()
        
        if not path:
            messagebox.showwarning("警告", "请先选择文件或文件夹！")
            return
        
        if not os.path.exists(path):
            messagebox.showerror("错误", "指定的路径不存在！")
            return
        
        # 验证时间格式
        if self.apply_create_var.get() and not self.validate_time_format(self.create_time_var.get()):
            messagebox.showerror("错误", "创建时间格式不正确，请使用 YYYY-MM-DD HH:MM:SS 格式")
            return
        
        if self.apply_modify_var.get() and not self.validate_time_format(self.modify_time_var.get()):
            messagebox.showerror("错误", "修改时间格式不正确，请使用 YYYY-MM-DD HH:MM:SS 格式")
            return
        
        if self.apply_access_var.get() and not self.validate_time_format(self.access_time_var.get()):
            messagebox.showerror("错误", "访问时间格式不正确，请使用 YYYY-MM-DD HH:MM:SS 格式")
            return
        
        # 解析时间
        create_time = self.parse_time(self.create_time_var.get()) if self.apply_create_var.get() else None
        modify_time = self.parse_time(self.modify_time_var.get()) if self.apply_modify_var.get() else None
        access_time = self.parse_time(self.access_time_var.get()) if self.apply_access_var.get() else None
        
        # 在新线程中执行
        thread = threading.Thread(target=self.execute_modification, args=(path, create_time, modify_time, access_time))
        thread.daemon = True
        thread.start()
    
    def execute_modification(self, path, create_time, modify_time, access_time):
        """执行修改操作"""
        self.status_var.set("正在处理...")
        
        try:
            results = self.process_files(path, create_time, modify_time, access_time)
            
            self.status_var.set(f"完成 - 成功: {results['success']}, 失败: {results['failed']}")
            
            if results['failed'] == 0:
                messagebox.showinfo("完成", f"所有 {results['success']} 已成功修改！")
            else:
                messagebox.showwarning("完成", f"处理完成！\n成功: {results['success']}\n失败: {results['failed']}")
        
        except Exception as e:
            self.status_var.set("处理失败")
            messagebox.showerror("错误", f"处理过程中发生错误: {str(e)}")
    
    def clear_log(self):
        """清空日志"""
        pass


def main():
    """主程序入口"""
    try:
        root = tk.Tk()
        app = TimeModifierApp(root)
        root.mainloop()
    except Exception as e:
        print(f"\n[ERROR] 应用启动失败：{e}")
        import traceback
        traceback.print_exc()
if __name__ == "__main__":
    main()