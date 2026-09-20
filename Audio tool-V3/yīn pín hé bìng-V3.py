# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import os
import threading
import importlib.util
from pathlib import Path
from dataclasses import dataclass, field

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


@dataclass
class AudioItem:
    """合并列表中的单个音频项。"""
    path: str
    name: str
    duration_ms: int
    gain_db: float = 0.0
    audio: AudioSegment | None = field(default=None, repr=False)


class AudioMergeApp:
    """音频合并工具

    - 一次导入多个 MP3 / WAV 文件
    - 上下拖动调整顺序
    - 独立调节每段音量（dB 增益）
    - 支持衔接处交叉淡化，听不出接缝
    - 导出为单个 MP3 / WAV 文件
    """

    def __init__(self):
        self.page = None
        self.font_family = APP_FONT_FAMILY
        self.items: list[AudioItem] = []
        self.running = False

        # 全局设置
        self.crossfade_ms = 500
        self.fade_in_ms = 0
        self.fade_out_ms = 0
        self.output_format = "mp3"
        self.output_bitrate = "192k"

    def build(self, page: ft.Page):
        self.page = page
        page.title = "音频合并"
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
        self.save_picker = ft.FilePicker(on_result=self.on_save_picked)
        page.overlay.extend([self.file_picker, self.save_picker])

        # --- 顶部标题栏 ---
        header = ft.Row(
            [
                ft.Icon(ft.Icons.CALL_MERGE, size=32, color=ft.Colors.TEAL),
                ft.Text("音频合并", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                ft.Container(width=8),
                ft.Text(
                    "多文件拼接 · 独立音量 · 交叉淡化 · 无缝导出",
                    size=13,
                    color=ft.Colors.BLUE_GREY_500,
                    font_family=self.font_family,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        )

        # --- 文件列表操作按钮 ---
        list_toolbar = ft.Row(
            [
                ft.ElevatedButton(
                    "添加音频文件",
                    icon=ft.Icons.ADD,
                    on_click=self.pick_files,
                ),
                ft.OutlinedButton(
                    "全部下移到底",
                    icon=ft.Icons.VERTICAL_ALIGN_BOTTOM,
                    on_click=lambda e: self.reverse_list(),
                    tooltip="反转整个列表顺序",
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

        # --- 音频列表 ---
        self.items_column = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
        self.empty_hint = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.QUEUE_MUSIC, size=56, color=ft.Colors.GREY_300),
                    ft.Text("还没有音频，点击上方【添加音频文件】开始", size=14,
                            color=ft.Colors.GREY_500, font_family=self.font_family),
                    ft.Text("支持 MP3 / WAV，可一次多选", size=12,
                            color=ft.Colors.GREY_400, font_family=self.font_family),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=6,
            ),
            height=180,
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

        list_card = self._make_card_expand("合并顺序（从上到下依次拼接）", list_container)

        # --- 全局效果设置 ---
        self.crossfade_slider = ft.Slider(
            min=0, max=5000, divisions=100, value=self.crossfade_ms,
            label="{value} ms", width=260, active_color=ft.Colors.TEAL,
            on_change=self.on_crossfade_change,
        )
        self.crossfade_text = ft.Text(
            f"{self.crossfade_ms} ms", size=12, width=70,
            color=ft.Colors.BLUE_GREY_800, font_family="Consolas",
        )

        self.fade_in_slider = ft.Slider(
            min=0, max=5000, divisions=100, value=self.fade_in_ms,
            label="{value} ms", width=200, active_color=ft.Colors.TEAL,
            on_change=self.on_fade_in_change,
        )
        self.fade_in_text = ft.Text(
            f"{self.fade_in_ms} ms", size=12, width=70,
            color=ft.Colors.BLUE_GREY_800, font_family="Consolas",
        )

        self.fade_out_slider = ft.Slider(
            min=0, max=5000, divisions=100, value=self.fade_out_ms,
            label="{value} ms", width=200, active_color=ft.Colors.TEAL,
            on_change=self.on_fade_out_change,
        )
        self.fade_out_text = ft.Text(
            f"{self.fade_out_ms} ms", size=12, width=70,
            color=ft.Colors.BLUE_GREY_800, font_family="Consolas",
        )

        effects_row1 = ft.Row(
            [
                ft.Icon(ft.Icons.SWAP_HORIZ, size=18, color=ft.Colors.TEAL),
                ft.Text("交叉淡化", size=13, font_family=self.font_family, width=80),
                self.crossfade_slider,
                self.crossfade_text,
                ft.Icon(
                    ft.Icons.HELP_OUTLINE, size=16, color=ft.Colors.BLUE_GREY_400,
                    tooltip="衔接处的重叠过渡时长，越长越柔和，会缩短总时长",
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        effects_row2 = ft.Row(
            [
                ft.Icon(ft.Icons.TRENDING_UP, size=18, color=ft.Colors.TEAL),
                ft.Text("开头淡入", size=13, font_family=self.font_family, width=80),
                self.fade_in_slider,
                self.fade_in_text,
                ft.Container(width=20),
                ft.Icon(ft.Icons.TRENDING_DOWN, size=18, color=ft.Colors.TEAL),
                ft.Text("结尾淡出", size=13, font_family=self.font_family, width=80),
                self.fade_out_slider,
                self.fade_out_text,
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
        )

        effects_card = self._make_card("全局效果", ft.Column([effects_row1, effects_row2], spacing=10))

        # --- 导出设置 ---
        self.format_dropdown = ft.Dropdown(
            label="输出格式",
            value=self.output_format,
            width=130,
            text_size=13,
            options=[
                ft.dropdown.Option("mp3", "MP3 (有损压缩)"),
                ft.dropdown.Option("wav", "WAV (无损)"),
            ],
            on_change=self.on_format_change,
        )
        self.bitrate_dropdown = ft.Dropdown(
            label="MP3 比特率",
            value=self.output_bitrate,
            width=140,
            text_size=13,
            options=[
                ft.dropdown.Option("128k", "128 kbps"),
                ft.dropdown.Option("192k", "192 kbps"),
                ft.dropdown.Option("256k", "256 kbps"),
                ft.dropdown.Option("320k", "320 kbps (最高)"),
            ],
            on_change=self.on_bitrate_change,
        )

        self.export_button = ft.ElevatedButton(
            "合并并导出",
            icon=ft.Icons.SAVE_ALT,
            on_click=self.start_export,
            height=44,
            disabled=True,
            style=ft.ButtonStyle(bgcolor=ft.Colors.TEAL, color=ft.Colors.WHITE),
        )
        self.progress = ft.ProgressBar(
            visible=False,
            color=ft.Colors.TEAL,
            bgcolor=ft.Colors.GREY_200,
            bar_height=6,
            border_radius=4,
            expand=True,
        )

        export_row = ft.Row(
            [
                self.format_dropdown,
                self.bitrate_dropdown,
                ft.Container(expand=True),
                self.progress,
                self.export_button,
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # --- 状态栏 ---
        self.status_text = ft.Text(
            "就绪 - 请添加音频文件",
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
            list_toolbar,
            list_card,
            effects_card,
            export_row,
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
            "共 0 段 · 总时长 00:00.00",
            size=13,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.TEAL_800,
            font_family=self.font_family,
        )
        return ft.Container(
            content=self.stat_text,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            bgcolor=ft.Colors.TEAL_50,
            border_radius=6,
            border=ft.border.all(1, ft.Colors.TEAL_200),
        )

    def show_status(self, message: str, success: bool = True):
        self.status_text.value = message
        self.page.snack_bar = ft.SnackBar(
            ft.Text(message, font_family=self.font_family),
            bgcolor=ft.Colors.GREEN if success else ft.Colors.RED,
            open=True,
        )
        self.page.update()

    # ==================== 文件管理 ====================

    def pick_files(self, e):
        self.file_picker.pick_files(
            dialog_title="选择音频文件（可多选）",
            allow_multiple=True,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["mp3", "wav"],
        )

    def on_files_picked(self, e: ft.FilePickerResultEvent):
        if not e.files:
            return
        paths = [f.path for f in e.files if f.path and os.path.exists(f.path)]
        if not paths:
            self.show_status("未选择有效文件", success=False)
            return

        self.show_status(f"正在加载 {len(paths)} 个文件...")
        self.running = True
        threading.Thread(target=self._load_files_worker, args=(paths,), daemon=True).start()

    def _load_files_worker(self, paths: list[str]):
        loaded: list[AudioItem] = []
        failed: list[str] = []
        for p in paths:
            try:
                audio = AudioSegment.from_file(p)
                loaded.append(AudioItem(
                    path=p,
                    name=os.path.basename(p),
                    duration_ms=len(audio),
                    audio=audio,
                ))
            except Exception as err:
                failed.append(f"{os.path.basename(p)}: {err}")

        self.items.extend(loaded)
        self.running = False

        self._refresh_items_list()
        self._update_stat()
        self._update_export_button()

        if failed:
            self.show_status(
                f"已加载 {len(loaded)} 个文件，{len(failed)} 个失败：" + "; ".join(failed[:2]),
                success=False,
            )
        else:
            self.show_status(f"已成功加载 {len(loaded)} 个音频文件")

    def clear_list(self, e):
        if not self.items:
            return
        self.items.clear()
        self._refresh_items_list()
        self._update_stat()
        self._update_export_button()
        self.show_status("已清空列表")

    def reverse_list(self, e):
        if len(self.items) < 2:
            self.show_status("列表不足两项，无需反转", success=False)
            return
        self.items.reverse()
        self._refresh_items_list()
        self.show_status("已反转列表顺序")

    def move_item(self, index: int, direction: int):
        """上下移动列表项。direction: -1 上移, +1 下移"""
        new_index = index + direction
        if not (0 <= new_index < len(self.items)):
            return
        self.items[index], self.items[new_index] = self.items[new_index], self.items[index]
        self._refresh_items_list()

    def remove_item(self, index: int):
        if 0 <= index < len(self.items):
            removed = self.items.pop(index)
            self._refresh_items_list()
            self._update_stat()
            self._update_export_button()
            self.show_status(f"已移除: {removed.name}")

    def duplicate_item(self, index: int):
        """复制一段到列表末尾（不重复加载文件）。"""
        if not (0 <= index < len(self.items)):
            return
        src = self.items[index]
        clone = AudioItem(
            path=src.path,
            name=src.name,
            duration_ms=src.duration_ms,
            gain_db=src.gain_db,
            audio=src.audio,  # 共享 AudioSegment 引用（pydub 不可变）
        )
        self.items.insert(index + 1, clone)
        self._refresh_items_list()
        self._update_stat()
        self._update_export_button()
        self.show_status(f"已复制: {src.name}")

    def on_gain_change(self, index: int, value: float):
        """每段的音量增益改变。"""
        if 0 <= index < len(self.items):
            self.items[index].gain_db = round(value, 1)
            self._update_stat()
            # 找到对应行更新数字显示（避免整表重建）
            row = self.items_column.controls[index] if index < len(self.items_column.controls) else None
            if row is not None:
                self._update_row_gain_label(row, value)
                self.page.update()

    def _update_row_gain_label(self, row: ft.Control, value: float):
        """在行控件中找到 gain 数字标签并更新。"""
        content = getattr(row, 'content', None)
        if isinstance(content, ft.Column):
            for child in content.controls:
                if isinstance(child, ft.Row):
                    for c in child.controls:
                        if isinstance(c, ft.Text) and getattr(c, 'data', None) == 'gain_label':
                            sign = '+' if value > 0 else ''
                            c.value = f"{sign}{value:.1f} dB"

    # ==================== 列表 UI ====================

    def _refresh_items_list(self):
        """重建整个列表 UI。"""
        self.items_column.controls.clear()

        if not self.items:
            self.empty_hint.visible = True
        else:
            self.empty_hint.visible = False
            for idx, item in enumerate(self.items):
                self.items_column.controls.append(self._build_item_row(idx, item))

        self.page.update()

    def _build_item_row(self, index: int, item: AudioItem) -> ft.Control:
        duration_sec = item.duration_ms / 1000.0
        minutes = int(duration_sec // 60)
        seconds = duration_sec % 60
        duration_str = f"{minutes:02d}:{seconds:05.2f}"

        sign = '+' if item.gain_db > 0 else ''
        gain_label = ft.Text(
            f"{sign}{item.gain_db:.1f} dB",
            size=12, width=70, data='gain_label',
            color=ft.Colors.BLUE_GREY_800, font_family="Consolas",
        )

        gain_slider = ft.Slider(
            min=-24, max=24, divisions=96, value=item.gain_db,
            label="{value} dB", width=180, active_color=ft.Colors.TEAL,
            on_change=lambda e, i=index: self.on_gain_change(i, e.control.value),
        )

        header_row = ft.Row(
            [
                ft.Container(
                    content=ft.Text(
                        str(index + 1),
                        size=13, weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE, font_family=self.font_family,
                    ),
                    bgcolor=ft.Colors.TEAL,
                    border_radius=12,
                    width=28, height=28,
                    alignment=ft.alignment.center,
                ),
                ft.Icon(ft.Icons.AUDIOTRACK, size=18, color=ft.Colors.TEAL_400),
                ft.Text(
                    item.name, size=13, weight=ft.FontWeight.W_500,
                    color=ft.Colors.BLUE_GREY_900, font_family=self.font_family,
                    expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(
                    duration_str, size=12,
                    color=ft.Colors.BLUE_GREY_700, font_family="Consolas",
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        controls_row = ft.Row(
            [
                ft.Text("音量:", size=12, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family),
                gain_slider,
                gain_label,
                ft.Container(width=8),
                ft.IconButton(
                    icon=ft.Icons.ARROW_UPWARD,
                    icon_size=18, tooltip="上移",
                    on_click=lambda e, i=index: self.move_item(i, -1),
                    disabled=(index == 0),
                ),
                ft.IconButton(
                    icon=ft.Icons.ARROW_DOWNWARD,
                    icon_size=18, tooltip="下移",
                    on_click=lambda e, i=index: self.move_item(i, 1),
                    disabled=(index == len(self.items) - 1),
                ),
                ft.IconButton(
                    icon=ft.Icons.CONTENT_COPY,
                    icon_size=18, tooltip="复制此段",
                    on_click=lambda e, i=index: self.duplicate_item(i),
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_size=18, tooltip="移除",
                    icon_color=ft.Colors.RED_400,
                    on_click=lambda e, i=index: self.remove_item(i),
                ),
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        return ft.Container(
            content=ft.Column([header_row, controls_row], spacing=6),
            padding=ft.padding.all(10),
            border_radius=8,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.TEAL_100),
            ink=True,
        )

    # ==================== 统计 ====================

    def _update_stat(self):
        """更新总段数与总时长（含交叉淡化）。"""
        n = len(self.items)
        if n == 0:
            self.stat_text.value = "共 0 段 · 总时长 00:00.00"
            self.page.update()
            return

        total_ms = sum(item.duration_ms for item in self.items)
        # 交叉淡化会缩短总时长：每处衔接减去 crossfade_ms
        if n > 1:
            # 每段淡化不能超过相邻段的最短长度
            effective_crossfade = 0
            for i in range(n - 1):
                limit = min(self.items[i].duration_ms, self.items[i + 1].duration_ms) // 2
                effective_crossfade += min(self.crossfade_ms, limit)
            total_ms -= effective_crossfade

        total_ms = max(total_ms, 0)
        total_sec = total_ms / 1000.0
        minutes = int(total_sec // 60)
        seconds = total_sec % 60
        self.stat_text.value = f"共 {n} 段 · 总时长 {minutes:02d}:{seconds:05.2f}"
        self.page.update()

    def _update_export_button(self):
        self.export_button.disabled = len(self.items) < 1 or self.running
        self.page.update()

    # ==================== 全局设置 ====================

    def on_crossfade_change(self, e):
        self.crossfade_ms = int(e.control.value)
        self.crossfade_text.value = f"{self.crossfade_ms} ms"
        self._update_stat()

    def on_fade_in_change(self, e):
        self.fade_in_ms = int(e.control.value)
        self.fade_in_text.value = f"{self.fade_in_ms} ms"

    def on_fade_out_change(self, e):
        self.fade_out_ms = int(e.control.value)
        self.fade_out_text.value = f"{self.fade_out_ms} ms"

    def on_format_change(self, e):
        self.output_format = e.control.value
        self.bitrate_dropdown.disabled = (self.output_format != "mp3")
        self.page.update()

    def on_bitrate_change(self, e):
        self.output_bitrate = e.control.value

    # ==================== 导出 ====================

    def start_export(self, e):
        if not self.items:
            self.show_status("请先添加音频文件", success=False)
            return

        default_name = f"merged_{len(self.items)}_tracks.{self.output_format}"
        self.save_picker.save_file(
            dialog_title="保存合并后的音频",
            file_name=default_name,
            allowed_extensions=[self.output_format],
        )

    def on_save_picked(self, e: ft.FilePickerResultEvent):
        if not e.path:
            return
        output_path = e.path

        # 校验交叉淡化参数不超过最短段的一半
        min_dur = min(item.duration_ms for item in self.items)
        effective_crossfade = min(self.crossfade_ms, max(0, min_dur // 2))
        if effective_crossfade < self.crossfade_ms:
            self.show_status(
                f"交叉淡化自动调整为 {effective_crossfade} ms（受最短音频段限制）",
                success=False,
            )

        self.running = True
        self.export_button.disabled = True
        self.progress.visible = True
        self.progress.value = 0.3
        self.show_status("正在合并...")

        # 快照参数
        snapshot = [
            (item.audio, item.gain_db, item.name)
            for item in self.items
        ]
        threading.Thread(
            target=self._run_merge,
            args=(snapshot, effective_crossfade, self.fade_in_ms, self.fade_out_ms,
                  self.output_format, self.output_bitrate, output_path),
            daemon=True,
        ).start()

    def _run_merge(self, snapshot, crossfade_ms, fade_in_ms, fade_out_ms,
                   fmt, bitrate, output_path):
        try:
            if not snapshot:
                raise ValueError("没有可合并的音频段")

            # 应用每段增益
            processed: list[AudioSegment] = []
            for audio, gain_db, name in snapshot:
                if abs(gain_db) > 0.05:
                    processed.append(audio.apply_gain(gain_db))
                else:
                    processed.append(audio)

            # 统一采样率与声道数（以最丰富的为基准，避免 pydub 拼接报错）
            target_rate = max(seg.frame_rate for seg in processed)
            target_channels = max(seg.channels for seg in processed)
            target_width = max(seg.sample_width for seg in processed)

            normalized: list[AudioSegment] = []
            for seg in processed:
                if seg.frame_rate != target_rate:
                    seg = seg.set_frame_rate(target_rate)
                if seg.channels != target_channels:
                    seg = seg.set_channels(target_channels)
                if seg.sample_width != target_width:
                    seg = seg.set_sample_width(target_width)
                normalized.append(seg)

            # 依次拼接，衔接处交叉淡化
            result = normalized[0]
            for seg in normalized[1:]:
                if crossfade_ms > 0:
                    result = result.append(seg, crossfade=crossfade_ms)
                else:
                    result = result + seg

            # 首尾淡入淡出
            if fade_in_ms > 0:
                result = result.fade_in(min(fade_in_ms, len(result) // 2))
            if fade_out_ms > 0:
                result = result.fade_out(min(fade_out_ms, len(result) // 2))

            self.progress.value = 0.7
            self.page.update()

            export_params = {}
            if fmt == "mp3":
                export_params = {"bitrate": bitrate}
            result.export(output_path, format=fmt, **export_params)

            self.progress.value = 1
            self.page.update()

            kept_sec = len(result) / 1000.0
            self.show_status("合并成功！")
            self._show_result_dialog(
                "合并完成",
                f"文件已保存至：\n{output_path}\n\n"
                f"合并段数: {len(normalized)}\n"
                f"输出时长: {int(kept_sec // 60):02d}:{kept_sec % 60:05.2f}\n"
                f"交叉淡化: {crossfade_ms} ms\n"
                f"输出格式: {fmt.upper()}"
                + (f"  ·  {bitrate}" if fmt == "mp3" else "")
            )
        except Exception as err:
            self.show_status(f"合并失败: {err}", success=False)
        finally:
            self.running = False
            self.export_button.disabled = False
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
    app = AudioMergeApp()
    ft.app(target=app.build)
