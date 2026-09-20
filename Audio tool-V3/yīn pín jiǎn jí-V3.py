# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import os
import io
import threading
import tempfile
import importlib.util
from pathlib import Path

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


class AudioEditorApp:
    """音频剪辑工具

    支持导入 MP3/WAV 文件，在波形图上设置剪切起点和终点，导出剪辑后的音频。
    """

    def __init__(self):
        self.page = None
        self.font_family = APP_FONT_FAMILY
        self.audio: AudioSegment | None = None
        self.audio_path: str | None = None
        self.samples: np.ndarray | None = None
        self.duration_ms: int = 0
        self.cut_start_ms: int | None = None
        self.cut_end_ms: int | None = None
        self.waveform_image_path: str | None = None
        self.setting_mode: str | None = None  # 'start' 或 'end'
        self.running = False

    def build(self, page: ft.Page):
        self.page = page
        page.title = "音频剪辑"
        page.window.width = 960
        page.window.height = 700
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

        # --- 顶部标题栏 ---
        header = ft.Row(
            [
                ft.Icon(ft.Icons.CONTENT_CUT, size=32, color=ft.Colors.BLUE),
                ft.Text("音频剪辑", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
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
            width=880,
            height=220,
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
            width=880,
            height=220,
            alignment=ft.alignment.center,
            border_radius=8,
            bgcolor=ft.Colors.GREY_50,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )

        # 手势检测层，用于点击波形设置剪切点
        self.gesture_detector = ft.GestureDetector(
            content=ft.Stack([
                self.waveform_placeholder,
                self.waveform_image,
            ]),
            on_tap_down=self.on_waveform_tap,
        )

        waveform_card = self._make_card("波形预览（点击波形设置剪切点）", self.gesture_detector)

        # --- 剪切控制区域 ---
        self.start_time_field = ft.TextField(
            label="起点时间 (秒)",
            width=150,
            text_size=13,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self.on_start_time_change,
        )
        self.end_time_field = ft.TextField(
            label="终点时间 (秒)",
            width=150,
            text_size=13,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self.on_end_time_change,
        )

        self.set_start_btn = ft.OutlinedButton(
            "设置起点",
            icon=ft.Icons.FLAG,
            on_click=lambda e: self.enter_set_mode('start'),
        )
        self.set_end_btn = ft.OutlinedButton(
            "设置终点",
            icon=ft.Icons.FLAG,
            on_click=lambda e: self.enter_set_mode('end'),
        )
        self.clear_cut_btn = ft.TextButton(
            "清除剪切点",
            icon=ft.Icons.CLEAR,
            on_click=self.clear_cut_points,
        )

        cut_controls = ft.Row(
            [
                self.set_start_btn,
                self.start_time_field,
                self.set_end_btn,
                self.end_time_field,
                self.clear_cut_btn,
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
        )

        # --- 操作按钮 ---
        self.export_button = ft.ElevatedButton(
            "导出剪辑",
            icon=ft.Icons.SAVE_ALT,
            on_click=self.export_audio,
            height=40,
            disabled=True,
        )
        self.select_all_button = ft.OutlinedButton(
            "选择全部",
            icon=ft.Icons.SELECT_ALL,
            on_click=self.select_all,
            height=40,
            disabled=True,
        )
        self.progress = ft.ProgressBar(
            visible=False,
            color=ft.Colors.BLUE,
            bgcolor=ft.Colors.GREY_200,
            bar_height=6,
            border_radius=4,
            expand=True,
        )

        action_row = ft.Row(
            [self.progress, self.select_all_button, self.export_button],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # --- 状态栏 ---
        self.status_text = ft.Text("就绪 - 请打开音频文件", size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)
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
            cut_controls,
            action_row,
            status_bar,
        )
        return page

    # ==================== UI 辅助方法 ====================

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

    def show_status(self, message: str, success: bool = True):
        """更新状态栏并显示全局提示消息。"""
        self.status_text.value = message
        self.page.snack_bar = ft.SnackBar(
            ft.Text(message, font_family=self.font_family),
            bgcolor=ft.Colors.GREEN if success else ft.Colors.RED,
            open=True,
        )
        self.page.update()

    # ==================== 文件操作 ====================

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
        """在后台线程加载音频文件并生成波形。"""
        try:
            audio = AudioSegment.from_file(file_path)
            self.audio = audio
            self.audio_path = file_path
            self.duration_ms = len(audio)
            self.cut_start_ms = None
            self.cut_end_ms = None

            # 转换为 numpy 数组用于波形绘制
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            if audio.channels == 2:
                samples = samples.reshape((-1, 2)).mean(axis=1)
            self.samples = samples

            # 渲染波形图
            self._render_waveform()

            # 更新 UI（需要在主线程调度）
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

            self.export_button.disabled = True
            self.select_all_button.disabled = False
            self.start_time_field.value = ""
            self.end_time_field.value = ""

            self.show_status(f"已加载: {os.path.basename(file_path)}")

        except Exception as err:
            self.show_status(f"加载失败: {err}", success=False)
        finally:
            self.running = False

    # ==================== 波形渲染 ====================

    def _render_waveform(self):
        """使用 matplotlib 渲染波形图并保存为临时 PNG。"""
        samples = self.samples
        duration_sec = self.duration_ms / 1000.0
        time_axis = np.linspace(0, duration_sec, len(samples))

        # 降采样以加速绘制（保留包络）
        max_points = 4000
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
            time_peaks = np.linspace(0, duration_sec, max_points)
        else:
            peaks = samples
            troughs = samples
            time_peaks = time_axis

        fig, ax = plt.subplots(figsize=(11, 2.6), dpi=100)
        fig.patch.set_facecolor('#FAFAFA')
        ax.set_facecolor('#FAFAFA')

        # 绘制波形填充
        ax.fill_between(time_peaks, troughs, peaks, color='#42A5F5', alpha=0.7, linewidth=0)
        ax.plot(time_peaks, peaks, color='#1565C0', linewidth=0.3, alpha=0.8)
        ax.plot(time_peaks, troughs, color='#1565C0', linewidth=0.3, alpha=0.8)

        # 绘制剪切点标记
        if self.cut_start_ms is not None:
            start_sec = self.cut_start_ms / 1000.0
            ax.axvline(x=start_sec, color='#E53935', linewidth=1.5, linestyle='--', label=f'起点 {start_sec:.2f}s')
        if self.cut_end_ms is not None:
            end_sec = self.cut_end_ms / 1000.0
            ax.axvline(x=end_sec, color='#43A047', linewidth=1.5, linestyle='--', label=f'终点 {end_sec:.2f}s')

        # 高亮选中区域
        if self.cut_start_ms is not None and self.cut_end_ms is not None:
            s = min(self.cut_start_ms, self.cut_end_ms) / 1000.0
            e = max(self.cut_start_ms, self.cut_end_ms) / 1000.0
            ax.axvspan(s, e, color='#FFEB3B', alpha=0.2)

        ax.set_xlim(0, duration_sec)
        ax.set_xlabel('时间 (秒)', fontsize=9)
        ax.set_ylabel('振幅', fontsize=9)
        ax.tick_params(labelsize=8)
        ax.grid(True, alpha=0.3)
        if self.cut_start_ms is not None or self.cut_end_ms is not None:
            ax.legend(loc='upper right', fontsize=8)

        plt.tight_layout(pad=0.5)

        # 保存到临时文件
        tmp_dir = tempfile.gettempdir()
        img_path = os.path.join(tmp_dir, 'audio_waveform_preview.png')
        fig.savefig(img_path, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)

        self.waveform_image_path = img_path

    def _refresh_waveform(self):
        """重新渲染波形并刷新显示。"""
        if self.samples is None:
            return
        self._render_waveform()
        self.waveform_image.src = self.waveform_image_path
        self.page.update()

    # ==================== 剪切点交互 ====================

    def enter_set_mode(self, mode: str):
        """进入设置剪切点模式，下一次点击波形将设置对应的点。"""
        if self.audio is None:
            self.show_status("请先打开音频文件", success=False)
            return
        self.setting_mode = mode
        label = "起点" if mode == 'start' else "终点"
        self.show_status(f"请点击波形设置{label}位置")

    def on_waveform_tap(self, e: ft.TapEvent):
        """处理波形点击事件，根据坐标计算时间位置。"""
        if self.audio is None or self.setting_mode is None:
            return

        # 获取点击的 x 坐标相对于控件宽度的比例
        # GestureDetector 在 Stack 上，波形图片宽度为 880
        local_x = e.local_x
        widget_width = 880.0

        # matplotlib 的 tight_layout 会在两侧留下边距，大约左边 5%，右边 2%
        margin_left = 0.055
        margin_right = 0.02
        effective_width = widget_width * (1 - margin_left - margin_right)
        effective_x = local_x - widget_width * margin_left

        ratio = max(0.0, min(1.0, effective_x / effective_width))
        time_ms = int(ratio * self.duration_ms)

        if self.setting_mode == 'start':
            self.cut_start_ms = time_ms
            self.start_time_field.value = f"{time_ms / 1000.0:.2f}"
        elif self.setting_mode == 'end':
            self.cut_end_ms = time_ms
            self.end_time_field.value = f"{time_ms / 1000.0:.2f}"

        label = "起点" if self.setting_mode == 'start' else "终点"
        self.setting_mode = None
        self._update_export_button()
        self._refresh_waveform()
        self.show_status(f"已设置{label}: {time_ms / 1000.0:.2f} 秒")

    def on_start_time_change(self, e):
        """手动输入起点时间变化时更新。"""
        self._apply_time_from_field('start')

    def on_end_time_change(self, e):
        """手动输入终点时间变化时更新。"""
        self._apply_time_from_field('end')

    def _apply_time_from_field(self, which: str):
        """从输入框读取时间值并应用。"""
        if self.audio is None:
            return
        field = self.start_time_field if which == 'start' else self.end_time_field
        try:
            val = float(field.value)
            time_ms = int(val * 1000)
            if time_ms < 0:
                time_ms = 0
            if time_ms > self.duration_ms:
                time_ms = self.duration_ms
            if which == 'start':
                self.cut_start_ms = time_ms
            else:
                self.cut_end_ms = time_ms
            self._update_export_button()
            self._refresh_waveform()
        except (ValueError, TypeError):
            pass

    def clear_cut_points(self, e):
        """清除所有剪切点。"""
        self.cut_start_ms = None
        self.cut_end_ms = None
        self.start_time_field.value = ""
        self.end_time_field.value = ""
        self.setting_mode = None
        self._update_export_button()
        self._refresh_waveform()
        self.show_status("已清除剪切点")

    def select_all(self, e):
        """选择全部音频范围。"""
        if self.audio is None:
            return
        self.cut_start_ms = 0
        self.cut_end_ms = self.duration_ms
        self.start_time_field.value = "0.00"
        self.end_time_field.value = f"{self.duration_ms / 1000.0:.2f}"
        self._update_export_button()
        self._refresh_waveform()
        self.show_status("已选择全部范围")

    def _update_export_button(self):
        """根据剪切点状态更新导出按钮可用性。"""
        if self.cut_start_ms is not None and self.cut_end_ms is not None:
            self.export_button.disabled = False
        else:
            self.export_button.disabled = True
        self.page.update()

    # ==================== 导出 ====================

    def export_audio(self, e):
        """导出剪辑后的音频。"""
        if self.audio is None:
            self.show_status("请先打开音频文件", success=False)
            return
        if self.cut_start_ms is None or self.cut_end_ms is None:
            self.show_status("请设置剪切起点和终点", success=False)
            return

        start_ms = min(self.cut_start_ms, self.cut_end_ms)
        end_ms = max(self.cut_start_ms, self.cut_end_ms)

        if start_ms >= end_ms:
            self.show_status("起点不能大于或等于终点", success=False)
            return

        # 弹出保存对话框
        default_name = Path(self.audio_path).stem + "_剪辑"
        ext = Path(self.audio_path).suffix.lstrip('.').lower()
        self.save_picker.save_file(
            dialog_title="保存剪辑音频",
            file_name=f"{default_name}.{ext}",
            allowed_extensions=["mp3", "wav"],
        )

    def on_save_picked(self, e: ft.FilePickerResultEvent):
        """保存对话框回调。"""
        if not e.path:
            return
        output_path = e.path
        start_ms = min(self.cut_start_ms, self.cut_end_ms)
        end_ms = max(self.cut_start_ms, self.cut_end_ms)

        self.running = True
        self.export_button.disabled = True
        self.progress.visible = True
        self.progress.value = 0.5
        self.show_status("正在导出...")

        threading.Thread(
            target=self._run_export,
            args=(start_ms, end_ms, output_path),
            daemon=True,
        ).start()

    def _run_export(self, start_ms: int, end_ms: int, output_path: str):
        """执行音频剪辑导出。"""
        try:
            clipped = self.audio[start_ms:end_ms]
            ext = Path(output_path).suffix.lower()

            export_params = {}
            if ext == '.mp3':
                export_params = {'bitrate': '192k'}

            clipped.export(output_path, format=ext.lstrip('.'), **export_params)

            duration_sec = (end_ms - start_ms) / 1000.0
            self.progress.value = 1
            self.page.update()

            self.show_status("导出成功！")
            self._show_result_dialog(
                "导出完成",
                f"音频已保存至：\n{output_path}\n\n"
                f"剪辑范围: {start_ms / 1000.0:.2f}s ~ {end_ms / 1000.0:.2f}s\n"
                f"剪辑时长: {duration_sec:.2f}s"
            )
        except Exception as err:
            self.show_status(f"导出失败: {err}", success=False)
        finally:
            self.running = False
            self.export_button.disabled = False
            self.progress.visible = False
            self._update_export_button()

    def _show_result_dialog(self, title: str, message: str):
        """显示结果弹窗。"""
        self.page.dialog = ft.AlertDialog(
            title=ft.Text(title, font_family=self.font_family),
            content=ft.Text(message, font_family=self.font_family),
            actions=[ft.TextButton("关闭", on_click=lambda e: self._close_dialog())],
        )
        self.page.dialog.open = True
        self.page.update()

    def _close_dialog(self):
        """关闭当前对话框。"""
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()


if __name__ == '__main__':
    app = AudioEditorApp()
    ft.app(target=app.build)
