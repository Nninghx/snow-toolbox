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

# 定义项目根目录和核心模块目录
ROOT_DIR = Path(__file__).resolve().parent
CORE_DIR = ROOT_DIR.parent / "Core"
sys.path.insert(0, str(CORE_DIR))


class AudioExtractorApp:
    """音频提取工具主应用类"""
    
    def __init__(self, root):
        """初始化应用界面和配置"""
        # 首先检查开源协议文档是否存在并验证完整性
        if not self.check_license():
            messagebox.showerror(
                "错误", 
                "缺少授权！无法使用！请先获取授权！\n"
            )
            root.destroy()
            return
        
        self.root = root
        self.root.title("音频提取工具")
        self.root.geometry("520x150")
        self.root.resizable(False, False)

        # 定义视频路径和音频输出路径的变量
        self.video_path = tk.StringVar()
        self.audio_path = tk.StringVar()

        # 设置窗口图标、加载字体并构建UI
        self.set_window_icon()
        self.load_font()
        self.build_ui()

    def check_license(self):
        """检查开源协议文档是否存在并验证完整性"""
        try:
            # 验证授权
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
        # 优先尝试使用项目自带的中文字体
        font_path = ROOT_DIR.parent / "Image" / "AlibabaPuHuiTi-3-55-RegularL3.ttf"
        
        if font_path.exists():
            try:
                # 注册自定义字体
                from tkinter import font as tkfont
                custom_font = tkfont.Font(family="Alibaba PuHuiTi", size=10)
                
                # 验证字体是否正确加载 - 渲染测试文本
                test_text = "音频提取工具"
                test_render = custom_font.measure(test_text)
                
                if test_render > 0:
                    self.current_font = ("Alibaba PuHuiTi", 10)
                    self.root.option_add("*Font", self.current_font)
                    print(f"✅ 成功加载自定义字体: {font_path}")
                    return
                else:
                    print(f"⚠️ 字体渲染失败，将使用系统默认字体")
            except Exception as e:
                print(f"⚠️ 字体加载异常: {e}，将使用系统默认字体")
        
        # 降级方案：使用系统默认字体
        self.current_font = ("Microsoft YaHei", 10) if os.name == 'nt' else ("Arial", 10)
        self.root.option_add("*Font", self.current_font)
        print(f"ℹ️ 使用系统默认字体: {self.current_font[0]}")

    def build_ui(self):
        """构建用户界面"""
        # 视频文件选择区域
        tk.Label(self.root, text="选择视频文件:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
        tk.Entry(self.root, textvariable=self.video_path, width=40).grid(row=0, column=1, padx=10, pady=10)
        tk.Button(self.root, text="浏览...", command=self.select_video).grid(row=0, column=2, padx=10, pady=10)

        # 音频输出文件选择区域
        tk.Label(self.root, text="输出音频文件:").grid(row=1, column=0, padx=10, pady=10, sticky="e")
        tk.Entry(self.root, textvariable=self.audio_path, width=40).grid(row=1, column=1, padx=10, pady=10)
        tk.Button(self.root, text="浏览...", command=self.select_audio).grid(row=1, column=2, padx=10, pady=10)

        # 开始提取按钮
        self.extract_button = tk.Button(self.root, text="开始提取", command=self.extract_audio)
        self.extract_button.grid(row=2, column=1, pady=10)

        # 查看开源协议按钮
        license_button = tk.Button(self.root, text="软件开源协议", command=self.show_license)
        license_button.grid(row=2, column=2, padx=10, pady=10)

        # 状态显示标签
        self.status_label = tk.Label(self.root, text="", fg="green")
        self.status_label.grid(row=3, column=1, pady=5)
        
        # 字体信息显示标签（用于调试）
        self.font_info_label = tk.Label(self.root, text=f"当前字体: {self.current_font[0]}", fg="gray", font=("Arial", 8))
        self.font_info_label.grid(row=4, column=1, pady=2)

    def select_video(self):
        """选择视频文件对话框"""
        file_path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[("视频文件", "*.mp4 *.avi *.mkv *.mov"), ("所有文件", "*.*")]
        )
        if file_path:
            self.video_path.set(file_path)
            # 如果音频路径为空，自动生成默认的MP3文件名
            if not self.audio_path.get():
                self.audio_path.set(str(Path(file_path).with_suffix(".mp3")))

    def select_audio(self):
        """选择音频输出文件对话框"""
        default_name = Path(self.video_path.get()).with_suffix(".mp3").name if self.video_path.get() else "output.mp3"
        file_path = filedialog.asksaveasfilename(
            title="保存音频文件",
            initialfile=default_name,
            defaultextension=".mp3",
            filetypes=[("MP3 文件", "*.mp3"), ("WAV 文件", "*.wav"), ("所有文件", "*.*")]
        )
        if file_path:
            self.audio_path.set(file_path)

    def set_window_icon(self):
        """设置应用程序窗口图标"""
        icon_ico_path = ROOT_DIR.parent / "Image" / "icon.ico"
        icon_png_path = ROOT_DIR.parent / "Image" / "icon.png"

        # Windows系统设置应用ID
        if os.name == 'nt':
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.YinPinTiQu")
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

    def extract_audio(self):
        """开始音频提取流程"""
        video_file = self.video_path.get().strip()
        audio_file = self.audio_path.get().strip()

        # 验证输入文件是否有效
        if not video_file or not Path(video_file).is_file():
            messagebox.showerror("错误", "请选择有效的视频文件！")
            return

        # 验证输出路径是否已设置
        if not audio_file:
            messagebox.showerror("错误", "请输入音频输出路径！")
            return

        # 检查FFmpeg是否可用
        if not self.is_ffmpeg_available():
            messagebox.showerror("错误", "FFmpeg 未安装或不在系统路径中。")
            return

        # 禁用按钮并更新状态
        self.extract_button.config(state="disabled")
        self.status_label.config(text="正在提取中...", fg="blue")

        # 在后台线程中执行提取操作，避免界面卡顿
        thread = threading.Thread(target=self.run_extraction, args=(video_file, audio_file), daemon=True)
        thread.start()

    def is_ffmpeg_available(self):
        """检查FFmpeg是否已安装并可用"""
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def run_extraction(self, video_file, audio_file):
        """执行音频提取命令"""
        # 构建FFmpeg命令：从视频中提取音频流并转换为MP3格式
        command = [
            "ffmpeg",
            "-i",           # 输入文件
            video_file,     # 视频文件路径
            "-q:a",         # 音频质量参数
            "0",            # 最高质量
            "-map",         # 选择流
            "a",            # 仅音频流
            "-y",           # 覆盖输出文件
            audio_file      # 输出音频文件路径
        ]

        try:
            # 执行FFmpeg命令
            subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            # 在主线程中更新UI
            self.root.after(0, lambda: self.on_extraction_success(audio_file))
        except subprocess.CalledProcessError as exc:
            # 获取错误信息
            error_text = exc.stderr.strip().splitlines()[-1] if exc.stderr else "音频提取过程中发生错误。"
            self.root.after(0, lambda: self.on_extraction_failure(error_text))

    def on_extraction_success(self, audio_file):
        """提取成功后的回调处理"""
        self.status_label.config(text="✅ 提取成功！", fg="green")
        self.extract_button.config(state="normal")
        messagebox.showinfo("成功", f"音频已保存至：{audio_file}")

    def on_extraction_failure(self, error_message="音频提取过程中发生错误。"):
        """提取失败后的回调处理"""
        self.status_label.config(text="❌ 提取失败！", fg="red")
        self.extract_button.config(state="normal")
        messagebox.showerror("错误", error_message)

    def show_license(self):
        """读取并显示开源协议文档"""
        license_path = ROOT_DIR.parent / "Image" / "LICENSE.txt"
        
        if not license_path.exists():
            messagebox.showerror("错误", f"未找到开源协议文件：{license_path}")
            return
        
        try:
            with open(license_path, 'r', encoding='utf-8') as f:
                license_content = f.read()
            
            # 创建新窗口显示协议内容
            license_window = tk.Toplevel(self.root)
            license_window.title("Apache License 2.0")
            license_window.geometry("550x500")
            
            # 添加滚动条
            scrollbar = tk.Scrollbar(license_window)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 添加文本框显示协议内容
            text_widget = tk.Text(
                license_window, 
                wrap=tk.WORD, 
                yscrollcommand=scrollbar.set,
                font=("Consolas", 10),
                padx=10,
                pady=10
            )
            text_widget.insert(tk.END, license_content)
            text_widget.config(state=tk.DISABLED)  # 设置为只读
            text_widget.pack(fill=tk.BOTH, expand=True)
            
            scrollbar.config(command=text_widget.yview)
            
        except Exception as e:
            messagebox.showerror("错误", f"读取开源协议文件失败：{str(e)}")

if __name__ == "__main__":
    # 创建主窗口并启动应用
    root = tk.Tk()
    app = AudioExtractorApp(root)
    root.mainloop()