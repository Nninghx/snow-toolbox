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

SUPPORTED_FORMATS = ['jpg', 'jpeg', 'png', 'webp', 'bmp', 'gif', 'tiff']
SUPPORTED_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff', '.psd'}


class ImageConverterApp:
    def __init__(self):
        self.page = None
        self.input_file = None
        self.batch_dir = None
        self.output_dir = None
        self.processing = False
        self.font_family = APP_FONT_FAMILY

    def build(self, page: ft.Page):
        self.page = page
        page.title = "图片格式转换"
        page.window.width = 600
        page.window.height = 660
        page.window.center()
        page.padding = 16
        page.theme_mode = ft.ThemeMode.LIGHT

        # 设置窗口图标
        icon_path = get_project_root() / 'Image' / 'icon.ico'
        if icon_path.exists():
            page.window.icon = str(icon_path)

        # 文件与目录选择器
        self.file_picker = ft.FilePicker(on_result=self.on_file_picked)
        self.dir_input_picker = ft.FilePicker(on_result=self.on_dir_input_picked)
        self.dir_output_picker = ft.FilePicker(on_result=self.on_dir_output_picked)
        self.save_picker = ft.FilePicker(on_result=self.on_save_picked)
        page.overlay.extend([self.file_picker, self.dir_input_picker, self.dir_output_picker, self.save_picker])

        # 模式选择
        self.mode_group = ft.RadioGroup(
            value="single",
            on_change=self.on_mode_change,
            content=ft.Row(
                [
                    ft.Radio(
                        value="single",
                        label="单文件模式",
                        label_style=ft.TextStyle(font_family=self.font_family, size=14),
                    ),
                    ft.Radio(
                        value="batch",
                        label="批量模式",
                        label_style=ft.TextStyle(font_family=self.font_family, size=14),
                    ),
                ],
                spacing=20,
            ),
        )

        # 单文件选择
        self.file_text = ft.Text(
            "未选择文件",
            size=13,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
            expand=True,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.single_row = ft.Row(
            [
                ft.Icon(ft.Icons.IMAGE, size=18, color=ft.Colors.BLUE_GREY_400),
                self.file_text,
                ft.ElevatedButton("选择文件", icon=ft.Icons.UPLOAD_FILE, on_click=self.select_file),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        )

        # 批量目录选择
        self.batch_text = ft.Text(
            "未选择目录",
            size=13,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
            expand=True,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.batch_row = ft.Row(
            [
                ft.Icon(ft.Icons.FOLDER, size=18, color=ft.Colors.BLUE_GREY_400),
                self.batch_text,
                ft.ElevatedButton("选择目录", icon=ft.Icons.FOLDER_OPEN, on_click=self.select_batch_dir),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
            visible=False,
        )

        input_card = self._make_card(
            "图片文件",
            ft.Column([self.mode_group, self.single_row, self.batch_row], spacing=8),
        )

        # 转换设置
        self.format_dropdown = ft.Dropdown(
            label="输出格式",
            value="png",
            width=180,
            border_radius=8,
            text_size=14,
            text_style=ft.TextStyle(font_family=self.font_family),
            options=[ft.dropdown.Option(f) for f in SUPPORTED_FORMATS],
        )
        self.quality_field = ft.TextField(
            label="输出质量 (1-100)",
            value="100",
            width=180,
            border_radius=8,
            content_padding=ft.padding.all(10),
            text_size=14,
            keyboard_type=ft.KeyboardType.NUMBER,
            text_style=ft.TextStyle(font_family=self.font_family),
        )
        setting_card = self._make_card(
            "转换设置",
            ft.Row([self.format_dropdown, self.quality_field], spacing=16),
        )

        # 输出目录
        self.output_text = ft.Text(
            "未选择目录（单文件模式下可留空，将弹窗询问保存位置）",
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
                    ft.Icon(ft.Icons.FOLDER_OPEN, size=18, color=ft.Colors.BLUE_GREY_400),
                    self.output_text,
                    ft.ElevatedButton("选择目录", icon=ft.Icons.FOLDER_OPEN, on_click=self.select_output_dir),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
        )

        # 进度条与操作按钮
        self.convert_button = ft.ElevatedButton(
            "开始转换",
            icon=ft.Icons.SWAP_HORIZ,
            on_click=self.start_conversion,
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
        self.stats_text = ft.Text(size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)

        page.add(
            ft.Row(
                [
                    ft.Icon(ft.Icons.SWAP_HORIZ, size=32, color=ft.Colors.BLUE),
                    ft.Text("图片格式转换", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            ft.Divider(thickness=1, opacity=0.3),
            input_card,
            setting_card,
            output_card,
            ft.Row(
                [self.progress, self.progress_text],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            ft.Row([self.convert_button], alignment=ft.MainAxisAlignment.END),
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

    def on_mode_change(self, e):
        """模式切换：单文件/批量。"""
        is_single = self.mode_group.value == "single"
        self.single_row.visible = is_single
        self.batch_row.visible = not is_single
        self.page.update()

    def select_file(self, e):
        exts = ",".join(SUPPORTED_FORMATS)
        self.file_picker.pick_files(
            dialog_title="选择图片文件",
            allow_multiple=False,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=SUPPORTED_FORMATS,
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

    def select_batch_dir(self, e):
        self.dir_input_picker.get_directory_path(dialog_title="选择图片目录")

    def on_dir_input_picked(self, e):
        if not e.path:
            return
        self.batch_dir = e.path
        self.batch_text.value = e.path
        self.batch_text.color = ft.Colors.BLUE_GREY_900
        self.page.update()

    def select_output_dir(self, e):
        self.dir_output_picker.get_directory_path(dialog_title="选择输出目录")

    def on_dir_output_picked(self, e):
        if not e.path:
            return
        self.output_dir = e.path
        self.output_text.value = e.path
        self.output_text.color = ft.Colors.BLUE_GREY_900
        self.page.update()

    def on_save_picked(self, e):
        """单文件保存位置选择回调。"""
        if not e.path:
            self.convert_button.disabled = False
            self.convert_button.update()
            return
        output_format = self.format_dropdown.value
        try:
            quality = self._get_quality()
            result = self._convert_single_image(self.input_file, e.path, output_format, quality)
            if result is True:
                self.show_status("转换完成")
                self.show_info("成功", "图片转换完成！")
            else:
                self.show_status(f"转换失败: {result}", success=False)
        except Exception as err:
            self.show_status(f"转换失败: {err}", success=False)
        finally:
            self.convert_button.disabled = False
            self.convert_button.update()

    def _get_quality(self):
        """获取质量值。"""
        try:
            return max(1, min(100, int(self.quality_field.value or "100")))
        except ValueError:
            return 100

    def start_conversion(self, e):
        if self.processing:
            return

        output_format = self.format_dropdown.value

        if self.mode_group.value == "single":
            if not self.input_file:
                self.show_status("请先选择输入文件", success=False)
                return
            # 单文件模式：如果设置了输出目录则直接转换，否则弹窗询问
            if self.output_dir:
                filename = os.path.basename(self.input_file)
                name = os.path.splitext(filename)[0]
                output_path = os.path.join(self.output_dir, f"{name}.{output_format}")
                self.convert_button.disabled = True
                quality = self._get_quality()
                try:
                    result = self._convert_single_image(self.input_file, output_path, output_format, quality)
                    if result is True:
                        self.show_status("转换完成")
                        self.show_info("成功", "图片转换完成！")
                    else:
                        self.show_status(f"转换失败: {result}", success=False)
                except Exception as err:
                    self.show_status(f"转换失败: {err}", success=False)
                finally:
                    self.convert_button.disabled = False
            else:
                self.convert_button.disabled = True
                self.save_picker.save_file(
                    dialog_title="保存为",
                    file_name=os.path.splitext(os.path.basename(self.input_file))[0] + f".{output_format}",
                    allowed_extensions=[output_format],
                )
        else:
            # 批量模式
            if not self.batch_dir:
                self.show_status("请先选择输入目录", success=False)
                return
            if not self.output_dir:
                self.show_status("请先选择输出目录", success=False)
                return

            self.processing = True
            self.convert_button.disabled = True
            self.progress.value = 0
            self.progress.visible = True
            self.progress_text.value = "0/0"
            self.show_status("正在批量转换...")

            threading.Thread(
                target=self._run_batch,
                args=(output_format,),
                daemon=True,
            ).start()

    def _run_batch(self, output_format):
        """批量转换后台线程。"""
        try:
            quality = self._get_quality()
            image_files = [
                f for f in os.listdir(self.batch_dir)
                if os.path.splitext(f)[1].lower() in SUPPORTED_EXTS
            ]
            total = len(image_files)
            if total == 0:
                self.show_status("指定目录中没有找到支持的图片文件", success=False)
                return

            self.progress_text.value = f"0/{total}"
            self.progress_text.update()
            self.stats_text.value = f"共 {total} 个文件"
            self.stats_text.update()

            success_count = 0
            for i, filename in enumerate(image_files):
                input_path = os.path.join(self.batch_dir, filename)
                name = os.path.splitext(filename)[0]
                output_path = os.path.join(self.output_dir, f"{name}.{output_format}")
                result = self._convert_single_image(input_path, output_path, output_format, quality)
                if result is True:
                    success_count += 1
                self._update_progress(i + 1, total)

            self.show_status(f"批量转换完成 - 成功: {success_count}, 失败: {total - success_count}")
            self.show_info("完成", f"批量转换完成！\n成功: {success_count}\n失败: {total - success_count}")
        except Exception as err:
            self.show_status(f"批量转换失败: {err}", success=False)
        finally:
            self.processing = False
            self.convert_button.disabled = False
            self.convert_button.update()

    def _convert_single_image(self, input_path, output_path, output_format, quality):
        """转换单张图片，返回 True 或错误信息。"""
        try:
            img = Image.open(input_path)
            save_args = {'format': output_format.upper()}
            if output_format.lower() in ['jpg', 'jpeg', 'webp']:
                save_args['quality'] = quality
            elif output_format.lower() == 'png':
                save_args['compress_level'] = 9 - int(quality / 11.11)
            img.save(output_path, **save_args)
            return True
        except Image.DecompressionBombError:
            return "图片尺寸过大"
        except Exception as e:
            return str(e)

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
    app = ImageConverterApp()
    ft.app(target=app.build)
