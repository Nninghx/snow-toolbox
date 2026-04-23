import os
import sys
import subprocess
import ctypes
import json
from tkinter import Tk, Label, Button, StringVar, messagebox, ttk
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def load_font_config():
    """动态读取字体配置文件"""
    try:
        with open(os.path.join(os.path.dirname(__file__), '../Core/ziti.json'), 'r', encoding='utf-8') as f:
            font_config = json.load(f)
            return font_config.get('family', 'Microsoft YaHei')
    except Exception as e:
        print(f"加载字体配置失败: {e}")
        return 'Microsoft YaHei'


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


class MemoryCompressionTool:
    def __init__(self, master):
        self.master = master
        master.title("内存压缩管理工具")

        # 设置窗口图标
        self.set_window_icon(master)

        # 加载字体配置
        font_family = load_font_config()
        self.font = (font_family, 12)
        self.title_font = (font_family, 14, "bold")

        # 检查管理员权限
        self.is_admin = is_admin()

        # 主框架
        main_frame = ttk.Frame(master, padding="20")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # 标题
        title_label = Label(main_frame, text="Windows 内存压缩管理", font=self.title_font)
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # 说明
        desc_label = Label(
            main_frame,
            text="内存压缩可以将很少使用的内存页面压缩，\n释放物理 RAM 来改善性能。",
            font=self.font,
            justify="center"
        )
        desc_label.grid(row=1, column=0, columnspan=2, pady=(0, 20))

        # 状态显示
        status_label = Label(main_frame, text="当前状态:", font=self.font)
        status_label.grid(row=2, column=0, sticky="w", pady=10)

        self.status_var = StringVar()
        self.status_value_label = Label(main_frame, textvariable=self.status_var, font=self.font, foreground="blue")
        self.status_value_label.grid(row=2, column=1, sticky="w", pady=10)

        # 管理员权限提示
        if not self.is_admin:
            admin_label = Label(
                main_frame,
                text="提示: 部分操作可能需要管理员权限",
                font=(font_family, 10),
                foreground="orange"
            )
            admin_label.grid(row=3, column=0, columnspan=2, pady=(0, 10))

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)

        # 启用按钮
        self.enable_btn = Button(
            button_frame,
            text="启用内存压缩",
            command=self.enable_compression,
            font=self.font,
            width=15,
            bg="#4CAF50",
            fg="white",
            activebackground="#45a049"
        )
        self.enable_btn.grid(row=0, column=0, padx=10)

        # 禁用按钮
        self.disable_btn = Button(
            button_frame,
            text="禁用内存压缩",
            command=self.disable_compression,
            font=self.font,
            width=15,
            bg="#f44336",
            fg="white",
            activebackground="#da190b"
        )
        self.disable_btn.grid(row=0, column=1, padx=10)

        # 刷新按钮
        self.refresh_btn = Button(
            button_frame,
            text="刷新状态",
            command=self.refresh_status,
            font=self.font,
            width=15
        )
        self.refresh_btn.grid(row=0, column=2, padx=10)

        # 详细信息框架
        info_frame = ttk.LabelFrame(main_frame, text="详细信息", padding="10")
        info_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky="nsew")

        self.info_text = ""
        self.info_label = Label(info_frame, text=self.info_text, font=(font_family, 10), justify="left")
        self.info_label.grid(row=0, column=0, sticky="w")

        # 初始刷新状态
        self.refresh_status()

        # 配置窗口大小
        master.resizable(False, False)

    def set_window_icon(self, master):
        """设置窗口图标"""
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Image", "icon.ico"))
        if not os.path.exists(icon_path):
            return

        try:
            if os.name == 'nt':
                try:
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox.memory_compression")
                except Exception as e:
                    print(f"设置 AppUserModelID 失败: {e}")

                try:
                    master.iconbitmap(default=icon_path)
                except Exception as e:
                    print(f"Windows iconbitmap 设置失败: {e}")

            if PIL_AVAILABLE:
                try:
                    icon = Image.open(icon_path)
                    icon_photo = ImageTk.PhotoImage(icon)
                    master.iconphoto(True, icon_photo)
                    master._icon_photo = icon_photo
                except Exception as e:
                    print(f"PIL iconphoto 设置失败: {e}")
            else:
                try:
                    from tkinter import PhotoImage
                    icon_photo = PhotoImage(file=icon_path)
                    master.iconphoto(True, icon_photo)
                    master._icon_photo = icon_photo
                except Exception as e:
                    print(f"tk.PhotoImage iconphoto 设置失败: {e}")
        except Exception as e:
            print(f"加载图标失败: {e}")

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
    root = Tk()
    app = MemoryCompressionTool(root)
    root.mainloop()
