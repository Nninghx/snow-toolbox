# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import os
import re
import threading
import importlib.util
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Callable

import flet as ft


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


# ======================== 字幕解析模块 ========================

@dataclass
class SubtitleSegment:
    """字幕段落数据"""
    start: float       # 开始时间（秒）
    end: float         # 结束时间（秒）
    text: str          # 字幕文本
    image_path: Optional[str] = None  # 分配的图片路径（None=纯白背景）


def _parse_time_srt(time_str: str) -> float:
    """解析 SRT 时间格式 HH:MM:SS,mmm -> 秒"""
    time_str = time_str.strip().replace(',', '.')
    parts = time_str.split(':')
    h, m = int(parts[0]), int(parts[1])
    s_parts = parts[2].split('.')
    s = int(s_parts[0])
    ms = int(s_parts[1]) if len(s_parts) > 1 else 0
    return h * 3600 + m * 60 + s + ms / 1000.0


def _parse_time_vtt(time_str: str) -> float:
    """解析 VTT 时间格式 [HH:]MM:SS.mmm -> 秒"""
    time_str = time_str.strip()
    parts = time_str.split(':')
    if len(parts) == 3:
        h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
        return h * 3600 + m * 60 + s
    elif len(parts) == 2:
        m, s = int(parts[0]), float(parts[1])
        return m * 60 + s
    return 0.0


def _parse_time_ass(time_str: str) -> float:
    """解析 ASS 时间格式 H:MM:SS.cc -> 秒"""
    time_str = time_str.strip()
    parts = time_str.split(':')
    h = int(parts[0])
    m = int(parts[1])
    s_parts = parts[2].split('.')
    s = int(s_parts[0])
    cs = int(s_parts[1]) if len(s_parts) > 1 else 0
    return h * 3600 + m * 60 + s + cs / 100.0


def _parse_time_lrc(time_str: str) -> float:
    """解析 LRC 时间格式 MM:SS.xx -> 秒"""
    parts = time_str.strip().split(':')
    m = int(parts[0])
    s_parts = parts[1].split('.')
    s = int(s_parts[0])
    frac = int(s_parts[1]) if len(s_parts) > 1 else 0
    divisor = 100 if len(s_parts) > 1 and len(s_parts[1]) == 2 else 1000
    return m * 60 + s + frac / divisor


def _strip_ass_tags(text: str) -> str:
    """去除 ASS 格式标签，如 {\\b1} {\\pos(x,y)} 等"""
    return re.sub(r'\{[^}]*\}', '', text).strip()


def parse_srt(filepath: str) -> List[SubtitleSegment]:
    """解析 SRT 字幕文件"""
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    segments = []
    blocks = re.split(r'\n\s*\n', content.strip())
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 2:
            continue
        # 查找时间行
        time_line_idx = 0
        if '-->' not in lines[0] and len(lines) > 1:
            time_line_idx = 1
        if '-->' not in lines[time_line_idx]:
            continue
        time_parts = lines[time_line_idx].split('-->')
        if len(time_parts) != 2:
            continue
        start = _parse_time_srt(time_parts[0])
        end = _parse_time_srt(time_parts[1])
        text = ' '.join(lines[time_line_idx + 1:]).strip()
        if text:
            segments.append(SubtitleSegment(start=start, end=end, text=text))
    return segments


def parse_ass_ssa(filepath: str) -> List[SubtitleSegment]:
    """解析 ASS/SSA 字幕文件"""
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    segments = []
    in_events = False
    format_fields = []

    for line in content.split('\n'):
        line = line.strip()
        if line.lower() == '[events]':
            in_events = True
            continue
        elif line.startswith('[') and in_events:
            in_events = False
            continue

        if not in_events:
            continue

        if line.lower().startswith('format:'):
            format_fields = [f.strip().lower() for f in line[7:].split(',')]
            continue

        if line.lower().startswith('dialogue:') or line.lower().startswith('dialog:'):
            prefix_len = len('dialogue:') if line.lower().startswith('dialogue:') else len('dialog:')
            values = line[prefix_len:].split(',', len(format_fields) - 1) if format_fields else line[prefix_len:].split(',', 9)

            if format_fields and 'start' in format_fields and 'end' in format_fields and 'text' in format_fields:
                start_idx = format_fields.index('start')
                end_idx = format_fields.index('end')
                text_idx = format_fields.index('text')
                if len(values) > max(start_idx, end_idx, text_idx):
                    start = _parse_time_ass(values[start_idx])
                    end = _parse_time_ass(values[end_idx])
                    text = _strip_ass_tags(values[text_idx].replace('\\N', ' ').replace('\\n', ' '))
                    if text:
                        segments.append(SubtitleSegment(start=start, end=end, text=text))
            elif len(values) >= 10:
                # 默认 ASS 格式: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
                start = _parse_time_ass(values[1])
                end = _parse_time_ass(values[2])
                text = _strip_ass_tags(values[9].replace('\\N', ' ').replace('\\n', ' '))
                if text:
                    segments.append(SubtitleSegment(start=start, end=end, text=text))

    segments.sort(key=lambda s: s.start)
    return segments


def parse_vtt(filepath: str) -> List[SubtitleSegment]:
    """解析 WebVTT 字幕文件"""
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    # 去除 WEBVTT 头部
    content = re.sub(r'^WEBVTT.*?\n\n', '', content, flags=re.DOTALL)
    segments = []
    blocks = re.split(r'\n\s*\n', content.strip())

    for block in blocks:
        lines = block.strip().split('\n')
        time_line = None
        text_lines = []
        for i, line in enumerate(lines):
            if '-->' in line:
                time_line = line
                text_lines = lines[i + 1:]
                break
        if not time_line:
            continue
        time_parts = time_line.split('-->')
        start = _parse_time_vtt(time_parts[0])
        end = _parse_time_vtt(time_parts[1].split()[0] if ' ' in time_parts[1] else time_parts[1])
        text = ' '.join(l.strip() for l in text_lines if l.strip())
        # 去除 VTT 标签
        text = re.sub(r'<[^>]+>', '', text)
        if text:
            segments.append(SubtitleSegment(start=start, end=end, text=text))
    return segments


def parse_lrc(filepath: str) -> List[SubtitleSegment]:
    """解析 LRC 歌词文件"""
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()

    timestamps = []  # (time, text)
    time_pattern = re.compile(r'\[(\d{1,3}:\d{2}(?:\.\d{1,3})?)\]')

    for line in lines:
        line = line.strip()
        if not line:
            continue
        matches = time_pattern.findall(line)
        if matches:
            text = time_pattern.sub('', line).strip()
            for t in matches:
                timestamps.append((_parse_time_lrc(t), text))

    timestamps.sort(key=lambda x: x[0])
    segments = []
    for i, (start, text) in enumerate(timestamps):
        end = timestamps[i + 1][0] if i + 1 < len(timestamps) else start + 3.0
        if text:
            segments.append(SubtitleSegment(start=start, end=end, text=text))
    return segments


def parse_subtitle(filepath: str) -> List[SubtitleSegment]:
    """自动识别字幕格式并解析"""
    ext = Path(filepath).suffix.lower()
    parsers = {
        '.srt': parse_srt,
        '.ass': parse_ass_ssa,
        '.ssa': parse_ass_ssa,
        '.vtt': parse_vtt,
        '.lrc': parse_lrc,
    }
    parser = parsers.get(ext)
    if parser is None:
        # 尝试通过内容检测格式
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            head = f.read(512)
        if 'WEBVTT' in head:
            parser = parse_vtt
        elif '[Script Info]' in head or '[Events]' in head:
            parser = parse_ass_ssa
        elif '-->' in head:
            parser = parse_srt
        elif re.search(r'\[\d{1,3}:\d{2}', head):
            parser = parse_lrc
        else:
            raise ValueError(f"不支持的字幕格式：{ext}")
    return parser(filepath)


# ======================== 视频合成模块 ========================

def compose_video(
    segments: List[SubtitleSegment],
    audio_path: str,
    output_path: str,
    resolution: tuple = (1080, 1920),
    fade_duration: float = 0.5,
    progress_callback: Optional[Callable[[float], None]] = None,
):
    """根据字幕时间轴和图片分配合成视频。

    Args:
        segments: 带图片分配的字幕段落列表
        audio_path: 音频文件路径
        output_path: 输出视频路径
        resolution: 视频分辨率 (宽, 高)
        fade_duration: 淡入淡出时长（秒）
        progress_callback: 进度回调函数 (0.0 ~ 1.0)
    """
    try:
        from moviepy import VideoClip, AudioFileClip, ImageClip, CompositeVideoClip, ColorClip
    except ImportError:
        from moviepy.editor import VideoClip, AudioFileClip, ImageClip, CompositeVideoClip, ColorClip

    import numpy as np
    from PIL import Image

    width, height = resolution
    fps = 30

    # 加载音频获取总时长
    audio = AudioFileClip(audio_path)
    total_duration = audio.duration

    # 按时间轴构建帧序列：为每个时间段确定显示哪张图片
    # 先合并相邻的同图片段落
    timeline = []  # [(start, end, image_path_or_None)]
    for seg in segments:
        if timeline and timeline[-1][2] == seg.image_path and abs(timeline[-1][1] - seg.start) < 0.05:
            # 与上一段连续且同一图片，合并
            timeline[-1] = (timeline[-1][0], seg.end, seg.image_path)
        else:
            timeline.append((seg.start, seg.end, seg.image_path))

    # 填充空白时间段（字幕段之间的间隙）
    filled_timeline = []
    prev_end = 0.0
    for start, end, img in timeline:
        if start > prev_end + 0.01:
            filled_timeline.append((prev_end, start, None))
        filled_timeline.append((start, end, img))
        prev_end = end
    if prev_end < total_duration:
        filled_timeline.append((prev_end, total_duration, None))

    # 预加载并处理图片（居中，等比缩放适应画面）
    image_cache = {}
    for _, _, img_path in filled_timeline:
        if img_path and img_path not in image_cache:
            img = Image.open(img_path).convert('RGB')
            # 等比缩放使图片适应画面（留出边距）
            max_w = int(width * 0.9)
            max_h = int(height * 0.7)
            img.thumbnail((max_w, max_h), Image.LANCZOS)
            image_cache[img_path] = np.array(img)

    # 创建白色背景基底
    white_frame = np.ones((height, width, 3), dtype=np.uint8) * 255

    def make_frame(t):
        """根据时间 t 生成当前帧"""
        # 查找当前时间对应的段落
        current_img = None
        for start, end, img_path in filled_timeline:
            if start <= t < end:
                current_img = img_path
                break

        if current_img is None or current_img not in image_cache:
            return white_frame.copy()

        # 计算淡入淡出 alpha
        seg_start, seg_end = None, None
        for start, end, img_path in filled_timeline:
            if img_path == current_img and start <= t < end:
                seg_start, seg_end = start, end
                break

        alpha = 1.0
        if seg_start is not None:
            # 淡入
            if t - seg_start < fade_duration:
                alpha = (t - seg_start) / fade_duration
            # 淡出
            if seg_end - t < fade_duration:
                alpha = min(alpha, (seg_end - t) / fade_duration)
        alpha = max(0.0, min(1.0, alpha))

        if alpha <= 0.0:
            return white_frame.copy()

        # 将图片居中合成到白色背景上
        frame = white_frame.copy()
        img_array = image_cache[current_img]
        img_h, img_w = img_array.shape[:2]
        y_offset = (height - img_h) // 2
        x_offset = (width - img_w) // 2

        # Alpha 混合
        roi = frame[y_offset:y_offset + img_h, x_offset:x_offset + img_w]
        blended = (roi * (1 - alpha) + img_array * alpha).astype(np.uint8)
        frame[y_offset:y_offset + img_h, x_offset:x_offset + img_w] = blended
        return frame

    # 创建视频剪辑
    video = VideoClip(make_frame, duration=total_duration)
    video = video.with_fps(fps)
    video = video.with_audio(audio)

    # 导出
    if progress_callback:
        video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            fps=fps,
            preset='medium',
            logger=None,
        )
    else:
        video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            fps=fps,
            preset='medium',
        )

    video.close()
    audio.close()


# ======================== Flet GUI ========================

class VideoCreatorApp:
    """图片卡点视频制作工具

    导入音频和字幕文件，为每段字幕分配图片，
    自动合成 9:16 竖屏视频，图片切换带淡入淡出效果。
    """

    def __init__(self):
        self.page = None
        self.font_family = APP_FONT_FAMILY
        self.audio_path = None
        self.subtitle_path = None
        self.output_path = None
        self.images: List[str] = []         # 已导入的图片路径列表
        self.segments: List[SubtitleSegment] = []  # 解析后的字幕段落
        self.segment_controls: List[ft.Row] = []   # 字幕列表 UI 控件
        self.running = False

    def build(self, page: ft.Page):
        self.page = page
        page.title = "图片卡点视频"
        page.window.width = 800
        page.window.height = 700
        page.window.center()
        page.padding = 16
        page.theme_mode = ft.ThemeMode.LIGHT
        page.scroll = ft.ScrollMode.AUTO

        # 设置窗口图标
        icon_path = get_project_root() / 'Image' / 'icon.ico'
        if icon_path.exists():
            page.window.icon = str(icon_path)

        # 文件选择器
        self.audio_picker = ft.FilePicker(on_result=self.on_audio_picked)
        self.subtitle_picker = ft.FilePicker(on_result=self.on_subtitle_picked)
        self.image_picker = ft.FilePicker(on_result=self.on_images_picked)
        self.output_picker = ft.FilePicker(on_result=self.on_output_picked)
        page.overlay.extend([
            self.audio_picker, self.subtitle_picker,
            self.image_picker, self.output_picker
        ])

        # === 音频文件卡片 ===
        self.audio_text = ft.Text(
            "未选择文件", size=13, color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family, expand=True,
            no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
        )
        audio_card = self._make_card("音频文件", ft.Row([
            ft.Icon(ft.Icons.MUSIC_NOTE, size=18, color=ft.Colors.BLUE_GREY_400),
            self.audio_text,
            ft.ElevatedButton("选择", icon=ft.Icons.UPLOAD_FILE, on_click=self.select_audio),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8))

        # === 字幕文件卡片 ===
        self.subtitle_text = ft.Text(
            "未选择文件", size=13, color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family, expand=True,
            no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
        )
        subtitle_card = self._make_card("字幕文件（SRT / ASS / VTT / LRC）", ft.Row([
            ft.Icon(ft.Icons.SUBTITLES, size=18, color=ft.Colors.BLUE_GREY_400),
            self.subtitle_text,
            ft.ElevatedButton("选择", icon=ft.Icons.UPLOAD_FILE, on_click=self.select_subtitle),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8))

        # === 图片导入卡片 ===
        self.images_text = ft.Text(
            "未导入图片", size=13, color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family, expand=True,
            no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
        )
        images_card = self._make_card("图片素材", ft.Row([
            ft.Icon(ft.Icons.IMAGE, size=18, color=ft.Colors.BLUE_GREY_400),
            self.images_text,
            ft.ElevatedButton("导入图片", icon=ft.Icons.ADD_PHOTO_ALTERNATE, on_click=self.select_images),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8))

        # === 字幕-图片分配卡片 ===
        self.segments_list = ft.Column(
            spacing=4,
            scroll=ft.ScrollMode.AUTO,
            height=280,
        )
        self.segments_card = self._make_card(
            "字幕段落 → 图片分配",
            ft.Column([
                ft.Text(
                    "请先导入字幕文件和图片素材",
                    size=12, color=ft.Colors.BLUE_GREY_400,
                    font_family=self.font_family,
                ),
                self.segments_list,
            ], spacing=8),
        )

        # === 输出路径卡片 ===
        self.output_text = ft.Text(
            "未设置", size=13, color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family, expand=True,
            no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
        )
        output_card = self._make_card("输出视频", ft.Row([
            ft.Icon(ft.Icons.VIDEO_FILE, size=18, color=ft.Colors.BLUE_GREY_400),
            self.output_text,
            ft.ElevatedButton("选择位置", icon=ft.Icons.SAVE, on_click=self.select_output),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8))

        # === 淡入淡出时长设置 ===
        self.fade_slider = ft.Slider(
            min=0.1, max=2.0, value=0.5, divisions=18,
            label="{value}s", expand=True,
            active_color=ft.Colors.BLUE,
        )
        self.fade_value_text = ft.Text("0.5s", size=12, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)
        self.fade_slider.on_change = self._on_fade_change
        fade_card = self._make_card("转场淡入淡出时长", ft.Row([
            ft.Icon(ft.Icons.BLUR_ON, size=18, color=ft.Colors.BLUE_GREY_400),
            self.fade_slider,
            self.fade_value_text,
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8))

        # === 操作按钮和进度 ===
        self.generate_button = ft.ElevatedButton(
            "生成视频", icon=ft.Icons.MOVIE_CREATION,
            on_click=self.generate_video, height=42,
            style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE),
        )
        self.progress = ft.ProgressBar(
            visible=False, color=ft.Colors.BLUE,
            bgcolor=ft.Colors.GREY_200, bar_height=6,
            border_radius=4, expand=True,
        )

        # === 状态栏 ===
        self.status_text = ft.Text("就绪", size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)

        page.add(
            # 页面标题
            ft.Row([
                ft.Icon(ft.Icons.MOVIE_CREATION, size=32, color=ft.Colors.BLUE),
                ft.Text("图片卡点视频", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            ft.Divider(thickness=1, opacity=0.3),
            audio_card,
            subtitle_card,
            images_card,
            self.segments_card,
            fade_card,
            output_card,
            self.progress,
            ft.Row([self.generate_button], alignment=ft.MainAxisAlignment.END),
            # 底部状态区
            ft.Container(
                content=self.status_text,
                padding=ft.padding.symmetric(vertical=8, horizontal=12),
                bgcolor=ft.Colors.BLUE_GREY_50,
                border_radius=8,
                border=ft.border.all(1, ft.Colors.GREY_300),
            ),
        )

    def _make_card(self, title, content):
        """创建统一的白色卡片容器。"""
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=13, weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_GREY_700, font_family=self.font_family),
                content,
            ], spacing=8),
            padding=ft.padding.all(12),
            border_radius=10,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )

    def _on_fade_change(self, e):
        self.fade_value_text.value = f"{self.fade_slider.value:.1f}s"
        self.page.update()

    # ---------- 文件选择回调 ----------

    def select_audio(self, e):
        self.audio_picker.pick_files(
            dialog_title="选择音频文件",
            allow_multiple=False,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["mp3", "wav", "flac", "aac", "m4a", "ogg", "wma"],
        )

    def on_audio_picked(self, e):
        if not e.files:
            return
        self.audio_path = e.files[0].path
        self.audio_text.value = os.path.basename(self.audio_path)
        self.audio_text.color = ft.Colors.BLUE_GREY_900
        # 自动设置输出路径
        if not self.output_path:
            self.output_path = str(Path(self.audio_path).with_suffix('.mp4'))
            self.output_text.value = self.output_path
            self.output_text.color = ft.Colors.BLUE_GREY_900
        self.page.update()

    def select_subtitle(self, e):
        self.subtitle_picker.pick_files(
            dialog_title="选择字幕文件",
            allow_multiple=False,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["srt", "ass", "ssa", "vtt", "lrc"],
        )

    def on_subtitle_picked(self, e):
        if not e.files:
            return
        self.subtitle_path = e.files[0].path
        self.subtitle_text.value = os.path.basename(self.subtitle_path)
        self.subtitle_text.color = ft.Colors.BLUE_GREY_900

        # 解析字幕
        try:
            self.segments = parse_subtitle(self.subtitle_path)
            self.show_status(f"字幕解析成功，共 {len(self.segments)} 段")
            self._rebuild_segments_list()
        except Exception as err:
            self.show_status(f"字幕解析失败：{err}", success=False)
            self.segments = []
        self.page.update()

    def select_images(self, e):
        self.image_picker.pick_files(
            dialog_title="选择图片素材（可多选）",
            allow_multiple=True,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["png", "jpg", "jpeg", "bmp", "webp", "gif"],
        )

    def on_images_picked(self, e):
        if not e.files:
            return
        self.images = [f.path for f in e.files if f.path]
        self.images_text.value = f"已导入 {len(self.images)} 张图片"
        self.images_text.color = ft.Colors.BLUE_GREY_900
        self._rebuild_segments_list()
        self.page.update()

    def select_output(self, e):
        self.output_picker.save_file(
            dialog_title="保存视频文件",
            file_name="output.mp4",
            allowed_extensions=["mp4"],
        )

    def on_output_picked(self, e):
        if not e.path:
            return
        self.output_path = e.path
        if not self.output_path.lower().endswith('.mp4'):
            self.output_path += '.mp4'
        self.output_text.value = self.output_path
        self.output_text.color = ft.Colors.BLUE_GREY_900
        self.page.update()

    # ---------- 字幕段落列表 UI ----------

    def _rebuild_segments_list(self):
        """重建字幕段落分配列表"""
        self.segments_list.controls.clear()
        self.segment_controls.clear()

        if not self.segments:
            self.segments_list.controls.append(
                ft.Text("请先导入字幕文件", size=12, color=ft.Colors.BLUE_GREY_400,
                        font_family=self.font_family)
            )
            return

        # 表头
        header = ft.Row([
            ft.Container(ft.Text("#", size=11, weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLUE_GREY_600, font_family=self.font_family), width=30),
            ft.Container(ft.Text("时间", size=11, weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLUE_GREY_600, font_family=self.font_family), width=140),
            ft.Container(ft.Text("内容", size=11, weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLUE_GREY_600, font_family=self.font_family), expand=True),
            ft.Container(ft.Text("分配图片", size=11, weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLUE_GREY_600, font_family=self.font_family), width=160),
        ], spacing=4)
        self.segments_list.controls.append(header)
        self.segments_list.controls.append(ft.Divider(thickness=1, opacity=0.2))

        # 图片选项：无图片 + 已导入的图片
        image_options = [ft.dropdown.Option(key="-1", text="无图片（白色背景）")]
        for i, img_path in enumerate(self.images):
            img_name = os.path.basename(img_path)
            if len(img_name) > 15:
                img_name = img_name[:12] + "..."
            image_options.append(ft.dropdown.Option(key=str(i), text=f"图{i+1}: {img_name}"))

        for idx, seg in enumerate(self.segments):
            time_str = f"{self._fmt_time(seg.start)} → {self._fmt_time(seg.end)}"
            text_display = seg.text[:30] + "..." if len(seg.text) > 30 else seg.text

            dropdown = ft.Dropdown(
                options=image_options,
                value="-1",
                height=32,
                text_size=11,
                content_padding=ft.padding.symmetric(horizontal=8, vertical=2),
                on_change=lambda e, i=idx: self._on_image_assign(i, e),
            )

            row = ft.Row([
                ft.Container(ft.Text(str(idx + 1), size=11, color=ft.Colors.BLUE_GREY_600,
                                    font_family=self.font_family), width=30),
                ft.Container(ft.Text(time_str, size=11, color=ft.Colors.BLUE_GREY_600,
                                    font_family=self.font_family), width=140),
                ft.Container(ft.Text(text_display, size=11, color=ft.Colors.BLUE_GREY_800,
                                    font_family=self.font_family, no_wrap=True,
                                    overflow=ft.TextOverflow.ELLIPSIS), expand=True),
                ft.Container(dropdown, width=160),
            ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER)

            self.segments_list.controls.append(row)
            self.segment_controls.append(row)

    def _on_image_assign(self, segment_idx: int, e):
        """用户为字幕段落分配图片"""
        dropdown = e.control
        key = dropdown.value
        if key == "-1":
            self.segments[segment_idx].image_path = None
        else:
            img_idx = int(key)
            if 0 <= img_idx < len(self.images):
                self.segments[segment_idx].image_path = self.images[img_idx]

    def _fmt_time(self, seconds: float) -> str:
        """格式化时间为 MM:SS.s"""
        m = int(seconds) // 60
        s = seconds % 60
        return f"{m:02d}:{s:04.1f}"

    # ---------- 视频生成 ----------

    def generate_video(self, e):
        """开始生成视频"""
        if self.running:
            return

        # 校验
        if not self.audio_path or not os.path.isfile(self.audio_path):
            self.show_status("请选择有效的音频文件", success=False)
            return
        if not self.segments:
            self.show_status("请导入并解析字幕文件", success=False)
            return
        if not self.output_path:
            self.show_status("请设置输出视频路径", success=False)
            return

        # 检查是否至少分配了一张图片
        has_image = any(seg.image_path for seg in self.segments)
        if not has_image:
            self.show_status("请至少为一段字幕分配图片", success=False)
            return

        # 检查 moviepy 是否可用
        try:
            import moviepy
        except ImportError:
            self.show_status("缺少依赖：请安装 moviepy（pip install moviepy）", success=False)
            return

        self.running = True
        self.generate_button.disabled = True
        self.progress.visible = True
        self.progress.value = 0
        self.show_status("正在生成视频...")

        threading.Thread(target=self._run_compose, daemon=True).start()

    def _run_compose(self):
        """后台线程执行视频合成"""
        try:
            fade_dur = self.fade_slider.value if self.fade_slider.value else 0.5

            compose_video(
                segments=self.segments,
                audio_path=self.audio_path,
                output_path=self.output_path,
                resolution=(1080, 1920),
                fade_duration=fade_dur,
                progress_callback=self._update_progress,
            )

            self.progress.value = 1
            self.progress.update()
            self.show_status("视频生成成功！")
            self.show_info("完成", f"视频已保存至：\n{self.output_path}")
        except Exception as err:
            self.show_status(f"生成失败：{err}", success=False)
        finally:
            self.running = False
            self.generate_button.disabled = False
            self.progress.visible = False
            self.generate_button.update()
            self.progress.update()

    def _update_progress(self, value: float):
        """更新进度条"""
        self.progress.value = value
        self.progress.update()

    # ---------- 通用方法 ----------

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
    app = VideoCreatorApp()
    ft.app(target=app.build)
