# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
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


def get_project_root():
    """获取项目根目录"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
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


class PDFMergerApp:
    def __init__(self):
        self.page = None
        self.files = []  # [{'path', 'name', 'pages', 'reader'}]，reader 为缓存的 pikepdf 句柄
        self.processing = False
        self.font_family = APP_FONT_FAMILY

    def build(self, page: ft.Page):
        self.page = page
        page.title = "PDF合并"
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

        # 合并列表卡片（可扩展滚动）
        self.file_rows = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
        self.empty_hint = ft.Text(
            "暂无文件，点击「添加文件」选择要合并的PDF",
            size=13,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
            text_align=ft.TextAlign.CENTER,
        )
        list_card = self._make_card(
            "合并列表（可通过箭头按钮调整合并顺序）",
            ft.Column(
                [self._list_header_row(), self.file_rows, self.empty_hint],
                spacing=8,
                expand=True,
            ),
            expand=True,
        )

        # 进度条与合并按钮
        self.progress = ft.ProgressBar(
            visible=False,
            color=ft.Colors.BLUE,
            bgcolor=ft.Colors.GREY_200,
            bar_height=6,
            border_radius=4,
            expand=True,
        )
        self.progress_text = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)
        self.merge_btn = ft.ElevatedButton(
            "合并PDF",
            icon=ft.Icons.MERGE_TYPE,
            on_click=self.merge_pdfs,
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
                            ft.Icon(ft.Icons.MERGE_TYPE, size=32, color=ft.Colors.BLUE),
                            ft.Text("PDF合并", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
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
                    ft.Row([self.merge_btn], alignment=ft.MainAxisAlignment.END),
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

    def _list_header_row(self):
        """列表表头：序号 / 文件名 / 页数 / 操作"""
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
                    ft.Container(ft.Text("页数", style=style), width=60, alignment=ft.alignment.center),
                    ft.Container(ft.Text("操作", style=style), width=110, alignment=ft.alignment.center),
                ],
                spacing=8,
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
        )

    def _build_file_row(self, index, item):
        """构建单个文件行：序号徽章 + 文件名 + 页数 + 上移/下移/删除按钮"""
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
        pages_text = ft.Text(
            f"{item['pages']} 页",
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
            on_click=lambda e, i=index: self.move_file(i, -1),
        )
        down_btn = ft.IconButton(
            ft.Icons.ARROW_DOWNWARD,
            icon_size=18,
            width=30,
            height=30,
            tooltip="下移",
            disabled=self.processing or index == len(self.files) - 1,
            on_click=lambda e, i=index: self.move_file(i, 1),
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
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(order_badge, width=36, alignment=ft.alignment.center),
                    name_text,
                    ft.Container(pages_text, width=60, alignment=ft.alignment.center),
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

    def _refresh_file_list(self):
        """重建文件列表与统计信息"""
        self.file_rows.controls.clear()
        for index, item in enumerate(self.files):
            self.file_rows.controls.append(self._build_file_row(index, item))
        self.empty_hint.visible = not self.files
        total_pages = sum(item['pages'] for item in self.files)
        self.stats_text.value = f"共 {len(self.files)} 个文件，合计 {total_pages} 页" if self.files else ""
        self.page.update()

    def add_files(self, e):
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
            try:
                # 用 pikepdf 打开并缓存句柄（C++ 解析，合并时无需重新解析）
                reader = pikepdf.open(file)
                page_count = len(reader.pages)
            except Exception as err:
                self.show_status(f"无法读取文件 {os.path.basename(file)}: {err}", success=False)
                skipped += 1
                continue
            self.files.append({
                'path': file,
                'name': os.path.basename(file),
                'pages': page_count,
                'reader': reader,
            })
            existing_paths.add(file)
            added += 1
        if added:
            self.show_status(f"已添加 {added} 个文件" + (f"，跳过 {skipped} 个" if skipped else ""))
        elif skipped:
            self.show_status("所选文件均无法添加", success=False)
        self._refresh_file_list()

    def move_file(self, index, delta):
        """上移/下移文件，调整合并顺序"""
        if self.processing:
            return
        target = index + delta
        if 0 <= index < len(self.files) and 0 <= target < len(self.files):
            self.files[index], self.files[target] = self.files[target], self.files[index]
            self._refresh_file_list()

    def remove_file(self, index):
        """移除单个文件并释放其缓存句柄"""
        if self.processing:
            return
        if 0 <= index < len(self.files):
            item = self.files.pop(index)
            self._close_reader(item.get('reader'))
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
        """清空所有文件并释放缓存句柄"""
        self.close_dialog()
        for item in self.files:
            self._close_reader(item.get('reader'))
        self.files.clear()
        self._refresh_file_list()
        self.show_status("已清空文件列表")

    @staticmethod
    def _close_reader(reader):
        if reader is not None:
            try:
                reader.close()
            except Exception:
                pass

    def merge_pdfs(self, e):
        if self.processing:
            return
        if not self.files:
            self.show_status("请先添加PDF文件", success=False)
            return
        self.save_picker.save_file(
            dialog_title="保存合并后的PDF",
            file_name="合并结果.pdf",
            allowed_extensions=["pdf"],
        )

    def on_save_picked(self, e):
        if not e.path:
            return
        output_file = e.path
        if not output_file.lower().endswith('.pdf'):
            output_file += '.pdf'

        # 在后台线程执行合并，避免阻塞 UI；pikepdf C++ 操作会释放 GIL
        self.processing = True
        self.merge_btn.disabled = True
        self.add_btn.disabled = True
        self.clear_btn.disabled = True
        self.progress.value = 0
        self.progress.visible = True
        self.progress_text.value = ""
        self._refresh_file_list()
        self.show_status("正在合并...")

        threading.Thread(
            target=self._do_merge,
            args=(output_file,),
            daemon=True,
        ).start()

    def _do_merge(self, output_file):
        """执行实际的合并操作（后台线程）"""
        try:
            total_files = len(self.files)
            merged = pikepdf.new()
            for i, item in enumerate(self.files):
                # 复用已缓存的句柄，避免重复解析 PDF 结构
                reader = item.get('reader')
                if reader is None:
                    reader = pikepdf.open(item['path'])
                    item['reader'] = reader
                # 使用 pages 接口批量复制页面，自动处理跨文件对象复制
                merged.pages.extend(reader.pages)
                self._update_progress(i + 1, total_files + 1)
            merged.save(output_file)
            self._update_progress(total_files + 1, total_files + 1)
            self.show_status("PDF合并完成")
            self.show_info(
                "成功",
                f"PDF合并完成!\n共合并 {total_files} 个文件\n保存到: {output_file}",
            )
        except Exception as err:
            self.show_status(f"合并失败: {err}", success=False)
        finally:
            self.processing = False
            self.merge_btn.disabled = False
            self.add_btn.disabled = False
            self.clear_btn.disabled = False
            self.merge_btn.update()
            self.add_btn.update()
            self.clear_btn.update()
            self._refresh_file_list()

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
    app = PDFMergerApp()
    ft.app(target=app.build)
