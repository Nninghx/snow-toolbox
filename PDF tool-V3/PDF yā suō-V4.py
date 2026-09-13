# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import io
import os
import shutil
import threading
import importlib.util
from pathlib import Path

import flet as ft

import pikepdf
from PIL import Image


def get_project_root():
    """获取项目根目录"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def run_startup_preflight():
    """复用 Core 公共基类执行启动前置流程：授权检查 -> 窗口图标 -> 字体加载；失败时直接报错"""
    base_file = get_project_root() / 'Core' / 'Public base class.py'
    if not base_file.exists():
        raise FileNotFoundError(f"缺少公共基类：{base_file}")

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

        font_family = current_font[0]
        return True, font_family
    except Exception as exc:
        if root.winfo_exists():
            root.destroy()
        raise RuntimeError(f"启动前置检查失败：无法使用项目自带字体。{exc}") from exc
    finally:
        if root.winfo_exists():
            root.destroy()


STARTUP_OK, APP_FONT_FAMILY = run_startup_preflight()
if not STARTUP_OK:
    raise RuntimeError("启动前置检查失败：项目自带字体无法使用")


class PDFCompressorApp:
    # 压缩档位：(最大边长限制, JPEG 质量)；无损档不处理图片
    LEVELS = {
        'lossless': (None, None),
        'standard': (2500, 75),
        'extreme': (1600, 50),
    }
    LEVEL_LABELS = {
        'lossless': '无损压缩',
        'standard': '标准压缩',
        'extreme': '极限压缩',
    }

    def __init__(self):
        self.page = None
        self.files = []  # [{'path','name','size', 以及行内动态控件引用}]
        self.processing = False
        self.output_dir = None
        self.font_family = APP_FONT_FAMILY

    def build(self, page: ft.Page):
        self.page = page
        page.title = "PDF压缩"
        page.window.width = 780
        page.window.height = 700
        page.window.min_width = 660
        page.window.min_height = 600
        page.window.center()
        page.padding = 16
        page.theme_mode = ft.ThemeMode.LIGHT

        # 设置窗口图标
        icon_path = get_project_root() / 'Image' / 'icon.ico'
        if icon_path.exists():
            page.window.icon = str(icon_path)

        # 文件选择 / 目录选择对话框
        self.file_picker = ft.FilePicker(on_result=self.on_files_picked)
        self.dir_picker = ft.FilePicker(on_result=self.on_dir_picked)
        page.overlay.extend([self.file_picker, self.dir_picker])

        # 工具栏：添加文件 / 清空列表 / 统计信息
        self.add_btn = ft.ElevatedButton(
            "添加文件",
            icon=ft.Icons.ADD_CIRCLE_OUTLINE,
            on_click=self.add_files,
            height=36,
        )
        self.clear_btn = ft.TextButton(
            "清空列表",
            icon=ft.Icons.DELETE_SWEEP,
            on_click=self.confirm_clear,
        )
        self.stats_text = ft.Text(size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)
        toolbar_card = self._make_card(
            "文件操作",
            ft.Row(
                [
                    self.add_btn,
                    self.clear_btn,
                    ft.Container(expand=True),
                    self.stats_text,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
        )

        # 压缩列表卡片（可扩展滚动）
        self.file_rows = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
        self.empty_hint = ft.Text(
            "暂无文件，点击「添加文件」选择要压缩的PDF",
            size=13,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
            text_align=ft.TextAlign.CENTER,
        )
        list_card = self._make_card(
            "压缩列表（显示压缩前后大小与压缩率）",
            ft.Column(
                [self._list_header_row(), self.file_rows, self.empty_hint],
                spacing=8,
                expand=True,
            ),
            expand=True,
        )

        # 压缩设置卡片
        setting_card = self._make_card(
            "压缩设置",
            ft.Column(
                [
                    self._build_level_setting(),
                    ft.Divider(thickness=1, opacity=0.3),
                    self._build_output_setting(),
                ],
                spacing=8,
            ),
        )

        # 进度条与压缩按钮
        self.progress = ft.ProgressBar(
            visible=False,
            color=ft.Colors.BLUE,
            bgcolor=ft.Colors.GREY_200,
            bar_height=6,
            border_radius=4,
            expand=True,
        )
        self.progress_text = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)
        self.start_btn = ft.ElevatedButton(
            "开始压缩",
            icon=ft.Icons.COMPRESS,
            on_click=self.start_compress,
            height=40,
        )

        # 底部状态栏
        self.status_text = ft.Text("就绪", size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)

        page.add(
            ft.Column(
                [
                    # 顶部标题栏
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.COMPRESS, size=32, color=ft.Colors.BLUE),
                            ft.Text("PDF压缩", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Divider(thickness=1, opacity=0.3),
                    toolbar_card,
                    list_card,
                    setting_card,
                    ft.Row(
                        [self.progress, self.progress_text],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Row([self.start_btn], alignment=ft.MainAxisAlignment.END),
                    # 底部状态栏
                    ft.Container(
                        content=self.status_text,
                        padding=ft.padding.symmetric(vertical=8, horizontal=12),
                        bgcolor=ft.Colors.BLUE_GREY_50,
                        border_radius=8,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                    ),
                ],
                expand=True,
                spacing=10,
            )
        )
        self._refresh_file_list()

    def _make_card(self, title, content, expand=False):
        """创建白色圆角卡片（与主程序工具卡片风格一致）"""
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
                expand=bool(expand),
            ),
            padding=ft.padding.all(12),
            border_radius=10,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
            expand=expand,
        )

    def _build_level_setting(self):
        """压缩档位选择：无损 / 标准 / 极限"""
        self.level_group = ft.RadioGroup(
            value="standard",
            content=ft.Row(
                [
                    ft.Radio(value="lossless", label="无损压缩"),
                    ft.Radio(value="standard", label="标准压缩"),
                    ft.Radio(value="extreme", label="极限压缩"),
                ],
                spacing=20,
            ),
        )
        for radio in self.level_group.content.controls:
            radio.label_style = ft.TextStyle(font_family=self.font_family, size=14)
        return ft.Column(
            [
                self.level_group,
                ft.Text(
                    "无损档仅优化 PDF 内部数据；标准/极限档会将超大图片重编码为 JPEG，压缩率更高。",
                    size=12,
                    color=ft.Colors.BLUE_GREY_500,
                    font_family=self.font_family,
                ),
            ],
            spacing=6,
        )

    def _build_output_setting(self):
        """输出位置选择：原目录（加 _compressed 后缀）/ 指定目录"""
        self.output_mode = ft.RadioGroup(
            value="same",
            on_change=self.on_output_mode_change,
            content=ft.Row(
                [
                    ft.Radio(value="same", label="保存到原目录（添加 _compressed 后缀）"),
                    ft.Radio(value="custom", label="保存到指定目录"),
                ],
                spacing=16,
            ),
        )
        for radio in self.output_mode.content.controls:
            radio.label_style = ft.TextStyle(font_family=self.font_family, size=14)
        self.output_dir_text = ft.Text(
            "未选择目录",
            size=13,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
            expand=True,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.select_dir_btn = ft.ElevatedButton(
            "选择目录",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self.select_output_dir,
            height=36,
        )
        self.output_dir_row = ft.Row(
            [self.output_dir_text, self.select_dir_btn],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
            visible=False,
        )
        return ft.Column([self.output_mode, self.output_dir_row], spacing=8)

    def _list_header_row(self):
        """列表表头：序号 / 文件名 / 原大小 / 压缩后 / 压缩率 / 状态 / 操作"""
        style = ft.TextStyle(
            size=12,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_GREY_600,
            font_family=self.font_family,
        )
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(ft.Text("序号", style=style), width=34, alignment=ft.alignment.center),
                    ft.Text("文件名", style=style, expand=True),
                    ft.Container(ft.Text("原大小", style=style), width=72, alignment=ft.alignment.center),
                    ft.Container(ft.Text("压缩后", style=style), width=72, alignment=ft.alignment.center),
                    ft.Container(ft.Text("压缩率", style=style), width=60, alignment=ft.alignment.center),
                    ft.Container(ft.Text("状态", style=style), width=80, alignment=ft.alignment.center),
                    ft.Container(ft.Text("操作", style=style), width=34, alignment=ft.alignment.center),
                ],
                spacing=8,
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
        )

    def _build_file_row(self, index, item):
        """构建单个文件行：序号徽章 + 文件名 + 压缩信息 + 删除按钮"""
        order_badge = ft.Container(
            content=ft.Text(
                str(index + 1),
                size=12,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.WHITE,
                font_family=self.font_family,
            ),
            width=24,
            height=24,
            border_radius=12,
            bgcolor=ft.Colors.BLUE,
            alignment=ft.alignment.center,
        )
        name_text = ft.Text(
            item['name'],
            size=13,
            font_family=self.font_family,
            expand=True,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
            tooltip=item['path'],
        )
        origin_text = ft.Text(
            self._format_size(item['size']),
            size=12,
            color=ft.Colors.BLUE_GREY_700,
            font_family=self.font_family,
        )
        result_text = ft.Text("-", size=12, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)
        ratio_text = ft.Text("-", size=12, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)
        status_text = ft.Text(
            "等待压缩",
            size=12,
            color=ft.Colors.BLUE_GREY_600,
            font_family=self.font_family,
        )
        del_btn = ft.IconButton(
            ft.Icons.DELETE_OUTLINE,
            icon_size=18,
            width=30,
            height=30,
            icon_color=ft.Colors.RED_400,
            tooltip="移除",
            disabled=self.processing,
            on_click=lambda e, i=index: self.remove_file(i),
        )
        # 保存行内动态控件引用，供压缩过程中后台线程更新
        item.update({
            'origin_text': origin_text,
            'result_text': result_text,
            'ratio_text': ratio_text,
            'status_text': status_text,
            'del_btn': del_btn,
        })
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(order_badge, width=34, alignment=ft.alignment.center),
                    name_text,
                    ft.Container(origin_text, width=72, alignment=ft.alignment.center),
                    ft.Container(result_text, width=72, alignment=ft.alignment.center),
                    ft.Container(ratio_text, width=60, alignment=ft.alignment.center),
                    ft.Container(status_text, width=80, alignment=ft.alignment.center),
                    ft.Container(del_btn, width=34),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            border_radius=8,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )

    @staticmethod
    def _format_size(size):
        """格式化文件大小"""
        for unit in ('B', 'KB', 'MB', 'GB'):
            if size < 1024 or unit == 'GB':
                return f"{size:.1f} {unit}"
            size /= 1024

    def _refresh_file_list(self):
        """重建文件列表与统计信息"""
        self.file_rows.controls.clear()
        for index, item in enumerate(self.files):
            self.file_rows.controls.append(self._build_file_row(index, item))
        self.empty_hint.visible = not self.files
        if self.files:
            total_size = sum(item['size'] for item in self.files)
            self.stats_text.value = f"共 {len(self.files)} 个文件，合计 {self._format_size(total_size)}"
        else:
            self.stats_text.value = ""
        self.page.update()

    def add_files(self, e):
        if self.processing:
            return
        self.file_picker.pick_files(
            dialog_title="选择PDF文件",
            allow_multiple=True,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["pdf"],
        )

    def on_files_picked(self, e):
        if not e.files:
            return
        added, skipped = 0, 0
        existing_paths = {item['path'] for item in self.files}
        for picked in e.files:
            file = picked.path
            if not os.path.exists(file):
                skipped += 1
                continue
            if not file.lower().endswith('.pdf'):
                self.show_status(f"已跳过非PDF文件：{os.path.basename(file)}", success=False)
                skipped += 1
                continue
            if file in existing_paths:
                skipped += 1
                continue
            self.files.append({
                'path': file,
                'name': os.path.basename(file),
                'size': os.path.getsize(file),
            })
            existing_paths.add(file)
            added += 1
        if added:
            self.show_status(f"已添加 {added} 个文件" + (f"，跳过 {skipped} 个" if skipped else ""))
        elif skipped:
            self.show_status("所选文件均无法添加", success=False)
        self._refresh_file_list()

    def remove_file(self, index):
        """移除单个文件"""
        if self.processing:
            return
        if 0 <= index < len(self.files):
            item = self.files.pop(index)
            self._refresh_file_list()
            self.show_status(f"已移除：{item['name']}")

    def confirm_clear(self, e):
        """清空列表前弹窗确认"""
        if self.processing or not self.files:
            return
        self.page.dialog = ft.AlertDialog(
            title=ft.Text("确认", font_family=self.font_family),
            content=ft.Text("确定要清空文件列表吗？", font_family=self.font_family),
            actions=[
                ft.TextButton("取消", on_click=lambda e: self.close_dialog()),
                ft.TextButton("确定", on_click=lambda e: self.do_clear()),
            ],
        )
        self.page.dialog.open = True
        self.page.update()

    def do_clear(self):
        """清空所有文件"""
        self.close_dialog()
        self.files.clear()
        self._refresh_file_list()
        self.show_status("已清空文件列表")

    def select_output_dir(self, e):
        if self.processing:
            return
        self.dir_picker.get_directory_path(dialog_title="选择输出目录")

    def on_dir_picked(self, e):
        if not e.path:
            return
        self.output_dir = e.path
        self.output_dir_text.value = e.path
        self.output_dir_text.color = ft.Colors.BLUE_GREY_900
        self.output_dir_text.tooltip = e.path
        self.page.update()

    def on_output_mode_change(self, e):
        """输出模式切换：原目录 / 指定目录"""
        is_custom = self.output_mode.value == "custom"
        self.output_dir_row.visible = is_custom
        self.page.update()

    def _get_output_path(self, src, out_dir):
        """生成输出文件路径：自定义目录直接使用原文件名；原目录添加 _compressed 后缀并避免覆盖"""
        if out_dir:
            return os.path.join(out_dir, os.path.basename(src))
        stem, ext = os.path.splitext(src)
        path = f"{stem}_compressed{ext}"
        counter = 1
        while os.path.exists(path):
            path = f"{stem}_compressed({counter}){ext}"
            counter += 1
        return path

    def start_compress(self, e):
        """校验输入后开始后台压缩"""
        if self.processing:
            return
        if not self.files:
            self.show_status("请先添加PDF文件", success=False)
            return
        level = self.level_group.value
        if self.output_mode.value == 'custom':
            if not self.output_dir:
                self.show_status("请先选择输出目录", success=False)
                return
            out_dir = self.output_dir
        else:
            out_dir = None

        # 锁定界面，避免处理期间修改列表
        self.processing = True
        self.start_btn.disabled = True
        self.add_btn.disabled = True
        self.clear_btn.disabled = True
        for item in self.files:
            item['del_btn'].disabled = True
        for item in self.files:
            self._update_row(item, result="-", ratio="-", status="等待压缩",
                             color=ft.Colors.BLUE_GREY_600)
        self.progress.value = 0
        self.progress.visible = True
        self.progress_text.value = ""
        self.page.update()
        self.show_status(f"正在压缩（{self.LEVEL_LABELS[level]}）...")

        threading.Thread(
            target=self._do_compress,
            args=(level, out_dir),
            daemon=True,
        ).start()

    def _do_compress(self, level, out_dir):
        """执行实际的压缩操作（后台线程）"""
        total = len(self.files)
        success = 0
        try:
            max_dim, quality = self.LEVELS[level]
            for i, item in enumerate(self.files):
                src = item['path']
                self._update_row(item, status="压缩中...", color=ft.Colors.BLUE)
                try:
                    tmp_path = self._compress_one(src, out_dir, max_dim, quality)
                    final_path = tmp_path[:-4] if tmp_path.endswith('.tmp') else tmp_path
                    os.replace(tmp_path, final_path)
                    new_size = os.path.getsize(final_path)
                    old_size = item['size']
                    ratio = (1 - new_size / old_size) * 100 if old_size else 0
                    self._update_row(
                        item,
                        result=self._format_size(new_size),
                        ratio=f"{ratio:.1f}%",
                        status="完成",
                        color=ft.Colors.GREEN,
                    )
                    success += 1
                except Exception as err:
                    print(f"压缩失败 {src}: {err}")
                    self._update_row(item, status="失败", color=ft.Colors.RED_400)
                self._update_progress(i + 1, total)
            self._update_progress(total, total)
            if success:
                self.show_status(f"压缩完成：成功 {success}/{total} 个文件")
                self.show_info(
                    "成功",
                    f"PDF压缩完成！\n成功 {success}/{total} 个文件\n压缩档位：{self.LEVEL_LABELS[level]}",
                )
            else:
                self.show_status("压缩失败：所有文件均处理失败", success=False)
        except Exception as err:
            self.show_status(f"压缩失败: {err}", success=False)
        finally:
            self.processing = False
            self.start_btn.disabled = False
            self.add_btn.disabled = False
            self.clear_btn.disabled = False
            for item in self.files:
                item['del_btn'].disabled = False
            self.page.update()

    def _compress_one(self, src, out_dir, max_dim, quality):
        """压缩单个文件并返回临时输出路径（若压缩后反而变大则退回原文件）"""
        out_path = self._get_output_path(src, out_dir)
        tmp_path = f"{out_path}.tmp"
        pdf = pikepdf.open(src)
        try:
            if max_dim is not None:
                self._downsample_images(pdf, max_dim, quality)
            pdf.save(
                tmp_path,
                compress_streams=True,
                recompress_flate=True,
                stream_decode_level=pikepdf.StreamDecodeLevel.generalized,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
            )
        except Exception:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            raise
        finally:
            pdf.close()

        # 压缩后反而变大时，直接复制原文件（无损）
        if os.path.getsize(tmp_path) >= os.path.getsize(src):
            os.remove(tmp_path)
            shutil.copy2(src, tmp_path)
        return tmp_path

    def _downsample_images(self, pdf, max_dim, quality):
        """对超过尺寸限制的光栅图片重新编码为 JPEG"""
        for page in pdf.pages:
            resources = page.get('/Resources')
            if resources is None:
                continue
            xobjects = resources.get('/XObject')
            if xobjects is None:
                continue
            for key in list(xobjects.keys()):
                obj = xobjects.get(key)
                if obj is None or obj.get('/Subtype') != '/Image':
                    continue
                # 带透明通道或蒙版的图片跳过，避免破坏显示效果
                if obj.get('/SMask') is not None or obj.get('/Mask') is not None:
                    continue
                try:
                    pdfimage = pikepdf.PdfImage(obj)
                    if pdfimage.width <= max_dim and pdfimage.height <= max_dim:
                        continue
                    image = pdfimage.as_pil_image()
                    # 按最大边等比缩放
                    scale = max_dim / max(image.width, image.height)
                    new_size = (max(1, int(image.width * scale)),
                                max(1, int(image.height * scale)))
                    image = image.resize(new_size, Image.LANCZOS)
                    if image.mode not in ('RGB', 'L'):
                        image = image.convert('RGB')
                    buf = io.BytesIO()
                    image.save(buf, format='JPEG', quality=quality, optimize=True)
                    obj.write(buf.getvalue(), filter=pikepdf.Name.DCTDecode)
                except Exception:
                    # 单张图片处理失败不影响整体压缩
                    continue

    def _update_row(self, item, result=None, ratio=None, status=None, color=None):
        """后台线程中更新某一行的压缩状态显示"""
        if result is not None:
            item['result_text'].value = result
        if ratio is not None:
            item['ratio_text'].value = ratio
        if status is not None:
            item['status_text'].value = status
        if color is not None:
            item['status_text'].color = color
        item['result_text'].update()
        item['ratio_text'].update()
        item['status_text'].update()

    def _update_progress(self, done, total):
        """更新进度条与进度文本"""
        self.progress.value = done / total
        self.progress_text.value = f"{done}/{total}"
        self.progress.update()
        self.progress_text.update()

    def show_status(self, message: str, success: bool = True):
        """显示状态消息（底部状态栏 + SnackBar）"""
        self.status_text.value = message
        self.page.snack_bar = ft.SnackBar(
            ft.Text(message, font_family=self.font_family),
            bgcolor=ft.Colors.GREEN if success else ft.Colors.RED,
            open=True,
        )
        self.page.update()

    def show_info(self, title: str, message: str):
        """显示信息对话框"""
        self.page.dialog = ft.AlertDialog(
            title=ft.Text(title, font_family=self.font_family),
            content=ft.Text(message, font_family=self.font_family),
            actions=[ft.TextButton("关闭", on_click=lambda e: self.close_dialog())],
        )
        self.page.dialog.open = True
        self.page.update()

    def close_dialog(self, e=None):
        """关闭对话框"""
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()


if __name__ == '__main__':
    app = PDFCompressorApp()
    ft.app(target=app.build)
