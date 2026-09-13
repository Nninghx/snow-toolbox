# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import os
import threading
import importlib.util
from pathlib import Path

import flet as ft

import fitz  # PyMuPDF
from PIL import Image


def get_project_root():
    """获取项目根目录"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def _resolve_base_class_path():
    """解析公共基类文件路径，打包后自动使用 .pyc 字节码"""
    base_py = get_project_root() / 'Core' / 'Public base class.py'
    if getattr(sys, 'frozen', False):
        import importlib.util
        return Path(importlib.util.cache_from_source(str(base_py)))
    return base_py


def run_startup_preflight():
    """复用 Core 公共基类执行启动前置流程：授权检查 -> 窗口图标 -> 字体加载；失败时直接报错"""
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


class PDFToImageApp:
    """PDF转图片：选择 PDF -> 设置格式/DPI/质量/页码范围 -> 渲染导出为图片"""

    # 输出格式：扩展名 -> Pillow 格式名（与用户显示顺序一致）
    FORMATS = [
        ('png', 'PNG'),
        ('jpg', 'JPEG'),
        ('tiff', 'TIFF'),
        ('bmp', 'BMP'),
    ]
    # 扩展名 -> 显示名 / Pillow 格式名
    FORMAT_MAP = dict(FORMATS)
    DPI_OPTIONS = [72, 96, 150, 300, 600]

    def __init__(self):
        self.page = None
        self.input_file = None
        self.total_pages = 0
        self.output_dir = None      # 仅「指定目录」模式使用
        self.processing = False
        self.font_family = APP_FONT_FAMILY

    def build(self, page: ft.Page):
        self.page = page
        page.title = "PDF转图片"
        page.window.width = 740
        page.window.height = 760
        page.window.min_width = 660
        page.window.min_height = 660
        page.window.center()
        page.padding = 16
        page.theme_mode = ft.ThemeMode.LIGHT

        # 设置窗口图标
        icon_path = get_project_root() / 'Image' / 'icon.ico'
        if icon_path.exists():
            page.window.icon = str(icon_path)

        # 文件 / 目录选择器
        self.file_picker = ft.FilePicker(on_result=self.on_file_picked)
        self.dir_picker = ft.FilePicker(on_result=self.on_dir_picked)
        page.overlay.extend([self.file_picker, self.dir_picker])

        # 卡片1：PDF 文件
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
            "PDF文件",
            ft.Row(
                [
                    ft.Icon(ft.Icons.INSERT_DRIVE_FILE, size=18, color=ft.Colors.BLUE_GREY_400),
                    self.file_text,
                    ft.ElevatedButton("选择文件", icon=ft.Icons.UPLOAD_FILE, on_click=self.select_file, height=36),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
        )

        # 卡片2：页面范围
        self.page_mode = ft.RadioGroup(
            value="all",
            on_change=self.on_page_mode_change,
            content=ft.Row(
                [
                    ft.Radio(
                        value="all",
                        label="全部页面",
                        label_style=ft.TextStyle(font_family=self.font_family, size=14),
                    ),
                    ft.Radio(
                        value="custom",
                        label="指定页码",
                        label_style=ft.TextStyle(font_family=self.font_family, size=14),
                    ),
                ],
                spacing=20,
            ),
        )
        self.range_field = ft.TextField(
            label="页码范围",
            hint_text="如 1-3,5,7-9",
            expand=True,
            border_radius=8,
            content_padding=ft.padding.all(10),
            text_size=14,
            text_style=ft.TextStyle(font_family=self.font_family),
        )
        self.range_row = ft.Row([self.range_field], visible=False)
        self.page_hint = ft.Text(
            "默认转换 PDF 的全部页面",
            size=12,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
        )
        page_card = self._make_card(
            "转换范围",
            ft.Column([self.page_mode, self.range_row, self.page_hint], spacing=8),
        )

        # 卡片3：转换设置
        setting_card = self._make_card(
            "转换设置",
            ft.Column(
                [
                    self._build_format_setting(),
                    ft.Divider(thickness=1, opacity=0.3),
                    self._build_quality_setting(),
                ],
                spacing=8,
            ),
        )

        # 卡片4：输出位置
        self.output_mode = ft.RadioGroup(
            value="same",
            on_change=self.on_output_mode_change,
            content=ft.Row(
                [
                    ft.Radio(
                        value="same",
                        label="PDF 所在目录",
                        label_style=ft.TextStyle(font_family=self.font_family, size=14),
                    ),
                    ft.Radio(
                        value="custom",
                        label="指定目录",
                        label_style=ft.TextStyle(font_family=self.font_family, size=14),
                    ),
                ],
                spacing=20,
            ),
        )
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
        output_card = self._make_card(
            "输出位置",
            ft.Column(
                [
                    self.output_mode,
                    self.output_dir_row,
                    ft.Text(
                        "图片将保存到所选目录下的「PDF文件名_images」子文件夹",
                        size=12,
                        color=ft.Colors.BLUE_GREY_500,
                        font_family=self.font_family,
                    ),
                ],
                spacing=8,
            ),
        )

        # 进度条与开始按钮
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
            "开始转换",
            icon=ft.Icons.IMAGE,
            on_click=self.start_convert,
            height=40,
        )

        # 底部状态栏
        self.status_text = ft.Text("就绪", size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)
        self.stats_text = ft.Text(size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)

        page.add(
            ft.Column(
                [
                    # 顶部标题栏
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.IMAGE, size=32, color=ft.Colors.BLUE),
                            ft.Text("PDF转图片", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Divider(thickness=1, opacity=0.3),
                    file_card,
                    page_card,
                    setting_card,
                    output_card,
                    ft.Row(
                        [self.progress, self.progress_text],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Row([self.start_btn], alignment=ft.MainAxisAlignment.END),
                    # 底部状态栏
                    ft.Container(
                        content=ft.Row(
                            [self.status_text, self.stats_text],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
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

    def _make_card(self, title, content):
        """创建统一的白色卡片容器（与 V4 系列工具风格一致）"""
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

    def _build_format_setting(self):
        """输出格式单选：PNG / JPEG / TIFF / BMP"""
        self.format_group = ft.RadioGroup(
            value="png",
            on_change=self.on_format_change,
            content=ft.Row(
                [
                    ft.Radio(value=ext, label=label,
                             label_style=ft.TextStyle(font_family=self.font_family, size=14))
                    for ext, label in self.FORMATS
                ],
                spacing=16,
            ),
        )
        return ft.Column([self.format_group], spacing=6)

    def _build_quality_setting(self):
        """DPI 与 JPEG 质量（质量行仅 JPEG 格式显示）"""
        dpi_row = ft.Row(
            [
                ft.Text("分辨率 DPI：", size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family),
                ft.Dropdown(
                    value="300",
                    width=120,
                    options=[ft.dropdown.Option(str(v)) for v in self.DPI_OPTIONS],
                    content_padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    text_style=ft.TextStyle(font_family=self.font_family),
                ),
                ft.Container(expand=True),
                self._build_quality_row(),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        )
        self.dpi_drop = dpi_row.controls[1]
        self.quality_row = dpi_row.controls[3]
        self.quality_row.visible = False
        return ft.Column([dpi_row], spacing=6)

    def _build_quality_row(self):
        """JPEG 质量滑块 + 百分比显示"""
        self.quality_slider = ft.Slider(
            min=1,
            max=100,
            divisions=99,
            value=90,
            width=200,
            on_change=self.on_quality_change,
        )
        self.quality_text = ft.Text(
            "90%",
            size=13,
            width=40,
            color=ft.Colors.BLUE_GREY_700,
            font_family=self.font_family,
        )
        return ft.Row(
            [
                ft.Text("JPEG质量：", size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family),
                self.quality_slider,
                self.quality_text,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
        )

    def on_quality_change(self, e):
        self.quality_text.value = f"{int(self.quality_slider.value)}%"
        self.quality_text.update()

    def on_format_change(self, e):
        """切换格式时：仅 JPEG 显示质量设置"""
        self.quality_row.visible = self.format_group.value == 'jpg'
        self.page.update()

    def on_page_mode_change(self, e):
        """页面范围切换：全部页面 / 指定页码"""
        is_custom = self.page_mode.value == "custom"
        self.range_row.visible = is_custom
        self.page_hint.value = "默认转换 PDF 的全部页面" if not is_custom else "输入要转换的页码，支持 1-3,5,7-9 格式"
        self.page.update()

    def on_output_mode_change(self, e):
        """输出位置切换：PDF 所在目录 / 指定目录"""
        is_custom = self.output_mode.value == "custom"
        self.output_dir_row.visible = is_custom
        self.page.update()

    # ---------- 文件与目录选择 ----------
    def select_file(self, e):
        if self.processing:
            return
        self.file_picker.pick_files(
            dialog_title="选择PDF文件",
            allow_multiple=False,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["pdf"],
        )

    def on_file_picked(self, e):
        if not e.files:
            return
        file = e.files[0].path
        if not os.path.exists(file):
            self.show_status("文件不存在", success=False)
            return
        if not file.lower().endswith('.pdf'):
            self.show_status("请选择PDF文件", success=False)
            return
        self.input_file = file
        self.file_text.value = os.path.basename(file)
        self.file_text.color = ft.Colors.BLUE_GREY_900
        self.file_text.tooltip = file
        self.page_mode.value = "all"
        self.range_row.visible = False
        self.page_hint.value = "默认转换 PDF 的全部页面"
        self._refresh_page_info()
        self.page.update()

    def _get_pdf_total_pages(self, pdf_path=None):
        """返回指定 PDF 的总页数"""
        target = pdf_path or self.input_file
        doc = fitz.open(target)
        try:
            return len(doc)
        finally:
            doc.close()

    def _refresh_page_info(self):
        try:
            self.total_pages = self._get_pdf_total_pages()
            self.stats_text.value = f"共 {self.total_pages} 页"
            self.stats_text.color = ft.Colors.BLUE_GREY_700
        except Exception:
            self.total_pages = 0
            self.stats_text.value = ""

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

    def parse_page_ranges(self, range_str, total_pages):
        """解析页码范围字符串，返回 0 基索引列表（升序去重）"""
        ranges = []
        for part in range_str.split(','):
            if not part.strip():
                continue
            if '-' in part:
                start, end = map(int, part.split('-', 1))
                ranges.extend(range(max(start - 1, 0), min(end, total_pages)))
            else:
                page = int(part)
                if 1 <= page <= total_pages:
                    ranges.append(page - 1)
        return sorted(set(ranges))

    # ---------- 转换 ----------
    def start_convert(self, e):
        if self.processing:
            return
        if not self.input_file:
            self.show_status("请先选择PDF文件", success=False)
            return
        if not os.path.exists(self.input_file):
            self.show_status("PDF文件不存在", success=False)
            return

        # 解析页面范围
        if self.page_mode.value == "custom":
            range_str = (self.range_field.value or "").strip()
            if not range_str:
                self.show_status("请输入有效的页码范围", success=False)
                return
            try:
                page_indices = self.parse_page_ranges(range_str, self.total_pages)
                if not page_indices:
                    raise ValueError("没有有效的页码被选择")
            except ValueError as err:
                self.show_status(f"页码范围无效: {err}", success=False)
                return
        else:
            page_indices = list(range(self.total_pages))
            if not page_indices:
                self.show_status("PDF文件没有有效页面", success=False)
                return

        # 解析输出位置
        fmt = self.format_group.value
        if self.output_mode.value == "custom":
            if not self.output_dir:
                self.show_status("请先选择输出目录", success=False)
                return
            out_root = self.output_dir
        else:
            out_root = os.path.dirname(self.input_file)

        # 输出参数快照，供后台线程使用
        dpi = int(self.dpi_drop.value)
        quality = int(self.quality_slider.value)

        # 锁定界面
        self.processing = True
        self.start_btn.disabled = True
        self.file_picker = self.file_picker  # noqa
        self.progress.value = 0
        self.progress.visible = True
        self.progress_text.value = f"0/{len(page_indices)}"
        self.page.update()
        self.show_status(f"正在转换（{self.FORMAT_MAP.get(fmt, fmt)}，{dpi} DPI）...")

        threading.Thread(
            target=self._do_convert,
            args=(page_indices, out_root, fmt, dpi, quality),
            daemon=True,
        ).start()

    def _do_convert(self, page_indices, out_root, fmt, dpi, quality):
        """在后台线程中渲染并保存图片（PDF 文件名_images 子目录）"""
        try:
            pdf_name = os.path.splitext(os.path.basename(self.input_file))[0]
            out_subdir = os.path.join(out_root, f"{pdf_name}_images")
            os.makedirs(out_subdir, exist_ok=True)

            zoom = dpi / 72  # 默认 PDF 坐标按 72 DPI
            mat = fitz.Matrix(zoom, zoom)
            total = len(page_indices)
            success = 0
            ext = fmt
            pil_format = self.FORMAT_MAP[fmt]

            doc = fitz.open(self.input_file)
            try:
                for i, page_num in enumerate(page_indices):
                    self.status_text.value = f"正在转换第 {page_num + 1} 页（{i + 1}/{total}）"
                    self.status_text.update()
                    try:
                        pix = doc[page_num].get_pixmap(matrix=mat)
                        img = Image.frombytes(
                            "RGB" if pix.alpha == 0 else "RGBA",
                            (pix.width, pix.height),
                            pix.samples,
                        )
                        if fmt == 'jpg' and img.mode not in ('RGB', 'L'):
                            img = img.convert('RGB')

                        out_path = os.path.join(out_subdir, f"{pdf_name}_page_{page_num + 1}.{ext}")
                        if fmt == 'jpg':
                            img.save(out_path, format=pil_format, quality=quality, dpi=(dpi, dpi))
                        elif fmt == 'bmp':
                            img.save(out_path, format=pil_format)
                        else:
                            img.save(out_path, format=pil_format, dpi=(dpi, dpi))
                        success += 1
                    except Exception as err:
                        print(f"第 {page_num + 1} 页转换失败: {err}")
                    self._update_progress(i + 1, total)
            finally:
                doc.close()

            if success:
                self.show_status(f"转换完成：成功 {success}/{total} 个页面")
                self.show_info(
                    "成功",
                    f"PDF转图片完成！\n成功 {success}/{total} 个页面\n保存位置：{out_subdir}",
                )
                self._open_output_folder(out_subdir)
            else:
                self.show_status("转换失败：所有页面均处理失败", success=False)
        except Exception as err:
            self.show_status(f"转换失败: {err}", success=False)
        finally:
            self.processing = False
            self.start_btn.disabled = False
            self.page.update()

    def _open_output_folder(self, folder_path):
        """在文件资源管理器中打开输出文件夹"""
        try:
            if sys.platform == 'win32':
                os.startfile(folder_path)
            elif sys.platform == 'darwin':
                os.system(f'open "{folder_path}"')
            else:
                os.system(f'xdg-open "{folder_path}"')
        except Exception as err:
            print(f"无法打开输出文件夹: {err}")

    # ---------- 通用 UI 辅助 ----------
    def _update_progress(self, done, total):
        """更新进度条与进度文本"""
        self.progress.value = done / total
        self.progress_text.value = f"{done}/{total}"
        self.progress.update()
        self.progress_text.update()

    def show_status(self, message: str, success: bool = True):
        """更新状态栏并显示全局提示消息"""
        self.status_text.value = message
        self.page.snack_bar = ft.SnackBar(
            ft.Text(message, font_family=self.font_family),
            bgcolor=ft.Colors.GREEN if success else ft.Colors.RED,
            open=True,
        )
        self.page.update()

    def show_info(self, title: str, message: str):
        """显示结果弹窗"""
        self.page.dialog = ft.AlertDialog(
            title=ft.Text(title, font_family=self.font_family),
            content=ft.Text(message, font_family=self.font_family),
            actions=[ft.TextButton("关闭", on_click=lambda e: self.close_dialog())],
        )
        self.page.dialog.open = True
        self.page.update()

    def close_dialog(self, e=None):
        """关闭当前对话框"""
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()


if __name__ == '__main__':
    app = PDFToImageApp()
    ft.app(target=app.build)
