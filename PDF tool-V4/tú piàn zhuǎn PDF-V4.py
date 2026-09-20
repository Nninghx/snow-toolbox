# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import threading
import importlib.util
from pathlib import Path

import flet as ft

from PIL import Image
import fitz  # PyMuPDF


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


class ImageToPDFApp:
    def __init__(self):
        self.page = None
        self.images = []  # [{'path', 'name', 'size_text'}]，按列表顺序转成 PDF 页面
        self.processing = False
        self.font_family = APP_FONT_FAMILY

    def build(self, page: ft.Page):
        self.page = page
        page.title = "图片转PDF"
        page.window.width = 720
        page.window.height = 660
        page.window.min_width = 620
        page.window.min_height = 560
        page.window.center()
        page.padding = 16
        page.theme_mode = ft.ThemeMode.LIGHT

        # 设置窗口图标
        icon_path = get_project_root() / 'Image' / 'icon.ico'
        if icon_path.exists():
            page.window.icon = str(icon_path)

        # 文件选择 / 保存对话框
        self.file_picker = ft.FilePicker(on_result=self.on_files_picked)
        self.save_picker = ft.FilePicker(on_result=self.on_save_picked)
        page.overlay.extend([self.file_picker, self.save_picker])

        # 工具栏：添加图片 / 清空列表 / 统计信息
        self.add_btn = ft.ElevatedButton(
            "添加图片",
            icon=ft.Icons.ADD_CIRCLE_OUTLINE,
            on_click=self.add_images,
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

        # 图片列表卡片（可扩展滚动，顺序即 PDF 页面顺序）
        self.image_rows = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
        self.empty_hint = ft.Text(
            "暂无图片，点击「添加图片」选择要转换的图片",
            size=13,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
            text_align=ft.TextAlign.CENTER,
        )
        list_card = self._make_card(
            "图片列表（可通过箭头按钮调整页面顺序）",
            ft.Column(
                [self._list_header_row(), self.image_rows, self.empty_hint],
                spacing=8,
                expand=True,
            ),
            expand=True,
        )

        # 进度条与转换按钮
        self.progress = ft.ProgressBar(
            visible=False,
            color=ft.Colors.BLUE,
            bgcolor=ft.Colors.GREY_200,
            bar_height=6,
            border_radius=4,
            expand=True,
        )
        self.progress_text = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)
        self.convert_btn = ft.ElevatedButton(
            "转换为PDF",
            icon=ft.Icons.PICTURE_AS_PDF,
            on_click=self.convert_to_pdf,
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
                            ft.Icon(ft.Icons.PICTURE_AS_PDF, size=32, color=ft.Colors.BLUE),
                            ft.Text("图片转PDF", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Divider(thickness=1, opacity=0.3),
                    toolbar_card,
                    list_card,
                    ft.Row(
                        [self.progress, self.progress_text],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Row([self.convert_btn], alignment=ft.MainAxisAlignment.END),
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
        self._refresh_image_list()

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

    def _list_header_row(self):
        """列表表头：序号 / 文件名 / 尺寸 / 操作"""
        style = ft.TextStyle(
            size=12,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_GREY_600,
            font_family=self.font_family,
        )
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(ft.Text("序号", style=style), width=36, alignment=ft.alignment.center),
                    ft.Text("文件名", style=style, expand=True),
                    ft.Container(ft.Text("尺寸", style=style), width=110, alignment=ft.alignment.center),
                    ft.Container(ft.Text("操作", style=style), width=110, alignment=ft.alignment.center),
                ],
                spacing=8,
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
        )

    def _build_image_row(self, index, item):
        """构建单个图片行：序号徽章 + 文件名 + 尺寸 + 上移/下移/删除按钮"""
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
        size_text = ft.Text(
            item['size_text'],
            size=12,
            color=ft.Colors.BLUE_GREY_600,
            font_family=self.font_family,
        )
        up_btn = ft.IconButton(
            ft.Icons.ARROW_UPWARD,
            icon_size=18,
            width=30,
            height=30,
            tooltip="上移",
            disabled=self.processing or index == 0,
            on_click=lambda e, i=index: self.move_image(i, -1),
        )
        down_btn = ft.IconButton(
            ft.Icons.ARROW_DOWNWARD,
            icon_size=18,
            width=30,
            height=30,
            tooltip="下移",
            disabled=self.processing or index == len(self.images) - 1,
            on_click=lambda e, i=index: self.move_image(i, 1),
        )
        del_btn = ft.IconButton(
            ft.Icons.DELETE_OUTLINE,
            icon_size=18,
            width=30,
            height=30,
            icon_color=ft.Colors.RED_400,
            tooltip="移除",
            disabled=self.processing,
            on_click=lambda e, i=index: self.remove_image(i),
        )
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(order_badge, width=36, alignment=ft.alignment.center),
                    name_text,
                    ft.Container(size_text, width=110, alignment=ft.alignment.center),
                    ft.Container(
                        ft.Row([up_btn, down_btn, del_btn], spacing=2, alignment=ft.MainAxisAlignment.CENTER),
                        width=110,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            border_radius=8,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )

    def _refresh_image_list(self):
        """重建图片列表与统计信息"""
        self.image_rows.controls.clear()
        for index, item in enumerate(self.images):
            self.image_rows.controls.append(self._build_image_row(index, item))
        self.empty_hint.visible = not self.images
        self.stats_text.value = f"共 {len(self.images)} 张图片" if self.images else ""
        self.page.update()

    def add_images(self, e):
        self.file_picker.pick_files(
            dialog_title="选择图片文件",
            allow_multiple=True,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["png", "jpg", "jpeg", "bmp", "tiff"],
        )

    def on_files_picked(self, e):
        if not e.files:
            return
        added, skipped = 0, 0
        existing_paths = {item['path'] for item in self.images}
        for picked in e.files:
            file = picked.path
            if not os.path.exists(file):
                skipped += 1
                continue
            if file in existing_paths:
                skipped += 1
                continue
            try:
                # 只读图片头部获取尺寸，同时校验文件可被 PIL 解析
                with Image.open(file) as img:
                    width, height = img.size
                size_text = f"{width} × {height} px"
            except Exception as err:
                self.show_status(f"无法读取图片 {os.path.basename(file)}: {err}", success=False)
                skipped += 1
                continue
            self.images.append({
                'path': file,
                'name': os.path.basename(file),
                'size_text': size_text,
            })
            existing_paths.add(file)
            added += 1
        if added:
            self.show_status(f"已添加 {added} 张图片" + (f"，跳过 {skipped} 张" if skipped else ""))
        elif skipped:
            self.show_status("所选图片均无法添加", success=False)
        self._refresh_image_list()

    def move_image(self, index, delta):
        """上移/下移图片，调整页面顺序"""
        if self.processing:
            return
        target = index + delta
        if 0 <= index < len(self.images) and 0 <= target < len(self.images):
            self.images[index], self.images[target] = self.images[target], self.images[index]
            self._refresh_image_list()

    def remove_image(self, index):
        """移除单张图片"""
        if self.processing:
            return
        if 0 <= index < len(self.images):
            item = self.images.pop(index)
            self._refresh_image_list()
            self.show_status(f"已移除：{item['name']}")

    def confirm_clear(self, e):
        """清空列表前弹窗确认"""
        if self.processing or not self.images:
            return
        self.page.dialog = ft.AlertDialog(
            title=ft.Text("确认", font_family=self.font_family),
            content=ft.Text("确定要清空图片列表吗？", font_family=self.font_family),
            actions=[
                ft.TextButton("取消", on_click=lambda e: self.close_dialog()),
                ft.TextButton("确定", on_click=lambda e: self.do_clear()),
            ],
        )
        self.page.dialog.open = True
        self.page.update()

    def do_clear(self):
        """清空图片列表"""
        self.close_dialog()
        self.images.clear()
        self._refresh_image_list()
        self.show_status("已清空图片列表")

    def convert_to_pdf(self, e):
        if self.processing:
            return
        if not self.images:
            self.show_status("请先添加图片", success=False)
            return
        self.save_picker.save_file(
            dialog_title="保存PDF文件",
            file_name="图片合集.pdf",
            allowed_extensions=["pdf"],
        )

    def on_save_picked(self, e):
        if not e.path:
            return
        output_file = e.path
        if not output_file.lower().endswith('.pdf'):
            output_file += '.pdf'

        # 在后台线程执行转换，避免阻塞 UI；fitz C++ 操作会释放 GIL
        self.processing = True
        self.convert_btn.disabled = True
        self.add_btn.disabled = True
        self.clear_btn.disabled = True
        self.progress.value = 0
        self.progress.visible = True
        self.progress_text.value = ""
        self._refresh_image_list()
        self.show_status("正在转换...")

        threading.Thread(
            target=self._do_convert,
            args=(output_file,),
            daemon=True,
        ).start()

    def _do_convert(self, output_file):
        """后台线程：按顺序将图片插入PDF（PDF页面顺序必须串行插入）"""
        total = len(self.images)
        failed = []
        pdf_document = None
        try:
            # 创建PDF文档
            pdf_document = fitz.open()
            for i, item in enumerate(self.images):
                img_path = item['path']
                try:
                    # 一次性读入内存，避免 PIL 和 fitz 重复打开文件（PIL 懒加载只读头部获取尺寸）
                    with open(img_path, 'rb') as f:
                        img_data = f.read()
                    with Image.open(img_path) as img:
                        width, height = img.size

                    # 创建与图片同尺寸的PDF页面
                    pdf_page = pdf_document.new_page(width=width, height=height)

                    # 用字节流插入图片，跳过磁盘重复读取开销
                    pdf_page.insert_image(
                        fitz.Rect(0, 0, width, height),
                        stream=img_data,
                    )
                except Exception as err:
                    failed.append(f"{item['name']}（{err}）")
                self._update_progress(i + 1, total)

            if len(pdf_document) == 0:
                self.show_status("没有可转换的图片", success=False)
                return

            pdf_document.save(output_file)
            pdf_document.close()
            pdf_document = None

            success_count = total - len(failed)
            detail = ""
            if failed:
                preview = "\n".join(failed[:5])
                detail = f"\n\n以下 {len(failed)} 张图片处理失败：\n{preview}"
                if len(failed) > 5:
                    detail += f"\n…等共 {len(failed)} 张"
            self.show_status("PDF转换完成")
            self.show_info(
                "成功",
                f"已成功将 {success_count} 张图片转换为PDF\n保存位置: {output_file}{detail}",
            )
            self._open_output_folder(os.path.dirname(output_file))
        except Exception as err:
            self.show_status(f"转换失败: {err}", success=False)
        finally:
            if pdf_document is not None:
                try:
                    pdf_document.close()
                except Exception:
                    pass
            self.processing = False
            self.convert_btn.disabled = False
            self.add_btn.disabled = False
            self.clear_btn.disabled = False
            self.convert_btn.update()
            self.add_btn.update()
            self.clear_btn.update()
            self._refresh_image_list()

    def _open_output_folder(self, folder_path):
        """在文件资源管理器中打开输出文件夹"""
        try:
            if sys.platform == 'win32':
                os.startfile(folder_path)
            elif sys.platform == 'darwin':  # macOS
                os.system(f'open "{folder_path}"')
            else:  # Linux
                os.system(f'xdg-open "{folder_path}"')
        except Exception:
            pass

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
    app = ImageToPDFApp()
    ft.app(target=app.build)
