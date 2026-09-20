# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import os
import subprocess
import threading
import importlib.util
from pathlib import Path

import flet as ft

from PIL import Image


def get_project_root():
    """返回项目根目录。"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def _resolve_base_class_path():
    """解析公共基类文件路径，打包后自动使用 .pyc 字节码"""
    base_py = get_project_root() / 'Core' / 'Public base class.py'
    if getattr(sys, 'frozen', False):
        return Path(importlib.util.cache_from_source(str(base_py)))
    return base_py


def run_startup_preflight():
    """执行启动前置检查：加载公共基类并验证字体可用性。"""
    base_file = _resolve_base_class_path()

    spec = importlib.util.spec_from_file_location('public_base_class', str(base_file))
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载公共基类：{base_file}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    try:
        base = module.PDFToolBase(root)
        if not root.winfo_exists():
            raise RuntimeError("授权或窗口初始化失败")

        current_font = getattr(base, 'current_font', None)
        if not current_font:
            raise RuntimeError("公共基类未成功加载字体")

        return current_font[0]
    except Exception as exc:
        if root.winfo_exists():
            root.destroy()
        raise RuntimeError(f"启动前置检查失败：无法使用项目自带字体。{exc}") from exc
    finally:
        if root.winfo_exists():
            root.destroy()


APP_FONT_FAMILY = run_startup_preflight()


class ChangTuScrollVideoApp:
    """长图滚动视频工具

    导入一张长图，生成画面内容自下而上滚动的视频。
    底层通过 FFmpeg 的 crop 滤镜按时间平移视口，一次编码输出 H.264/mp4。
    """

    ASPECT_PRESETS = [
        ("9:16 竖屏", 9, 16),
        ("16:9 横屏", 16, 9),
    ]
    DEFAULT_ASPECT = "9:16 竖屏"
    MAX_LONG_SIDE = 1920
    FPS = 30
    SECONDS_PER_VIEWPORT = 2.5
    MIN_DURATION = 3.0
    MAX_DURATION = 60.0

    def __init__(self):
        self.page = None
        self.image_path = None
        self.output_path = None
        self.font_family = APP_FONT_FAMILY
        self.running = False
        self._proc = None

    def build(self, page: ft.Page):
        self.page = page
        page.title = "长图滚动视频"
        page.window.width = 620
        page.window.height = 620
        page.window.center()
        page.padding = 16
        page.theme_mode = ft.ThemeMode.LIGHT

        # 设置窗口图标
        icon_path = get_project_root() / 'Image' / 'icon.ico'
        if icon_path.exists():
            page.window.icon = str(icon_path)

        # 文件选择器
        self.file_picker = ft.FilePicker(on_result=self.on_file_picked)
        self.save_picker = ft.FilePicker(on_result=self.on_save_picked)
        page.overlay.extend([self.file_picker, self.save_picker])

        # 长图选择
        self.file_text = ft.Text(
            "未选择文件",
            size=13,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
            expand=True,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        file_card = self._make_card(
            "长图选择",
            ft.Row(
                [
                    ft.Icon(ft.Icons.PANORAMA, size=18, color=ft.Colors.BLUE_GREY_400),
                    self.file_text,
                    ft.ElevatedButton("选择文件", icon=ft.Icons.UPLOAD_FILE, on_click=self.select_image),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
        )

        # 输出视频
        self.output_text = ft.Text(
            "未设置",
            size=13,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
            expand=True,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        output_card = self._make_card(
            "输出视频",
            ft.Row(
                [
                    ft.Icon(ft.Icons.VIDEO_FILE, size=18, color=ft.Colors.BLUE_GREY_400),
                    self.output_text,
                    ft.ElevatedButton("选择位置", icon=ft.Icons.SAVE, on_click=self.select_output),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
        )

        # 画面比例
        self.aspect_group = ft.RadioGroup(
            value=self.DEFAULT_ASPECT,
            on_change=self.on_aspect_change,
            content=ft.Row(
                [
                    ft.Radio(
                        value=label,
                        label=label,
                        label_style=ft.TextStyle(font_family=self.font_family, size=14),
                    )
                    for label, _, _ in self.ASPECT_PRESETS
                ],
                spacing=20,
            ),
        )
        aspect_card = self._make_card("画面比例", self.aspect_group)

        # 图片信息展示
        self.info_text = ft.Text(
            "请选择一张长图（如长截图、聊天记录、长微博）",
            size=13,
            color=ft.Colors.BLUE_GREY_700,
            font_family=self.font_family,
        )
        info_card = self._make_card("图片信息", self.info_text)

        # 进度条与操作按钮
        self.generate_button = ft.ElevatedButton(
            "开始生成视频",
            icon=ft.Icons.MOVIE_CREATION,
            on_click=self.start_generate,
            height=40,
        )
        self.progress = ft.ProgressBar(
            visible=False,
            color=ft.Colors.BLUE,
            bgcolor=ft.Colors.GREY_200,
            bar_height=6,
            border_radius=4,
            expand=True,
        )
        self.progress_text = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)

        # 状态栏
        self.status_text = ft.Text("就绪", size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)

        page.add(
            ft.Row(
                [
                    ft.Icon(ft.Icons.MOVIE_CREATION, size=32, color=ft.Colors.BLUE),
                    ft.Text("长图滚动视频", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            ft.Divider(thickness=1, opacity=0.3),
            file_card,
            output_card,
            aspect_card,
            info_card,
            ft.Row(
                [self.progress, self.progress_text],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            ft.Row([self.generate_button], alignment=ft.MainAxisAlignment.END),
            ft.Container(
                content=self.status_text,
                padding=ft.padding.symmetric(vertical=8, horizontal=12),
                bgcolor=ft.Colors.BLUE_GREY_50,
                border_radius=8,
                border=ft.border.all(1, ft.Colors.GREY_300),
            ),
        )

        # 窗口关闭事件
        page.window.on_close = self.on_window_close

        return page

    def _make_card(self, title, content):
        """创建统一的白色卡片容器。"""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        title,
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_GREY_700,
                        font_family=self.font_family,
                    ),
                    content,
                ],
                spacing=8,
            ),
            padding=ft.padding.all(12),
            border_radius=10,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )

    def select_image(self, e):
        self.file_picker.pick_files(
            dialog_title="选择长图",
            allow_multiple=False,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["png", "jpg", "jpeg", "webp", "bmp"],
        )

    def on_file_picked(self, e):
        if not e.files:
            return
        file = e.files[0].path
        if not os.path.exists(file):
            self.show_status("文件不存在", success=False)
            return
        self.image_path = file
        self.file_text.value = os.path.basename(file)
        self.file_text.color = ft.Colors.BLUE_GREY_900
        # 默认输出路径
        if not self.output_path:
            self.output_path = str(Path(file).with_suffix(".mp4"))
            self.output_text.value = self.output_path
            self.output_text.color = ft.Colors.BLUE_GREY_900
        self.refresh_info()
        self.page.update()

    def select_output(self, e):
        default_name = Path(self.image_path).with_suffix(".mp4").name if self.image_path else "scroll_video.mp4"
        self.save_picker.save_file(
            dialog_title="保存视频",
            file_name=default_name,
            allowed_extensions=["mp4"],
        )

    def on_save_picked(self, e):
        if not e.path:
            return
        self.output_path = e.path
        self.output_text.value = e.path
        self.output_text.color = ft.Colors.BLUE_GREY_900
        self.page.update()

    def on_aspect_change(self, e):
        if self.image_path:
            self.refresh_info()

    def refresh_info(self):
        """读取图片尺寸并刷新预计的输出参数。"""
        path = self.image_path
        if not path or not Path(path).is_file():
            self.info_text.value = "请选择一张长图（如长截图、聊天记录、长微博）"
            return

        try:
            with Image.open(path) as im:
                w, h = im.size
                has_alpha = im.mode in ("RGBA", "LA", "PA") or (
                    im.mode == "P" and "transparency" in im.info
                )
        except Exception as e:
            self.info_text.value = f"无法读取图片：{e}"
            return

        label, _aw, _ah = self._current_aspect()
        params = self.compute_params(w, h)
        if params is None:
            self.info_text.value = (
                f"图片尺寸：{w}×{h}\n"
                f"高度不足一个 {label} 视口（至少需高于 {self._viewport_height(w)} px），无法滚动，请换更长的图片。"
            )
            return

        text = (
            f"图片尺寸：{w}×{h}    输出分辨率：{params['W_out']}×{params['H_out']}（{label}）\n"
            f"滚动距离：{params['scroll_dist']} px    预计时长：{params['duration']:.1f} 秒    "
            f"帧率：{self.FPS} fps"
        )
        if has_alpha:
            text += "\n提示：图片含透明通道，透明区域在视频中会显示为黑色。"
        self.info_text.value = text

    @staticmethod
    def _round_even(n):
        """取不小于 n 的最近偶数（H.264 要求宽高为偶数）。"""
        n = int(round(n))
        if n < 2:
            return 2
        return n if n % 2 == 0 else n + 1

    def _current_aspect(self):
        """返回当前选中的画面比例 (名称, 宽比, 高比)。"""
        selected = self.aspect_group.value if hasattr(self, 'aspect_group') else self.DEFAULT_ASPECT
        for label, aw, ah in self.ASPECT_PRESETS:
            if label == selected:
                return label, aw, ah
        return self.ASPECT_PRESETS[0]

    def _viewport_height(self, img_w):
        """按当前比例计算源图中一个视口的高度（偶数）。"""
        _label, aw, ah = self._current_aspect()
        return self._round_even(img_w * ah / aw)

    def compute_params(self, img_w, img_h):
        """根据图片尺寸与当前画面比例计算输出参数。"""
        _label, aw, ah = self._current_aspect()
        crop_h = self._round_even(img_w * ah / aw)
        scroll_dist = img_h - crop_h
        if scroll_dist <= 0:
            return None

        max_w = int(self.MAX_LONG_SIDE * aw / max(aw, ah))
        W_out = self._round_even(min(img_w, max_w))
        H_out = self._round_even(W_out * ah / aw)

        duration = self.SECONDS_PER_VIEWPORT * scroll_dist / crop_h
        duration = max(self.MIN_DURATION, min(self.MAX_DURATION, duration))

        return {
            "W_out": W_out,
            "H_out": H_out,
            "crop_h": crop_h,
            "scroll_dist": scroll_dist,
            "duration": duration,
        }

    def _ffmpeg_candidates(self):
        """枚举所有 ffmpeg 可执行文件候选。"""
        names = ("ffmpeg.exe", "ffmpeg") if os.name == "nt" else ("ffmpeg",)
        seen = []
        for directory in os.environ.get("PATH", "").split(os.pathsep):
            if not directory:
                continue
            for name in names:
                candidate = os.path.join(directory, name)
                if os.path.isfile(candidate) and candidate not in seen:
                    seen.append(candidate)
        return seen

    def _resolve_ffmpeg(self):
        """返回可用的 ffmpeg 绝对路径，找不到则返回 None。"""
        for candidate in self._ffmpeg_candidates():
            try:
                result = subprocess.run(
                    [candidate, "-hide_banner", "-version"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if result.returncode == 0:
                    return candidate
            except Exception:
                continue
        return None

    def start_generate(self, e):
        """校验输入并启动后台生成线程。"""
        if self.running:
            return

        if not self.image_path or not Path(self.image_path).is_file():
            self.show_status("请选择有效的图片文件", success=False)
            return
        if not self.output_path:
            self.show_status("请设置输出视频路径", success=False)
            return

        # 检查 ffmpeg
        ffmpeg = self._resolve_ffmpeg()
        if ffmpeg is None:
            self.show_status(
                "未找到可用的 FFmpeg，请安装较新版本：winget install Gyan.FFmpeg",
                success=False,
            )
            return

        # 读取图片尺寸
        try:
            with Image.open(self.image_path) as im:
                w, h = im.size
        except Exception as e:
            self.show_status(f"读取图片失败：{e}", success=False)
            return

        params = self.compute_params(w, h)
        if params is None:
            label, _, _ = self._current_aspect()
            self.show_status(f"图片高度不足一个 {label} 视口，无法生成滚动视频", success=False)
            return

        # 输出文件已存在时覆盖
        if Path(self.output_path).exists():
            try:
                os.remove(self.output_path)
            except Exception:
                pass

        self.running = True
        self.generate_button.disabled = True
        self.progress.value = 0
        self.progress.visible = True
        self.progress_text.value = "0%"
        self.show_status("正在生成视频...")

        threading.Thread(
            target=self._run_generation,
            args=(ffmpeg, self.image_path, self.output_path, params),
            daemon=True,
        ).start()

    def _run_generation(self, ffmpeg_exe, image_file, output_file, params):
        """执行 FFmpeg 生成滚动视频。"""
        crop_h = params["crop_h"]
        W_out = params["W_out"]
        H_out = params["H_out"]
        duration = params["duration"]
        dur_str = f"{duration:.3f}"

        vf = (
            f"crop=iw:{crop_h}:0:'min(ih-{crop_h},(ih-{crop_h})*t/{dur_str})',"
            f"scale={W_out}:{H_out}"
        )
        command = [
            ffmpeg_exe, "-hide_banner", "-nostats", "-loglevel", "error",
            "-loop", "1", "-framerate", str(self.FPS), "-i", image_file,
            "-t", dur_str,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-progress", "pipe:1",
            "-y", output_file,
        ]

        err_lines = []
        try:
            self._proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="ignore",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

            # 独立线程排空 stderr
            def _drain_stderr():
                for line in self._proc.stderr:
                    err_lines.append(line)
            threading.Thread(target=_drain_stderr, daemon=True).start()

            # 读取进度
            for line in self._proc.stdout:
                line = line.strip()
                if line.startswith("out_time="):
                    current = self._parse_time(line.split("=", 1)[1])
                    frac = min(1.0, current / duration) if duration > 0 else 0.0
                    self._update_progress(frac)

            self._proc.wait()
            returncode = self._proc.returncode
        except Exception as e:
            self.show_status(f"生成过程发生异常：{e}", success=False)
            self._finish_generation(False)
            return
        finally:
            self._proc = None

        if returncode == 0:
            self._update_progress(1.0)
            self.show_status("视频生成成功！")
            self.show_info("成功", f"视频已保存至：\n{output_file}")
        else:
            msg = self._extract_error("".join(err_lines))
            self.show_status(f"生成失败: {msg}", success=False)
        self._finish_generation(returncode == 0)

    def _finish_generation(self, success):
        """生成完成后恢复界面状态。"""
        self.running = False
        self.generate_button.disabled = False
        self.generate_button.update()

    @staticmethod
    def _parse_time(tstr):
        """解析 ffmpeg 的 HH:MM:SS.micro 时间戳为秒。"""
        try:
            h, m, s = tstr.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
        except Exception:
            return 0.0

    @staticmethod
    def _extract_error(stderr_text):
        """从 ffmpeg 的 stderr 中挑出最能说明问题的错误行。"""
        lines = [ln.strip() for ln in stderr_text.splitlines() if ln.strip()]
        if not lines:
            return "FFmpeg 生成视频失败。"
        for keyword in ("Unrecognized option", "Unknown encoder", "Invalid",
                        "No such file", "does not exist", "Error"):
            for i, ln in enumerate(lines):
                if keyword in ln:
                    return "\n".join(lines[i:i + 2])
        return "\n".join(lines[-2:])

    def _update_progress(self, frac):
        """更新进度条和进度文本。"""
        self.progress.value = frac
        self.progress_text.value = f"{int(frac * 100)}%"
        self.progress.update()
        self.progress_text.update()

    def on_window_close(self, e):
        """窗口关闭时终止 ffmpeg 子进程。"""
        if self._proc is not None:
            try:
                self._proc.terminate()
            except Exception:
                pass
        self.page.window.destroy()

    def show_status(self, message: str, success: bool = True):
        """更新状态栏并显示全局提示消息。"""
        self.status_text.value = message
        self.page.snack_bar = ft.SnackBar(
            ft.Text(message, font_family=self.font_family),
            bgcolor=ft.Colors.GREEN if success else ft.Colors.RED,
            open=True,
        )
        self.page.update()

    def show_info(self, title: str, message: str):
        """显示结果弹窗。"""
        self.page.dialog = ft.AlertDialog(
            title=ft.Text(title, font_family=self.font_family),
            content=ft.Text(message, font_family=self.font_family),
            actions=[ft.TextButton("关闭", on_click=lambda e: self.close_dialog())],
        )
        self.page.dialog.open = True
        self.page.update()

    def close_dialog(self, e=None):
        """关闭当前对话框。"""
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()


if __name__ == '__main__':
    app = ChangTuScrollVideoApp()
    ft.app(target=app.build)
