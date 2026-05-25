# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import subprocess
import threading
import os
from pathlib import Path
from fontTools.ttLib import TTFont

ICON_PATH = "Image/icon.ico"

class ModelScopeDownloader:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.download_process = None

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)

    def download(self, model_name, file_name=None, local_dir=None):
        if not model_name:
            raise ValueError("模型名称不能为空")

        self.log(f"[开始] 下载: {model_name}")
        cmd = ["modelscope", "download", "--model", model_name]
        if file_name:
            cmd.extend([file_name, "--local_dir", local_dir or "."])
        elif local_dir:
            cmd.extend(["--local_dir", local_dir])

        return self._run_command(cmd)

    def _run_command(self, cmd):
        try:
            self.download_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            for line in self.download_process.stdout:
                self.log(line.strip())
            self.download_process.wait()
            return self.download_process.returncode == 0
        except FileNotFoundError:
            self.log("[错误] 未找到 modelscope 命令，请先安装: pip install modelscope")
            raise RuntimeError("未找到 modelscope 命令！")
        except Exception as e:
            self.log(f"[错误] {e}")
            raise

    def cancel(self):
        if self.download_process:
            self.download_process.terminate()
            self.log("[取消] 下载已取消")


class DownloaderGUI:
    def __init__(self, root):
        # 首先检查开源协议文档是否存在并验证完整性
        if not self.check_license():
            messagebox.showerror(
                "错误", 
                "缺少授权！无法使用！请先获取授权！\n"
            )
            root.destroy()
            return
        
        self.root = root
        self.downloader = ModelScopeDownloader(log_callback=self.log)
        self.is_downloading = False
        self._setup_window()
        self.set_window_icon()
        self.load_font()
        self._create_widgets()

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
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.ModelScopeDownloader")
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

    def load_font(self):
        """从配置文件加载字体设置"""
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        IMAGE_DIR = PROJECT_ROOT / "Image"
        
        font_path = IMAGE_DIR / "AlibabaPuHuiTi-3-55-RegularL3.ttf"
        
        if not font_path.exists():
            print(f"警告：找不到字体文件：{font_path}，将使用默认字体")
            self.current_font = ("Microsoft YaHei", 10)
            self.root.option_add("*Font", self.current_font)
            return
        
        # 使用 fonttools 获取字体名称
        tt = TTFont(str(font_path))
        font_name = None
        for record in tt['name'].names:
            if record.nameID == 1:  # Font Family
                font_name = record.toUnicode()
                break
        if not font_name:
            print(f"警告：无法从字体文件获取字体名称：{font_path}，将使用默认字体")
            self.current_font = ("Microsoft YaHei", 10)
            self.root.option_add("*Font", self.current_font)
            tt.close()
            return
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

    def _setup_window(self):
        self.root.title("ModelScope 模型下载器")
        self.root.geometry("450x400")
        self.root.resizable(False, False)

    def _create_widgets(self):
        # 标题
        title_label = tk.Label(
            self.root, 
            text="ModelScope 模型下载器",
            font=(self.current_font[0], 13, "bold")
        )
        title_label.pack(pady=8)

        # 输入区域
        frame = tk.Frame(self.root)
        frame.pack(pady=5, padx=30, fill="x")

        tk.Label(frame, text="模型名称:", font=self.current_font).grid(row=0, column=0, sticky="w", pady=2)
        self.model_entry = tk.Entry(frame, width=35, font=self.current_font)
        self.model_entry.grid(row=0, column=1, padx=5, pady=2)
        self.model_entry.insert(0, "Qwen/Qwen3.5-4B")

        tk.Label(frame, text="文件名:", font=self.current_font).grid(row=1, column=0, sticky="w", pady=2)
        self.file_entry = tk.Entry(frame, width=35, font=self.current_font)
        self.file_entry.grid(row=1, column=1, padx=5, pady=2)

        tk.Label(frame, text="本地目录:", font=self.current_font).grid(row=2, column=0, sticky="w", pady=2)
        self.dir_entry = tk.Entry(frame, width=35, font=self.current_font)
        self.dir_entry.grid(row=2, column=1, padx=5, pady=2)
        browse_btn = tk.Button(
            frame, 
            text="浏览", 
            command=self._browse_dir, 
            width=6,
            font=self.current_font
        )
        browse_btn.grid(row=2, column=2, padx=2)

        # 按钮区域
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=8)

        self.download_model_btn = tk.Button(
            btn_frame, 
            text="下载完整模型", 
            command=self._download_model, 
            width=12,
            font=self.current_font
        )
        self.download_model_btn.pack(side="left", padx=3)

        self.download_file_btn = tk.Button(
            btn_frame, 
            text="下载单个文件", 
            command=self._download_file, 
            width=12,
            font=self.current_font
        )
        self.download_file_btn.pack(side="left", padx=3)

        self.cancel_btn = tk.Button(
            btn_frame, 
            text="取消下载", 
            command=self._cancel, 
            width=12, 
            state="disabled",
            font=self.current_font
        )
        self.cancel_btn.pack(side="left", padx=3)

        # 进度条
        self.progress = ttk.Progressbar(self.root, mode="indeterminate", length=350)
        self.progress.pack(pady=3)

        # 日志区域
        tk.Label(self.root, text="下载日志:", font=self.current_font).pack(anchor="w", padx=30)
        self.log_text = scrolledtext.ScrolledText(
            self.root, 
            width=65, 
            height=10, 
            font=("Consolas", 9)
        )
        self.log_text.pack(fill="both", expand=True, padx=30, pady=3)

    def _browse_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, path)

    def log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def _set_buttons(self, enabled):
        state = "normal" if enabled else "disabled"
        self.download_model_btn.configure(state=state)
        self.download_file_btn.configure(state=state)
        self.cancel_btn.configure(state="normal" if not enabled else "disabled")
        self.is_downloading = not enabled

    def _run_download(self, full=False):
        model_name = self.model_entry.get().strip()
        file_name = self.file_entry.get().strip() or None
        local_dir = self.dir_entry.get().strip() or None

        try:
            self._set_buttons(False)
            self.progress.start(10)

            def run():
                try:
                    success = self.downloader.download(model_name, file_name, local_dir)
                    self.root.after(0, lambda: (
                        self.log("[成功] 下载完成！" if success else "[失败] 下载失败"),
                        messagebox.showinfo("结果", "下载完成！" if success else "下载失败")
                    ))
                except Exception as e:
                    self.root.after(0, lambda: (
                        self.log(f"[错误] {e}"),
                        messagebox.showerror("错误", str(e))
                    ))
                finally:
                    self.root.after(0, self._done)

            threading.Thread(target=run, daemon=True).start()
        except ValueError as e:
            messagebox.showerror("错误", str(e))

    def _download_model(self):
        self.file_entry.delete(0, tk.END)
        self._run_download()

    def _download_file(self):
        self._run_download()

    def _cancel(self):
        self.downloader.cancel()

    def _done(self):
        self.progress.stop()
        self._set_buttons(True)


if __name__ == "__main__":
    root = tk.Tk()
    DownloaderGUI(root)
    root.mainloop()
