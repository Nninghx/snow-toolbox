# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import os

from os.path import dirname, join
sys.path.insert(0, join(dirname(dirname(__file__)), "Tool module"))
from BangZhu import get_help_system


class AudioExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("视频提取音频工具Alpha1.0.3")
        self.root.geometry("480x200")
        self.root.resizable(False, False)

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

        # 帮助和更新日志按钮
        button_frame = tk.Frame(root)
        button_frame.grid(row=3, column=1, pady=5)
        
        tk.Button(button_frame, text="帮助", command=self.show_help).pack(side="left", padx=5)
        tk.Button(button_frame, text="更新日志", command=self.show_changelog).pack(side="left", padx=5)

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

    def show_changelog(self):
        changelog_text = """视频提取音频工具更新日志

版本: Alpha1.0.0 (2025-05-22)
- 初始版本发布
- 实现基本视频提取音频功能
- 添加帮助文档
- 支持MP4/AVI/MKV/MOV输入格式
- 支持MP3/WAV输出格式
版本: Alpha1.0.1 (2025-05-23)
- 界面尺寸优化为480x200
- 新增WAV格式支持
- 错误处理优化
- 修复在处理大体积视频时会出现内存溢出或中断报错
版本: Alpha1.0.2 (2025-05-26)
- 添加更新日志
版本 Alpha1.0.3 (2025-6-7)
- 1.对帮助文档调用进行拆分，简化代码长度
- 2.禁止生成 .pyc 文件


"""
        messagebox.showinfo("更新日志", changelog_text)

    def show_help(self):
        help_system = get_help_system()
        help_system.show_help("视频提取音频")


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