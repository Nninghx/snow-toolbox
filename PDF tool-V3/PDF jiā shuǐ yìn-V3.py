# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import io
import subprocess
import threading
import importlib.util
from pathlib import Path

import flet as ft

try:
    import pikepdf
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pikepdf'])
    import pikepdf

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont as RLTTFont


def get_project_root():
    """获取项目根目录"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def register_reportlab_font(font_family):
    """向 reportlab 注册项目自带字体：系统级注册对 reportlab 不可见，必须显式注册 TTF"""
    try:
        pdfmetrics.getFont(font_family)
        return  # 已注册过，无需重复处理
    except KeyError:
        pass
    font_path = get_project_root() / 'Image' / 'AlibabaPuHuiTi-3-55-RegularL3.ttf'
    if not font_path.exists():
        raise FileNotFoundError(f"项目自带字体不存在：{font_path}")
    pdfmetrics.registerFont(RLTTFont(font_family, str(font_path)))


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

register_reportlab_font(APP_FONT_FAMILY)


class PDFWatermarkApp:
    def __init__(self):
        self.page = None
        self.input_file = None
        self.total_pages = 0
        self.processing = False
        self.font_family = APP_FONT_FAMILY

    def build(self, page: ft.Page):
        self.page = page
        page.title = "PDF加水印"
        page.window.width = 620
        page.window.height = 640
        page.window.min_width = 560
        page.window.min_height = 560
        page.window.center()
        page.padding = 16
        page.theme_mode = ft.ThemeMode.LIGHT

        # 设置窗口图标
        icon_path = get_project_root() / 'Image' / 'icon.ico'
        if icon_path.exists():
            page.window.icon = str(icon_path)

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

        # 水印文字卡片
        self.text_field = ft.TextField(
            label="水印文字",
            value="机密",
            expand=3,
            border_radius=8,
            content_padding=ft.padding.all(10),
            text_size=14,
            text_style=ft.TextStyle(font_family=self.font_family),
        )
        self.font_size_field = ft.TextField(
            label="字体大小",
            value="36",
            expand=1,
            border_radius=8,
            content_padding=ft.padding.all(10),
            text_size=14,
            keyboard_type=ft.KeyboardType.NUMBER,
            text_style=ft.TextStyle(font_family=self.font_family),
        )
        text_card = self._make_card(
            "水印文字",
            ft.Row([self.text_field, self.font_size_field], spacing=12),
        )

        # 透明度卡片
        self.opacity_value = ft.Text(
            "50%",
            size=13,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_GREY_700,
            font_family=self.font_family,
        )
        self.opacity_slider = ft.Slider(
            value=0.5,
            min=0.1,
            max=1.0,
            divisions=18,
            active_color=ft.Colors.BLUE,
            inactive_color=ft.Colors.GREY_300,
            on_change=self.on_opacity_change,
            expand=True,
        )
        opacity_card = self._make_card(
            "透明度",
            ft.Row(
                [self.opacity_slider, self.opacity_value],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
        )

        # 水印位置卡片
        self.position_group = ft.RadioGroup(
            value="center",
            content=ft.Row(
                [
                    ft.Radio(value="center", label="居中"),
                    ft.Radio(value="topleft", label="左上"),
                    ft.Radio(value="topright", label="右上"),
                    ft.Radio(value="bottomleft", label="左下"),
                    ft.Radio(value="bottomright", label="右下"),
                ],
                spacing=6,
                wrap=True,
            ),
        )
        for radio in self.position_group.content.controls:
            radio.label_style = ft.TextStyle(font_family=self.font_family, size=14)
        position_card = self._make_card("水印位置", self.position_group)

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
        self.wm_button = ft.ElevatedButton(
            "添加水印",
            icon=ft.Icons.BRUSH,
            on_click=self.add_watermark,
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
                            ft.Icon(ft.Icons.BRUSH, size=32, color=ft.Colors.BLUE),
                            ft.Text("PDF加水印", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Divider(thickness=1, opacity=0.3),
                    file_card,
                    text_card,
                    opacity_card,
                    position_card,
                    ft.Row(
                        [self.progress, self.progress_text],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Row([self.wm_button], alignment=ft.MainAxisAlignment.END),
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
            with pikepdf.open(self.input_file) as pdf:
                self.total_pages = len(pdf.pages)
            self.stats_text.value = f"共 {self.total_pages} 页"
        except Exception:
            self.total_pages = 0
            self.stats_text.value = ""

    def on_opacity_change(self, e):
        """透明度滑块变化：同步右侧百分比显示"""
        self.opacity_value.value = f"{int(round(self.opacity_slider.value * 100))}%"
        self.opacity_value.update()

    def create_text_watermark(self, text, font_size, opacity, position):
        """用 reportlab 创建文本水印PDF"""
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        can.setFillColorRGB(0.5, 0.5, 0.5, opacity)
        can.setFont(self.font_family, font_size)

        width, height = letter
        # 根据位置设置文本坐标
        if position == "center":
            can.drawCentredString(width / 2, height / 2, text)
        elif position == "topleft":
            can.drawString(50, height - 50, text)
        elif position == "topright":
            can.drawRightString(width - 50, height - 50, text)
        elif position == "bottomleft":
            can.drawString(50, 50, text)
        elif position == "bottomright":
            can.drawRightString(width - 50, 50, text)

        can.save()
        packet.seek(0)
        return pikepdf.open(packet)

    def add_watermark(self, e):
        """校验输入后选择保存路径"""
        if self.processing:
            return
        if not self.input_file:
            self.show_status("请先选择PDF文件", success=False)
            return
        if not os.path.exists(self.input_file):
            self.show_status("PDF文件不存在", success=False)
            return

        text = (self.text_field.value or "").strip()
        if not text:
            self.show_status("请输入水印文字", success=False)
            return

        try:
            font_size = int(self.font_size_field.value or "0")
            if font_size <= 0:
                raise ValueError("字体大小必须大于0")
        except ValueError:
            self.show_status("请输入有效的字体大小", success=False)
            return

        base_name = os.path.splitext(os.path.basename(self.input_file))[0]
        self.save_picker.save_file(
            dialog_title="保存加水印的PDF",
            file_name=f"{base_name}_水印.pdf",
            allowed_extensions=["pdf"],
        )

    def on_save_picked(self, e):
        if not e.path:
            return
        output_path = e.path
        if not output_path.lower().endswith('.pdf'):
            output_path += '.pdf'

        text = (self.text_field.value or "").strip()
        font_size = int(self.font_size_field.value or "0")
        opacity = float(self.opacity_slider.value)
        position = self.position_group.value

        try:
            # 读取原始PDF（pikepdf C++ 解析，速度快）
            pdf = pikepdf.open(self.input_file)
            if len(pdf.pages) == 0:
                pdf.close()
                self.show_status("PDF文件没有有效页面", success=False)
                return
            # 生成文本水印
            watermark = self.create_text_watermark(text, font_size, opacity, position)
        except Exception as err:
            self.show_status(f"加水印过程中发生错误: {err}", success=False)
            return

        # 后台线程执行加水印，避免阻塞 UI；pikepdf C++ 操作会释放 GIL
        self.processing = True
        self.wm_button.disabled = True
        self.progress.value = 0
        self.progress.visible = True
        self.progress_text.value = ""
        self.show_status("正在添加水印...")

        threading.Thread(
            target=self._do_add_watermark,
            args=(pdf, watermark, output_path),
            daemon=True,
        ).start()

    def _do_add_watermark(self, pdf, watermark, output_path):
        """后台线程：为每一页叠加水印并保存（pikepdf C++ 操作释放 GIL）"""
        total_pages = len(pdf.pages)
        try:
            result = pikepdf.new()
            wm_page = watermark.pages[0]
            # 通过 pages 接口批量复制原页面，自动处理跨文件对象复制（copy_foreign 已废弃）
            result.pages.extend(pdf.pages)
            for i, new_page in enumerate(result.pages):
                # 叠加水印层（保留原始页面内容不丢失）
                new_page.add_overlay(wm_page)
                self._update_progress(i + 1, total_pages + 1)
            result.save(output_path)
            self._update_progress(total_pages + 1, total_pages + 1)
            self.show_status("PDF加水印完成")
            self.show_info(
                "成功",
                f"PDF加水印完成!\n共处理 {total_pages} 页\n保存到: {output_path}",
            )
        except Exception as err:
            self.show_status(f"加水印过程中发生错误: {err}", success=False)
        finally:
            try:
                pdf.close()
                watermark.close()
            except Exception:
                pass
            self.processing = False
            self.wm_button.disabled = False
            self.wm_button.update()

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
    app = PDFWatermarkApp()
    ft.app(target=app.build)
