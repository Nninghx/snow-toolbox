# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import os
import threading
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


class ImageSplitterApp:
    def __init__(self):
        self.page = None
        self.input_file = None
        self.output_dir = None
        self.font_family = APP_FONT_FAMILY

    def build(self, page: ft.Page):
        self.page = page
        page.title = "图片九宫格分割"
        page.window.width = 580
        page.window.height = 520
        page.window.center()
        page.padding = 16
        page.theme_mode = ft.ThemeMode.LIGHT

        # 设置窗口图标
        icon_path = get_project_root() / 'Image' / 'icon.ico'
        if icon_path.exists():
            page.window.icon = str(icon_path)

        # 文件与目录选择器
        self.file_picker = ft.FilePicker(on_result=self.on_file_picked)
        self.dir_picker = ft.FilePicker(on_result=self.on_dir_picked)
        page.overlay.extend([self.file_picker, self.dir_picker])

        # 输入图片信息
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
            "输入图片",
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

        # 输出目录信息
        self.output_text = ft.Text(
            "未选择目录",
            size=13,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
            expand=True,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        output_card = self._make_card(
            "输出目录",
            ft.Row(
                [
                    ft.Icon(ft.Icons.FOLDER, size=18, color=ft.Colors.BLUE_GREY_400),
                    self.output_text,
                    ft.ElevatedButton("选择目录", icon=ft.Icons.FOLDER_OPEN, on_click=self.select_output_dir),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
        )

        # 进度条与操作按钮
        self.split_button = ft.ElevatedButton(
            "开始分割",
            icon=ft.Icons.CROP_SQUARE,
            on_click=self.start_split,
            height=40,
        )
        self.progress = ft.ProgressBar(
            visible=False,
            color=ft.Colors.BLUE,
            bgcolor=ft.Colors.GREY_200,
            bar_height=6,
            border_radius=4,
            expand=True,
        )
        self.progress_text = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)

        # 状态栏
        self.status_text = ft.Text("就绪", size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)

        page.add(
            # 页面标题栏
            ft.Row(
                [
                    ft.Icon(ft.Icons.CROP_SQUARE, size=32, color=ft.Colors.BLUE),
                    ft.Text("图片九宫格分割", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            ft.Divider(thickness=1, opacity=0.3),
            file_card,
            output_card,
            ft.Row(
                [self.progress, self.progress_text],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            ft.Row([self.split_button], alignment=ft.MainAxisAlignment.END),
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
            dialog_title="选择图片文件",
            allow_multiple=False,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["jpg", "jpeg", "png", "bmp", "gif", "webp"],
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

    def select_output_dir(self, e):
        self.dir_picker.get_directory_path(dialog_title="选择输出目录")

    def on_dir_picked(self, e):
        if not e.path:
            return
        self.output_dir = e.path
        self.output_text.value = e.path
        self.output_text.color = ft.Colors.BLUE_GREY_900
        self.page.update()

    def start_split(self, e):
        if not self.input_file:
            self.show_status("请先选择输入图片", success=False)
            return
        if not self.output_dir:
            self.show_status("请先选择输出目录", success=False)
            return

        self.progress.value = 0
        self.progress.visible = True
        self.progress_text.value = "0/9"
        self.split_button.disabled = True
        self.show_status("正在分割...")

        threading.Thread(
            target=self._run_split,
            daemon=True,
        ).start()

    def _run_split(self):
        """在后台线程中执行九宫格分割任务。"""
        try:
            base_name = os.path.splitext(os.path.basename(self.input_file))[0]
            save_dir = os.path.join(self.output_dir, base_name + "_split")
            os.makedirs(save_dir, exist_ok=True)

            with Image.open(self.input_file) as img:
                width, height = img.size
                tile_width = width // 3
                tile_height = height // 3

                for i in range(3):
                    for j in range(3):
                        left = j * tile_width
                        upper = i * tile_height
                        right = left + tile_width
                        lower = upper + tile_height

                        tile = img.crop((left, upper, right, lower))
                        tile.save(os.path.join(save_dir, f'{base_name}_tile_{i}_{j}.png'))

                        done = i * 3 + j + 1
                        self._update_progress(done, 9)

            self.progress.value = 1
            self.progress_text.value = "9/9"
            self.progress.update()
            self.progress_text.update()
            self.show_status("分割完成")
            self.show_info("完成", f"图片已成功分割为9份，保存在:\n{save_dir}")
        except Exception as err:
            self.show_status(f"分割失败: {err}", success=False)
        finally:
            self.split_button.disabled = False
            self.split_button.update()

    def _update_progress(self, done, total):
        """更新进度条和进度文本。"""
        self.progress.value = done / total
        self.progress_text.value = f"{done}/{total}"
        self.progress.update()
        self.progress_text.update()

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
    app = ImageSplitterApp()
    ft.app(target=app.build)
