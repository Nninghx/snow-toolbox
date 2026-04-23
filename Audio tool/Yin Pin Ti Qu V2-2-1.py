# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import json
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
CORE_DIR = ROOT_DIR.parent / "Core"
sys.path.insert(0, str(CORE_DIR))
from BangZhu import get_help_system


class AudioExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("音频提取工具")
        self.root.geometry("530x200")
        self.root.resizable(False, False)

        self.video_path = tk.StringVar()
        self.audio_path = tk.StringVar()

        self.set_window_icon()
        self.load_font()
        self.build_ui()

    def load_font(self):
        font_config_path = CORE_DIR / "ziti.json"
        try:
            with font_config_path.open("r", encoding="utf-8") as f:
                font_config = json.load(f)
            family = font_config.get("family", "Arial")
        except Exception:
            family = "Arial"
        self.current_font = (family, 10)
        self.root.option_add("*Font", self.current_font)

    def build_ui(self):
        tk.Label(self.root, text="选择视频文件:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
        tk.Entry(self.root, textvariable=self.video_path, width=40).grid(row=0, column=1, padx=10, pady=10)
        tk.Button(self.root, text="浏览...", command=self.select_video).grid(row=0, column=2, padx=10, pady=10)

        tk.Label(self.root, text="输出音频文件:").grid(row=1, column=0, padx=10, pady=10, sticky="e")
        tk.Entry(self.root, textvariable=self.audio_path, width=40).grid(row=1, column=1, padx=10, pady=10)
        tk.Button(self.root, text="浏览...", command=self.select_audio).grid(row=1, column=2, padx=10, pady=10)

        self.extract_button = tk.Button(self.root, text="开始提取", command=self.extract_audio)
        self.extract_button.grid(row=2, column=1, pady=10)

        button_frame = tk.Frame(self.root)
        button_frame.grid(row=3, column=1, pady=5)
        tk.Button(button_frame, text="帮助", command=self.show_help).pack(side="left", padx=5)

        self.status_label = tk.Label(self.root, text="", fg="green")
        self.status_label.grid(row=4, column=1, pady=5)

    def select_video(self):
        file_path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[("视频文件", "*.mp4 *.avi *.mkv *.mov"), ("所有文件", "*.*")]
        )
        if file_path:
            self.video_path.set(file_path)
            if not self.audio_path.get():
                self.audio_path.set(str(Path(file_path).with_suffix(".mp3")))

    def select_audio(self):
        default_name = Path(self.video_path.get()).with_suffix(".mp3").name if self.video_path.get() else "output.mp3"
        file_path = filedialog.asksaveasfilename(
            title="保存音频文件",
            initialfile=default_name,
            defaultextension=".mp3",
            filetypes=[("MP3 文件", "*.mp3"), ("WAV 文件", "*.wav"), ("所有文件", "*.*")]
        )
        if file_path:
            self.audio_path.set(file_path)

    def show_help(self):
        get_help_system().show_help("视频提取音频")

    def set_window_icon(self):
        icon_ico_path = ROOT_DIR.parent / "Image" / "icon.ico"
        icon_png_path = ROOT_DIR.parent / "Image" / "icon.png"

        if os.name == 'nt':
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.YinPinTiQu")
            except Exception:
                pass

        if icon_ico_path.exists():
            try:
                self.root.iconbitmap(default=str(icon_ico_path))
            except Exception:
                try:
                    self.root.iconbitmap(str(icon_ico_path))
                except Exception:
                    pass

        if hasattr(self.root, "iconphoto") and icon_png_path.exists():
            try:
                self.icon_image = tk.PhotoImage(file=str(icon_png_path))
                self.root.iconphoto(True, self.icon_image)
            except Exception:
                pass

    def extract_audio(self):
        video_file = self.video_path.get().strip()
        audio_file = self.audio_path.get().strip()

        if not video_file or not Path(video_file).is_file():
            messagebox.showerror("错误", "请选择有效的视频文件！")
            return

        if not audio_file:
            messagebox.showerror("错误", "请输入音频输出路径！")
            return

        if not self.is_ffmpeg_available():
            messagebox.showerror("错误", "FFmpeg 未安装或不在系统路径中。")
            return

        self.extract_button.config(state="disabled")
        self.status_label.config(text="正在提取中...", fg="blue")

        thread = threading.Thread(target=self.run_extraction, args=(video_file, audio_file), daemon=True)
        thread.start()

    def is_ffmpeg_available(self):
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def run_extraction(self, video_file, audio_file):
        command = [
            "ffmpeg",
            "-i",
            video_file,
            "-q:a",
            "0",
            "-map",
            "a",
            "-y",
            audio_file
        ]

        try:
            subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            self.root.after(0, lambda: self.on_extraction_success(audio_file))
        except subprocess.CalledProcessError as exc:
            error_text = exc.stderr.strip().splitlines()[-1] if exc.stderr else "音频提取过程中发生错误。"
            self.root.after(0, lambda: self.on_extraction_failure(error_text))

    def on_extraction_success(self, audio_file):
        self.status_label.config(text="✅ 提取成功！", fg="green")
        self.extract_button.config(state="normal")
        messagebox.showinfo("成功", f"音频已保存至：{audio_file}")

    def on_extraction_failure(self, error_message="音频提取过程中发生错误。"):
        self.status_label.config(text="❌ 提取失败！", fg="red")
        self.extract_button.config(state="normal")
        messagebox.showerror("错误", error_message)

if __name__ == "__main__":
    root = tk.Tk()
    app = AudioExtractorApp(root)
    root.mainloop()