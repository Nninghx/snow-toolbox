# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import os
import math
import time
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

# 输出格式选项：key -> (显示名, 文件扩展名, 是否有损, 是否需要比特率)
OUTPUT_FORMATS = {
    "keep":    ("保持源格式",       None,   False, False),
    "mp3":     ("MP3  (有损)",      "mp3",  True,  True),
    "wav":     ("WAV  (无损 PCM)",  "wav",  False, False),
    "flac":    ("FLAC (无损压缩)",  "flac", False, False),
    "ogg":     ("OGG  (Vorbis)",    "ogg",  True,  True),
    "m4a":     ("M4A  (AAC)",       "m4a",  True,  True),
}

# 处理模式：key -> (显示名, 说明)
PROCESS_MODES = {
    "tempo_only": ("变速不变调", "只改变播放快慢，音调（音高）保持不变，适合调整语速"),
    "pitch_only": ("变调不变速", "只改变音高，时长与速度保持不变，适合升降 Key"),
    "linked":     ("变速又变调（联动）", "速度与音调同步变化，如同快放/慢放磁带，加速即升调"),
    "custom":     ("自由调节", "速度与音调分别独立设置，互不影响"),
}

# 预设：(标签, 模式, 速度, 半音)
PRESETS = [
    ("原速原调",   "custom",     1.0,  0.0),
    ("1.25× 变速", "tempo_only", 1.25, 0.0),
    ("1.5× 变速",  "tempo_only", 1.5,  0.0),
    ("0.8× 慢放",  "tempo_only", 0.8,  0.0),
    ("0.5× 慢放",  "tempo_only", 0.5,  0.0),
    ("升 2 半音",  "pitch_only", 1.0,  2.0),
    ("降 2 半音",  "pitch_only", 1.0,  -2.0),
    ("升 1 八度",  "pitch_only", 1.0,  12.0),
    ("降 1 八度",  "pitch_only", 1.0,  -12.0),
    ("2× 磁带加速", "linked",    2.0,  0.0),
]

TEMPO_MIN = 0.25
TEMPO_MAX = 4.0
PITCH_MIN = -12.0
PITCH_MAX = 12.0


@dataclass
class FileItem:
    path: str
    name: str
    size_bytes: int
    duration_ms: int
    src_ext: str
    frame_rate: int
    channels: int


class AudioSpeedPitchApp:
    """音频变速变调工具

    - 支持批量导入音频文件，一键变速 / 变调
    - 四种处理模式：变速不变调、变调不变速、变速又变调（联动）、自由调节
    - 基于 FFmpeg 滤镜链（asetrate → aresample → atempo）实现高质量处理
    - 提供试听预览与波形对比
    - 依赖系统 FFmpeg（本工具核心功能必须依赖）
    """

    def __init__(self):
        self.page = None
        self.font_family = APP_FONT_FAMILY
        self.items: list[FileItem] = []
        self.running = False

        # 处理参数
        self.mode_key: str = "tempo_only"
        self.tempo: float = 1.0
        self.pitch: float = 0.0

        # 输出设置
        self.output_dir: str | None = None
        self.output_format_key: str = "keep"
        self.bitrate: str = "192k"
        self.filename_suffix: str = "_sp"

        # 预览 / 试听
        self.preview_index: int = 0
        self.waveform_image_path: str | None = None
        self.preview_audio_path: str | None = None

        # 目录选择器意图标记（'input' = 导入文件夹，'output' = 输出目录）
        self._last_dir_intent: str = 'output'

        # 统计
        self.success_count = 0
        self.failed_count = 0

    # ==================== 界面构建 ====================

    def build(self, page: ft.Page):
        self.page = page
        page.title = "音频变速变调"
        page.window.width = 1100
        page.window.height = 900
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
        self.dir_picker = ft.FilePicker(on_result=self.on_dir_picked)
        # 音频播放器（试听）
        self.audio_player = ft.Audio(src="", autoplay=False, volume=100)
        page.overlay.extend([self.file_picker, self.dir_picker, self.audio_player])

        # --- 顶部标题栏 ---
        header = ft.Row(
            [
                ft.Icon(ft.Icons.SPEED, size=32, color=ft.Colors.TEAL),
                ft.Text("变速变调", size=28, weight=ft.FontWeight.BOLD,
                        font_family=self.font_family),
                ft.Container(width=8),
                ft.Text(
                    "调整音频速度与音高 · 变速不变调 / 升降 Key / 磁带联动 · 支持批量与试听",
                    size=13, color=ft.Colors.BLUE_GREY_500, font_family=self.font_family,
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
                ft.ElevatedButton("添加音频文件", icon=ft.Icons.ADD, on_click=self.pick_files),
                ft.OutlinedButton("添加整个文件夹", icon=ft.Icons.FOLDER_OPEN,
                                  on_click=self.pick_input_folder),
                ft.OutlinedButton("清空列表", icon=ft.Icons.DELETE_SWEEP,
                                  on_click=self.clear_list,
                                  style=ft.ButtonStyle(color=ft.Colors.RED_700)),
                ft.Container(expand=True),
                self._make_stat_label(),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # --- 文件列表 ---
        self.items_column = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=150)
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
            height=120,
            alignment=ft.alignment.center,
            border_radius=8,
            bgcolor=ft.Colors.GREY_50,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )
        list_card = self._make_card(
            "待处理音频（单击选中作为试听/预览目标）",
            ft.Column([self.empty_hint, self.items_column], spacing=6),
        )

        # --- 变速变调参数 ---
        self.mode_dropdown = ft.Dropdown(
            label="处理模式",
            value=self.mode_key,
            width=260,
            text_size=13,
            options=[ft.dropdown.Option(k, v[0]) for k, v in PROCESS_MODES.items()],
            on_change=self.on_mode_change,
        )
        self.mode_hint = ft.Text(
            PROCESS_MODES[self.mode_key][1],
            size=12, color=ft.Colors.BLUE_GREY_500, font_family=self.font_family,
            expand=True,
        )

        self.tempo_slider = ft.Slider(
            min=TEMPO_MIN, max=TEMPO_MAX, divisions=int((TEMPO_MAX - TEMPO_MIN) / 0.01),
            value=self.tempo, label="{value}×", active_color=ft.Colors.TEAL,
            on_change=self.on_tempo_slider, expand=True,
        )
        self.tempo_input = ft.TextField(
            label="速度倍率", value="1.00", width=110, text_size=13,
            keyboard_type=ft.KeyboardType.NUMBER, on_change=self.on_tempo_input,
            on_blur=self.on_tempo_input,
        )
        tempo_row = ft.Row(
            [
                ft.Text("速度", width=42, size=13, weight=ft.FontWeight.BOLD,
                        color=ft.Colors.TEAL_800, font_family=self.font_family),
                self.tempo_slider,
                self.tempo_input,
            ],
            spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.pitch_slider = ft.Slider(
            min=PITCH_MIN, max=PITCH_MAX, divisions=int(PITCH_MAX - PITCH_MIN),
            value=self.pitch, label="{value} 半音", active_color=ft.Colors.DEEP_ORANGE,
            on_change=self.on_pitch_slider, expand=True,
        )
        self.pitch_input = ft.TextField(
            label="音调(半音)", value="0", width=110, text_size=13,
            keyboard_type=ft.KeyboardType.NUMBER, on_change=self.on_pitch_input,
            on_blur=self.on_pitch_input,
        )
        pitch_row = ft.Row(
            [
                ft.Text("音调", width=42, size=13, weight=ft.FontWeight.BOLD,
                        color=ft.Colors.DEEP_ORANGE_800, font_family=self.font_family),
                self.pitch_slider,
                self.pitch_input,
            ],
            spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # 预设按钮
        preset_controls = []
        for i, (label, mode, tempo, pitch) in enumerate(PRESETS):
            preset_controls.append(
                ft.OutlinedButton(
                    label, height=30, style=ft.ButtonStyle(
                        color=ft.Colors.TEAL_800, padding=ft.padding.symmetric(horizontal=10),
                    ),
                    on_click=lambda e, idx=i: self.apply_preset(idx),
                )
            )
        preset_row = ft.Row(
            [ft.Text("快捷预设：", size=12, color=ft.Colors.BLUE_GREY_600,
                     font_family=self.font_family)] + preset_controls,
            spacing=6, wrap=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # 时长预估
        self.duration_estimate = ft.Text(
            "预计输出时长：-- （原 --）",
            size=13, weight=ft.FontWeight.BOLD,
            color=ft.Colors.TEAL_800, font_family=self.font_family,
        )
        self.pitch_detail = ft.Text(
            "", size=12, color=ft.Colors.BLUE_GREY_500, font_family=self.font_family,
        )

        param_card = self._make_card(
            "变速变调参数",
            ft.Column(
                [
                    ft.Row([self.mode_dropdown, self.mode_hint], spacing=12,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    tempo_row,
                    pitch_row,
                    ft.Divider(height=1, opacity=0.2),
                    preset_row,
                    ft.Row([self.duration_estimate, ft.Container(width=16), self.pitch_detail],
                           vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True),
                ],
                spacing=12,
            ),
        )

        # --- 试听 / 波形预览 ---
        self.waveform_image = ft.Image(src="", width=1020, height=220,
                                       fit=ft.ImageFit.FILL, visible=False)
        self.waveform_placeholder = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.GRAPHIC_EQ, size=44, color=ft.Colors.GREY_300),
                    ft.Text("点击【生成波形预览】查看处理前后对比", size=14,
                            color=ft.Colors.GREY_500, font_family=self.font_family),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=1020, height=220, alignment=ft.alignment.center,
            border_radius=8, bgcolor=ft.Colors.GREY_50,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )

        self.preview_button = ft.OutlinedButton("生成波形预览", icon=ft.Icons.VISIBILITY,
                                                on_click=self.generate_preview, disabled=True)
        self.listen_button = ft.ElevatedButton("试听处理效果", icon=ft.Icons.PLAY_ARROW,
                                               on_click=self.generate_listen, disabled=True,
                                               style=ft.ButtonStyle(
                                                   bgcolor=ft.Colors.TEAL, color=ft.Colors.WHITE))
        self.stop_button = ft.OutlinedButton("停止", icon=ft.Icons.STOP,
                                             on_click=self.stop_listen, disabled=True)
        self.listen_hint = ft.Text("试听目标：未选择", size=12,
                                   color=ft.Colors.BLUE_GREY_600, font_family=self.font_family)

        preview_toolbar = ft.Row(
            [
                self.listen_button, self.preview_button, self.stop_button,
                ft.Container(width=8),
                self.listen_hint,
                ft.Container(expand=True),
                ft.Text("上：原始  ·  下：处理后", size=12, color=ft.Colors.BLUE_GREY_600,
                        font_family=self.font_family, italic=True),
            ],
            spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True,
        )

        waveform_card = self._make_card(
            "试听与波形预览",
            ft.Column([preview_toolbar,
                       ft.Stack([self.waveform_placeholder, self.waveform_image])],
                      spacing=8),
        )

        # --- 输出设置 ---
        self.format_dropdown = ft.Dropdown(
            label="输出格式", value=self.output_format_key, width=190, text_size=13,
            options=[ft.dropdown.Option(k, v[0]) for k, v in OUTPUT_FORMATS.items()],
            on_change=self.on_format_change,
        )
        self.bitrate_dropdown = ft.Dropdown(
            label="比特率", value=self.bitrate, width=120, text_size=13, disabled=True,
            options=[ft.dropdown.Option(b, b) for b in ["128k", "192k", "256k", "320k"]],
            on_change=self.on_bitrate_change,
        )
        self.suffix_field = ft.TextField(
            label="文件名后缀", value=self.filename_suffix, width=150, text_size=13,
            on_change=self.on_suffix_change,
        )
        self.output_dir_text = ft.Text(
            "未选择（默认与源文件同目录）", size=13, color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family, expand=True, no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        output_dir_row = ft.Row(
            [
                ft.Icon(ft.Icons.FOLDER, size=18, color=ft.Colors.TEAL_400),
                self.output_dir_text,
                ft.OutlinedButton("选择输出目录", icon=ft.Icons.FOLDER_OPEN,
                                  on_click=self.pick_output_folder),
                ft.TextButton("清除", icon=ft.Icons.CLEAR, on_click=self.clear_output_dir),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8,
        )
        format_row = ft.Row(
            [self.format_dropdown, self.bitrate_dropdown, self.suffix_field],
            spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True,
        )
        output_card = self._make_card(
            "输出设置", ft.Column([format_row, output_dir_row], spacing=10),
        )

        # --- 操作区 ---
        self.process_button = ft.ElevatedButton(
            "开始变速变调并导出", icon=ft.Icons.SPEED, on_click=self.start_process,
            height=44, disabled=True,
            style=ft.ButtonStyle(bgcolor=ft.Colors.TEAL, color=ft.Colors.WHITE),
        )
        self.progress = ft.ProgressBar(visible=False, width=280, color=ft.Colors.TEAL,
                                       bgcolor=ft.Colors.GREY_200, bar_height=8,
                                       border_radius=4)
        self.progress_text = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_700,
                                     font_family=self.font_family)
        action_row = ft.Row(
            [self.progress, self.progress_text, ft.Container(expand=True), self.process_button],
            spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # --- 状态栏 ---
        self.status_text = ft.Text("就绪 - 请添加音频文件", size=13,
                                   color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)
        status_bar = ft.Container(
            content=ft.Column([self.ffmpeg_status, self.status_text], spacing=4),
            padding=ft.padding.symmetric(vertical=8, horizontal=12),
            bgcolor=ft.Colors.BLUE_GREY_50, border_radius=8,
            border=ft.border.all(1, ft.Colors.GREY_300),
        )

        page.add(
            header,
            ft.Divider(thickness=1, opacity=0.3),
            list_toolbar,
            list_card,
            param_card,
            waveform_card,
            output_card,
            action_row,
            status_bar,
        )
        self._sync_controls_from_mode()
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
        self.stat_text = ft.Text("共 0 个文件 · 0.00 MB", size=13, weight=ft.FontWeight.BOLD,
                                 color=ft.Colors.TEAL_800, font_family=self.font_family)
        return ft.Container(
            content=self.stat_text,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            bgcolor=ft.Colors.TEAL_50, border_radius=6,
            border=ft.border.all(1, ft.Colors.TEAL_200),
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
            self.ffmpeg_status.value = "✅ FFmpeg 已就绪（变速变调核心依赖）"
            self.ffmpeg_status.color = ft.Colors.GREEN_700
        else:
            self.ffmpeg_status.value = (
                "⚠️ 未检测到 FFmpeg，本工具无法工作。请安装：winget install Gyan.FFmpeg"
            )
            self.ffmpeg_status.color = ft.Colors.RED_700

    @staticmethod
    def _is_ffmpeg_available() -> bool:
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
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

    def on_dir_picked(self, e: ft.FilePickerResultEvent):
        """dir_picker 复用于「添加文件夹」与「选择输出目录」，用意图标记区分。"""
        if not e.path or not os.path.isdir(e.path):
            return
        if self._last_dir_intent == 'input':
            audio_paths = []
            for name in sorted(os.listdir(e.path)):
                full = os.path.join(e.path, name)
                if os.path.isfile(full) and Path(name).suffix.lstrip('.').lower() in INPUT_EXTENSIONS:
                    audio_paths.append(full)
            if audio_paths:
                self._add_paths(audio_paths)
            else:
                self.show_status(f"文件夹中没有找到支持的音频: {e.path}", success=False)
        else:
            self.output_dir = e.path
            self.output_dir_text.value = e.path
            self.output_dir_text.color = ft.Colors.BLUE_GREY_900
            self.page.update()
            self.show_status(f"输出目录: {e.path}")

    def pick_input_folder(self, e):
        self._last_dir_intent = 'input'
        self.dir_picker.get_directory_path(dialog_title="选择包含音频的文件夹")

    def pick_output_folder(self, e):
        self._last_dir_intent = 'output'
        self.dir_picker.get_directory_path(dialog_title="选择输出目录")

    def clear_output_dir(self, e):
        self.output_dir = None
        self.output_dir_text.value = "未选择（默认与源文件同目录）"
        self.output_dir_text.color = ft.Colors.BLUE_GREY_500
        self.page.update()

    def _add_paths(self, paths: list[str]):
        if not paths:
            return
        if not self._is_ffmpeg_available():
            self.show_status("未检测到 FFmpeg，无法处理音频。请先安装 FFmpeg。", success=False)
            return
        self.show_status(f"正在加载 {len(paths)} 个文件...")
        self.running = True
        self._update_buttons()
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
                    frame_rate=audio.frame_rate,
                    channels=audio.channels,
                ))
                existing.add(p)
            except Exception as err:
                failed.append(f"{os.path.basename(p)}: {err}")

        self.items.extend(loaded)
        self.running = False

        self._refresh_list()
        self._update_stat()
        self._update_buttons()
        self._update_duration_estimate()

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
        self.preview_index = 0
        self.waveform_image.visible = False
        self.waveform_placeholder.visible = True
        self.listen_hint.value = "试听目标：未选择"
        self._refresh_list()
        self._update_stat()
        self._update_buttons()
        self._update_duration_estimate()
        self.show_status("已清空列表")

    def remove_item(self, index: int):
        if 0 <= index < len(self.items):
            removed = self.items.pop(index)
            if self.preview_index >= len(self.items):
                self.preview_index = max(0, len(self.items) - 1)
            self._refresh_list()
            self._update_stat()
            self._update_buttons()
            self._update_duration_estimate()
            self.show_status(f"已移除: {removed.name}")

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
        duration_str = self._format_time(item.duration_ms / 1000.0)
        size_str = self._format_size(item.size_bytes)
        selected = (index == self.preview_index)
        border_color = ft.Colors.TEAL if selected else ft.Colors.GREY_200
        bg_color = ft.Colors.TEAL_50 if selected else ft.Colors.WHITE

        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Text(str(index + 1), size=11, weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.WHITE, font_family=self.font_family),
                        bgcolor=ft.Colors.TEAL if selected else ft.Colors.BLUE_GREY_300,
                        border_radius=10, width=24, height=24, alignment=ft.alignment.center,
                    ),
                    ft.Container(
                        content=ft.Text(item.src_ext.upper(), size=10, weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.TEAL_800, font_family=self.font_family),
                        bgcolor=ft.Colors.TEAL_100, border_radius=4,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    ),
                    ft.Text(item.name, size=13, expand=True, no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            color=ft.Colors.BLUE_GREY_900, font_family=self.font_family),
                    ft.Text(duration_str, size=12, width=66,
                            color=ft.Colors.BLUE_GREY_700, font_family="Consolas"),
                    ft.Text(size_str, size=12, width=78,
                            color=ft.Colors.BLUE_GREY_700, font_family="Consolas"),
                    ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_size=18,
                                  icon_color=ft.Colors.RED_400, tooltip="移除",
                                  on_click=lambda e, i=index: self.remove_item(i)),
                ],
                spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            border_radius=6, bgcolor=bg_color, border=ft.border.all(1, border_color),
            ink=True, on_click=lambda e, i=index: self.select_item(i),
        )

    def select_item(self, index: int):
        if not (0 <= index < len(self.items)):
            return
        self.preview_index = index
        item = self.items[index]
        self.listen_hint.value = f"试听目标：{item.name}"
        self._refresh_list()
        self._update_duration_estimate()

    @staticmethod
    def _format_size(n: int) -> str:
        if n < 1024:
            return f"{n} B"
        if n < 1024 ** 2:
            return f"{n / 1024:.1f} KB"
        return f"{n / 1024 ** 2:.2f} MB"

    @staticmethod
    def _format_time(seconds: float) -> str:
        if seconds < 0:
            seconds = 0
        m = int(seconds // 60)
        s = seconds % 60
        return f"{m:02d}:{s:05.2f}"

    def _update_stat(self):
        n = len(self.items)
        total_size = sum(it.size_bytes for it in self.items)
        self.stat_text.value = f"共 {n} 个文件 · {self._format_size(total_size)}"
        self.page.update()

    def _update_buttons(self):
        has_files = len(self.items) > 0
        busy = self.running
        self.process_button.disabled = (not has_files) or busy
        self.preview_button.disabled = (not has_files) or busy
        self.listen_button.disabled = (not has_files) or busy
        self.page.update()

    # ==================== 参数控制 ====================

    def _effective_params(self) -> tuple[float, float]:
        """根据当前模式返回实际应用的 (速度, 半音)。"""
        if self.mode_key == "tempo_only":
            return self.tempo, 0.0
        if self.mode_key == "pitch_only":
            return 1.0, self.pitch
        if self.mode_key == "linked":
            # 磁带联动：音调随速度按倍频程变化
            return self.tempo, 12.0 * math.log2(self.tempo)
        return self.tempo, self.pitch

    def on_mode_change(self, e):
        self.mode_key = e.control.value
        self.mode_hint.value = PROCESS_MODES[self.mode_key][1]
        self._sync_controls_from_mode()
        self._update_duration_estimate()

    def _sync_controls_from_mode(self):
        """根据模式启用/禁用滑块，并同步显示值。"""
        mode = self.mode_key
        tempo_enabled = mode in ("tempo_only", "linked", "custom")
        pitch_enabled = mode == "custom"

        self.tempo_slider.disabled = not tempo_enabled
        self.tempo_input.disabled = not tempo_enabled
        self.pitch_slider.disabled = not pitch_enabled
        self.pitch_input.disabled = not pitch_enabled

        if mode == "tempo_only":
            self.pitch_slider.value = 0
            self.pitch_input.value = "0"
        elif mode == "pitch_only":
            self.tempo_slider.value = 1.0
            self.tempo_input.value = "1.00"
        elif mode == "linked":
            linked_pitch = 12.0 * math.log2(self.tempo)
            self.pitch_slider.value = max(PITCH_MIN, min(PITCH_MAX, linked_pitch))
            self.pitch_input.value = f"{linked_pitch:+.1f}"
        else:  # custom
            self.pitch_slider.value = self.pitch
            self.pitch_input.value = f"{self.pitch:g}"
        self.page.update()

    def on_tempo_slider(self, e):
        self.tempo = float(e.control.value)
        self.tempo_input.value = f"{self.tempo:.2f}"
        if self.mode_key == "linked":
            linked_pitch = 12.0 * math.log2(self.tempo)
            self.pitch_slider.value = max(PITCH_MIN, min(PITCH_MAX, linked_pitch))
            self.pitch_input.value = f"{linked_pitch:+.1f}"
        self._update_duration_estimate()
        self.page.update()

    def on_pitch_slider(self, e):
        self.pitch = float(e.control.value)
        self.pitch_input.value = f"{self.pitch:g}"
        self._update_duration_estimate()
        self.page.update()

    def on_tempo_input(self, e):
        raw = (e.control.value or "").strip().replace("×", "").replace("x", "")
        try:
            val = float(raw)
        except ValueError:
            self.tempo_input.value = f"{self.tempo:.2f}"
            self.page.update()
            return
        val = max(TEMPO_MIN, min(TEMPO_MAX, val))
        self.tempo = val
        self.tempo_slider.value = val
        self.tempo_input.value = f"{val:.2f}"
        if self.mode_key == "linked":
            linked_pitch = 12.0 * math.log2(val)
            self.pitch_slider.value = max(PITCH_MIN, min(PITCH_MAX, linked_pitch))
            self.pitch_input.value = f"{linked_pitch:+.1f}"
        self._update_duration_estimate()
        self.page.update()

    def on_pitch_input(self, e):
        raw = (e.control.value or "").strip()
        try:
            val = float(raw)
        except ValueError:
            self.pitch_input.value = f"{self.pitch:g}"
            self.page.update()
            return
        val = max(PITCH_MIN, min(PITCH_MAX, val))
        self.pitch = val
        self.pitch_slider.value = val
        self.pitch_input.value = f"{val:g}"
        self._update_duration_estimate()
        self.page.update()

    def apply_preset(self, index: int):
        if not (0 <= index < len(PRESETS)):
            return
        label, mode, tempo, pitch = PRESETS[index]
        self.mode_key = mode
        self.mode_dropdown.value = mode
        self.mode_hint.value = PROCESS_MODES[mode][1]
        self.tempo = tempo
        self.tempo_slider.value = tempo
        self.tempo_input.value = f"{tempo:.2f}"
        self.pitch = pitch
        self._sync_controls_from_mode()
        self._update_duration_estimate()
        self.show_status(f"已应用预设：{label}")

    def _update_duration_estimate(self):
        tempo, pitch = self._effective_params()
        if self.items:
            idx = self.preview_index if 0 <= self.preview_index < len(self.items) else 0
            orig = self.items[idx].duration_ms / 1000.0
            new = orig / tempo if tempo > 0 else orig
            self.duration_estimate.value = (
                f"预计输出时长：{self._format_time(new)} （原 {self._format_time(orig)}）"
            )
        else:
            self.duration_estimate.value = "预计输出时长：-- （原 --）"
        self.pitch_detail.value = f"速度 {tempo:.2f}× · 音调 {pitch:+.1f} 半音"
        self.page.update()

    def on_format_change(self, e):
        self.output_format_key = e.control.value
        need_bitrate = OUTPUT_FORMATS[self.output_format_key][3]
        self.bitrate_dropdown.disabled = not need_bitrate
        if not need_bitrate:
            self.bitrate_dropdown.value = None
        self.page.update()

    def on_bitrate_change(self, e):
        self.bitrate = e.control.value

    def on_suffix_change(self, e):
        self.filename_suffix = e.control.value or ""

    # ==================== 试听预览 ====================

    def _current_preview_item(self) -> FileItem | None:
        if not self.items:
            return None
        idx = self.preview_index if 0 <= self.preview_index < len(self.items) else 0
        return self.items[idx]

    def generate_listen(self, e):
        item = self._current_preview_item()
        if item is None:
            self.show_status("请先添加并选中一个音频文件", success=False)
            return
        if not self._is_ffmpeg_available():
            self.show_status("未检测到 FFmpeg，无法试听", success=False)
            return
        self.listen_button.disabled = True
        self.stop_button.disabled = True
        self.show_status(f"正在生成试听片段（前 15 秒）: {item.name}")
        self.page.update()
        threading.Thread(target=self._listen_worker, args=(item,), daemon=True).start()

    def _listen_worker(self, item: FileItem):
        try:
            tempo, pitch = self._effective_params()
            tmp = os.path.join(tempfile.gettempdir(), f"sp_listen_{int(time.time() * 1000)}.mp3")
            self._process_with_ffmpeg(
                item.path, tmp, item.frame_rate, tempo, pitch,
                bitrate="192k", limit_input_sec=15,
            )
            self.preview_audio_path = tmp
            self.audio_player.src = tmp
            self.audio_player.autoplay = True
            self.stop_button.disabled = False
            self.show_status(f"试听已生成，正在播放：{tempo:.2f}× / {pitch:+.1f} 半音")
        except Exception as err:
            self.show_status(f"试听失败: {err}", success=False)
        finally:
            self.listen_button.disabled = self.running or not self.items
            self.page.update()

    def stop_listen(self, e):
        try:
            self.audio_player.autoplay = False
            self.audio_player.src = ""
            self.stop_button.disabled = True
            self.page.update()
        except Exception:
            pass

    def generate_preview(self, e):
        item = self._current_preview_item()
        if item is None:
            self.show_status("请先添加并选中一个音频文件", success=False)
            return
        if not self._is_ffmpeg_available():
            self.show_status("未检测到 FFmpeg，无法预览", success=False)
            return
        self.preview_button.disabled = True
        self.show_status("正在生成波形预览...")
        self.page.update()
        threading.Thread(target=self._preview_worker, args=(item,), daemon=True).start()

    def _preview_worker(self, item: FileItem):
        tmp = None
        try:
            tempo, pitch = self._effective_params()
            tmp = os.path.join(tempfile.gettempdir(), f"sp_preview_{int(time.time() * 1000)}.wav")
            self._process_with_ffmpeg(
                item.path, tmp, item.frame_rate, tempo, pitch, limit_input_sec=20,
            )
            orig = AudioSegment.from_file(item.path)[:20000]
            proc = AudioSegment.from_file(tmp)
            self._render_compare_waveform(orig, proc, item.name)
            self.waveform_placeholder.visible = False
            self.waveform_image.visible = True
            self.waveform_image.src = self.waveform_image_path
            self.show_status(f"波形预览已生成: {item.name}")
        except Exception as err:
            self.show_status(f"预览失败: {err}", success=False)
        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            self._update_buttons()

    def _render_compare_waveform(self, orig: AudioSegment, proc: AudioSegment, name: str):
        """上下并列渲染原始与处理后波形（各自独立时间轴，体现时长变化）。"""
        def to_mono(seg: AudioSegment) -> np.ndarray:
            arr = np.array(seg.get_array_of_samples(), dtype=np.float32)
            if seg.channels == 2:
                arr = arr.reshape((-1, 2)).mean(axis=1)
            return arr

        def downsample(samples: np.ndarray, dur: float, max_points: int = 4000):
            if len(samples) <= max_points or len(samples) == 0:
                return samples, samples, np.linspace(0, dur, max(1, len(samples)))
            chunk = len(samples) // max_points
            peaks = np.array([samples[i * chunk:(i + 1) * chunk].max() for i in range(max_points)])
            troughs = np.array([samples[i * chunk:(i + 1) * chunk].min() for i in range(max_points)])
            return peaks, troughs, np.linspace(0, dur, max_points)

        o_dur = len(orig) / 1000.0
        p_dur = len(proc) / 1000.0
        o_peaks, o_troughs, o_time = downsample(to_mono(orig), o_dur)
        p_peaks, p_troughs, p_time = downsample(to_mono(proc), p_dur)

        fig, axes = plt.subplots(2, 1, figsize=(12.8, 2.8), dpi=100)
        fig.patch.set_facecolor('#FAFAFA')
        for ax, peaks, troughs, t, dur, color, edge, title in [
            (axes[0], o_peaks, o_troughs, o_time, o_dur, '#26A69A', '#00695C',
             f'原始波形  ·  {name}  ({o_dur:.1f}s)'),
            (axes[1], p_peaks, p_troughs, p_time, p_dur, '#EF6C00', '#BF360C',
             f'处理后波形  ({p_dur:.1f}s)'),
        ]:
            ax.set_facecolor('#FAFAFA')
            if len(t) > 0:
                ax.fill_between(t, troughs, peaks, color=color, alpha=0.75, linewidth=0)
                ax.plot(t, peaks, color=edge, linewidth=0.3, alpha=0.85)
                ax.plot(t, troughs, color=edge, linewidth=0.3, alpha=0.85)
            ax.set_xlim(0, max(dur, 0.01))
            ax.set_title(title, fontsize=9, loc='left', color=edge, weight='bold')
            ax.tick_params(labelsize=7)
            ax.grid(True, alpha=0.3)
        axes[1].set_xlabel('时间 (秒)', fontsize=8)
        plt.tight_layout(pad=0.4)

        img_path = os.path.join(tempfile.gettempdir(), 'audio_speed_pitch_preview.png')
        fig.savefig(img_path, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)
        self.waveform_image_path = img_path

    # ==================== FFmpeg 处理 ====================

    def _build_atempo_chain(self, value: float) -> str:
        """构建 atempo 滤镜链，atempo 仅支持 [0.5, 2.0]，超出需级联。"""
        parts = []
        x = value
        while x > 2.0:
            parts.append("atempo=2.0")
            x /= 2.0
        while x < 0.5:
            parts.append("atempo=0.5")
            x /= 0.5
        parts.append(f"atempo={x:.6f}")
        return ",".join(parts)

    def _build_filter_chain(self, sample_rate: int, tempo: float, pitch_semitones: float) -> str:
        """构建完整滤镜链：asetrate(变调) → aresample(复位采样率) → atempo(恢复速度)。

        - R = 2^(半音/12) 为音高倍率
        - asetrate=SR*R 同时升/降音高与速度，atempo=tempo/R 将速度修正到目标倍率
        - 最终时长 = 原时长 / tempo
        """
        R = 2 ** (pitch_semitones / 12.0)
        new_rate = max(1000, int(round(sample_rate * R)))
        atempo_val = tempo / R
        return (f"asetrate={new_rate},aresample={sample_rate},"
                f"{self._build_atempo_chain(atempo_val)}")

    def _process_with_ffmpeg(self, input_path: str, output_path: str, sample_rate: int,
                             tempo: float, pitch: float, bitrate: str | None = None,
                             limit_input_sec: int | None = None):
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
        if limit_input_sec:
            cmd += ["-t", str(limit_input_sec)]
        cmd += ["-i", input_path]
        cmd += ["-af", self._build_filter_chain(sample_rate, tempo, pitch)]
        if bitrate:
            cmd += ["-b:a", bitrate]
        cmd += [output_path]
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            tail = (result.stderr or "").strip().splitlines()[-3:]
            raise RuntimeError("; ".join(tail) or "FFmpeg 处理失败")

    # ==================== 批量处理执行 ====================

    def start_process(self, e):
        if not self.items:
            self.show_status("请先添加音频文件", success=False)
            return
        if not self._is_ffmpeg_available():
            self.show_status("FFmpeg 未安装或不在系统路径，无法处理。请安装：winget install Gyan.FFmpeg",
                             success=False)
            return
        tempo, pitch = self._effective_params()
        if abs(tempo - 1.0) < 1e-6 and abs(pitch) < 1e-6:
            self.show_status("当前参数为原速原调，无任何变化，请调整参数", success=False)
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
        self.stop_listen(None)
        self._update_buttons()
        self.progress.visible = True
        self.progress.value = 0
        self.progress_text.value = f"0 / {len(self.items)}"
        self.show_status(f"开始处理（{tempo:.2f}× / {pitch:+.1f} 半音）...")

        snapshot = list(self.items)
        threading.Thread(target=self._process_worker, args=(snapshot,), daemon=True).start()

    def _process_worker(self, items: list[FileItem]):
        tempo, pitch = self._effective_params()
        total = len(items)
        for idx, item in enumerate(items):
            try:
                out_path = self._compute_output_path(item)
                self._process_single(item, out_path, tempo, pitch)
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

        msg = f"处理完成：成功 {self.success_count} 个，失败 {self.failed_count} 个"
        self.show_status(msg, success=(self.failed_count == 0))
        self._show_result_dialog(
            "变速变调完成",
            f"总文件数: {total}\n"
            f"成功: {self.success_count}\n"
            f"失败: {self.failed_count}\n"
            f"处理模式: {PROCESS_MODES[self.mode_key][0]}\n"
            f"速度: {tempo:.2f}×   音调: {pitch:+.1f} 半音\n"
            f"输出格式: {OUTPUT_FORMATS[self.output_format_key][0]}\n"
            f"输出目录: {self.output_dir or '（与源文件同目录）'}"
        )
        self._update_buttons()

    def _process_single(self, item: FileItem, out_path: str, tempo: float, pitch: float):
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        ext = Path(out_path).suffix.lower().lstrip('.')
        lossy_exts = {"mp3", "ogg", "m4a", "aac", "opus", "wma"}
        bitrate = self.bitrate if ext in lossy_exts else None
        self._process_with_ffmpeg(
            item.path, out_path, item.frame_rate, tempo, pitch, bitrate=bitrate,
        )

    def _compute_output_path(self, item: FileItem) -> str:
        src_stem = Path(item.path).stem
        if self.output_format_key == "keep":
            ext = item.src_ext
        else:
            ext = OUTPUT_FORMATS[self.output_format_key][1]
        new_name = f"{src_stem}{self.filename_suffix}.{ext}"
        base_dir = self.output_dir or os.path.dirname(item.path)
        return os.path.join(base_dir, new_name)

    # ==================== 对话框 ====================

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
    app = AudioSpeedPitchApp()
    ft.app(target=app.build)
