# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

"""
PDF 合并为单页
将多份 PDF 的所有页面按顺序垂直拼接成一个连续的超长单页，
生成可滚动的单页 PDF 文档，适合长图式阅读或连续展示。
"""

import os
import threading
import importlib.util
from pathlib import Path

import flet as ft

import fitz  # PyMuPDF


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


# PDF 阅读器可安全渲染的单页最大高度（约 200 英寸 / 14400 磅）
MAX_PAGE_HEIGHT = 14400.0


class PDFMergeToSinglePageApp:
    """PDF合并为单页：把多份 PDF 的页面垂直拼接成一个可滚动的单页文档。"""

    WIDTH_MODES = [
        ('stretch', '拉伸至统一宽度（保持比例）'),
        ('original', '保持原始尺寸（居中）'),
    ]
    GAP_OPTIONS = [
        ('0', '无缝 (0 pt)'),
        ('8', '小间距 (8 pt)'),
        ('16', '中间距 (16 pt)'),
        ('32', '大间距 (32 pt)'),
    ]

    def __init__(self):
        self.page = None
        self.files = []  # [{'path','name','pages','doc'}]
        self.processing = False
        self.font_family = APP_FONT_FAMILY

    def build(self, page: ft.Page):
        self.page = page
        page.title = "PDF合并为单页"
        page.window.width = 720
        page.window.height = 700
        page.window.min_width = 640
        page.window.min_height = 600
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

        # 工具栏
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

        # 文件列表
        self.file_rows = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
        self.empty_hint = ft.Text(
            "暂无文件，点击「添加文件」选择要拼接的PDF",
            size=13,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
            text_align=ft.TextAlign.CENTER,
        )
        list_card = self._make_card(
            "拼接列表（可通过箭头按钮调整拼接顺序）",
            ft.Column(
                [self._list_header_row(), self.file_rows, self.empty_hint],
                spacing=8,
                expand=True,
            ),
            expand=True,
        )

        # 选项卡片
        self.mode_drop = ft.Dropdown(
            value='stretch',
            width=220,
            options=[ft.dropdown.Option(key=v, text=t) for v, t in self.WIDTH_MODES],
            content_padding=ft.padding.symmetric(horizontal=10, vertical=6),
            text_style=ft.TextStyle(font_family=self.font_family),
        )
        self.gap_drop = ft.Dropdown(
            value='0',
            width=180,
            options=[ft.dropdown.Option(key=v, text=t) for v, t in self.GAP_OPTIONS],
            content_padding=ft.padding.symmetric(horizontal=10, vertical=6),
            text_style=ft.TextStyle(font_family=self.font_family),
        )
        self.options_hint = ft.Text(
            "所有页面会按列表顺序上下拼接为一个连续页面；结果超高时会自动等比缩放至 14400 磅以内，保证常见 PDF 阅读器可正常打开。",
            size=12,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
        )
        options_card = self._make_card(
            "拼接选项",
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("宽度模式：", size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family),
                            self.mode_drop,
                            ft.Container(width=12),
                            ft.Text("页面间距：", size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family),
                            self.gap_drop,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    self.options_hint,
                ],
                spacing=8,
            ),
        )

        # 进度条与按钮
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
            "合并为单页",
            icon=ft.Icons.HEIGHT,  # 垂直拼接语义
            on_click=self.start_merge,
            height=40,
        )

        # 底部状态栏
        self.status_text = ft.Text("就绪", size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)

        page.add(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.HEIGHT, size=32, color=ft.Colors.BLUE),
                            ft.Text("PDF合并为单页", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Divider(thickness=1, opacity=0.3),
                    toolbar_card,
                    list_card,
                    options_card,
                    ft.Row(
                        [self.progress, self.progress_text],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Row([self.merge_btn], alignment=ft.MainAxisAlignment.END),
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
        """创建白色圆角卡片（与 V4 系列工具风格一致）"""
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
        """构建单个文件行"""
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
                doc = fitz.open(file)
                page_count = len(doc)
                if page_count == 0:
                    doc.close()
                    self.show_status(f"文件无页面：{os.path.basename(file)}", success=False)
                    skipped += 1
                    continue
            except Exception as err:
                self.show_status(f"无法读取文件 {os.path.basename(file)}: {err}", success=False)
                skipped += 1
                continue
            self.files.append({
                'path': file,
                'name': os.path.basename(file),
                'pages': page_count,
                'doc': doc,
            })
            existing_paths.add(file)
            added += 1
        if added:
            self.show_status(f"已添加 {added} 个文件" + (f"，跳过 {skipped} 个" if skipped else ""))
        elif skipped:
            self.show_status("所选文件均无法添加", success=False)
        self._refresh_file_list()

    def move_file(self, index, delta):
        if self.processing:
            return
        target = index + delta
        if 0 <= index < len(self.files) and 0 <= target < len(self.files):
            self.files[index], self.files[target] = self.files[target], self.files[index]
            self._refresh_file_list()

    def remove_file(self, index):
        if self.processing:
            return
        if 0 <= index < len(self.files):
            item = self.files.pop(index)
            self._close_doc(item.get('doc'))
            self._refresh_file_list()
            self.show_status(f"已移除：{item['name']}")

    def confirm_clear(self, e):
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
        self.close_dialog()
        for item in self.files:
            self._close_doc(item.get('doc'))
        self.files.clear()
        self._refresh_file_list()
        self.show_status("已清空文件列表")

    @staticmethod
    def _close_doc(doc):
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass

    def start_merge(self, e):
        if self.processing:
            return
        if not self.files:
            self.show_status("请先添加PDF文件", success=False)
            return
        self.save_picker.save_file(
            dialog_title="保存合并后的单页PDF",
            file_name="合并为单页.pdf",
            allowed_extensions=["pdf"],
        )

    def on_save_picked(self, e):
        if not e.path:
            return
        output_file = e.path
        if not output_file.lower().endswith('.pdf'):
            output_file += '.pdf'

        self.processing = True
        self.merge_btn.disabled = True
        self.add_btn.disabled = True
        self.clear_btn.disabled = True
        self.mode_drop.disabled = True
        self.gap_drop.disabled = True
        self.progress.value = 0
        self.progress.visible = True
        self.progress_text.value = ""
        self._refresh_file_list()
        self.show_status("正在拼接为单页...")

        mode = self.mode_drop.value
        gap = float(self.gap_drop.value)

        threading.Thread(
            target=self._do_merge,
            args=(output_file, mode, gap),
            daemon=True,
        ).start()

    def _do_merge(self, output_file, mode, gap):
        """在后台线程执行拼接（使用 PyMuPDF show_pdf_page 嵌入矢量页面）"""
        page_refs = []  # (doc, pno, rect)
        try:
            # 收集所有页面（按文件顺序）
            for item in self.files:
                doc = item['doc']
                for pno in range(len(doc)):
                    page = doc.load_page(pno)
                    page_refs.append((doc, pno, page.rect))

            total_pages = len(page_refs)
            if total_pages == 0:
                raise ValueError("没有有效的页面可供拼接")

            # 计算布局
            stretch = (mode == 'stretch')
            canvas_w = max(rect.width for _, _, rect in page_refs)
            if canvas_w <= 0:
                raise ValueError("页面宽度异常")

            heights = []
            for doc, pno, rect in page_refs:
                if stretch:
                    scale = canvas_w / rect.width
                else:
                    scale = 1.0
                heights.append(rect.height * scale)

            total_h = sum(heights) + gap * max(total_pages - 1, 0)
            overall_scale = 1.0
            if total_h > MAX_PAGE_HEIGHT:
                overall_scale = MAX_PAGE_HEIGHT / total_h
                canvas_w *= overall_scale
                heights = [h * overall_scale for h in heights]
                gap *= overall_scale
                total_h = MAX_PAGE_HEIGHT

            out = fitz.open()
            target = out.new_page(width=canvas_w, height=total_h)

            y = 0.0
            for i, ((doc, pno, rect), h) in enumerate(zip(page_refs, heights)):
                if stretch:
                    dst_w = canvas_w
                    dst_h = h
                    x0 = 0.0
                else:
                    dst_w = rect.width * overall_scale
                    dst_h = h
                    x0 = (canvas_w - dst_w) / 2.0
                dst = fitz.Rect(x0, y, x0 + dst_w, y + dst_h)
                target.show_pdf_page(dst, doc, pno=pno, clip=rect)
                y += dst_h + gap
                self._update_progress(i + 1, total_pages)

            out.save(output_file)
            self._update_progress(total_pages, total_pages)

            final_w = round(canvas_w, 1)
            final_h = round(total_h, 1)
            scale_pct = round(overall_scale * 100, 1)
            if overall_scale < 1.0:
                dim_msg = f"输出尺寸：{final_w} × {final_h} 磅（已自动缩放至 {scale_pct}% 以适配阅读器）"
            else:
                dim_msg = f"输出尺寸：{final_w} × {final_h} 磅"

            self.show_status("PDF合并为单页完成")
            self.show_info(
                "成功",
                f"已生成可滚动的单页 PDF\n共拼接 {total_pages} 个页面\n{dim_msg}\n保存到：{output_file}",
            )
            self._open_output_folder(os.path.dirname(output_file))
        except Exception as err:
            self.show_status(f"拼接失败: {err}", success=False)
        finally:
            # fitz 文档句柄缓存在 self.files 中，不在此处关闭，以便用户可直接再次拼接
            self.processing = False
            self.merge_btn.disabled = False
            self.add_btn.disabled = False
            self.clear_btn.disabled = False
            self.mode_drop.disabled = False
            self.gap_drop.disabled = False
            self.merge_btn.update()
            self.add_btn.update()
            self.clear_btn.update()
            self.mode_drop.update()
            self.gap_drop.update()
            self._refresh_file_list()

    def _update_progress(self, done, total):
        """更新进度条与进度文本"""
        self.progress.value = done / total
        self.progress_text.value = f"{done}/{total}"
        self.progress.update()
        self.progress_text.update()

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

    def show_status(self, message: str, success: bool = True):
        """显示状态消息"""
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
        """关闭对话框"""
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()


if __name__ == '__main__':
    app = PDFMergeToSinglePageApp()
    ft.app(target=app.build)
