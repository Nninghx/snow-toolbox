# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import os
import importlib.util
from pathlib import Path

import flet as ft

from PIL import Image


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


class IconConverterApp:
    DEFAULT_SIZES = [16, 32, 48, 64, 128]

    def __init__(self):
        self.page = None
        self.input_file = None
        self.font_family = APP_FONT_FAMILY

    def build(self, page: ft.Page):
        self.page = page
        page.title = "图片转图标"
        page.window.width = 580
        page.window.height = 540
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

        # 源图片信息
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
            "源图片",
            ft.Row(
                [
                    ft.Icon(ft.Icons.IMAGE, size=18, color=ft.Colors.BLUE_GREY_400),
                    self.file_text,
                    ft.ElevatedButton("选择文件", icon=ft.Icons.UPLOAD_FILE, on_click=self.select_file),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
        )

        # 图标尺寸选择
        size_row = ft.Row(
            [
                ft.Radio(
                    value=str(s),
                    label=f"{s}x{s}",
                    label_style=ft.TextStyle(font_family=self.font_family, size=14),
                )
                for s in self.DEFAULT_SIZES
            ],
            spacing=16,
        )
        self.size_group = ft.RadioGroup(
            value=str(self.DEFAULT_SIZES[0]),
            content=size_row,
        )

        # 自定义尺寸输入
        self.custom_field = ft.TextField(
            label="自定义尺寸",
            hint_text="如 64x64（16-256像素）",
            width=260,
            border_radius=8,
            content_padding=ft.padding.all(10),
            text_size=14,
            text_style=ft.TextStyle(font_family=self.font_family),
        )
        size_card = self._make_card(
            "图标尺寸",
            ft.Column(
                [
                    self.size_group,
                    ft.Divider(thickness=1, opacity=0.3),
                    ft.Row(
                        [
                            self.custom_field,
                            ft.Text(
                                "(留空则使用上方预设尺寸)",
                                size=12,
                                color=ft.Colors.BLUE_GREY_500,
                                font_family=self.font_family,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                ],
                spacing=10,
            ),
        )

        # 操作按钮
        self.convert_button = ft.ElevatedButton(
            "转换为ICO",
            icon=ft.Icons.SWAP_HORIZ,
            on_click=self.convert_to_ico,
            height=40,
        )

        # 状态栏
        self.status_text = ft.Text("就绪", size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)

        page.add(
            # 页面标题栏
            ft.Row(
                [
                    ft.Icon(ft.Icons.SWAP_HORIZ, size=32, color=ft.Colors.BLUE),
                    ft.Text("图片转图标", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            ft.Divider(thickness=1, opacity=0.3),
            file_card,
            size_card,
            ft.Row([self.convert_button], alignment=ft.MainAxisAlignment.END),
            # 底部状态区
            ft.Container(
                content=self.status_text,
                padding=ft.padding.symmetric(vertical=8, horizontal=12),
                bgcolor=ft.Colors.BLUE_GREY_50,
                border_radius=8,
                border=ft.border.all(1, ft.Colors.GREY_300),
            ),
        )
        return page

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

    def select_file(self, e):
        self.file_picker.pick_files(
            dialog_title="选择源图片",
            allow_multiple=False,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["png", "jpg", "jpeg", "bmp"],
        )

    def on_file_picked(self, e):
        if not e.files:
            return
        file = e.files[0].path
        if not os.path.exists(file):
            self.show_status("文件不存在", success=False)
            return
        self.input_file = file
        self.file_text.value = os.path.basename(file)
        self.file_text.color = ft.Colors.BLUE_GREY_900
        self.page.update()

    def on_save_picked(self, e):
        """保存文件选择回调。"""
        if not e.path:
            return
        output_path = e.path
        try:
            self._do_convert(output_path)
        except Exception as err:
            self.show_status(f"转换失败: {err}", success=False)
        finally:
            self.convert_button.disabled = False
            self.convert_button.update()

    def convert_to_ico(self, e):
        if not self.input_file:
            self.show_status("请先选择源图片文件", success=False)
            return

        # 解析尺寸
        size = self._parse_size()
        if size is None:
            return

        self.convert_button.disabled = True
        self.save_picker.save_file(
            dialog_title="保存ICO文件",
            file_name="icon.ico",
            allowed_extensions=["ico"],
        )

    def _parse_size(self):
        """解析用户选择的图标尺寸，返回 (width, height) 元组或 None。"""
        custom = (self.custom_field.value or "").strip()
        if custom:
            try:
                parts = custom.lower().split("x")
                if len(parts) != 2:
                    raise ValueError
                width, height = int(parts[0]), int(parts[1])
                if not (16 <= width <= 256 and 16 <= height <= 256):
                    self.show_status("尺寸必须在 16x16 到 256x256 之间", success=False)
                    self.convert_button.disabled = False
                    return None
                return (width, height)
            except ValueError:
                self.show_status("自定义尺寸格式无效，请输入如 64x64", success=False)
                self.convert_button.disabled = False
                return None
        else:
            s = int(self.size_group.value)
            return (s, s)

    def _do_convert(self, output_path):
        """执行实际的转换操作。"""
        image = Image.open(self.input_file)
        size = self._parse_size()
        if size is None:
            return
        resized_img = image.resize(size, Image.LANCZOS)
        resized_img.save(output_path)
        self.show_status("转换完成")
        self.show_info("成功", f"ICO文件已保存到:\n{output_path}")

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
    app = IconConverterApp()
    ft.app(target=app.build)
