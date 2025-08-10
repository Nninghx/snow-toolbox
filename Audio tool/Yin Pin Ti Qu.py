# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import os
import json

from os.path import dirname, join
sys.path.insert(0, join(dirname(__file__), "..", "Core"))
from BangZhu import get_help_system


class AudioExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("音频提取工具")
        self.root.geometry("530x200")
        self.root.resizable(False, False)
        
        # 设置窗口图标
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "..", "Image", "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"加载图标失败: {e}")
        
        # 加载字体配置
        font_config_path = join(dirname(__file__), "..", "Core", "ziti.json")
        with open(font_config_path, 'r', encoding='utf-8') as f:
            font_config = json.load(f)
        self.current_font = (font_config["family"], 10)
        self.root.option_add("*Font", self.current_font)

        # 视频文件路径
        self.video_path = tk.StringVar()
        tk.Label(root, text="选择视频文件:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
        tk.Entry(root, textvariable=self.video_path, width=40).grid(row=0, column=1, padx=10, pady=10)
        tk.Button(root, text="浏览...", command=self.select_video).grid(row=0, column=2, padx=10, pady=10)

        # 音频输出路径
        self.audio_path = tk.StringVar()
        tk.Label(root, text="输出音频文件:").grid(row=1, column=0, padx=10, pady=10, sticky="e")
        tk.Entry(root, textvariable=self.audio_path, width=40).grid(row=1, column=1, padx=10, pady=10)
        tk.Button(root, text="浏览...", command=self.select_audio).grid(row=1, column=2, padx=10, pady=10)

        # 提取按钮
        tk.Button(root, text="开始提取", command=self.extract_audio).grid(row=2, column=1, pady=10)

        # 帮助按钮
        button_frame = tk.Frame(root)
        button_frame.grid(row=3, column=1, pady=5)
        
        tk.Button(button_frame, text="帮助", command=self.show_help).pack(side="left", padx=5)

        # 状态显示
        self.status_label = tk.Label(root, text="", fg="green")
        self.status_label.grid(row=4, column=1, pady=5)

    def select_video(self):
        file_path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[("视频文件", "*.mp4 *.avi *.mkv *.mov")]
        )
        if file_path:
            self.video_path.set(file_path)

    def select_audio(self):
        file_path = filedialog.asksaveasfilename(
            title="保存音频文件",
            defaultextension=".mp3",
            filetypes=[("MP3 文件", "*.mp3"), ("WAV 文件", "*.wav"), ("所有文件", "*.*")]
        )
        if file_path:
            self.audio_path.set(file_path)

    def show_help(self):
        help_system = get_help_system()
        help_system.show_help("视频提取音频")
        
    def update_font(self, font_family, font_size=10):
        """更新界面字体"""
        self.current_font = (font_family, font_size)
        self.root.option_add("*Font", self.current_font)
        # 刷新界面以应用新字体
        for widget in self.root.winfo_children():
            widget.configure(font=self.current_font)


    def extract_audio(self):
        video_file = self.video_path.get()
        audio_file = self.audio_path.get()

        if not os.path.isfile(video_file):
            messagebox.showerror("错误", "请选择有效的视频文件！")
            return

        if not audio_file:
            messagebox.showerror("错误", "请输入音频输出路径！")
            return

        # 检查 FFmpeg 是否可用
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            messagebox.showerror("错误", "FFmpeg 未安装或不在系统路径中。")
            return

        # 执行 FFmpeg 命令
        command = [
            'ffmpeg',
            '-i', video_file,
            '-q:a', '0',
            '-map', 'a',
            '-y',
            audio_file
        ]

        try:
            subprocess.run(command, check=True)
            self.status_label.config(text="✅ 提取成功！", fg="green")
            messagebox.showinfo("成功", f"音频已保存至：{audio_file}")
        except subprocess.CalledProcessError:
            self.status_label.config(text="❌ 提取失败！", fg="red")
            messagebox.showerror("错误", "音频提取过程中发生错误。")

if __name__ == "__main__":
    root = tk.Tk()
    app = AudioExtractorApp(root)
    root.mainloop()