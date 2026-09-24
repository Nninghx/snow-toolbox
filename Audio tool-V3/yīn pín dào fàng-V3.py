# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import os
import threading
import tempfile
import subprocess
import importlib.util
from pathlib import Path
from dataclasses import dataclass

import numpy as np
import flet as ft
from pydub import AudioSegment

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


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


# ==================== 常量 ====================

INPUT_EXTENSIONS = ["mp3", "wav", "flac", "ogg", "m4a", "aac", "opus", "aiff", "wma", "aif"]

# 输出格式选项：key -> (显示名, pydub export format, 是否需要 ffmpeg)
OUTPUT_FORMATS = {
    "keep":    ("保持源格式",        None,   False),
    "mp3":     ("MP3  (有损)",       "mp3",  True),
    "wav":     ("WAV  (无损 PCM)",   "wav",  False),
    "flac":    ("FLAC (无损压缩)",   "flac", False),
    "ogg":     ("OGG  (Vorbis)",     "ogg",  True),
    "m4a":     ("M4A  (AAC)",        "m4a",  True),
}


@dataclass
class FileItem:
    path: str
    name: str
    size_bytes: int
    duration_ms: int
    src_ext: str


class AudioReverseApp:
    """音频倒放工具

    - 支持批量导入音频文件，一键全部倒放
    - 显示原始波形与倒放后波形的对比预览
    - 输出格式可选：保持源格式 / MP3 / WAV / FLAC / OGG / M4A
    - 依赖系统 FFmpeg（用于非 WAV 格式）
    """

    def __init__(self):
        self.page = None
        self.font_family = APP_FONT_FAMILY
        self.items: list[FileItem] = []
        self.running = False

        # 输出设置
        self.output_dir: str | None = None
        self.output_format_key: str = "keep"
        self.bitrate: str = "192k"
        self.filename_suffix: str = "_reversed"

        # 预览
        self.preview_audio: AudioSegment | None = None
        self.preview_reversed: AudioSegment | None = None
        self.waveform_image_path: str | None = None

        # 目录选择器意图标记（'input' = 导入文件夹，'output' = 输出目录）
        self._last_dir_intent: str = 'output'

        # 统计
        self.success_count = 0
        self.failed_count = 0

    def build(self, page: ft.Page):
        self.page = page
        page.title = "音频倒放"
        page.window.width = 1080
        page.window.height = 820
        page.window.center()
        page.padding = 16
        page.theme_mode = ft.ThemeMode.LIGHT
        page.scroll = ft.ScrollMode.AUTO

        # 设置窗口图标
        icon_path = get_project_root() / 'Image' / 'icon.ico'
        if icon_path.exists():
            page.window.icon = str(icon_path)

        # 文件选择器
        self.file_picker = ft.FilePicker(on_result=self.on_files_picked)
        self.output_dir_picker = ft.FilePicker(on_result=self.on_output_dir_picked)
        page.overlay.extend([self.file_picker, self.output_dir_picker])

        # --- 顶部标题栏 ---
        header = ft.Row(
            [
                ft.Icon(ft.Icons.REPLAY, size=32, color=ft.Colors.INDIGO),
                ft.Text("音频倒放", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                ft.Container(width=8),
                ft.Text(
                    "把音频从尾到头翻转 · 支持批量 · 波形对比预览",
                    size=13,
                    color=ft.Colors.BLUE_GREY_500,
                    font_family=self.font_family,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        )

        # FFmpeg 状态提示
        self.ffmpeg_status = ft.Text("", size=12, font_family=self.font_family)
        self._check_ffmpeg_ui()

        # --- 文件列表工具栏 ---
        list_toolbar = ft.Row(
            [
                ft.ElevatedButton(
                    "添加音频文件",
                    icon=ft.Icons.ADD,
                    on_click=self.pick_files,
                ),
                ft.OutlinedButton(
                    "添加整个文件夹",
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=self.pick_input_folder,
                ),
                ft.OutlinedButton(
                    "清空列表",
                    icon=ft.Icons.DELETE_SWEEP,
                    on_click=self.clear_list,
                    style=ft.ButtonStyle(color=ft.Colors.RED_700),
                ),
                ft.Container(expand=True),
                self._make_stat_label(),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # --- 文件列表 ---
        self.items_column = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=170)
        self.empty_hint = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.LIBRARY_MUSIC, size=48, color=ft.Colors.GREY_300),
                    ft.Text("还没有音频文件", size=14, color=ft.Colors.GREY_500,
                            font_family=self.font_family),
                    ft.Text(f"支持: {', '.join(INPUT_EXTENSIONS[:6])} 等", size=12,
                            color=ft.Colors.GREY_400, font_family=self.font_family),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=6,
            ),
            height=140,
            alignment=ft.alignment.center,
            border_radius=8,
            bgcolor=ft.Colors.GREY_50,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )
        list_card = self._make_card(
            "待倒放音频（双击列表项可预览波形）",
            ft.Column([self.empty_hint, self.items_column], spacing=6),
        )

        # --- 波形对比预览 ---
        self.waveform_image = ft.Image(
            src="",
            width=1010,
            height=260,
            fit=ft.ImageFit.FILL,
            visible=False,
        )
        self.waveform_placeholder = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.SHOW_CHART, size=48, color=ft.Colors.GREY_300),
                    ft.Text("点击上方【预览】按钮查看波形对比", size=14,
                            color=ft.Colors.GREY_500, font_family=self.font_family),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=1010,
            height=260,
            alignment=ft.alignment.center,
            border_radius=8,
            bgcolor=ft.Colors.GREY_50,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )

        self.preview_button = ft.OutlinedButton(
            "生成波形预览",
            icon=ft.Icons.VISIBILITY,
            on_click=self.generate_preview,
            disabled=True,
        )
        preview_toolbar = ft.Row(
            [
                self.preview_button,
                ft.Text(
                    "上：原始波形  ·  下：倒放后波形",
                    size=12, color=ft.Colors.BLUE_GREY_600,
                    font_family=self.font_family, italic=True,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        waveform_card = self._make_card(
            "波形对比预览（预览列表中选中的第一个文件）",
            ft.Column([preview_toolbar,
                       ft.Stack([self.waveform_placeholder, self.waveform_image])],
                      spacing=8),
        )

        # --- 输出设置 ---
        self.format_dropdown = ft.Dropdown(
            label="输出格式",
            value=self.output_format_key,
            width=200,
            text_size=13,
            options=[ft.dropdown.Option(k, v[0]) for k, v in OUTPUT_FORMATS.items()],
            on_change=self.on_format_change,
        )
        self.bitrate_dropdown = ft.Dropdown(
            label="比特率",
            value=self.bitrate,
            width=130,
            text_size=13,
            disabled=True,
            options=[ft.dropdown.Option(b, b) for b in ["128k", "192k", "256k", "320k"]],
            on_change=self.on_bitrate_change,
        )
        self.suffix_field = ft.TextField(
            label="文件名后缀",
            value=self.filename_suffix,
            width=170,
            text_size=13,
            on_change=self.on_suffix_change,
        )

        self.output_dir_text = ft.Text(
            "未选择（默认与源文件同目录）",
            size=13, color=ft.Colors.BLUE_GREY_500, font_family=self.font_family,
            expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
        )
        output_dir_row = ft.Row(
            [
                ft.Icon(ft.Icons.FOLDER, size=18, color=ft.Colors.INDIGO_400),
                self.output_dir_text,
                ft.OutlinedButton(
                    "选择输出目录",
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=self.pick_output_folder,
                ),
                ft.TextButton("清除", icon=ft.Icons.CLEAR, on_click=self.clear_output_dir),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        )

        format_row = ft.Row(
            [self.format_dropdown, self.bitrate_dropdown, self.suffix_field],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
        )

        output_card = self._make_card(
            "输出设置",
            ft.Column([format_row, output_dir_row], spacing=10),
        )

        # --- 操作区 ---
        self.reverse_button = ft.ElevatedButton(
            "开始倒放并导出",
            icon=ft.Icons.REPLAY,
            on_click=self.start_reverse,
            height=44,
            disabled=True,
            style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO, color=ft.Colors.WHITE),
        )
        self.progress = ft.ProgressBar(
            visible=False, width=280,
            color=ft.Colors.INDIGO, bgcolor=ft.Colors.GREY_200,
            bar_height=8, border_radius=4,
        )
        self.progress_text = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_700,
                                     font_family=self.font_family)

        action_row = ft.Row(
            [
                self.progress,
                self.progress_text,
                ft.Container(expand=True),
                self.reverse_button,
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # --- 状态栏 ---
        self.status_text = ft.Text(
            "就绪 - 请添加音频文件",
            size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family,
        )
        status_bar = ft.Container(
            content=ft.Column([self.ffmpeg_status, self.status_text], spacing=4),
            padding=ft.padding.symmetric(vertical=8, horizontal=12),
            bgcolor=ft.Colors.BLUE_GREY_50,
            border_radius=8,
            border=ft.border.all(1, ft.Colors.GREY_300),
        )

        page.add(
            header,
            ft.Divider(thickness=1, opacity=0.3),
            list_toolbar,
            list_card,
            waveform_card,
            output_card,
            action_row,
            status_bar,
        )
        return page

    # ==================== UI 辅助 ====================

    def _make_card(self, title, content):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(title, size=13, weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_GREY_700, font_family=self.font_family),
                    content,
                ],
                spacing=8,
            ),
            padding=ft.padding.all(12),
            border_radius=10,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )

    def _make_stat_label(self):
        self.stat_text = ft.Text(
            "共 0 个文件 · 0.00 MB",
            size=13, weight=ft.FontWeight.BOLD,
            color=ft.Colors.INDIGO_800, font_family=self.font_family,
        )
        return ft.Container(
            content=self.stat_text,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            bgcolor=ft.Colors.INDIGO_50,
            border_radius=6,
            border=ft.border.all(1, ft.Colors.INDIGO_200),
        )

    def show_status(self, message: str, success: bool = True):
        self.status_text.value = message
        self.status_text.color = ft.Colors.BLUE_GREY_700 if success else ft.Colors.RED_700
        self.page.snack_bar = ft.SnackBar(
            ft.Text(message, font_family=self.font_family),
            bgcolor=ft.Colors.GREEN if success else ft.Colors.RED,
            open=True,
        )
        self.page.update()

    def _check_ffmpeg_ui(self):
        if self._is_ffmpeg_available():
            self.ffmpeg_status.value = "✅ FFmpeg 已就绪"
            self.ffmpeg_status.color = ft.Colors.GREEN_700
        else:
            self.ffmpeg_status.value = (
                "⚠️ 未检测到 FFmpeg，非 WAV 格式将无法读取或导出。"
                "请安装：winget install Gyan.FFmpeg"
            )
            self.ffmpeg_status.color = ft.Colors.RED_700

    @staticmethod
    def _is_ffmpeg_available() -> bool:
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    # ==================== 文件管理 ====================

    def pick_files(self, e):
        self.file_picker.pick_files(
            dialog_title="选择音频文件（可多选）",
            allow_multiple=True,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=INPUT_EXTENSIONS,
        )

    def on_files_picked(self, e: ft.FilePickerResultEvent):
        if not e.files:
            return
        paths = [f.path for f in e.files if f.path]
        self._add_paths(paths)

    def on_output_dir_picked(self, e: ft.FilePickerResultEvent):
        """output_dir_picker 同时用于「添加文件夹」和「选择输出目录」。

        通过 dialog_title 无法区分，这里通过 heuristic：
        - 若目录中包含音频文件且当前列表为空，视为"添加文件夹"
        - 否则视为"选择输出目录"
        为避免歧义，本工具默认将 dir 选择器视为输出目录；
        "添加整个文件夹"按钮走此逻辑：先扫描，若扫到音频则批量导入，否则设为输出目录。
        """
        if not e.path or not os.path.isdir(e.path):
            return

        # 扫描该目录中的音频文件
        audio_paths = []
        for name in sorted(os.listdir(e.path)):
            full = os.path.join(e.path, name)
            if os.path.isfile(full) and Path(name).suffix.lstrip('.').lower() in INPUT_EXTENSIONS:
                audio_paths.append(full)

        # 判定意图：若最近一次点击是"添加整个文件夹"，则导入
        if self._last_dir_intent == 'input' and audio_paths:
            self._add_paths(audio_paths)
        elif self._last_dir_intent == 'input' and not audio_paths:
            self.show_status(f"文件夹中没有找到支持的音频: {e.path}", success=False)
        else:
            # 输出目录
            self.output_dir = e.path
            self.output_dir_text.value = e.path
            self.output_dir_text.color = ft.Colors.BLUE_GREY_900
            self.page.update()
            self.show_status(f"输出目录: {e.path}")

    def pick_input_folder(self, e):
        self._last_dir_intent = 'input'
        self.output_dir_picker.get_directory_path(dialog_title="选择包含音频的文件夹")

    def pick_output_folder(self, e):
        self._last_dir_intent = 'output'
        self.output_dir_picker.get_directory_path(dialog_title="选择输出目录")

    def _add_paths(self, paths: list[str]):
        if not paths:
            return
        self.show_status(f"正在加载 {len(paths)} 个文件...")
        self.running = True
        threading.Thread(target=self._load_worker, args=(paths,), daemon=True).start()

    def _load_worker(self, paths: list[str]):
        loaded: list[FileItem] = []
        failed: list[str] = []
        existing = {it.path for it in self.items}

        for p in paths:
            if p in existing or not os.path.isfile(p):
                continue
            try:
                audio = AudioSegment.from_file(p)
                loaded.append(FileItem(
                    path=p,
                    name=os.path.basename(p),
                    size_bytes=os.path.getsize(p),
                    duration_ms=len(audio),
                    src_ext=Path(p).suffix.lower().lstrip('.'),
                ))
                existing.add(p)
            except Exception as err:
                failed.append(f"{os.path.basename(p)}: {err}")

        self.items.extend(loaded)
        self.running = False

        self._refresh_list()
        self._update_stat()
        self._update_buttons()

        if failed:
            self.show_status(
                f"已加载 {len(loaded)} 个，{len(failed)} 个失败：" + "; ".join(failed[:2]),
                success=False,
            )
        else:
            self.show_status(f"已加载 {len(loaded)} 个音频文件")

    def clear_list(self, e):
        if not self.items:
            return
        self.items.clear()
        self.preview_audio = None
        self.preview_reversed = None
        self.waveform_image.visible = False
        self.waveform_placeholder.visible = True
        self._refresh_list()
        self._update_stat()
        self._update_buttons()
        self.show_status("已清空列表")

    def remove_item(self, index: int):
        if 0 <= index < len(self.items):
            removed = self.items.pop(index)
            self._refresh_list()
            self._update_stat()
            self._update_buttons()
            self.show_status(f"已移除: {removed.name}")

    def clear_output_dir(self, e):
        self.output_dir = None
        self.output_dir_text.value = "未选择（默认与源文件同目录）"
        self.output_dir_text.color = ft.Colors.BLUE_GREY_500
        self.page.update()

    # ==================== 列表 UI ====================

    def _refresh_list(self):
        self.items_column.controls.clear()
        if not self.items:
            self.empty_hint.visible = True
        else:
            self.empty_hint.visible = False
            for idx, item in enumerate(self.items):
                self.items_column.controls.append(self._build_row(idx, item))
        self.page.update()

    def _build_row(self, index: int, item: FileItem) -> ft.Control:
        duration_sec = item.duration_ms / 1000.0
        duration_str = f"{int(duration_sec // 60):02d}:{duration_sec % 60:05.2f}"
        size_str = self._format_size(item.size_bytes)

        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Text(str(index + 1), size=11, weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.WHITE, font_family=self.font_family),
                        bgcolor=ft.Colors.INDIGO,
                        border_radius=10,
                        width=24, height=24,
                        alignment=ft.alignment.center,
                    ),
                    ft.Container(
                        content=ft.Text(item.src_ext.upper(), size=10, weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.INDIGO_800, font_family=self.font_family),
                        bgcolor=ft.Colors.INDIGO_100,
                        border_radius=4,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    ),
                    ft.Text(item.name, size=13, expand=True, no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            color=ft.Colors.BLUE_GREY_900, font_family=self.font_family),
                    ft.Text(duration_str, size=12, width=70,
                            color=ft.Colors.BLUE_GREY_700, font_family="Consolas"),
                    ft.Text(size_str, size=12, width=80,
                            color=ft.Colors.BLUE_GREY_700, font_family="Consolas"),
                    ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_size=18,
                                  icon_color=ft.Colors.RED_400, tooltip="移除",
                                  on_click=lambda e, i=index: self.remove_item(i)),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            border_radius=6,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.INDIGO_100),
            ink=True,
            on_click=lambda e, i=index: self._preview_index(i),
        )

    def _preview_index(self, index: int):
        """点击列表项，将该文件设为预览目标。"""
        if not (0 <= index < len(self.items)):
            return
        item = self.items[index]
        self.show_status(f"预览目标: {item.name}（点击【生成波形预览】查看）")

    @staticmethod
    def _format_size(n: int) -> str:
        if n < 1024:
            return f"{n} B"
        if n < 1024 ** 2:
            return f"{n / 1024:.1f} KB"
        return f"{n / 1024 ** 2:.2f} MB"

    def _update_stat(self):
        n = len(self.items)
        total_size = sum(it.size_bytes for it in self.items)
        self.stat_text.value = f"共 {n} 个文件 · {self._format_size(total_size)}"
        self.page.update()

    def _update_buttons(self):
        has_files = len(self.items) > 0
        self.reverse_button.disabled = (not has_files) or self.running
        self.preview_button.disabled = (not has_files) or self.running
        self.page.update()

    # ==================== 波形预览 ====================

    def generate_preview(self, e):
        """为列表中第一个文件生成原始 vs 倒放波形对比。"""
        if not self.items:
            return
        self.show_status("正在生成波形预览...")
        self.preview_button.disabled = True
        self.page.update()
        threading.Thread(target=self._preview_worker, args=(self.items[0].path,), daemon=True).start()

    def _preview_worker(self, path: str):
        try:
            audio = AudioSegment.from_file(path)
            reversed_audio = audio.reverse()
            self.preview_audio = audio
            self.preview_reversed = reversed_audio

            self._render_compare_waveform(audio, reversed_audio, os.path.basename(path))

            self.waveform_placeholder.visible = False
            self.waveform_image.visible = True
            self.waveform_image.src = self.waveform_image_path
            self.show_status(f"波形预览已生成: {os.path.basename(path)}")
        except Exception as err:
            self.show_status(f"预览失败: {err}", success=False)
        finally:
            self._update_buttons()

    def _render_compare_waveform(self, audio: AudioSegment, reversed_audio: AudioSegment, name: str):
        """上下并列渲染原始与倒放波形。"""
        def to_mono_samples(seg: AudioSegment) -> np.ndarray:
            arr = np.array(seg.get_array_of_samples(), dtype=np.float32)
            if seg.channels == 2:
                arr = arr.reshape((-1, 2)).mean(axis=1)
            return arr

        def downsample(samples: np.ndarray, duration_sec: float, max_points: int = 4000):
            if len(samples) <= max_points:
                return samples, samples, np.linspace(0, duration_sec, len(samples))
            chunk = len(samples) // max_points
            peaks = np.array([samples[i * chunk:(i + 1) * chunk].max() for i in range(max_points)])
            troughs = np.array([samples[i * chunk:(i + 1) * chunk].min() for i in range(max_points)])
            time_axis = np.linspace(0, duration_sec, max_points)
            return peaks, troughs, time_axis

        orig = to_mono_samples(audio)
        rev = to_mono_samples(reversed_audio)
        duration_sec = len(audio) / 1000.0

        o_peaks, o_troughs, o_time = downsample(orig, duration_sec)
        r_peaks, r_troughs, r_time = downsample(rev, duration_sec)

        fig, axes = plt.subplots(2, 1, figsize=(12.6, 3.2), dpi=100, sharex=True)
        fig.patch.set_facecolor('#FAFAFA')

        for ax, peaks, troughs, t, color, edge, title in [
            (axes[0], o_peaks, o_troughs, o_time, '#5C6BC0', '#283593', f'原始波形  ·  {name}'),
            (axes[1], r_peaks, r_troughs, r_time, '#EC407A', '#AD1457', '倒放后波形'),
        ]:
            ax.set_facecolor('#FAFAFA')
            ax.fill_between(t, troughs, peaks, color=color, alpha=0.75, linewidth=0)
            ax.plot(t, peaks, color=edge, linewidth=0.3, alpha=0.85)
            ax.plot(t, troughs, color=edge, linewidth=0.3, alpha=0.85)
            ax.set_xlim(0, duration_sec)
            ax.set_title(title, fontsize=10, loc='left', color=edge, weight='bold')
            ax.set_ylabel('振幅', fontsize=9)
            ax.tick_params(labelsize=8)
            ax.grid(True, alpha=0.3)

        axes[1].set_xlabel('时间 (秒)', fontsize=9)
        plt.tight_layout(pad=0.5)

        tmp_dir = tempfile.gettempdir()
        img_path = os.path.join(tmp_dir, 'audio_reverse_preview.png')
        fig.savefig(img_path, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)

        self.waveform_image_path = img_path

    # ==================== 输出参数 ====================

    def on_format_change(self, e):
        self.output_format_key = e.control.value
        # 只有有损格式才启用比特率
        need_bitrate = self.output_format_key in ("mp3", "ogg", "m4a")
        self.bitrate_dropdown.disabled = not need_bitrate
        if not need_bitrate:
            self.bitrate_dropdown.value = None
        self.page.update()

    def on_bitrate_change(self, e):
        self.bitrate = e.control.value

    def on_suffix_change(self, e):
        self.filename_suffix = e.control.value or ""

    # ==================== 转换执行 ====================

    def start_reverse(self, e):
        if not self.items:
            self.show_status("请先添加音频文件", success=False)
            return

        need_ffmpeg = False
        # 判断是否需要 ffmpeg
        for item in self.items:
            if item.src_ext != "wav":
                need_ffmpeg = True
                break
            if self.output_format_key not in ("keep", "wav", "flac"):
                need_ffmpeg = True
                break
        if need_ffmpeg and not self._is_ffmpeg_available():
            self.show_status(
                "FFmpeg 未安装或不在系统路径中，无法处理该组合。"
                "请安装：winget install Gyan.FFmpeg",
                success=False,
            )
            return

        if self.output_dir:
            try:
                os.makedirs(self.output_dir, exist_ok=True)
            except Exception as err:
                self.show_status(f"无法创建输出目录: {err}", success=False)
                return

        self.running = True
        self.success_count = 0
        self.failed_count = 0
        self.reverse_button.disabled = True
        self.preview_button.disabled = True
        self.progress.visible = True
        self.progress.value = 0
        self.progress_text.value = f"0 / {len(self.items)}"
        self.show_status("开始倒放...")

        snapshot = list(self.items)
        threading.Thread(target=self._reverse_worker, args=(snapshot,), daemon=True).start()

    def _reverse_worker(self, items: list[FileItem]):
        total = len(items)
        for idx, item in enumerate(items):
            try:
                out_path = self._compute_output_path(item)
                self._reverse_single(item, out_path)
                self.success_count += 1
                self.progress.value = (idx + 1) / total
                self.progress_text.value = f"{idx + 1} / {total}  ✓ {item.name}"
            except Exception as err:
                self.failed_count += 1
                self.progress_text.value = f"{idx + 1} / {total}  ✗ {item.name}: {err}"
            self.page.update()

        self.running = False
        self.progress.value = 1
        self.page.update()

        msg = f"倒放完成：成功 {self.success_count} 个，失败 {self.failed_count} 个"
        self.show_status(msg, success=(self.failed_count == 0))
        self._show_result_dialog(
            "音频倒放完成",
            f"总文件数: {total}\n"
            f"成功: {self.success_count}\n"
            f"失败: {self.failed_count}\n"
            f"输出格式: {OUTPUT_FORMATS[self.output_format_key][0]}\n"
            f"输出目录: {self.output_dir or '（与源文件同目录）'}"
        )
        self._update_buttons()

    def _reverse_single(self, item: FileItem, out_path: str):
        audio = AudioSegment.from_file(item.path)
        reversed_audio = audio.reverse()

        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

        fmt_key = self.output_format_key
        if fmt_key == "keep":
            export_fmt = item.src_ext
        else:
            export_fmt = OUTPUT_FORMATS[fmt_key][1]

        export_params = {}
        if export_fmt in ("mp3", "ogg", "m4a"):
            export_params["bitrate"] = self.bitrate

        reversed_audio.export(out_path, format=export_fmt, **export_params)

    def _compute_output_path(self, item: FileItem) -> str:
        src_stem = Path(item.path).stem
        new_name = f"{src_stem}{self.filename_suffix}"

        fmt_key = self.output_format_key
        if fmt_key == "keep":
            ext = item.src_ext
        else:
            ext = OUTPUT_FORMATS[fmt_key][1]
        new_name = f"{new_name}.{ext}"

        base_dir = self.output_dir or os.path.dirname(item.path)
        return os.path.join(base_dir, new_name)

    def _show_result_dialog(self, title: str, message: str):
        self.page.dialog = ft.AlertDialog(
            title=ft.Text(title, font_family=self.font_family),
            content=ft.Text(message, font_family=self.font_family),
            actions=[ft.TextButton("关闭", on_click=lambda e: self._close_dialog())],
        )
        self.page.dialog.open = True
        self.page.update()

    def _close_dialog(self):
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()


if __name__ == '__main__':
    app = AudioReverseApp()
    ft.app(target=app.build)
