# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import subprocess
import threading
import os

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
        self.root = root
        self.downloader = ModelScopeDownloader(log_callback=self.log)
        self.is_downloading = False
        self._setup_window()
        self._create_widgets()

    def _setup_window(self):
        self.root.title("ModelScope 模型下载器")
        self.root.geometry("450x400")
        if os.path.exists(ICON_PATH):
            try:
                self.root.iconbitmap(ICON_PATH)
            except:
                pass

    def _create_widgets(self):
        # 标题
        tk.Label(self.root, text="ModelScope 模型下载器", font=("Arial", 13, "bold")).pack(pady=8)

        # 输入区域
        frame = tk.Frame(self.root)
        frame.pack(pady=5, padx=30, fill="x")

        tk.Label(frame, text="模型名称:").grid(row=0, column=0, sticky="w", pady=2)
        self.model_entry = tk.Entry(frame, width=35)
        self.model_entry.grid(row=0, column=1, padx=5, pady=2)
        self.model_entry.insert(0, "Qwen/Qwen3.5-4B")

        tk.Label(frame, text="文件名:").grid(row=1, column=0, sticky="w", pady=2)
        self.file_entry = tk.Entry(frame, width=35)
        self.file_entry.grid(row=1, column=1, padx=5, pady=2)

        tk.Label(frame, text="本地目录:").grid(row=2, column=0, sticky="w", pady=2)
        self.dir_entry = tk.Entry(frame, width=35)
        self.dir_entry.grid(row=2, column=1, padx=5, pady=2)
        tk.Button(frame, text="浏览", command=self._browse_dir, width=6).grid(row=2, column=2, padx=2)

        # 按钮区域
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=8)

        self.download_model_btn = tk.Button(btn_frame, text="下载完整模型", command=self._download_model, width=12)
        self.download_model_btn.pack(side="left", padx=3)

        self.download_file_btn = tk.Button(btn_frame, text="下载单个文件", command=self._download_file, width=12)
        self.download_file_btn.pack(side="left", padx=3)

        self.cancel_btn = tk.Button(btn_frame, text="取消下载", command=self._cancel, width=12, state="disabled")
        self.cancel_btn.pack(side="left", padx=3)

        # 进度条
        self.progress = ttk.Progressbar(self.root, mode="indeterminate", length=350)
        self.progress.pack(pady=3)

        # 日志区域
        tk.Label(self.root, text="下载日志:").pack(anchor="w", padx=30)
        self.log_text = scrolledtext.ScrolledText(self.root, width=65, height=10, font=("Consolas", 9))
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
