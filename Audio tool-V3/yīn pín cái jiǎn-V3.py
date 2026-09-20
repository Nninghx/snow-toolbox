# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import os
import threading
import tempfile
import importlib.util
from pathlib import Path

import numpy as np
import flet as ft
from pydub import AudioSegment
from pydub.silence import detect_silence

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


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


class AudioTrimApp:
    """音频裁剪工具

    - 修剪开头 / 结尾（去掉多余空白）
    - 标记中间不需要的多段片段（咳嗽、口误、长停顿），一并删除
    - 支持静音自动检测，快速定位长停顿
    - 导出为干净的 MP3 / WAV 文件
    """

    # 交互模式常量
    MODE_NONE = None
    MODE_TRIM_START = 'trim_start'
    MODE_TRIM_END = 'trim_end'
    MODE_MARK_START = 'mark_start'
    MODE_MARK_END = 'mark_end'

    def __init__(self):
        self.page = None
        self.font_family = APP_FONT_FAMILY

        self.audio: AudioSegment | None = None
        self.audio_path: str | None = None
        self.samples: np.ndarray | None = None
        self.duration_ms: int = 0

        # 头尾修剪点（None 表示未设置）
        self.trim_start_ms: int | None = None
        self.trim_end_ms: int | None = None

        # 中间删除段列表：[(start_ms, end_ms), ...]
        self.cut_segments: list[tuple[int, int]] = []

        # 当前正在标记的段的起点（临时变量）
        self._pending_mark_start_ms: int | None = None

        self.setting_mode = self.MODE_NONE
        self.waveform_image_path: str | None = None
        self.running = False

        # 静音检测默认参数
        self.silence_threshold_db = -40
        self.silence_min_len_ms = 500

    def build(self, page: ft.Page):
        self.page = page
        page.title = "音频裁剪"
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
        self.file_picker = ft.FilePicker(on_result=self.on_file_picked)
        self.save_picker = ft.FilePicker(on_result=self.on_save_picked)
        page.overlay.extend([self.file_picker, self.save_picker])

        # --- 顶部标题栏 ---
        header = ft.Row(
            [
                ft.Icon(ft.Icons.CROP_FREE, size=32, color=ft.Colors.DEEP_ORANGE),
                ft.Text("音频裁剪", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                ft.Container(width=8),
                ft.Text(
                    "修剪头尾 · 删除中间片段 · 一键导出干净音频",
                    size=13,
                    color=ft.Colors.BLUE_GREY_500,
                    font_family=self.font_family,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        )

        # --- 文件信息卡片 ---
        self.file_text = ft.Text(
            "未选择文件",
            size=13,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
            expand=True,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.info_text = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_600, font_family=self.font_family)

        file_card = self._make_card(
            "音频文件",
            ft.Column([
                ft.Row(
                    [
                        ft.Icon(ft.Icons.MUSIC_NOTE, size=18, color=ft.Colors.BLUE_GREY_400),
                        self.file_text,
                        ft.ElevatedButton("打开文件", icon=ft.Icons.FOLDER_OPEN, on_click=self.open_file),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                self.info_text,
            ], spacing=4),
        )

        # --- 波形显示区域 ---
        self.waveform_image = ft.Image(
            src="",
            width=1010,
            height=240,
            fit=ft.ImageFit.FILL,
            visible=False,
        )
        self.waveform_placeholder = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.SHOW_CHART, size=48, color=ft.Colors.GREY_300),
                    ft.Text("打开音频文件后显示波形", size=14, color=ft.Colors.GREY_400, font_family=self.font_family),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=1010,
            height=240,
            alignment=ft.alignment.center,
            border_radius=8,
            bgcolor=ft.Colors.GREY_50,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )

        # 交互模式提示
        self.mode_hint = ft.Text(
            "提示：点击下方按钮进入设置模式，再点击波形选择位置",
            size=12,
            color=ft.Colors.BLUE_GREY_600,
            font_family=self.font_family,
            italic=True,
        )

        self.gesture_detector = ft.GestureDetector(
            content=ft.Stack([
                self.waveform_placeholder,
                self.waveform_image,
            ]),
            on_tap_down=self.on_waveform_tap,
        )

        waveform_card = self._make_card(
            "波形预览",
            ft.Column([self.mode_hint, self.gesture_detector], spacing=8),
        )

        # --- 头尾修剪控制 ---
        self.trim_start_field = ft.TextField(
            label="保留起点 (秒)",
            width=140,
            text_size=13,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_blur=self._on_trim_start_blur,
        )
        self.trim_end_field = ft.TextField(
            label="保留终点 (秒)",
            width=140,
            text_size=13,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_blur=self._on_trim_end_blur,
        )

        trim_row = ft.Row(
            [
                ft.OutlinedButton(
                    "① 设置保留起点",
                    icon=ft.Icons.FIRST_PAGE,
                    on_click=lambda e: self._enter_mode(self.MODE_TRIM_START),
                    style=ft.ButtonStyle(color=ft.Colors.RED_700),
                ),
                self.trim_start_field,
                ft.Container(width=8),
                ft.OutlinedButton(
                    "② 设置保留终点",
                    icon=ft.Icons.LAST_PAGE,
                    on_click=lambda e: self._enter_mode(self.MODE_TRIM_END),
                    style=ft.ButtonStyle(color=ft.Colors.GREEN_700),
                ),
                self.trim_end_field,
                ft.Container(width=8),
                ft.TextButton(
                    "自动去头尾静音",
                    icon=ft.Icons.AUTO_FIX_HIGH,
                    on_click=self.auto_trim_silence,
                ),
                ft.TextButton(
                    "清除头尾",
                    icon=ft.Icons.CLEAR,
                    on_click=self.clear_trim,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
        )

        trim_card = self._make_card("头尾修剪（删除开头 / 结尾多余部分）", trim_row)

        # --- 中间删除段控制 ---
        self.mark_start_field = ft.TextField(
            label="片段起点 (秒)",
            width=140,
            text_size=13,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.mark_end_field = ft.TextField(
            label="片段终点 (秒)",
            width=140,
            text_size=13,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        mark_row = ft.Row(
            [
                ft.OutlinedButton(
                    "③ 标记片段起点",
                    icon=ft.Icons.ADD_LOCATION_ALT,
                    on_click=lambda e: self._enter_mode(self.MODE_MARK_START),
                    style=ft.ButtonStyle(color=ft.Colors.ORANGE_800),
                ),
                ft.OutlinedButton(
                    "④ 标记片段终点",
                    icon=ft.Icons.LOCATION_OFF,
                    on_click=lambda e: self._enter_mode(self.MODE_MARK_END),
                    style=ft.ButtonStyle(color=ft.Colors.ORANGE_800),
                ),
                ft.Container(width=4),
                self.mark_start_field,
                self.mark_end_field,
                ft.ElevatedButton(
                    "手动添加片段",
                    icon=ft.Icons.ADD,
                    on_click=self.add_manual_segment,
                ),
                ft.TextButton(
                    "取消当前标记",
                    icon=ft.Icons.CLOSE,
                    on_click=self.cancel_pending_mark,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
        )

        # 静音检测参数
        self.silence_threshold_field = ft.TextField(
            label="静音阈值 (dB)",
            value=str(self.silence_threshold_db),
            width=130,
            text_size=13,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.silence_min_len_field = ft.TextField(
            label="最短静音 (ms)",
            value=str(self.silence_min_len_ms),
            width=140,
            text_size=13,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        silence_row = ft.Row(
            [
                ft.Icon(ft.Icons.VOLUME_OFF, size=18, color=ft.Colors.BLUE_GREY_500),
                self.silence_threshold_field,
                self.silence_min_len_field,
                ft.ElevatedButton(
                    "检测中间静音并加入删除列表",
                    icon=ft.Icons.SEARCH,
                    on_click=self.detect_middle_silence,
                ),
                ft.Text(
                    "（可用于自动识别长停顿）",
                    size=11,
                    color=ft.Colors.BLUE_GREY_500,
                    font_family=self.font_family,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
        )

        # 删除段列表
        self.segments_column = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=140)
        self.segments_summary = ft.Text(
            "尚未添加任何删除片段",
            size=12,
            color=ft.Colors.BLUE_GREY_600,
            font_family=self.font_family,
        )
        segments_container = ft.Container(
            content=ft.Column([self.segments_summary, self.segments_column], spacing=6),
            padding=ft.padding.all(8),
            border_radius=8,
            bgcolor=ft.Colors.ORANGE_50,
            border=ft.border.all(1, ft.Colors.ORANGE_200),
        )

        segments_card = self._make_card(
            "中间删除片段（咳嗽声、口误、停顿等）",
            ft.Column([mark_row, silence_row, segments_container], spacing=10),
        )

        # --- 操作按钮 ---
        self.export_button = ft.ElevatedButton(
            "导出干净音频",
            icon=ft.Icons.SAVE_ALT,
            on_click=self.export_audio,
            height=42,
            disabled=True,
            style=ft.ButtonStyle(bgcolor=ft.Colors.DEEP_ORANGE, color=ft.Colors.WHITE),
        )
        self.reset_button = ft.OutlinedButton(
            "重置全部",
            icon=ft.Icons.RESTART_ALT,
            on_click=self.reset_all,
            height=42,
            disabled=True,
        )
        self.progress = ft.ProgressBar(
            visible=False,
            color=ft.Colors.DEEP_ORANGE,
            bgcolor=ft.Colors.GREY_200,
            bar_height=6,
            border_radius=4,
            expand=True,
        )

        action_row = ft.Row(
            [self.progress, self.reset_button, self.export_button],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # --- 状态栏 ---
        self.status_text = ft.Text(
            "就绪 - 请打开音频文件",
            size=13,
            color=ft.Colors.BLUE_GREY_700,
            font_family=self.font_family,
        )
        status_bar = ft.Container(
            content=self.status_text,
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
            trim_card,
            segments_card,
            action_row,
            status_bar,
        )
        return page

    # ==================== UI 辅助 ====================

    def _make_card(self, title, content):
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

    def show_status(self, message: str, success: bool = True):
        self.status_text.value = message
        self.page.snack_bar = ft.SnackBar(
            ft.Text(message, font_family=self.font_family),
            bgcolor=ft.Colors.GREEN if success else ft.Colors.RED,
            open=True,
        )
        self.page.update()

    def _update_mode_hint(self):
        hints = {
            self.MODE_TRIM_START: "👉 请点击波形：选择音频【保留起点】（此点之前将被删除）",
            self.MODE_TRIM_END: "👉 请点击波形：选择音频【保留终点】（此点之后将被删除）",
            self.MODE_MARK_START: "👉 请点击波形：选择要删除片段的【起点】",
            self.MODE_MARK_END: "👉 请点击波形：选择要删除片段的【终点】",
            self.MODE_NONE: "提示：点击下方按钮进入设置模式，再点击波形选择位置",
        }
        self.mode_hint.value = hints.get(self.setting_mode, hints[self.MODE_NONE])
        color_map = {
            self.MODE_TRIM_START: ft.Colors.RED_700,
            self.MODE_TRIM_END: ft.Colors.GREEN_700,
            self.MODE_MARK_START: ft.Colors.ORANGE_800,
            self.MODE_MARK_END: ft.Colors.ORANGE_800,
            self.MODE_NONE: ft.Colors.BLUE_GREY_600,
        }
        self.mode_hint.color = color_map.get(self.setting_mode, ft.Colors.BLUE_GREY_600)

    def _enter_mode(self, mode):
        if self.audio is None:
            self.show_status("请先打开音频文件", success=False)
            return
        self.setting_mode = mode
        self._update_mode_hint()
        self.page.update()

    # ==================== 文件加载 ====================

    def open_file(self, e):
        self.file_picker.pick_files(
            dialog_title="选择音频文件",
            allow_multiple=False,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["mp3", "wav"],
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
        threading.Thread(target=self._load_audio, args=(file_path,), daemon=True).start()

    def _load_audio(self, file_path: str):
        try:
            audio = AudioSegment.from_file(file_path)
            self.audio = audio
            self.audio_path = file_path
            self.duration_ms = len(audio)

            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            if audio.channels == 2:
                samples = samples.reshape((-1, 2)).mean(axis=1)
            self.samples = samples

            # 重置所有裁剪标记
            self.trim_start_ms = None
            self.trim_end_ms = None
            self.cut_segments = []
            self._pending_mark_start_ms = None
            self.setting_mode = self.MODE_NONE

            self._render_waveform()

            self.file_text.value = os.path.basename(file_path)
            self.file_text.color = ft.Colors.BLUE_GREY_900

            duration_sec = self.duration_ms / 1000.0
            minutes = int(duration_sec // 60)
            seconds = duration_sec % 60
            self.info_text.value = (
                f"时长: {minutes:02d}:{seconds:05.2f}  |  "
                f"采样率: {audio.frame_rate} Hz  |  "
                f"声道: {'立体声' if audio.channels == 2 else '单声道'}  |  "
                f"位深: {audio.sample_width * 8} bit"
            )

            self.waveform_placeholder.visible = False
            self.waveform_image.visible = True
            self.waveform_image.src = self.waveform_image_path

            self.trim_start_field.value = ""
            self.trim_end_field.value = ""
            self.mark_start_field.value = ""
            self.mark_end_field.value = ""
            self.reset_button.disabled = False

            self._update_mode_hint()
            self._refresh_segments_list()
            self._update_export_button()
            self.show_status(f"已加载: {os.path.basename(file_path)}")

        except Exception as err:
            self.show_status(f"加载失败: {err}", success=False)
        finally:
            self.running = False

    # ==================== 波形渲染 ====================

    def _render_waveform(self):
        """渲染波形并高亮将被删除的区域。"""
        samples = self.samples
        duration_sec = self.duration_ms / 1000.0

        max_points = 4500
        if len(samples) > max_points:
            chunk_size = len(samples) // max_points
            peaks = np.array([
                samples[i * chunk_size:(i + 1) * chunk_size].max()
                for i in range(max_points)
            ])
            troughs = np.array([
                samples[i * chunk_size:(i + 1) * chunk_size].min()
                for i in range(max_points)
            ])
            time_axis = np.linspace(0, duration_sec, max_points)
        else:
            peaks = samples
            troughs = samples
            time_axis = np.linspace(0, duration_sec, len(samples))

        # 计算 y 轴范围
        y_max = float(max(np.max(np.abs(peaks)), 1.0))

        fig, ax = plt.subplots(figsize=(12.6, 2.9), dpi=100)
        fig.patch.set_facecolor('#FAFAFA')
        ax.set_facecolor('#FAFAFA')

        # 绘制波形（保留区域为蓝色）
        ax.fill_between(time_axis, troughs, peaks, color='#42A5F5', alpha=0.75, linewidth=0)
        ax.plot(time_axis, peaks, color='#1565C0', linewidth=0.3, alpha=0.85)
        ax.plot(time_axis, troughs, color='#1565C0', linewidth=0.3, alpha=0.85)

        # 灰色遮罩：头尾修剪区域
        trim_s = (self.trim_start_ms or 0) / 1000.0
        trim_e = (self.trim_end_ms if self.trim_end_ms is not None else self.duration_ms) / 1000.0

        if self.trim_start_ms is not None and trim_s > 0:
            ax.add_patch(Rectangle(
                (0, -y_max), trim_s, 2 * y_max,
                facecolor='#9E9E9E', alpha=0.65, edgecolor='none', zorder=2,
            ))
            ax.axvline(x=trim_s, color='#D32F2F', linewidth=1.6, linestyle='--', zorder=3)
        if self.trim_end_ms is not None and trim_e < duration_sec:
            ax.add_patch(Rectangle(
                (trim_e, -y_max), duration_sec - trim_e, 2 * y_max,
                facecolor='#9E9E9E', alpha=0.65, edgecolor='none', zorder=2,
            ))
            ax.axvline(x=trim_e, color='#2E7D32', linewidth=1.6, linestyle='--', zorder=3)

        # 橙色遮罩：中间删除段
        for seg_start_ms, seg_end_ms in self.cut_segments:
            s = seg_start_ms / 1000.0
            e = seg_end_ms / 1000.0
            ax.add_patch(Rectangle(
                (s, -y_max), max(e - s, 0.001), 2 * y_max,
                facecolor='#FF7043', alpha=0.6, edgecolor='#D84315',
                linewidth=0.8, zorder=2,
            ))

        # 当前正在标记的临时段
        if self._pending_mark_start_ms is not None:
            s = self._pending_mark_start_ms / 1000.0
            ax.axvline(x=s, color='#EF6C00', linewidth=1.8, linestyle=':', zorder=4)

        ax.set_xlim(0, duration_sec)
        ax.set_ylim(-y_max * 1.05, y_max * 1.05)
        ax.set_xlabel('时间 (秒)  ·  灰色=头尾删除  橙色=中间删除片段', fontsize=9)
        ax.set_ylabel('振幅', fontsize=9)
        ax.tick_params(labelsize=8)
        ax.grid(True, alpha=0.3)

        plt.tight_layout(pad=0.5)

        tmp_dir = tempfile.gettempdir()
        img_path = os.path.join(tmp_dir, 'audio_trim_waveform.png')
        fig.savefig(img_path, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)

        self.waveform_image_path = img_path

    def _refresh_waveform(self):
        if self.samples is None:
            return
        self._render_waveform()
        self.waveform_image.src = self.waveform_image_path
        self.page.update()

    # ==================== 波形点击交互 ====================

    def on_waveform_tap(self, e: ft.TapEvent):
        if self.audio is None or self.setting_mode == self.MODE_NONE:
            return

        local_x = e.local_x
        widget_width = 1010.0

        margin_left = 0.05
        margin_right = 0.02
        effective_width = widget_width * (1 - margin_left - margin_right)
        effective_x = local_x - widget_width * margin_left

        ratio = max(0.0, min(1.0, effective_x / effective_width))
        time_ms = int(ratio * self.duration_ms)

        mode = self.setting_mode

        if mode == self.MODE_TRIM_START:
            self.trim_start_ms = time_ms
            self.trim_start_field.value = f"{time_ms / 1000.0:.2f}"
            self.setting_mode = self.MODE_NONE
            self.show_status(f"已设置保留起点: {time_ms / 1000.0:.2f}s")

        elif mode == self.MODE_TRIM_END:
            self.trim_end_ms = time_ms
            self.trim_end_field.value = f"{time_ms / 1000.0:.2f}"
            self.setting_mode = self.MODE_NONE
            self.show_status(f"已设置保留终点: {time_ms / 1000.0:.2f}s")

        elif mode == self.MODE_MARK_START:
            self._pending_mark_start_ms = time_ms
            self.mark_start_field.value = f"{time_ms / 1000.0:.2f}"
            # 自动进入终点标记模式，简化操作
            self.setting_mode = self.MODE_MARK_END
            self.show_status(f"片段起点: {time_ms / 1000.0:.2f}s，请点击终点")

        elif mode == self.MODE_MARK_END:
            if self._pending_mark_start_ms is None:
                self.show_status("请先设置片段起点", success=False)
                return
            start_ms = min(self._pending_mark_start_ms, time_ms)
            end_ms = max(self._pending_mark_start_ms, time_ms)
            if end_ms - start_ms < 10:
                self.show_status("片段过短（<10ms），已忽略", success=False)
                self._pending_mark_start_ms = None
                self.setting_mode = self.MODE_NONE
            else:
                self._add_segment(start_ms, end_ms)
                self._pending_mark_start_ms = None
                self.setting_mode = self.MODE_NONE
                self.mark_end_field.value = f"{end_ms / 1000.0:.2f}"
                self.show_status(
                    f"已添加删除片段: {start_ms / 1000.0:.2f}s ~ {end_ms / 1000.0:.2f}s "
                    f"(时长 {(end_ms - start_ms) / 1000.0:.2f}s)"
                )

        self._update_mode_hint()
        self._update_export_button()
        self._refresh_waveform()

    # ==================== 手动输入处理 ====================

    def _on_trim_start_blur(self, e):
        self._apply_trim_from_fields()

    def _on_trim_end_blur(self, e):
        self._apply_trim_from_fields()

    def _apply_trim_from_fields(self):
        if self.audio is None:
            return
        try:
            if self.trim_start_field.value:
                val = int(float(self.trim_start_field.value) * 1000)
                self.trim_start_ms = max(0, min(val, self.duration_ms))
            if self.trim_end_field.value:
                val = int(float(self.trim_end_field.value) * 1000)
                self.trim_end_ms = max(0, min(val, self.duration_ms))
            self._update_export_button()
            self._refresh_waveform()
        except (ValueError, TypeError):
            pass

    def add_manual_segment(self, e):
        """从手动输入框添加删除片段。"""
        if self.audio is None:
            self.show_status("请先打开音频文件", success=False)
            return
        try:
            s = float(self.mark_start_field.value)
            t = float(self.mark_end_field.value)
        except (ValueError, TypeError):
            self.show_status("请输入有效的起点和终点秒数", success=False)
            return

        start_ms = max(0, min(int(s * 1000), self.duration_ms))
        end_ms = max(0, min(int(t * 1000), self.duration_ms))
        if start_ms >= end_ms:
            self.show_status("起点必须小于终点", success=False)
            return
        if end_ms - start_ms < 10:
            self.show_status("片段过短（<10ms）", success=False)
            return

        self._add_segment(start_ms, end_ms)
        self.show_status(
            f"已添加删除片段: {start_ms / 1000.0:.2f}s ~ {end_ms / 1000.0:.2f}s"
        )

    def _add_segment(self, start_ms: int, end_ms: int):
        """添加删除段到列表（自动去重合并相邻段）。"""
        self.cut_segments.append((start_ms, end_ms))
        # 排序并合并重叠区间
        self.cut_segments.sort(key=lambda x: x[0])
        merged: list[tuple[int, int]] = []
        for s, e in self.cut_segments:
            if merged and s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))
        self.cut_segments = merged
        self._refresh_segments_list()

    def cancel_pending_mark(self, e):
        """取消当前正在进行的片段标记。"""
        self._pending_mark_start_ms = None
        if self.setting_mode in (self.MODE_MARK_START, self.MODE_MARK_END):
            self.setting_mode = self.MODE_NONE
        self._update_mode_hint()
        self._refresh_waveform()
        self.show_status("已取消当前标记")

    def clear_trim(self, e):
        """清除头尾修剪点。"""
        self.trim_start_ms = None
        self.trim_end_ms = None
        self.trim_start_field.value = ""
        self.trim_end_field.value = ""
        self._update_export_button()
        self._refresh_waveform()
        self.show_status("已清除头尾修剪点")

    def reset_all(self, e):
        """重置所有裁剪标记。"""
        self.trim_start_ms = None
        self.trim_end_ms = None
        self.cut_segments = []
        self._pending_mark_start_ms = None
        self.setting_mode = self.MODE_NONE
        self.trim_start_field.value = ""
        self.trim_end_field.value = ""
        self.mark_start_field.value = ""
        self.mark_end_field.value = ""
        self._update_mode_hint()
        self._refresh_segments_list()
        self._update_export_button()
        self._refresh_waveform()
        self.show_status("已重置全部裁剪标记")

    # ==================== 删除段列表 UI ====================

    def _refresh_segments_list(self):
        """刷新中间删除段的可视化列表。"""
        self.segments_column.controls.clear()

        if not self.cut_segments:
            self.segments_summary.value = "尚未添加任何删除片段"
            self.page.update()
            return

        total_cut_ms = sum(e - s for s, e in self.cut_segments)
        self.segments_summary.value = (
            f"共 {len(self.cut_segments)} 段将被删除，累计 "
            f"{total_cut_ms / 1000.0:.2f} 秒"
        )

        for idx, (s, e) in enumerate(self.cut_segments):
            duration = (e - s) / 1000.0
            row = ft.Row(
                [
                    ft.Container(
                        content=ft.Text(
                            f"#{idx + 1}",
                            size=11,
                            color=ft.Colors.WHITE,
                            weight=ft.FontWeight.BOLD,
                            font_family=self.font_family,
                        ),
                        bgcolor=ft.Colors.DEEP_ORANGE,
                        border_radius=4,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    ),
                    ft.Text(
                        f"{s / 1000.0:7.2f}s  →  {e / 1000.0:7.2f}s",
                        size=12,
                        color=ft.Colors.BLUE_GREY_800,
                        font_family="Consolas",
                    ),
                    ft.Text(
                        f"(时长 {duration:.2f}s)",
                        size=11,
                        color=ft.Colors.BLUE_GREY_600,
                        font_family=self.font_family,
                    ),
                    ft.Container(expand=True),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_size=18,
                        tooltip="删除此段",
                        on_click=lambda e, i=idx: self._remove_segment(i),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            )
            self.segments_column.controls.append(row)

        self.page.update()

    def _remove_segment(self, index: int):
        """删除指定索引的段。"""
        if 0 <= index < len(self.cut_segments):
            removed = self.cut_segments.pop(index)
            self._refresh_segments_list()
            self._update_export_button()
            self._refresh_waveform()
            self.show_status(
                f"已删除片段 #{index + 1}: "
                f"{removed[0] / 1000.0:.2f}s ~ {removed[1] / 1000.0:.2f}s"
            )

    def _update_export_button(self):
        """根据当前状态更新导出按钮可用性。"""
        has_any_mark = (
            self.trim_start_ms is not None
            or self.trim_end_ms is not None
            or len(self.cut_segments) > 0
        )
        self.export_button.disabled = (self.audio is None) or (not has_any_mark)
        self.page.update()

    # ==================== 静音检测 ====================

    def auto_trim_silence(self, e):
        """自动检测并修剪头尾静音。"""
        if self.audio is None:
            self.show_status("请先打开音频文件", success=False)
            return

        self.show_status("正在检测头尾静音...")
        threading.Thread(target=self._auto_trim_silence_worker, daemon=True).start()

    def _auto_trim_silence_worker(self):
        try:
            threshold = self._read_int_field(self.silence_threshold_field, self.silence_threshold_db)
            min_len = self._read_int_field(self.silence_min_len_field, self.silence_min_len_ms)

            head_ms = self._detect_leading_silence(self.audio, threshold)
            tail_ms = self._detect_trailing_silence(self.audio, threshold)

            # 至少保留 min_len 的一半作为过渡，避免过切
            keep_pad = min(min_len // 2, 200)

            new_start = max(0, head_ms - keep_pad) if head_ms > keep_pad else 0
            new_end = min(self.duration_ms, self.duration_ms - tail_ms + keep_pad) \
                if tail_ms > keep_pad else self.duration_ms

            self.trim_start_ms = new_start if new_start > 0 else None
            self.trim_end_ms = new_end if new_end < self.duration_ms else None

            self.trim_start_field.value = f"{new_start / 1000.0:.2f}" if self.trim_start_ms else ""
            self.trim_end_field.value = f"{new_end / 1000.0:.2f}" if self.trim_end_ms else ""

            self._update_export_button()
            self._refresh_waveform()
            self.show_status(
                f"头尾静音检测完成：开头 {head_ms / 1000.0:.2f}s，结尾 {tail_ms / 1000.0:.2f}s"
            )
        except Exception as err:
            self.show_status(f"检测失败: {err}", success=False)

    @staticmethod
    def _detect_leading_silence(audio: AudioSegment, threshold_db: int, chunk_ms: int = 10) -> int:
        """返回开头静音的毫秒数。"""
        trim_ms = 0
        for chunk in audio[::chunk_ms]:
            if chunk.dBFS > threshold_db:
                break
            trim_ms += chunk_ms
        return trim_ms

    @staticmethod
    def _detect_trailing_silence(audio: AudioSegment, threshold_db: int, chunk_ms: int = 10) -> int:
        """返回结尾静音的毫秒数。"""
        reversed_audio = audio.reverse()
        return AudioTrimApp._detect_leading_silence(reversed_audio, threshold_db, chunk_ms)

    def detect_middle_silence(self, e):
        """检测音频中间的静音片段，全部加入删除列表。"""
        if self.audio is None:
            self.show_status("请先打开音频文件", success=False)
            return

        self.show_status("正在检测中间静音...")
        threading.Thread(target=self._detect_middle_silence_worker, daemon=True).start()

    def _detect_middle_silence_worker(self):
        try:
            threshold = self._read_int_field(self.silence_threshold_field, self.silence_threshold_db)
            min_len = self._read_int_field(self.silence_min_len_field, self.silence_min_len_ms)

            # 只在头尾修剪后的范围内检测
            search_start = self.trim_start_ms or 0
            search_end = self.trim_end_ms if self.trim_end_ms is not None else self.duration_ms

            if search_end - search_start < min_len:
                self.show_status("有效音频过短，无法检测", success=False)
                return

            sub = self.audio[search_start:search_end]
            silences = detect_silence(sub, min_silence_len=min_len, silence_thresh=threshold)

            # 过滤掉位于首尾的静音（这些由头尾修剪处理）
            added_count = 0
            # 保留极短的过渡，避免完全掐掉
            keep_pad = 50
            for s_rel, e_rel in silences:
                s_abs = search_start + s_rel
                e_abs = search_start + e_rel
                # 跳过紧贴范围首尾的段
                if s_rel < 10 or (search_end - e_abs) < 10:
                    continue
                new_s = min(s_abs + keep_pad, e_abs - 1)
                new_e = max(e_abs - keep_pad, new_s + 1)
                if new_e - new_s < 10:
                    continue
                self._add_segment(new_s, new_e)
                added_count += 1

            self._update_export_button()
            self._refresh_waveform()

            if added_count == 0:
                self.show_status("未检测到符合条件的中间静音片段")
            else:
                self.show_status(f"已自动加入 {added_count} 段静音到删除列表")
        except Exception as err:
            self.show_status(f"检测失败: {err}", success=False)

    @staticmethod
    def _read_int_field(field: ft.TextField, default: int) -> int:
        try:
            return int(float(field.value))
        except (ValueError, TypeError):
            return default

    # ==================== 导出 ====================

    def export_audio(self, e):
        if self.audio is None:
            self.show_status("请先打开音频文件", success=False)
            return
        if not self._has_any_mark():
            self.show_status("请至少设置一处裁剪标记", success=False)
            return

        default_name = Path(self.audio_path).stem + "_裁剪"
        ext = Path(self.audio_path).suffix.lstrip('.').lower()
        self.save_picker.save_file(
            dialog_title="保存裁剪后的音频",
            file_name=f"{default_name}.{ext}",
            allowed_extensions=["mp3", "wav"],
        )

    def _has_any_mark(self) -> bool:
        return (
            self.trim_start_ms is not None
            or self.trim_end_ms is not None
            or len(self.cut_segments) > 0
        )

    def on_save_picked(self, e: ft.FilePickerResultEvent):
        if not e.path:
            return
        output_path = e.path

        self.running = True
        self.export_button.disabled = True
        self.reset_button.disabled = True
        self.progress.visible = True
        self.progress.value = 0.5
        self.show_status("正在导出...")

        # 快照当前裁剪参数，避免线程执行中被修改
        trim_start = self.trim_start_ms or 0
        trim_end = self.trim_end_ms if self.trim_end_ms is not None else self.duration_ms
        segments_snapshot = list(self.cut_segments)

        threading.Thread(
            target=self._run_export,
            args=(trim_start, trim_end, segments_snapshot, output_path),
            daemon=True,
        ).start()

    def _run_export(self, trim_start: int, trim_end: int,
                    segments: list[tuple[int, int]], output_path: str):
        try:
            if trim_start >= trim_end:
                raise ValueError("保留起点必须小于保留终点")

            # 先做头尾修剪
            base = self.audio[trim_start:trim_end]

            # 计算保留区间（相对于原音频时间轴）
            keep_ranges: list[tuple[int, int]] = []
            cursor = trim_start
            for s, e in segments:
                # 只考虑与保留范围相交的部分
                seg_s = max(s, trim_start)
                seg_e = min(e, trim_end)
                if seg_s >= seg_e:
                    continue
                if seg_s > cursor:
                    keep_ranges.append((cursor, seg_s))
                cursor = max(cursor, seg_e)
            if cursor < trim_end:
                keep_ranges.append((cursor, trim_end))

            # 拼接保留片段
            if not keep_ranges:
                raise ValueError("所有音频都被裁剪掉了，请检查标记")

            result = AudioSegment.empty()
            for s, e in keep_ranges:
                result += self.audio[s:e]

            ext = Path(output_path).suffix.lower().lstrip('.')
            export_params = {'bitrate': '192k'} if ext == 'mp3' else {}
            result.export(output_path, format=ext, **export_params)

            removed_ms = (trim_start - 0) + (self.duration_ms - trim_end) + \
                sum(min(e, trim_end) - max(s, trim_start)
                    for s, e in segments
                    if min(e, trim_end) > max(s, trim_start))
            kept_sec = len(result) / 1000.0

            self.progress.value = 1
            self.page.update()

            self.show_status("导出成功！")
            self._show_result_dialog(
                "裁剪完成",
                f"音频已保存至：\n{output_path}\n\n"
                f"原始时长: {self.duration_ms / 1000.0:.2f}s\n"
                f"保留时长: {kept_sec:.2f}s\n"
                f"删除时长: {removed_ms / 1000.0:.2f}s\n"
                f"删除段数: 头尾 {int(bool(trim_start)) + int(trim_end < self.duration_ms)} 处 + "
                f"中间 {len(segments)} 段"
            )
        except Exception as err:
            self.show_status(f"导出失败: {err}", success=False)
        finally:
            self.running = False
            self.export_button.disabled = False
            self.reset_button.disabled = False
            self.progress.visible = False
            self._update_export_button()

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
    app = AudioTrimApp()
    ft.app(target=app.build)
