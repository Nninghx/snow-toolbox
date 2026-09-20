# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import os
import shutil
import threading
import subprocess
import importlib.util
from pathlib import Path
from dataclasses import dataclass

import flet as ft
from pydub import AudioSegment


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


# ==================== 格式定义 ====================

# 输入支持的格式（依赖 ffmpeg）
INPUT_EXTENSIONS = ["mp3", "wav", "flac", "ogg", "m4a", "aac", "opus", "aiff", "wma", "amr", "aif"]

# 输出格式配置
@dataclass
class FormatSpec:
    key: str          # pydub export format 名
    label: str        # UI 显示名
    ext: str          # 文件扩展名
    lossy: bool       # 是否有损
    need_bitrate: bool  # 是否需要比特率参数
    bitrates: list[str]  # 可选比特率
    default_bitrate: str


OUTPUT_FORMATS: list[FormatSpec] = [
    FormatSpec("mp3", "MP3  (有损 · 通用)", "mp3", True, True,
               ["96k", "128k", "192k", "256k", "320k"], "192k"),
    FormatSpec("wav", "WAV  (无损 · PCM)", "wav", False, False, [], ""),
    FormatSpec("flac", "FLAC (无损 · 压缩)", "flac", False, False, [], ""),
    FormatSpec("ogg", "OGG  (有损 · Vorbis)", "ogg", True, True,
               ["96k", "128k", "160k", "192k", "256k", "320k"], "192k"),
    FormatSpec("m4a", "M4A  (有损 · AAC)", "m4a", True, True,
               ["96k", "128k", "160k", "192k", "256k", "320k"], "192k"),
    FormatSpec("opus", "OPUS (有损 · 高效率)", "opus", True, True,
               ["32k", "64k", "96k", "128k", "160k", "192k"], "128k"),
    FormatSpec("aiff", "AIFF (无损 · Apple)", "aiff", False, False, [], ""),
    FormatSpec("wma", "WMA  (有损 · Windows)", "wma", True, True,
               ["64k", "96k", "128k", "160k", "192k"], "128k"),
]

FORMAT_BY_KEY = {f.key: f for f in OUTPUT_FORMATS}

SAMPLE_RATES = ["保持原样", "8000 Hz (电话)", "22050 Hz", "44100 Hz (CD)", "48000 Hz (视频)", "96000 Hz (高清)"]
SAMPLE_RATE_VALUES = [None, 8000, 22050, 44100, 48000, 96000]

CHANNEL_OPTIONS = ["保持原样", "单声道 (Mono)", "立体声 (Stereo)"]
CHANNEL_VALUES = [None, 1, 2]


@dataclass
class FileItem:
    path: str
    name: str
    size_bytes: int
    duration_ms: int
    frame_rate: int
    channels: int


class AudioConverterApp:
    """音频格式转换工具

    - 支持 MP3 / WAV / FLAC / OGG / M4A / OPUS / AIFF / WMA 等格式互转
    - 批量转换，独立设置目标格式、比特率、采样率、声道
    - 输出到指定目录，可保留原文件名或添加后缀
    - 依赖系统 FFmpeg
    """

    def __init__(self):
        self.page = None
        self.font_family = APP_FONT_FAMILY
        self.items: list[FileItem] = []
        self.running = False

        # 输出设置
        self.output_dir: str | None = None
        self.target_format: FormatSpec = FORMAT_BY_KEY["mp3"]
        self.bitrate: str = "192k"
        self.sample_rate: int | None = None
        self.channels: int | None = None
        self.filename_mode: str = "keep"  # keep | suffix | numbered
        self.filename_suffix: str = "_converted"

        # 统计
        self.success_count = 0
        self.failed_count = 0

    def build(self, page: ft.Page):
        self.page = page
        page.title = "音频格式转换"
        page.window.width = 1080
        page.window.height = 820
        page.window.center()
        page.padding = 16
        page.theme_mode = ft.ThemeMode.LIGHT

        # 设置窗口图标
        icon_path = get_project_root() / 'Image' / 'icon.ico'
        if icon_path.exists():
            page.window.icon = str(icon_path)

        # 文件选择器
        self.file_picker = ft.FilePicker(on_result=self.on_files_picked)
        self.input_dir_picker = ft.FilePicker(on_result=self.on_input_dir_picked)
        self.output_dir_picker = ft.FilePicker(on_result=self.on_output_dir_picked)
        page.overlay.extend([self.file_picker, self.input_dir_picker, self.output_dir_picker])

        # --- 顶部标题栏 ---
        header = ft.Row(
            [
                ft.Icon(ft.Icons.SYNC_ALT, size=32, color=ft.Colors.PURPLE),
                ft.Text("音频格式转换", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                ft.Container(width=8),
                ft.Text(
                    "MP3 · WAV · FLAC · OGG · M4A · OPUS  ·  批量互转",
                    size=13,
                    color=ft.Colors.BLUE_GREY_500,
                    font_family=self.font_family,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        )

        # FFmpeg 检查
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
                    on_click=self.pick_folder,
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
        self.items_column = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)
        self.empty_hint = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.LIBRARY_MUSIC, size=56, color=ft.Colors.GREY_300),
                    ft.Text("还没有音频文件", size=14, color=ft.Colors.GREY_500,
                            font_family=self.font_family),
                    ft.Text(f"支持批量导入: {', '.join(INPUT_EXTENSIONS[:6])} 等", size=12,
                            color=ft.Colors.GREY_400, font_family=self.font_family),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=6,
            ),
            height=150,
            alignment=ft.alignment.center,
            border_radius=8,
            bgcolor=ft.Colors.GREY_50,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )
        list_container = ft.Container(
            content=ft.Column([self.empty_hint, self.items_column], spacing=6),
            padding=ft.padding.all(8),
            border_radius=8,
            expand=True,
        )
        list_card = self._make_card_expand("待转换文件", list_container)

        # --- 目标格式设置 ---
        self.format_dropdown = ft.Dropdown(
            label="目标格式",
            value=self.target_format.key,
            width=220,
            text_size=13,
            options=[ft.dropdown.Option(f.key, f.label) for f in OUTPUT_FORMATS],
            on_change=self.on_format_change,
        )
        self.bitrate_dropdown = ft.Dropdown(
            label="比特率",
            value=self.bitrate,
            width=140,
            text_size=13,
            options=[ft.dropdown.Option(b, b) for b in self.target_format.bitrates],
            on_change=self.on_bitrate_change,
        )
        self.sample_rate_dropdown = ft.Dropdown(
            label="采样率",
            value=SAMPLE_RATES[0],
            width=180,
            text_size=13,
            options=[ft.dropdown.Option(s, s) for s in SAMPLE_RATES],
            on_change=self.on_sample_rate_change,
        )
        self.channel_dropdown = ft.Dropdown(
            label="声道",
            value=CHANNEL_OPTIONS[0],
            width=160,
            text_size=13,
            options=[ft.dropdown.Option(c, c) for c in CHANNEL_OPTIONS],
            on_change=self.on_channel_change,
        )

        format_row = ft.Row(
            [
                self.format_dropdown,
                self.bitrate_dropdown,
                self.sample_rate_dropdown,
                self.channel_dropdown,
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
        )
        format_card = self._make_card("转换参数", format_row)

        # --- 输出设置 ---
        self.output_dir_text = ft.Text(
            "未选择（默认与源文件同目录）",
            size=13, color=ft.Colors.BLUE_GREY_500, font_family=self.font_family,
            expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
        )
        output_dir_row = ft.Row(
            [
                ft.Icon(ft.Icons.FOLDER, size=18, color=ft.Colors.PURPLE_400),
                self.output_dir_text,
                ft.OutlinedButton("选择输出目录", icon=ft.Icons.FOLDER_OPEN,
                                  on_click=lambda e: self.output_dir_picker.get_directory_path(
                                      dialog_title="选择输出目录")),
                ft.TextButton("清除", icon=ft.Icons.CLEAR, on_click=self.clear_output_dir),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        )

        self.filename_mode_group = ft.RadioGroup(
            value=self.filename_mode,
            on_change=self.on_filename_mode_change,
            content=ft.Row(
                [
                    ft.Radio(value="keep", label="保持原文件名"),
                    ft.Radio(value="suffix", label="加后缀"),
                    ft.Radio(value="numbered", label="编号命名"),
                ],
                spacing=16,
            ),
        )
        self.suffix_field = ft.TextField(
            label="后缀内容",
            value=self.filename_suffix,
            width=180,
            text_size=13,
            on_change=self.on_suffix_change,
        )

        output_row2 = ft.Row(
            [
                ft.Text("文件命名:", size=13, font_family=self.font_family,
                        color=ft.Colors.BLUE_GREY_700),
                self.filename_mode_group,
                self.suffix_field,
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
        )

        output_card = self._make_card(
            "输出设置",
            ft.Column([output_dir_row, output_row2], spacing=10),
        )

        # --- 操作区 ---
        self.convert_button = ft.ElevatedButton(
            "开始转换",
            icon=ft.Icons.PLAY_ARROW,
            on_click=self.start_convert,
            height=44,
            disabled=True,
            style=ft.ButtonStyle(bgcolor=ft.Colors.PURPLE, color=ft.Colors.WHITE),
        )
        self.progress = ft.ProgressBar(
            visible=False, width=280,
            color=ft.Colors.PURPLE, bgcolor=ft.Colors.GREY_200,
            bar_height=8, border_radius=4,
        )
        self.progress_text = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_700,
                                     font_family=self.font_family)

        action_row = ft.Row(
            [
                self.progress,
                self.progress_text,
                ft.Container(expand=True),
                self.convert_button,
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
            format_card,
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

    def _make_card_expand(self, title, content):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(title, size=13, weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_GREY_700, font_family=self.font_family),
                    content,
                ],
                spacing=8,
                expand=True,
            ),
            padding=ft.padding.all(12),
            border_radius=10,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
            expand=True,
        )

    def _make_stat_label(self):
        self.stat_text = ft.Text(
            "共 0 个文件 · 0.00 MB",
            size=13, weight=ft.FontWeight.BOLD,
            color=ft.Colors.PURPLE_800, font_family=self.font_family,
        )
        return ft.Container(
            content=self.stat_text,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            bgcolor=ft.Colors.PURPLE_50,
            border_radius=6,
            border=ft.border.all(1, ft.Colors.PURPLE_200),
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
            self.ffmpeg_status.value = "✅ FFmpeg 已就绪，可以进行转换"
            self.ffmpeg_status.color = ft.Colors.GREEN_700
        else:
            self.ffmpeg_status.value = (
                "⚠️ 未检测到 FFmpeg，非 WAV 格式将无法转换。"
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

    def pick_folder(self, e):
        self.input_dir_picker.get_directory_path(dialog_title="选择包含音频的文件夹")

    def on_files_picked(self, e: ft.FilePickerResultEvent):
        if not e.files:
            return
        paths = [f.path for f in e.files if f.path]
        self._add_paths(paths)

    def on_input_dir_picked(self, e: ft.FilePickerResultEvent):
        """选择包含音频的文件夹后自动扰描内容。"""
        if not e.path or not os.path.isdir(e.path):
            return
        paths = []
        for name in sorted(os.listdir(e.path)):
            full = os.path.join(e.path, name)
            if os.path.isfile(full) and Path(name).suffix.lstrip('.').lower() in INPUT_EXTENSIONS:
                paths.append(full)
        if not paths:
            self.show_status(f"文件夹中没有找到支持的音频: {e.path}", success=False)
            return
        self._add_paths(paths)

    def on_output_dir_picked(self, e: ft.FilePickerResultEvent):
        """选择输出目录回调。"""
        if not e.path:
            return
        self.output_dir = e.path
        self.output_dir_text.value = e.path
        self.output_dir_text.color = ft.Colors.BLUE_GREY_900
        self.page.update()
        self.show_status(f"输出目录: {e.path}")

    def _add_paths(self, paths: list[str]):
        """批量加载音频文件到列表。"""
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
            if p in existing:
                continue
            if not os.path.isfile(p):
                continue
            try:
                audio = AudioSegment.from_file(p)
                loaded.append(FileItem(
                    path=p,
                    name=os.path.basename(p),
                    size_bytes=os.path.getsize(p),
                    duration_ms=len(audio),
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
        self._update_convert_button()

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
        self._refresh_list()
        self._update_stat()
        self._update_convert_button()
        self.show_status("已清空列表")

    def remove_item(self, index: int):
        if 0 <= index < len(self.items):
            removed = self.items.pop(index)
            self._refresh_list()
            self._update_stat()
            self._update_convert_button()
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
        duration_sec = item.duration_ms / 1000.0
        duration_str = f"{int(duration_sec // 60):02d}:{duration_sec % 60:05.2f}"
        size_str = self._format_size(item.size_bytes)
        ext = Path(item.path).suffix.lstrip('.').upper()
        ch_str = "立体声" if item.channels == 2 else ("单声道" if item.channels == 1 else f"{item.channels}声道")

        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Text(str(index + 1), size=11, weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.WHITE, font_family=self.font_family),
                        bgcolor=ft.Colors.PURPLE,
                        border_radius=10,
                        width=24, height=24,
                        alignment=ft.alignment.center,
                    ),
                    ft.Container(
                        content=ft.Text(ext, size=10, weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.PURPLE_800, font_family=self.font_family),
                        bgcolor=ft.Colors.PURPLE_100,
                        border_radius=4,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    ),
                    ft.Text(item.name, size=13, expand=True, no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            color=ft.Colors.BLUE_GREY_900, font_family=self.font_family),
                    ft.Text(duration_str, size=12, width=70,
                            color=ft.Colors.BLUE_GREY_700, font_family="Consolas"),
                    ft.Text(f"{item.frame_rate}Hz", size=12, width=70,
                            color=ft.Colors.BLUE_GREY_600, font_family="Consolas"),
                    ft.Text(ch_str, size=12, width=65,
                            color=ft.Colors.BLUE_GREY_600, font_family=self.font_family),
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
            border=ft.border.all(1, ft.Colors.PURPLE_100),
            ink=True,
        )

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

    def _update_convert_button(self):
        self.convert_button.disabled = (len(self.items) == 0) or self.running
        self.page.update()

    # ==================== 参数事件 ====================

    def on_format_change(self, e):
        key = e.control.value
        spec = FORMAT_BY_KEY.get(key)
        if not spec:
            return
        self.target_format = spec
        # 更新比特率控件
        if spec.need_bitrate:
            self.bitrate = spec.default_bitrate
            self.bitrate_dropdown.options = [ft.dropdown.Option(b, b) for b in spec.bitrates]
            self.bitrate_dropdown.value = spec.default_bitrate
            self.bitrate_dropdown.disabled = False
        else:
            self.bitrate_dropdown.disabled = True
            self.bitrate_dropdown.value = None
        self.page.update()

    def on_bitrate_change(self, e):
        self.bitrate = e.control.value

    def on_sample_rate_change(self, e):
        idx = SAMPLE_RATES.index(e.control.value) if e.control.value in SAMPLE_RATES else 0
        self.sample_rate = SAMPLE_RATE_VALUES[idx]

    def clear_output_dir(self, e):
        self.output_dir = None
        self.output_dir_text.value = "未选择（默认与源文件同目录）"
        self.output_dir_text.color = ft.Colors.BLUE_GREY_500
        self.page.update()

    def on_filename_mode_change(self, e):
        self.filename_mode = e.control.value
        self.suffix_field.disabled = (self.filename_mode != "suffix")
        self.page.update()

    def on_suffix_change(self, e):
        self.filename_suffix = e.control.value or ""

    def on_channel_change(self, e):
        idx = CHANNEL_OPTIONS.index(e.control.value) if e.control.value in CHANNEL_OPTIONS else 0
        self.channels = CHANNEL_VALUES[idx]

    # ==================== 输出路径处理 ====================

    def _compute_output_path(self, item: FileItem, index: int) -> str:
        src_stem = Path(item.path).stem
        target_ext = self.target_format.ext

        if self.filename_mode == "suffix":
            new_name = f"{src_stem}{self.filename_suffix}.{target_ext}"
        elif self.filename_mode == "numbered":
            new_name = f"{index + 1:03d}_{src_stem}.{target_ext}"
        else:
            new_name = f"{src_stem}.{target_ext}"

        if self.output_dir:
            return os.path.join(self.output_dir, new_name)
        return os.path.join(os.path.dirname(item.path), new_name)

    # ==================== 转换执行 ====================

    def start_convert(self, e):
        if not self.items:
            self.show_status("请先添加音频文件", success=False)
            return

        if self.target_format.key != "wav" and not self._is_ffmpeg_available():
            self.show_status(
                "FFmpeg 未安装或不在系统路径中，非 WAV 格式无法转换。"
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
        self.convert_button.disabled = True
        self.progress.visible = True
        self.progress.value = 0
        self.progress_text.value = f"0 / {len(self.items)}"
        self.show_status("开始转换...")

        snapshot = list(self.items)
        threading.Thread(
            target=self._convert_worker,
            args=(snapshot,),
            daemon=True,
        ).start()

    def _convert_worker(self, items: list[FileItem]):
        total = len(items)
        for idx, item in enumerate(items):
            try:
                out_path = self._compute_output_path(item, idx)
                self._convert_single(item, out_path)
                self.success_count += 1
            except Exception as err:
                self.failed_count += 1
                self.progress_text.value = f"{idx + 1} / {total}  ✗ {item.name}: {err}"
                self.page.update()
                continue

            self.progress.value = (idx + 1) / total
            self.progress_text.value = f"{idx + 1} / {total}  ✓ {item.name}"
            self.page.update()

        self.running = False
        self.progress.value = 1
        self.page.update()

        msg = f"转换完成：成功 {self.success_count} 个，失败 {self.failed_count} 个"
        self.show_status(msg, success=(self.failed_count == 0))
        self._show_result_dialog(
            "批量转换完成",
            f"总文件数: {total}\n"
            f"成功: {self.success_count}\n"
            f"失败: {self.failed_count}\n"
            f"目标格式: {self.target_format.key.upper()}"
            + (f"  ·  {self.bitrate}" if self.target_format.need_bitrate else "")
            + f"\n输出目录: {self.output_dir or '（与源文件同目录）'}"
        )
        self._update_convert_button()

    def _convert_single(self, item: FileItem, out_path: str):
        """执行单个文件的转换。"""
        # 确保输出目录存在
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

        # WAV → WAV 且无参数变化，直接复制
        src_ext = Path(item.path).suffix.lower().lstrip('.')
        if (src_ext == "wav" and self.target_format.key == "wav"
                and self.sample_rate is None and self.channels is None):
            shutil.copyfile(item.path, out_path)
            return

        audio = AudioSegment.from_file(item.path)

        # 应用采样率与声道调整
        if self.sample_rate is not None and audio.frame_rate != self.sample_rate:
            audio = audio.set_frame_rate(self.sample_rate)
        if self.channels is not None and audio.channels != self.channels:
            audio = audio.set_channels(self.channels)

        export_params = {}
        if self.target_format.need_bitrate and self.bitrate:
            export_params["bitrate"] = self.bitrate

        audio.export(out_path, format=self.target_format.key, **export_params)

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
    app = AudioConverterApp()
    ft.app(target=app.build)
