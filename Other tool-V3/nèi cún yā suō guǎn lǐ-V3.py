# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import ctypes
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

# 导入公共基类
import importlib.util
_base_spec = importlib.util.spec_from_file_location(
    "public_base_class",
    Path(__file__).resolve().parent.parent / "Core" / "Public base class.py"
)
_base_module = importlib.util.module_from_spec(_base_spec)
_base_spec.loader.exec_module(_base_module)
PDFToolBase = _base_module.PDFToolBase
del _base_spec, _base_module

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


class MemoryCompressionTool(PDFToolBase):
    def __init__(self, master):
        super().__init__(master)
        if not master.winfo_exists():
            return
        self.master = master
        master.title("内存压缩管理工具")

        # 设置默认字体
        self.current_font = ("Microsoft YaHei", 10)

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
    root = tk.Tk()
    app = MemoryCompressionTool(root)
    if root.winfo_exists():
        root.mainloop()
