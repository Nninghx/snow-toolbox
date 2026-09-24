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
from pydub.silence import detect_silence

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

OUTPUT_FORMATS = {
    "keep": ("保持源格式", None),
    "mp3":  ("MP3",  "mp3"),
    "wav":  ("WAV",  "wav"),
    "flac": ("FLAC", "flac"),
    "ogg":  ("OGG",  "ogg"),
    "m4a":  ("M4A",  "m4a"),
}

# 分割模式
MODE_SILENCE = "silence"
MODE_DURATION = "duration"
MODE_PARTS = "parts"
MODE_MANUAL = "manual"


@dataclass
class Segment:
    """一个待导出的音频片段。"""
    index: int
    start_ms: int
    end_ms: int

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


class AudioSplitterApp:
    """音频分割器

    四种分割模式：
    - 按静音自动分段（播客/会议录音切章节）
    - 按固定时长切（每 N 秒一段）
    - 按段数等分（把整段切成 N 等份）
    - 手动标记分割点（点击波形添加）
    """

    def __init__(self):
        self.page = None
        self.font_family = APP_FONT_FAMILY

        self.audio: AudioSegment | None = None
        self.audio_path: str | None = None
        self.samples: np.ndarray | None = None
        self.duration_ms: int = 0

        # 分割模式与参数
        self.mode: str = MODE_SILENCE
        self.silence_threshold_db: int = -40
        self.silence_min_len_ms: int = 500
        self.silence_keep_ms: int = 200  # 保留静音长度（避免切太突兀）
        self.fixed_duration_sec: float = 60.0
        self.equal_parts: int = 2
        self.manual_points_ms: list[int] = []

        # 计算出的分段
        self.segments: list[Segment] = []

        # 输出设置
        self.output_dir: str | None = None
        self.output_format_key: str = "keep"
        self.bitrate: str = "192k"
        self.naming_template: str = "{name}_part{index:03d}"

        # 波形图
        self.waveform_image_path: str | None = None

        self.running = False
        self.success_count = 0
        self.failed_count = 0

    def build(self, page: ft.Page):
        self.page = page
        page.title = "音频分割器"
        page.window.width = 1120
        page.window.height = 880
        page.window.center()
        page.padding = 16
        page.theme_mode = ft.ThemeMode.LIGHT
        page.scroll = ft.ScrollMode.AUTO

        icon_path = get_project_root() / 'Image' / 'icon.ico'
        if icon_path.exists():
            page.window.icon = str(icon_path)

        self.file_picker = ft.FilePicker(on_result=self.on_file_picked)
        self.output_dir_picker = ft.FilePicker(on_result=self.on_output_dir_picked)
        page.overlay.extend([self.file_picker, self.output_dir_picker])

        # --- 顶部标题栏 ---
        header = ft.Row(
            [
                ft.Icon(ft.Icons.CONTENT_CUT, size=32, color=ft.Colors.DEEP_PURPLE),
                ft.Text("音频分割器", size=28, weight=ft.FontWeight.BOLD,
                        font_family=self.font_family),
                ft.Container(width=8),
                ft.Text(
                    "静音分段 · 定时长切 · 等分 · 手动标记",
                    size=13, color=ft.Colors.BLUE_GREY_500,
                    font_family=self.font_family,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        )

        self.ffmpeg_status = ft.Text("", size=12, font_family=self.font_family)
        self._check_ffmpeg_ui()

        # --- 文件选择卡片 ---
        self.file_text = ft.Text(
            "未选择文件", size=13, color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family, expand=True, no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.info_text = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_600,
                                 font_family=self.font_family)

        file_card = self._make_card(
            "音频文件",
            ft.Column([
                ft.Row(
                    [
                        ft.Icon(ft.Icons.MUSIC_NOTE, size=18, color=ft.Colors.DEEP_PURPLE_400),
                        self.file_text,
                        ft.ElevatedButton("打开文件", icon=ft.Icons.FOLDER_OPEN,
                                          on_click=self.open_file),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                self.info_text,
            ], spacing=4),
        )

        # --- 波形预览 ---
        self.waveform_image = ft.Image(
            src="", width=1050, height=220, fit=ft.ImageFit.FILL, visible=False,
        )
        self.waveform_placeholder = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.SHOW_CHART, size=48, color=ft.Colors.GREY_300),
                    ft.Text("打开音频文件后显示波形", size=14,
                            color=ft.Colors.GREY_400, font_family=self.font_family),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=1050, height=220, alignment=ft.alignment.center,
            border_radius=8, bgcolor=ft.Colors.GREY_50,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )
        self.gesture_detector = ft.GestureDetector(
            content=ft.Stack([self.waveform_placeholder, self.waveform_image]),
            on_tap_down=self.on_waveform_tap,
        )
        self.waveform_hint = ft.Text(
            "提示：手动标记模式下，点击波形添加分割点",
            size=12, color=ft.Colors.BLUE_GREY_600,
            font_family=self.font_family, italic=True,
        )
        waveform_card = self._make_card(
            "波形预览",
            ft.Column([self.waveform_hint, self.gesture_detector], spacing=8),
        )

        # --- 分割模式选择 ---
        self.mode_group = ft.RadioGroup(
            value=self.mode,
            on_change=self.on_mode_change,
            content=ft.Row(
                [
                    ft.Radio(value=MODE_SILENCE, label="按静音分段"),
                    ft.Radio(value=MODE_DURATION, label="按固定时长"),
                    ft.Radio(value=MODE_PARTS, label="等分为 N 段"),
                    ft.Radio(value=MODE_MANUAL, label="手动标记"),
                ],
                spacing=16,
            ),
        )

        # 各模式参数面板
        self.silence_panel = self._build_silence_panel()
        self.duration_panel = self._build_duration_panel()
        self.parts_panel = self._build_parts_panel()
        self.manual_panel = self._build_manual_panel()

        mode_card = self._make_card(
            "分割模式",
            ft.Column([
                self.mode_group,
                ft.Divider(thickness=1, opacity=0.2),
                self.silence_panel,
                self.duration_panel,
                self.parts_panel,
                self.manual_panel,
            ], spacing=10),
        )

        # --- 预览分段列表 ---
        self.preview_summary = ft.Text(
            "尚未计算分段", size=12, color=ft.Colors.BLUE_GREY_600,
            font_family=self.font_family,
        )
        self.preview_column = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=160)
        self.calc_button = ft.ElevatedButton(
            "计算分段预览",
            icon=ft.Icons.CALCULATE,
            on_click=self.calculate_segments,
            disabled=True,
        )
        preview_card = self._make_card(
            "分段预览",
            ft.Column([
                ft.Row([self.preview_summary, ft.Container(expand=True), self.calc_button],
                       spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(
                    content=self.preview_column,
                    padding=ft.padding.all(8),
                    border_radius=8,
                    bgcolor=ft.Colors.DEEP_PURPLE_50,
                    border=ft.border.all(1, ft.Colors.DEEP_PURPLE_100),
                ),
            ], spacing=8),
        )

        # --- 输出设置 ---
        self.format_dropdown = ft.Dropdown(
            label="输出格式", value=self.output_format_key, width=170, text_size=13,
            options=[ft.dropdown.Option(k, v[0]) for k, v in OUTPUT_FORMATS.items()],
            on_change=self.on_format_change,
        )
        self.bitrate_dropdown = ft.Dropdown(
            label="比特率", value=self.bitrate, width=120, text_size=13, disabled=True,
            options=[ft.dropdown.Option(b, b) for b in ["128k", "192k", "256k", "320k"]],
            on_change=self.on_bitrate_change,
        )
        self.naming_field = ft.TextField(
            label="命名模板", value=self.naming_template, width=260, text_size=13,
            on_change=self.on_naming_change,
            tooltip="可用占位符: {name}=源文件名, {index}=序号, {start}=起点秒, {end}=终点秒",
        )

        self.output_dir_text = ft.Text(
            "未选择（默认在源文件同目录创建子文件夹）",
            size=13, color=ft.Colors.BLUE_GREY_500, font_family=self.font_family,
            expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
        )
        output_dir_row = ft.Row(
            [
                ft.Icon(ft.Icons.FOLDER, size=18, color=ft.Colors.DEEP_PURPLE_400),
                self.output_dir_text,
                ft.OutlinedButton("选择输出目录", icon=ft.Icons.FOLDER_OPEN,
                                  on_click=lambda e: self.output_dir_picker.get_directory_path(
                                      dialog_title="选择输出目录")),
                ft.TextButton("清除", icon=ft.Icons.CLEAR, on_click=self.clear_output_dir),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        )

        output_card = self._make_card(
            "输出设置",
            ft.Column([
                ft.Row([self.format_dropdown, self.bitrate_dropdown, self.naming_field],
                       spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True),
                output_dir_row,
            ], spacing=10),
        )

        # --- 操作区 ---
        self.export_button = ft.ElevatedButton(
            "开始分割并导出",
            icon=ft.Icons.PLAY_ARROW,
            on_click=self.start_export,
            height=44,
            disabled=True,
            style=ft.ButtonStyle(bgcolor=ft.Colors.DEEP_PURPLE, color=ft.Colors.WHITE),
        )
        self.progress = ft.ProgressBar(
            visible=False, width=280,
            color=ft.Colors.DEEP_PURPLE, bgcolor=ft.Colors.GREY_200,
            bar_height=8, border_radius=4,
        )
        self.progress_text = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_700,
                                     font_family=self.font_family)

        action_row = ft.Row(
            [self.progress, self.progress_text, ft.Container(expand=True), self.export_button],
            spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # --- 状态栏 ---
        self.status_text = ft.Text("就绪 - 请打开音频文件", size=13,
                                   color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)
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
            file_card,
            waveform_card,
            mode_card,
            preview_card,
            output_card,
            action_row,
            status_bar,
        )

        # 初始只显示静音面板
        self._update_mode_panels()
        return page

    # ==================== 模式参数面板构建 ====================

    def _build_silence_panel(self) -> ft.Control:
        self.silence_threshold_field = ft.TextField(
            label="静音阈值 (dB)", value=str(self.silence_threshold_db),
            width=140, text_size=13, keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_silence_param_change,
        )
        self.silence_min_len_field = ft.TextField(
            label="最短静音 (ms)", value=str(self.silence_min_len_ms),
            width=150, text_size=13, keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_silence_param_change,
        )
        self.silence_keep_field = ft.TextField(
            label="段尾保留静音 (ms)", value=str(self.silence_keep_ms),
            width=170, text_size=13, keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_silence_param_change,
            tooltip="每段末尾保留多少静音，避免切得太突兀",
        )
        return ft.Row(
            [
                ft.Icon(ft.Icons.VOLUME_OFF, size=18, color=ft.Colors.DEEP_PURPLE_400),
                self.silence_threshold_field,
                self.silence_min_len_field,
                self.silence_keep_field,
                ft.Text("（适合播客/会议录音切章节）", size=11,
                        color=ft.Colors.BLUE_GREY_500, font_family=self.font_family),
            ],
            spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True,
        )

    def _build_duration_panel(self) -> ft.Control:
        self.fixed_duration_field = ft.TextField(
            label="每段时长 (秒)", value=str(self.fixed_duration_sec),
            width=160, text_size=13, keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_duration_param_change,
        )
        return ft.Row(
            [
                ft.Icon(ft.Icons.TIMER, size=18, color=ft.Colors.DEEP_PURPLE_400),
                self.fixed_duration_field,
                ft.Text("（每 N 秒切一段，最后一段可能不足）", size=11,
                        color=ft.Colors.BLUE_GREY_500, font_family=self.font_family),
            ],
            spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True,
        )

    def _build_parts_panel(self) -> ft.Control:
        self.equal_parts_field = ft.TextField(
            label="等分段数", value=str(self.equal_parts),
            width=130, text_size=13, keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_parts_param_change,
        )
        return ft.Row(
            [
                ft.Icon(ft.Icons.PIE_CHART, size=18, color=ft.Colors.DEEP_PURPLE_400),
                self.equal_parts_field,
                ft.Text("（把整段音频平均切成 N 份）", size=11,
                        color=ft.Colors.BLUE_GREY_500, font_family=self.font_family),
            ],
            spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True,
        )

    def _build_manual_panel(self) -> ft.Control:
        self.manual_points_text = ft.Text(
            "尚未添加分割点", size=12, color=ft.Colors.BLUE_GREY_700,
            font_family=self.font_family, expand=True,
        )
        return ft.Row(
            [
                ft.Icon(ft.Icons.ADD_LOCATION_ALT, size=18, color=ft.Colors.DEEP_PURPLE_400),
                self.manual_points_text,
                ft.OutlinedButton("撤销上一点", icon=ft.Icons.UNDO,
                                  on_click=self.undo_manual_point),
                ft.OutlinedButton("清空标记", icon=ft.Icons.CLEAR,
                                  on_click=self.clear_manual_points,
                                  style=ft.ButtonStyle(color=ft.Colors.RED_700)),
            ],
            spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True,
        )

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

    def show_status(self, message: str, success: bool = True):
        self.status_text.value = message
        self.status_text.color = ft.Colors.BLUE_GREY_700 if success else ft.Colors.RED_700
        self.page.snack_bar = ft.SnackBar(
            ft.Text(message, font_family=self.font_family),
            bgcolor=ft.Colors.GREEN if success else ft.Colors.RED,
            open=True,
        )
        self.page.update()

    # ==================== 文件加载 ====================

    def open_file(self, e):
        self.file_picker.pick_files(
            dialog_title="选择音频文件",
            allow_multiple=False,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=INPUT_EXTENSIONS,
        )

    def on_file_picked(self, e: ft.FilePickerResultEvent):
        if not e.files:
            return
        file_path = e.files[0].path
        if not os.path.exists(file_path):
            self.show_status("文件不存在", success=False)
            return
        self.show_status("正在加载音频...")
        self.running = True
        threading.Thread(target=self._load_worker, args=(file_path,), daemon=True).start()

    def _load_worker(self, file_path: str):
        try:
            audio = AudioSegment.from_file(file_path)
            self.audio = audio
            self.audio_path = file_path
            self.duration_ms = len(audio)

            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            if audio.channels == 2:
                samples = samples.reshape((-1, 2)).mean(axis=1)
            self.samples = samples

            # 重置分割状态
            self.manual_points_ms = []
            self.segments = []
            self.preview_column.controls.clear()
            self.preview_summary.value = "尚未计算分段"

            self.file_text.value = os.path.basename(file_path)
            self.file_text.color = ft.Colors.BLUE_GREY_900

            duration_sec = self.duration_ms / 1000.0
            minutes = int(duration_sec // 60)
            seconds = duration_sec % 60
            self.info_text.value = (
                f"时长: {minutes:02d}:{seconds:05.2f}  |  "
                f"采样率: {audio.frame_rate} Hz  |  "
                f"声道: {'立体声' if audio.channels == 2 else '单声道'}  |  "
                f"位深: {audio.sample_width * 8} bit  |  "
                f"大小: {os.path.getsize(file_path) / 1024 / 1024:.2f} MB"
            )

            self._render_waveform()
            self.waveform_placeholder.visible = False
            self.waveform_image.visible = True
            self.waveform_image.src = self.waveform_image_path

            self.calc_button.disabled = False
            self._update_export_button()
            self._update_manual_points_text()
            self.show_status(f"已加载: {os.path.basename(file_path)}")
        except Exception as err:
            self.show_status(f"加载失败: {err}", success=False)
        finally:
            self.running = False

    # ==================== 波形渲染 ====================

    def _render_waveform(self):
        """渲染波形并标记分割点。"""
        if self.samples is None:
            return

        samples = self.samples
        duration_sec = self.duration_ms / 1000.0

        max_points = 4500
        if len(samples) > max_points:
            chunk = len(samples) // max_points
            peaks = np.array([samples[i * chunk:(i + 1) * chunk].max() for i in range(max_points)])
            troughs = np.array([samples[i * chunk:(i + 1) * chunk].min() for i in range(max_points)])
            time_axis = np.linspace(0, duration_sec, max_points)
        else:
            peaks = samples
            troughs = samples
            time_axis = np.linspace(0, duration_sec, len(samples))

        fig, ax = plt.subplots(figsize=(13, 2.7), dpi=100)
        fig.patch.set_facecolor('#FAFAFA')
        ax.set_facecolor('#FAFAFA')

        ax.fill_between(time_axis, troughs, peaks, color='#7E57C2', alpha=0.75, linewidth=0)
        ax.plot(time_axis, peaks, color='#4527A0', linewidth=0.3, alpha=0.85)
        ax.plot(time_axis, troughs, color='#4527A0', linewidth=0.3, alpha=0.85)

        # 绘制当前已计算的分段边界
        for seg in self.segments:
            s = seg.start_ms / 1000.0
            e = seg.end_ms / 1000.0
            ax.axvline(x=s, color='#00897B', linewidth=1.0, linestyle='-', alpha=0.6, zorder=3)
            ax.axvline(x=e, color='#00897B', linewidth=1.0, linestyle='-', alpha=0.6, zorder=3)

        # 手动标记点（红色虚线）
        for pt_ms in self.manual_points_ms:
            ax.axvline(x=pt_ms / 1000.0, color='#D32F2F', linewidth=1.5,
                       linestyle='--', zorder=4)

        ax.set_xlim(0, duration_sec)
        ax.set_xlabel('时间 (秒)  ·  绿色实线=分段边界  红色虚线=手动标记', fontsize=9)
        ax.set_ylabel('振幅', fontsize=9)
        ax.tick_params(labelsize=8)
        ax.grid(True, alpha=0.3)

        plt.tight_layout(pad=0.5)
        tmp_dir = tempfile.gettempdir()
        img_path = os.path.join(tmp_dir, 'audio_splitter_waveform.png')
        fig.savefig(img_path, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)

        self.waveform_image_path = img_path

    def _refresh_waveform(self):
        if self.samples is None:
            return
        self._render_waveform()
        self.waveform_image.src = self.waveform_image_path
        self.page.update()

    # ==================== 波形点击（手动模式） ====================

    def on_waveform_tap(self, e: ft.TapEvent):
        if self.audio is None or self.mode != MODE_MANUAL:
            return

        local_x = e.local_x
        widget_width = 1050.0
        margin_left = 0.05
        margin_right = 0.02
        effective_width = widget_width * (1 - margin_left - margin_right)
        effective_x = local_x - widget_width * margin_left

        ratio = max(0.0, min(1.0, effective_x / effective_width))
        time_ms = int(ratio * self.duration_ms)

        # 避免在起点/终点附近添加
        if time_ms < 100 or time_ms > self.duration_ms - 100:
            self.show_status("分割点太靠近起点/终点，已忽略", success=False)
            return

        # 避免重复
        for existing in self.manual_points_ms:
            if abs(existing - time_ms) < 200:
                self.show_status("分割点太接近已有点，已忽略", success=False)
                return

        self.manual_points_ms.append(time_ms)
        self.manual_points_ms.sort()
        self._update_manual_points_text()
        self._refresh_waveform()
        self.show_status(f"已添加分割点: {time_ms / 1000.0:.2f}s")

    def _update_manual_points_text(self):
        if not self.manual_points_ms:
            self.manual_points_text.value = "尚未添加分割点"
        else:
            pts = ", ".join(f"{p / 1000.0:.2f}s" for p in self.manual_points_ms)
            self.manual_points_text.value = f"共 {len(self.manual_points_ms)} 个分割点: {pts}"
        self.page.update()

    def undo_manual_point(self, e):
        if not self.manual_points_ms:
            self.show_status("没有可撤销的分割点", success=False)
            return
        removed = self.manual_points_ms.pop()
        self._update_manual_points_text()
        self._refresh_waveform()
        self.show_status(f"已撤销分割点: {removed / 1000.0:.2f}s")

    def clear_manual_points(self, e):
        if not self.manual_points_ms:
            return
        self.manual_points_ms.clear()
        self._update_manual_points_text()
        self._refresh_waveform()
        self.show_status("已清空所有手动分割点")

    # ==================== 模式/参数事件 ====================

    def on_mode_change(self, e):
        self.mode = e.control.value
        self._update_mode_panels()
        self._refresh_waveform()

    def _on_silence_param_change(self, e):
        self.silence_threshold_db = self._read_int(self.silence_threshold_field, -40)
        self.silence_min_len_ms = self._read_int(self.silence_min_len_field, 500)
        self.silence_keep_ms = self._read_int(self.silence_keep_field, 200)

    def _on_duration_param_change(self, e):
        try:
            self.fixed_duration_sec = max(1.0, float(self.fixed_duration_field.value))
        except (ValueError, TypeError):
            pass

    def _on_parts_param_change(self, e):
        self.equal_parts = max(2, self._read_int(self.equal_parts_field, 2))

    @staticmethod
    def _read_int(field: ft.TextField, default: int) -> int:
        try:
            return int(float(field.value))
        except (ValueError, TypeError):
            return default

    def on_format_change(self, e):
        self.output_format_key = e.control.value
        need_bitrate = self.output_format_key in ("mp3", "ogg", "m4a")
        self.bitrate_dropdown.disabled = not need_bitrate
        if not need_bitrate:
            self.bitrate_dropdown.value = None
        self.page.update()

    def on_bitrate_change(self, e):
        self.bitrate = e.control.value

    def on_naming_change(self, e):
        self.naming_template = e.control.value or "{name}_part{index:03d}"

    def on_output_dir_picked(self, e: ft.FilePickerResultEvent):
        if not e.path:
            return
        self.output_dir = e.path
        self.output_dir_text.value = e.path
        self.output_dir_text.color = ft.Colors.BLUE_GREY_900
        self.page.update()
        self.show_status(f"输出目录: {e.path}")

    def clear_output_dir(self, e):
        self.output_dir = None
        self.output_dir_text.value = "未选择（默认在源文件同目录创建子文件夹）"
        self.output_dir_text.color = ft.Colors.BLUE_GREY_500
        self.page.update()

    # ==================== 分段计算 ====================

    def calculate_segments(self, e):
        """根据当前模式与参数计算分段列表。"""
        if self.audio is None:
            self.show_status("请先打开音频文件", success=False)
            return

        self.show_status("正在计算分段...")
        self.calc_button.disabled = True
        self.page.update()

        threading.Thread(target=self._calc_worker, daemon=True).start()

    def _calc_worker(self):
        try:
            if self.mode == MODE_SILENCE:
                self.segments = self._calc_by_silence()
            elif self.mode == MODE_DURATION:
                self.segments = self._calc_by_duration()
            elif self.mode == MODE_PARTS:
                self.segments = self._calc_by_parts()
            elif self.mode == MODE_MANUAL:
                self.segments = self._calc_by_manual()
            else:
                self.segments = []

            self._refresh_preview_list()
            self._refresh_waveform()
            self._update_export_button()

            if not self.segments:
                self.show_status("未计算出任何分段，请调整参数", success=False)
            else:
                total_dur = sum(s.duration_ms for s in self.segments) / 1000.0
                self.show_status(
                    f"计算完成：共 {len(self.segments)} 段，总时长 {total_dur:.2f}s"
                )
        except Exception as err:
            self.show_status(f"计算失败: {err}", success=False)
        finally:
            self.calc_button.disabled = False
            self.page.update()

    def _calc_by_silence(self) -> list[Segment]:
        """按静音分段：检测静音区间，以静音中心为分割点。"""
        silences = detect_silence(
            self.audio,
            min_silence_len=self.silence_min_len_ms,
            silence_thresh=self.silence_threshold_db,
        )
        if not silences:
            # 没有检测到静音，整段作为一个分段
            return [Segment(0, 0, self.duration_ms)]

        # 以每个静音区间的中心为分割点
        split_points: list[int] = [0]
        for s_ms, e_ms in silences:
            # 忽略太靠近起点/终点的静音
            if s_ms < 100 or e_ms > self.duration_ms - 100:
                continue
            center = (s_ms + e_ms) // 2
            split_points.append(center)
        split_points.append(self.duration_ms)

        # 去重并排序
        split_points = sorted(set(split_points))

        segments: list[Segment] = []
        idx = 0
        for i in range(len(split_points) - 1):
            s = split_points[i]
            e = split_points[i + 1]
            if e - s < 100:  # 跳过太短的分段
                continue
            # 段尾保留一点静音，避免切得太突兀
            keep = min(self.silence_keep_ms, (e - s) // 4)
            seg_end = min(e, s + (e - s))  # 保持原边界
            segments.append(Segment(idx, s, seg_end))
            idx += 1
        return segments

    def _calc_by_duration(self) -> list[Segment]:
        """按固定时长分段。"""
        step_ms = int(self.fixed_duration_sec * 1000)
        if step_ms <= 0:
            return []
        segments: list[Segment] = []
        idx = 0
        start = 0
        while start < self.duration_ms:
            end = min(start + step_ms, self.duration_ms)
            if end - start < 100:  # 跳过太短的尾段
                break
            segments.append(Segment(idx, start, end))
            idx += 1
            start = end
        return segments

    def _calc_by_parts(self) -> list[Segment]:
        """等分为 N 段。"""
        n = max(2, self.equal_parts)
        step_ms = self.duration_ms // n
        segments: list[Segment] = []
        for i in range(n):
            s = i * step_ms
            e = self.duration_ms if i == n - 1 else (i + 1) * step_ms
            segments.append(Segment(i, s, e))
        return segments

    def _calc_by_manual(self) -> list[Segment]:
        """按手动标记点分段。"""
        if not self.manual_points_ms:
            return [Segment(0, 0, self.duration_ms)]

        points = [0] + sorted(self.manual_points_ms) + [self.duration_ms]
        # 去重
        points = sorted(set(points))

        segments: list[Segment] = []
        idx = 0
        for i in range(len(points) - 1):
            s = points[i]
            e = points[i + 1]
            if e - s < 100:
                continue
            segments.append(Segment(idx, s, e))
            idx += 1
        return segments

    # ==================== 预览列表 ====================

    def _refresh_preview_list(self):
        self.preview_column.controls.clear()

        if not self.segments:
            self.preview_summary.value = "尚未计算分段"
            self.page.update()
            return

        total_dur = sum(s.duration_ms for s in self.segments) / 1000.0
        self.preview_summary.value = (
            f"共 {len(self.segments)} 段  ·  总时长 {total_dur:.2f}s  ·  "
            f"平均 {total_dur / len(self.segments):.2f}s/段"
        )

        for seg in self.segments:
            s_sec = seg.start_ms / 1000.0
            e_sec = seg.end_ms / 1000.0
            d_sec = seg.duration_ms / 1000.0
            row = ft.Row(
                [
                    ft.Container(
                        content=ft.Text(f"#{seg.index + 1:03d}", size=11,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.WHITE, font_family="Consolas"),
                        bgcolor=ft.Colors.DEEP_PURPLE,
                        border_radius=4,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    ),
                    ft.Text(
                        f"{int(s_sec // 60):02d}:{s_sec % 60:05.2f}  →  "
                        f"{int(e_sec // 60):02d}:{e_sec % 60:05.2f}",
                        size=12, color=ft.Colors.BLUE_GREY_800, font_family="Consolas",
                    ),
                    ft.Text(f"(时长 {d_sec:.2f}s)", size=11,
                            color=ft.Colors.BLUE_GREY_600, font_family=self.font_family),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            self.preview_column.controls.append(row)

        self.page.update()

    def _update_export_button(self):
        self.export_button.disabled = (
            self.audio is None or len(self.segments) == 0 or self.running
        )
        self.page.update()

    # ==================== 导出 ====================

    def start_export(self, e):
        if self.audio is None or not self.segments:
            self.show_status("请先计算分段", success=False)
            return

        # 检查 ffmpeg
        need_ffmpeg = False
        src_ext = Path(self.audio_path).suffix.lower().lstrip('.')
        if src_ext != "wav":
            need_ffmpeg = True
        if self.output_format_key not in ("keep", "wav", "flac"):
            need_ffmpeg = True
        if need_ffmpeg and not self._is_ffmpeg_available():
            self.show_status(
                "FFmpeg 未安装，无法处理该格式组合。请安装：winget install Gyan.FFmpeg",
                success=False,
            )
            return

        self.running = True
        self.success_count = 0
        self.failed_count = 0
        self.export_button.disabled = True
        self.calc_button.disabled = True
        self.progress.visible = True
        self.progress.value = 0
        self.progress_text.value = f"0 / {len(self.segments)}"
        self.show_status("开始分割导出...")

        segments_snapshot = list(self.segments)
        threading.Thread(target=self._export_worker, args=(segments_snapshot,), daemon=True).start()

    def _export_worker(self, segments: list[Segment]):
        total = len(segments)
        out_dir = self._resolve_output_dir()

        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as err:
            self.show_status(f"无法创建输出目录: {err}", success=False)
            self.running = False
            self._update_export_button()
            self.calc_button.disabled = False
            self.progress.visible = False
            return

        src_stem = Path(self.audio_path).stem
        fmt_key = self.output_format_key
        if fmt_key == "keep":
            export_fmt = Path(self.audio_path).suffix.lower().lstrip('.')
        else:
            export_fmt = OUTPUT_FORMATS[fmt_key][1]

        for i, seg in enumerate(segments):
            try:
                # 生成文件名
                try:
                    file_name = self.naming_template.format(
                        name=src_stem,
                        index=seg.index + 1,
                        start=f"{seg.start_ms / 1000.0:.2f}",
                        end=f"{seg.end_ms / 1000.0:.2f}",
                    )
                except (KeyError, ValueError, IndexError):
                    file_name = f"{src_stem}_part{seg.index + 1:03d}"

                # 清理非法字符
                file_name = self._sanitize_filename(file_name)
                out_path = os.path.join(out_dir, f"{file_name}.{export_fmt}")

                # 切片并导出
                clipped = self.audio[seg.start_ms:seg.end_ms]
                export_params = {}
                if export_fmt in ("mp3", "ogg", "m4a"):
                    export_params["bitrate"] = self.bitrate
                clipped.export(out_path, format=export_fmt, **export_params)

                self.success_count += 1
                self.progress.value = (i + 1) / total
                self.progress_text.value = f"{i + 1} / {total}  ✓ {file_name}.{export_fmt}"
            except Exception as err:
                self.failed_count += 1
                self.progress_text.value = f"{i + 1} / {total}  ✗ 段 #{seg.index + 1}: {err}"
            self.page.update()

        self.running = False
        self.progress.value = 1
        self.page.update()

        msg = f"分割完成：成功 {self.success_count} 段，失败 {self.failed_count} 段"
        self.show_status(msg, success=(self.failed_count == 0))
        self._show_result_dialog(
            "音频分割完成",
            f"总分段数: {total}\n"
            f"成功: {self.success_count}\n"
            f"失败: {self.failed_count}\n"
            f"输出格式: {export_fmt.upper()}\n"
            f"输出目录: {out_dir}"
        )
        self._update_export_button()
        self.calc_button.disabled = False

    def _resolve_output_dir(self) -> str:
        """确定输出目录：用户指定 > 源文件同目录下的子文件夹。"""
        if self.output_dir:
            return self.output_dir
        src_dir = os.path.dirname(self.audio_path)
        src_stem = Path(self.audio_path).stem
        return os.path.join(src_dir, f"{src_stem}_split")

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """清理文件名中的非法字符。"""
        illegal = '<>:"/\\|?*\0'
        for ch in illegal:
            name = name.replace(ch, '_')
        return name.strip('. ')

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
    app = AudioSplitterApp()
    ft.app(target=app.build)

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
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _update_mode_panels(self):
        """根据当前模式显示对应的参数面板。"""
        self.silence_panel.visible = (self.mode == MODE_SILENCE)
        self.duration_panel.visible = (self.mode == MODE_DURATION)
        self.parts_panel.visible = (self.mode == MODE_PARTS)
        self.manual_panel.visible = (self.mode == MODE_MANUAL)

        # 手动模式下波形可点击
        self.gesture_detector.visible = True
        if self.mode == MODE_MANUAL:
            self.waveform_hint.value = "👉 手动标记模式：点击波形添加分割点（红色虚线）"
            self.waveform_hint.color = ft.Colors.DEEP_PURPLE_700
        else:
            self.waveform_hint.value = "提示：当前模式下波形仅用于预览，不可点击添加分割点"
            self.waveform_hint.color = ft.Colors.BLUE_GREY_600
        self.page.update()
