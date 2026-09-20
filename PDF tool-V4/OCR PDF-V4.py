# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import shutil
import threading
import importlib.util
from pathlib import Path

import flet as ft

import ocrmypdf


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


def check_tesseract():
    """检查 Tesseract OCR 引擎是否可用，返回 (可用, 路径或错误信息)"""
    tesseract_path = shutil.which('tesseract')
    if tesseract_path:
        return True, tesseract_path
    # 检查 Windows 常见安装路径
    common_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        os.path.expanduser(r'~\AppData\Local\Tesseract-OCR\tesseract.exe'),
    ]
    for path in common_paths:
        if os.path.exists(path):
            return True, path
    return False, (
        "未找到 Tesseract OCR 引擎。\n\n"
        "请先安装 Tesseract：\n"
        "1. 访问 https://github.com/UB-Mannheim/tesseract/wiki\n"
        "2. 下载安装包并安装\n"
        "3. 安装时勾选需要的语言包（如 Chinese Simplified）\n"
        "4. 安装后重启本工具"
    )


STARTUP_OK, APP_FONT_FAMILY = run_startup_preflight()
if not STARTUP_OK:
    raise RuntimeError("启动前置检查失败：项目自带字体无法使用")


# OCR 语言选项映射
OCR_LANGUAGES = {
    '中文简体 + 英文': 'chi_sim+eng',
    '中文繁体 + 英文': 'chi_tra+eng',
    '仅英文': 'eng',
    '仅中文简体': 'chi_sim',
    '仅中文繁体': 'chi_tra',
    '日文 + 英文': 'jpn+eng',
    '韩文 + 英文': 'kor+eng',
}


class PDFOCRApp:
    def __init__(self):
        self.page = None
        self.input_file = None
        self.total_pages = 0
        self.processing = False
        self.font_family = APP_FONT_FAMILY
        self.tesseract_ok = False
        self.tesseract_info = ""

    def build(self, page: ft.Page):
        self.page = page
        page.title = "OCR PDF"
        page.window.width = 640
        page.window.height = 660
        page.window.min_width = 580
        page.window.min_height = 580
        page.window.center()
        page.padding = 16
        page.theme_mode = ft.ThemeMode.LIGHT

        # 设置窗口图标
        icon_path = get_project_root() / 'Image' / 'icon.ico'
        if icon_path.exists():
            page.window.icon = str(icon_path)

        # 检查 Tesseract 可用性
        self.tesseract_ok, self.tesseract_info = check_tesseract()

        # 文件选择 / 保存对话框
        self.file_picker = ft.FilePicker(on_result=self.on_file_picked)
        self.save_picker = ft.FilePicker(on_result=self.on_save_picked)
        page.overlay.extend([self.file_picker, self.save_picker])

        # PDF文件选择卡片
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
                    ft.ElevatedButton("选择文件", icon=ft.Icons.UPLOAD_FILE, on_click=self.select_file),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
        )

        # Tesseract 状态提示
        if self.tesseract_ok:
            engine_status = ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=16, color=ft.Colors.GREEN),
                    ft.Text(
                        f"Tesseract 已就绪",
                        size=12,
                        color=ft.Colors.GREEN,
                        font_family=self.font_family,
                    ),
                ],
                spacing=4,
            )
        else:
            engine_status = ft.Row(
                [
                    ft.Icon(ft.Icons.ERROR, size=16, color=ft.Colors.RED),
                    ft.Text(
                        "Tesseract 未安装",
                        size=12,
                        color=ft.Colors.RED,
                        font_family=self.font_family,
                    ),
                ],
                spacing=4,
            )

        # OCR 语言选择卡片
        lang_options = list(OCR_LANGUAGES.keys())
        self.lang_dropdown = ft.Dropdown(
            label="识别语言",
            value=lang_options[0],
            options=[ft.dropdown.Option(lang) for lang in lang_options],
            width=260,
            border_radius=8,
            text_size=14,
            text_style=ft.TextStyle(font_family=self.font_family),
            content_padding=ft.padding.symmetric(vertical=4, horizontal=10),
        )
        self.dpi_field = ft.TextField(
            label="DPI",
            value="300",
            width=100,
            border_radius=8,
            content_padding=ft.padding.all(10),
            text_size=14,
            keyboard_type=ft.KeyboardType.NUMBER,
            text_style=ft.TextStyle(font_family=self.font_family),
        )
        lang_card = self._make_card(
            "OCR 选项",
            ft.Column(
                [
                    engine_status,
                    ft.Row(
                        [self.lang_dropdown, self.dpi_field],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=12,
                    ),
                    ft.Text(
                        "DPI 越高识别越精确但速度越慢，扫描件推荐 300，清晰文档可用 150-200。",
                        size=12,
                        color=ft.Colors.BLUE_GREY_500,
                        font_family=self.font_family,
                    ),
                ],
                spacing=8,
            ),
        )

        # 进度条与操作按钮
        self.progress = ft.ProgressBar(
            visible=False,
            color=ft.Colors.BLUE,
            bgcolor=ft.Colors.GREY_200,
            bar_height=6,
            border_radius=4,
            expand=True,
        )
        self.progress_text = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)
        self.ocr_btn = ft.ElevatedButton(
            "开始识别",
            icon=ft.Icons.SEARCH,
            on_click=self.start_ocr,
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
                            ft.Icon(ft.Icons.SCANNER, size=32, color=ft.Colors.BLUE),
                            ft.Text("OCR PDF", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Divider(thickness=1, opacity=0.3),
                    file_card,
                    lang_card,
                    ft.Row(
                        [self.progress, self.progress_text],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Row([self.ocr_btn], alignment=ft.MainAxisAlignment.END),
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
                scroll=ft.ScrollMode.AUTO,
            )
        )

    def _make_card(self, title, content):
        """创建白色圆角卡片"""
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

    def select_file(self, e):
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
        self._refresh_page_info()
        self.page.update()

    def _refresh_page_info(self):
        """读取并展示PDF总页数"""
        try:
            import pikepdf
            with pikepdf.open(self.input_file) as pdf:
                self.total_pages = len(pdf.pages)
            self.stats_text.value = f"共 {self.total_pages} 页"
        except Exception:
            self.total_pages = 0
            self.stats_text.value = ""

    def start_ocr(self, e):
        """校验输入后开始 OCR 处理"""
        if self.processing:
            return
        if not self.tesseract_ok:
            self.show_status("Tesseract 未安装，请先安装", success=False)
            self.show_info("Tesseract 未安装", self.tesseract_info)
            return
        if not self.input_file:
            self.show_status("请先选择PDF文件", success=False)
            return
        if not os.path.exists(self.input_file):
            self.show_status("PDF文件不存在", success=False)
            return

        # 校验 DPI
        try:
            dpi = int(self.dpi_field.value or "300")
            if dpi < 72 or dpi > 2400:
                raise ValueError("DPI 需在 72-2400 之间")
        except ValueError as err:
            self.show_status(f"DPI 无效: {err}", success=False)
            return

        base_name = os.path.splitext(os.path.basename(self.input_file))[0]
        self.save_picker.save_file(
            dialog_title="保存OCR识别后的PDF",
            file_name=f"{base_name}_OCR.pdf",
            allowed_extensions=["pdf"],
        )

    def on_save_picked(self, e):
        if not e.path:
            return
        output_path = e.path
        if not output_path.lower().endswith('.pdf'):
            output_path += '.pdf'

        lang_name = self.lang_dropdown.value or '中文简体 + 英文'
        lang_code = OCR_LANGUAGES.get(lang_name, 'chi_sim+eng')

        try:
            dpi = int(self.dpi_field.value or "300")
        except ValueError:
            dpi = 300

        # 后台线程执行 OCR，避免阻塞 UI
        self.processing = True
        self.ocr_btn.disabled = True
        self.progress.value = 0
        self.progress.visible = True
        self.progress_text.value = "准备中..."
        self.show_status("正在识别，请耐心等待...")

        threading.Thread(
            target=self._do_ocr,
            args=(output_path, lang_code, dpi),
            daemon=True,
        ).start()

    def _do_ocr(self, output_path, lang_code, dpi):
        """后台线程：使用 ocrmypdf 执行 OCR"""
        try:
            # ocrmypdf 进度回调
            progress_state = {'current': 0}

            def progress_callback(progress_percent, total_pages_current, total_pages_total):
                """ocrmypdf 的进度回调，percent 为 0-1 之间的小数"""
                progress_state['current'] = progress_percent
                self._update_progress_from_ocr(progress_percent, total_pages_current, total_pages_total)

            ocrmypdf.ocr(
                input_file=self.input_file,
                output_file=output_path,
                language=lang_code,
                dpi=dpi,
                progress_bar=progress_callback,
                # 跳过已有文本的页面（仅对纯扫描页做 OCR）
                skip_text=True,
                # 输出 PDF/A 格式以确保长期可读
                output_type='pdfa',
                # 使用 HOCR 生成不可见文本层
                pdf_renderer='hocr',
                # 优化输出文件大小
                optimize=1,
                #  Jobs: 使用全部 CPU 核心加速
                jobs=0,
            )

            self._update_progress_from_ocr(1.0, self.total_pages, self.total_pages)
            self.show_status("OCR 识别完成")

            lang_display = self.lang_dropdown.value or '中文简体 + 英文'
            self.show_info(
                "成功",
                f"OCR 识别完成!\n"
                f"识别语言: {lang_display}\n"
                f"共 {self.total_pages} 页\n"
                f"保存到: {output_path}",
            )
        except ocrmypdf.exceptions.MissingDependencyError:
            self.show_status("Tesseract 引擎不可用", success=False)
            self.show_info("缺少依赖", "Tesseract OCR 引擎未正确安装，请重新安装。")
        except ocrmypdf.exceptions.InputFileError:
            self.show_status("输入文件无效", success=False)
        except Exception as err:
            error_msg = str(err)
            # 检查是否是语言包缺失
            if 'language' in error_msg.lower() or 'traineddata' in error_msg.lower():
                self.show_status("OCR 语言包缺失", success=False)
                self.show_info(
                    "语言包缺失",
                    f"缺少 {lang_code} 语言包。\n\n"
                    f"请在 Tesseract 安装目录的 tessdata 文件夹中\n"
                    f"添加对应语言的 traineddata 文件。\n"
                    f"下载地址: https://github.com/tesseract-ocr/tessdata",
                )
            else:
                self.show_status(f"OCR 失败: {error_msg[:60]}", success=False)
        finally:
            self.processing = False
            self.ocr_btn.disabled = False
            self.ocr_btn.update()

    def _update_progress_from_ocr(self, percent, current_page, total_pages):
        """根据 ocrmypdf 回调更新进度条"""
        self.progress.value = max(0.0, min(1.0, percent))
        if total_pages and total_pages > 0:
            self.progress_text.value = f"{current_page}/{total_pages}"
        else:
            self.progress_text.value = f"{int(percent * 100)}%"
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
    app = PDFOCRApp()
    ft.app(target=app.build)
