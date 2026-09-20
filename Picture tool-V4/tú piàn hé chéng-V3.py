# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import os
import math
import random
import tempfile
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


class ImageCombinerApp:
    def __init__(self):
        self.page = None
        self.image_paths = []
        self.font_family = APP_FONT_FAMILY
        self._preview_src = None  # 临时预览文件路径

    def build(self, page: ft.Page):
        self.page = page
        page.title = "图片合成工具"
        page.window.width = 620
        page.window.height = 700
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

        # 图片选择卡片
        self.file_count_text = ft.Text(
            "未选择图片",
            size=13,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
        )
        self.file_list_text = ft.Text(
            "",
            size=12,
            color=ft.Colors.BLUE_GREY_600,
            font_family=self.font_family,
            max_lines=3,
        )
        select_card = self._make_card(
            "图片选择",
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.IMAGE_OUTLINED, size=18, color=ft.Colors.BLUE_GREY_400),
                            self.file_count_text,
                            ft.Container(expand=True),
                            ft.ElevatedButton("选择图片", icon=ft.Icons.ADD_PHOTO_ALTERNATE, on_click=self.select_images),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    self.file_list_text,
                ],
                spacing=6,
            ),
        )

        # 布局选项卡片
        self.layout_group = ft.RadioGroup(
            value="uniform",
            content=ft.Row(
                [
                    ft.Radio(value="uniform", label="均匀分布",
                             label_style=ft.TextStyle(font_family=self.font_family, size=14)),
                    ft.Radio(value="horizontal", label="水平排列",
                             label_style=ft.TextStyle(font_family=self.font_family, size=14)),
                    ft.Radio(value="vertical", label="垂直排列",
                             label_style=ft.TextStyle(font_family=self.font_family, size=14)),
                ],
                spacing=16,
            ),
        )
        self.random_check = ft.Checkbox(
            label="随机分布",
            label_style=ft.TextStyle(font_family=self.font_family, size=14),
        )
        self.export_count_field = ft.TextField(
            label="导出数量",
            value="1",
            width=100,
            border_radius=8,
            content_padding=ft.padding.all(10),
            text_size=14,
            keyboard_type=ft.KeyboardType.NUMBER,
            text_style=ft.TextStyle(font_family=self.font_family),
        )
        self.random_select_field = ft.TextField(
            label="随机选择数量",
            value="0",
            hint_text="0=全部",
            width=140,
            border_radius=8,
            content_padding=ft.padding.all(10),
            text_size=14,
            keyboard_type=ft.KeyboardType.NUMBER,
            text_style=ft.TextStyle(font_family=self.font_family),
        )
        option_card = self._make_card(
            "布局选项",
            ft.Column(
                [
                    self.layout_group,
                    ft.Divider(thickness=1, opacity=0.3),
                    ft.Row(
                        [self.random_check, ft.Container(expand=True), self.export_count_field, self.random_select_field],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=12,
                    ),
                ],
                spacing=8,
            ),
        )

        # 预览卡片
        self.preview_image = ft.Image(
            visible=False,
            width=540,
            fit=ft.ImageFit.CONTAIN,
            border_radius=6,
        )
        preview_card = self._make_card(
            "合成预览",
            ft.Column(
                [
                    self.preview_image,
                    ft.Text(
                        "点击「预览」查看合成效果",
                        size=12,
                        color=ft.Colors.BLUE_GREY_500,
                        font_family=self.font_family,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        # 操作按钮
        self.preview_btn = ft.ElevatedButton(
            "预览",
            icon=ft.Icons.PREVIEW,
            on_click=self.preview,
            height=36,
        )
        self.save_btn = ft.ElevatedButton(
            "保存结果",
            icon=ft.Icons.SAVE,
            on_click=self.save_result,
            height=40,
        )

        # 状态栏
        self.status_text = ft.Text("就绪", size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)

        page.add(
            ft.Row(
                [
                    ft.Icon(ft.Icons.PHOTO_LIBRARY, size=32, color=ft.Colors.BLUE),
                    ft.Text("图片合成工具", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            ft.Divider(thickness=1, opacity=0.3),
            select_card,
            option_card,
            preview_card,
            ft.Row(
                [self.preview_btn, ft.Container(expand=True), self.save_btn],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
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

    def select_images(self, e):
        self.file_picker.pick_files(
            dialog_title="选择图片",
            allow_multiple=True,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["jpg", "jpeg", "png", "bmp", "gif", "webp"],
        )

    def on_files_picked(self, e):
        if not e.files:
            return
        self.image_paths = [f.path for f in e.files if os.path.exists(f.path)]
        count = len(self.image_paths)
        if count == 0:
            self.show_status("未选择有效图片", success=False)
            return
        self.file_count_text.value = f"已选择 {count} 张图片"
        self.file_count_text.color = ft.Colors.BLUE_GREY_900
        names = [os.path.basename(p) for p in self.image_paths[:5]]
        self.file_list_text.value = ", ".join(names) + (f" ...等{count}张" if count > 5 else "")
        self.status_text.value = f"已选择 {count} 张图片，请设置布局选项后预览"
        self.page.update()

    def preview(self, e):
        """预览合成效果。"""
        if not self.image_paths:
            self.show_status("请先选择图片", success=False)
            return

        try:
            self.status_text.value = "正在合成预览..."
            self.page.update()

            combined = self.combine_images()
            if combined is None:
                return

            # 保存为临时文件供 Flet 显示
            if self._preview_src and os.path.exists(self._preview_src):
                os.remove(self._preview_src)
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            combined.save(tmp.name, "PNG")
            tmp.close()
            self._preview_src = tmp.name

            self.preview_image.src = self._preview_src
            self.preview_image.visible = True
            self.preview_image.update()
            self.status_text.value = "预览完成"
        except Exception as err:
            self.show_status(f"预览失败: {err}", success=False)

    def on_save_picked(self, e):
        """保存文件选择回调。"""
        if not e.path:
            return
        try:
            count = self._get_export_count()
            save_path = e.path
            base, ext = os.path.splitext(save_path)
            ext = ext.lower() or ".png"

            for i in range(count):
                combined = self.combine_images()
                if combined is None:
                    break
                if count > 1:
                    current_path = f"{base}_{i+1}{ext}"
                else:
                    current_path = save_path
                self._save_image(combined, current_path, ext)

            self.show_status("保存完成")
            self.show_info("成功", f"已保存 {count} 张图片")
        except Exception as err:
            self.show_status(f"保存失败: {err}", success=False)

    def save_result(self, e):
        """保存合成结果。"""
        if not self.image_paths:
            self.show_status("请先选择图片", success=False)
            return
        self.save_picker.save_file(
            dialog_title="保存合成图片",
            file_name="combined.png",
            allowed_extensions=["png", "jpg", "jpeg", "bmp"],
        )

    def _get_export_count(self):
        try:
            return max(1, int(self.export_count_field.value or "1"))
        except ValueError:
            return 1

    def _save_image(self, img, path, ext):
        """根据扩展名保存图片。"""
        if ext in (".jpg", ".jpeg"):
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(path, "JPEG", quality=95)
        elif ext == ".png":
            img.save(path, "PNG")
        elif ext == ".bmp":
            img.save(path, "BMP")
        else:
            img.save(path)

    def combine_images(self):
        """核心图片合成方法，返回合成后的 PIL Image 或 None。"""
        if not self.image_paths:
            return None

        try:
            # 随机选择指定数量的图片
            select_count = 0
            try:
                select_count = int(self.random_select_field.value or "0")
            except ValueError:
                select_count = 0
            if select_count > 0 and select_count < len(self.image_paths):
                selected_paths = random.sample(self.image_paths, select_count)
            else:
                selected_paths = list(self.image_paths)

            # 加载图片
            images = []
            total_size = 0
            for path in selected_paths:
                img = Image.open(path)
                img.load()
                total_size += os.path.getsize(path)
                images.append(img)

            # 自动压缩大图片
            if total_size > 10 * 1024 * 1024:
                images = [self._compress_image(img) for img in images]

            # 根据布局模式合成
            mode = self.layout_group.value
            if self.random_check.value:
                result = self._random_layout(images)
            elif mode == "uniform":
                result = self._uniform_layout(images)
            elif mode == "horizontal":
                result = self._horizontal_layout(images)
            elif mode == "vertical":
                result = self._vertical_layout(images)
            else:
                result = self._uniform_layout(images)

            return result
        except Exception as err:
            self.show_status(f"合成失败: {err}", success=False)
            return None

    def _uniform_layout(self, images):
        """均匀分布布局。"""
        img_count = len(images)
        cols = math.ceil(math.sqrt(img_count))
        rows = math.ceil(img_count / cols)

        max_width = max(img.size[0] for img in images)
        max_height = max(img.size[1] for img in images)

        canvas_width = cols * max_width
        canvas_height = rows * max_height
        canvas = Image.new('RGB', (canvas_width, canvas_height), (255, 255, 255))

        for i, img in enumerate(images):
            row = i // cols
            col = i % cols
            x = col * max_width
            y = row * max_height
            if img.mode != 'RGB':
                img = img.convert('RGB')
            canvas.paste(img, (x, y))

        return canvas

    def _horizontal_layout(self, images):
        """水平排列布局。"""
        total_width = sum(img.size[0] for img in images)
        max_height = max(img.size[1] for img in images)

        canvas = Image.new('RGB', (total_width, max_height), (255, 255, 255))

        x_offset = 0
        for img in images:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            canvas.paste(img, (x_offset, 0))
            x_offset += img.size[0]

        return canvas

    def _vertical_layout(self, images):
        """垂直排列布局。"""
        max_width = max(img.size[0] for img in images)
        total_height = sum(img.size[1] for img in images)

        canvas = Image.new('RGB', (max_width, total_height), (255, 255, 255))

        y_offset = 0
        for img in images:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            canvas.paste(img, (0, y_offset))
            y_offset += img.size[1]

        return canvas

    def _random_layout(self, images):
        """随机分布布局。"""
        total_area = sum(img.size[0] * img.size[1] for img in images)
        canvas_size = int(math.sqrt(total_area) * 1.5)
        canvas = Image.new('RGB', (canvas_size, canvas_size), (255, 255, 255))

        placed = []
        for img in images:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            placed_success = False
            attempts = 0
            max_attempts = 100

            while not placed_success and attempts < max_attempts:
                attempts += 1
                x = random.randint(0, max(0, canvas_size - img.size[0]))
                y = random.randint(0, max(0, canvas_size - img.size[1]))

                new_rect = (x, y, x + img.size[0], y + img.size[1])
                overlap = False
                for existing in placed:
                    if self._check_overlap(new_rect, existing):
                        overlap = True
                        break

                if not overlap:
                    canvas.paste(img, (x, y))
                    placed.append(new_rect)
                    placed_success = True

        return canvas

    @staticmethod
    def _check_overlap(rect1, rect2):
        """检查两个矩形是否重叠。"""
        return not (rect1[2] <= rect2[0] or
                    rect1[0] >= rect2[2] or
                    rect1[3] <= rect2[1] or
                    rect1[1] >= rect2[3])

    @staticmethod
    def _compress_image(image):
        """压缩超大图片至约 1MP。"""
        try:
            original_size = image.size[0] * image.size[1]
            target_size = 1024 * 1024
            if original_size <= target_size:
                return image
            ratio = math.sqrt(target_size / original_size)
            new_width = int(image.size[0] * ratio)
            new_height = int(image.size[1] * ratio)
            return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        except Exception:
            return image

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
    app = ImageCombinerApp()
    ft.app(target=app.build)
