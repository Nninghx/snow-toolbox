import os
import sys
import subprocess
import ctypes
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from fontTools.ttLib import TTFont

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def is_admin():
    """检查是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_powershell_as_admin(command):
    """以管理员权限运行 PowerShell 命令"""
    try:
        # 使用 PowerShell 的 Start-Process -Verb RunAs 来提升权限
        ps_command = f'Start-Process powershell -ArgumentList "-Command {command}" -Verb RunAs -Wait'
        result = subprocess.run(
            ['powershell', '-Command', ps_command],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def get_memory_compression_status():
    """获取内存压缩状态"""
    try:
        # 使用 PowerShell 获取内存压缩状态
        command = "Get-MMAgent | Select-Object -ExpandProperty MemoryCompression"
        result = subprocess.run(
            ['powershell', '-Command', command],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        if result.returncode == 0:
            output = result.stdout.strip().lower()
            return output == 'true'
        return None
    except Exception as e:
        print(f"获取状态失败: {e}")
        return None


def enable_memory_compression():
    """启用内存压缩"""
    if is_admin():
        try:
            command = "Enable-MMAgent -MemoryCompression"
            result = subprocess.run(
                ['powershell', '-Command', command],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)
    else:
        # 需要管理员权限，使用提升的方式执行
        command = "Enable-MMAgent -MemoryCompression"
        ps_script = f'''
            Start-Process powershell -ArgumentList '-Command {command}' -Verb RunAs -Wait
        '''
        try:
            result = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)


def disable_memory_compression():
    """禁用内存压缩"""
    if is_admin():
        try:
            command = "Disable-MMAgent -MemoryCompression"
            result = subprocess.run(
                ['powershell', '-Command', command],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)
    else:
        # 需要管理员权限，使用提升的方式执行
        command = "Disable-MMAgent -MemoryCompression"
        ps_script = f'''
            Start-Process powershell -ArgumentList '-Command {command}' -Verb RunAs -Wait
        '''
        try:
            result = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)


def set_window_icon(root):
    """设置应用程序窗口图标"""
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    IMAGE_DIR = PROJECT_ROOT / "Image"
    
    icon_ico_path = IMAGE_DIR / "icon.ico"
    icon_png_path = IMAGE_DIR / "icon.png"

    # Windows系统设置应用ID
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.MemoryCompressionTool")
        except Exception:
            pass

    # 尝试设置ICO图标
    if icon_ico_path.exists():
        try:
            root.iconbitmap(default=str(icon_ico_path))
        except Exception:
            try:
                root.iconbitmap(str(icon_ico_path))
            except Exception:
                pass

    # 尝试设置PNG图标
    if hasattr(root, "iconphoto") and icon_png_path.exists():
        try:
            icon_image = tk.PhotoImage(file=str(icon_png_path))
            root.iconphoto(True, icon_image)
            # 保存引用防止垃圾回收
            root._icon_image = icon_image
        except Exception:
            pass


def check_license():
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


def load_font():
    """从配置文件加载字体设置"""
    # 定义项目根目录和图片目录
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    IMAGE_DIR = PROJECT_ROOT / "Image"
    
    font_path = IMAGE_DIR / "AlibabaPuHuiTi-3-55-RegularL3.ttf"
    
    if not font_path.exists():
        messagebox.showerror("错误", f"找不到字体文件：{font_path}")
        return None
    
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
    current_font = (font_name, 10)
    return current_font


class MemoryCompressionTool:
    def __init__(self, master, current_font=None):
        self.master = master
        master.title("内存压缩管理工具")

        # 设置默认字体，如果未提供则使用系统默认
        if current_font is None:
            self.current_font = ("Microsoft YaHei", 10)
        else:
            self.current_font = current_font

        # 检查管理员权限
        self.is_admin = is_admin()

        # 主框架
        main_frame = ttk.Frame(master, padding="20")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # 标题
        title_label = tk.Label(main_frame, text="Windows 内存压缩管理", font=(self.current_font[0], 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # 说明
        desc_label = tk.Label(
            main_frame,
            text="内存压缩可以将很少使用的内存页面压缩，\n释放物理 RAM 来改善性能。",
            font=self.current_font,
            justify="center"
        )
        desc_label.grid(row=1, column=0, columnspan=2, pady=(0, 20))

        # 状态显示
        status_label = tk.Label(main_frame, text="当前状态:", font=self.current_font)
        status_label.grid(row=2, column=0, sticky="w", pady=10)

        self.status_var = tk.StringVar()
        self.status_value_label = tk.Label(main_frame, textvariable=self.status_var, font=self.current_font, foreground="blue")
        self.status_value_label.grid(row=2, column=1, sticky="w", pady=10)

        # 管理员权限提示
        if not self.is_admin:
            admin_label = tk.Label(
                main_frame,
                text="提示: 部分操作可能需要管理员权限",
                font=(self.current_font[0], 10),
                foreground="orange"
            )
            admin_label.grid(row=3, column=0, columnspan=2, pady=(0, 10))

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)

        # 启用按钮
        self.enable_btn = tk.Button(
            button_frame,
            text="启用内存压缩",
            command=self.enable_compression,
            font=(self.current_font[0], 12),
            width=15,
            bg="#4CAF50",
            fg="white",
            activebackground="#45a049"
        )
        self.enable_btn.grid(row=0, column=0, padx=10)

        # 禁用按钮
        self.disable_btn = tk.Button(
            button_frame,
            text="禁用内存压缩",
            command=self.disable_compression,
            font=(self.current_font[0], 12),
            width=15,
            bg="#f44336",
            fg="white",
            activebackground="#da190b"
        )
        self.disable_btn.grid(row=0, column=1, padx=10)

        # 刷新按钮
        self.refresh_btn = tk.Button(
            button_frame,
            text="刷新状态",
            command=self.refresh_status,
            font=(self.current_font[0], 12),
            width=15
        )
        self.refresh_btn.grid(row=0, column=2, padx=10)

        # 详细信息框架
        info_frame = ttk.LabelFrame(main_frame, text="详细信息", padding="10")
        info_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky="nsew")

        self.info_text = ""
        self.info_label = tk.Label(info_frame, text=self.info_text, font=(self.current_font[0], 10), justify="left")
        self.info_label.grid(row=0, column=0, sticky="w")

        # 初始刷新状态
        self.refresh_status()

        # 配置窗口大小
        master.resizable(False, False)

    def refresh_status(self):
        """刷新内存压缩状态"""
        status = get_memory_compression_status()

        if status is None:
            self.status_var.set("无法获取状态\n(可能需要以管理员身份运行)")
            self.status_value_label.config(foreground="gray")
            self.info_text = "无法获取内存压缩状态。\n请确保以管理员身份运行此程序。"
        elif status:
            self.status_var.set("已启用")
            self.status_value_label.config(foreground="green")
            self.info_text = "内存压缩功能当前已启用。\n这有助于优化内存使用。"
        else:
            self.status_var.set("已禁用")
            self.status_value_label.config(foreground="red")
            self.info_text = "内存压缩功能当前已禁用。\n启用后可释放更多物理内存。"

        self.info_label.config(text=self.info_text)

    def enable_compression(self):
        """启用内存压缩"""
        if not self.is_admin:
            # 需要管理员权限
            confirm = messagebox.askyesno(
                "需要管理员权限",
                "启用内存压缩需要管理员权限。\n是否以管理员身份重新启动此程序？",
                icon='warning'
            )
            if confirm:
                self.restart_as_admin("enable")
            return

        success, output = enable_memory_compression()
        if success:
            messagebox.showinfo("成功", "内存压缩已成功启用！", icon='info')
            self.refresh_status()
        else:
            messagebox.showerror("错误", f"启用内存压缩失败：\n{output}", icon='error')

    def disable_compression(self):
        """禁用内存压缩"""
        if not self.is_admin:
            # 需要管理员权限
            confirm = messagebox.askyesno(
                "需要管理员权限",
                "禁用内存压缩需要管理员权限。\n是否以管理员身份重新启动此程序？",
                icon='warning'
            )
            if confirm:
                self.restart_as_admin("disable")
            return

        success, output = disable_memory_compression()
        if success:
            messagebox.showinfo("成功", "内存压缩已成功禁用！", icon='info')
            self.refresh_status()
        else:
            messagebox.showerror("错误", f"禁用内存压缩失败：\n{output}", icon='error')

    def restart_as_admin(self, action):
        """以管理员身份重新启动程序"""
        try:
            script_path = os.path.abspath(sys.argv[0])
            # 构建新的命令行，传递操作参数
            new_command = f'"{script_path}"'
            # 使用提升的权限启动新进程
            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                sys.executable,
                new_command,
                None,
                1
            )
            self.master.quit()
        except Exception as e:
            messagebox.showerror("错误", f"无法以管理员身份启动：\n{str(e)}", icon='error')


if __name__ == "__main__":
    # 创建主窗口
    root = tk.Tk()

    # 首先检查开源协议文档是否存在并验证完整性
    if not check_license():
        messagebox.showerror(
            "错误", 
            "缺少授权！无法使用！请先获取授权！\n"
        )
        root.destroy()
        sys.exit(1)

    # 设置窗口图标
    set_window_icon(root)

    # 加载并注册字体
    try:
        custom_font = load_font()
        if custom_font:
            root.option_add('*Font', custom_font)
            print(f"成功设置字体: {custom_font[0]}")
    except Exception as e:
        error_msg = f"字体设置失败: {str(e)}"
        print(error_msg)
        messagebox.showwarning("字体设置", error_msg)

    app = MemoryCompressionTool(root, current_font=custom_font if 'custom_font' in locals() and custom_font else None)
    root.mainloop()
