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


class PDFSplitterApp:
    def __init__(self):
        self.page = None
        self.input_file = None
        self.output_dir = None
        self.total_pages = 0
        self.font_family = APP_FONT_FAMILY

    def build(self, page: ft.Page):
        self.page = page
        page.title = "PDF拆分"
        page.window.width = 580
        page.window.height = 640
        page.window.center()
        page.padding = 16
        page.theme_mode = ft.ThemeMode.LIGHT

        # 设置窗口图标
        icon_path = get_project_root() / 'Image' / 'icon.ico'
        if icon_path.exists():
            page.window.icon = str(icon_path)

        # 文件/目录选择器
        self.file_picker = ft.FilePicker(on_result=self.on_file_picked)
        self.dir_picker = ft.FilePicker(on_result=self.on_dir_picked)
        page.overlay.extend([self.file_picker, self.dir_picker])

        # 文件选择卡片
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

        # 输出目录卡片
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

        # 拆分选项卡片
        self.mode_group = ft.RadioGroup(
            value="page_count",
            on_change=self.on_mode_change,
            content=ft.Row(
                [
                    ft.Radio(
                        value="page_count",
                        label="按页数拆分",
                        label_style=ft.TextStyle(font_family=self.font_family, size=14),
                    ),
                    ft.Radio(
                        value="page_range",
                        label="按范围拆分",
                        label_style=ft.TextStyle(font_family=self.font_family, size=14),
                    ),
                ],
                spacing=20,
            ),
        )
        self.page_count_row = ft.Row(
            [
                ft.TextField(
                    label="每份页数",
                    value="1",
                    width=160,
                    border_radius=8,
                    content_padding=ft.padding.all(10),
                    text_size=14,
                    keyboard_type=ft.KeyboardType.NUMBER,
                    text_style=ft.TextStyle(font_family=self.font_family),
                ),
            ]
        )
        self.range_row = ft.Row(
            [
                ft.TextField(
                    label="页码范围",
                    hint_text="如 1-3,5,7-9",
                    expand=True,
                    border_radius=8,
                    content_padding=ft.padding.all(10),
                    text_size=14,
                    text_style=ft.TextStyle(font_family=self.font_family),
                ),
            ],
            visible=False,
        )
        self.range_field = self.range_row.controls[0]
        self.page_count_field = self.page_count_row.controls[0]
        option_card = self._make_card(
            "拆分选项",
            ft.Column([self.mode_group, self.page_count_row, self.range_row], spacing=10),
        )

        # 操作按钮与进度条
        self.split_button = ft.ElevatedButton(
            "拆分PDF",
            icon=ft.Icons.CALL_SPLIT,
            on_click=self.split_pdf,
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

        # 底部状态栏
        self.status_text = ft.Text("就绪", size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)
        self.stats_text = ft.Text(size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)

        page.add(
            # 顶部标题栏
            ft.Row(
                [
                    ft.Icon(ft.Icons.CALL_SPLIT, size=32, color=ft.Colors.BLUE),
                    ft.Text("PDF拆分", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            ft.Divider(thickness=1, opacity=0.3),
            file_card,
            output_card,
            option_card,
            ft.Row(
                [self.progress, self.progress_text],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            ft.Row([self.split_button], alignment=ft.MainAxisAlignment.END),
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
        )
        return page

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

    def select_output_dir(self, e):
        self.dir_picker.get_directory_path(dialog_title="选择输出目录")

    def on_dir_picked(self, e):
        if not e.path:
            return
        self.output_dir = e.path
        self.output_text.value = e.path
        self.output_text.color = ft.Colors.BLUE_GREY_900
        self.page.update()

    def on_mode_change(self, e):
        """拆分模式切换：按页数/按范围显示对应输入框"""
        is_page_count = self.mode_group.value == "page_count"
        self.page_count_row.visible = is_page_count
        self.range_row.visible = not is_page_count
        self.page.update()

    def parse_page_ranges(self, range_str, total_pages):
        """解析页码范围字符串，返回页面索引列表"""
        ranges = []
        parts = range_str.split(',')
        for part in parts:
            if '-' in part:
                start, end = map(int, part.split('-'))
                ranges.extend(range(start - 1, min(end, total_pages)))
            else:
                page = int(part)
                if page <= total_pages:
                    ranges.append(page - 1)
        return sorted(list(set(ranges)))  # 去重并排序

    def split_pdf(self, e):
        if not self.input_file:
            self.show_status("请先选择PDF文件", success=False)
            return
        if not self.output_dir:
            self.show_status("请先选择输出目录", success=False)
            return
        try:
            # 验证PDF文件有效性
            if not os.path.exists(self.input_file):
                self.show_status("PDF文件不存在", success=False)
                return
            try:
                with pikepdf.open(self.input_file) as pdf:
                    total_pages = len(pdf.pages)
                if total_pages == 0:
                    self.show_status("PDF文件没有有效页面", success=False)
                    return
            except Exception as err:
                self.show_status(f"无效的PDF文件: {err}", success=False)
                return

            base_name = os.path.splitext(os.path.basename(self.input_file))[0]
            chunks = []  # (output_file, start_index, end_index) 采用连续页区间，减少 Python 级循环与 page 对象创建开销

            if self.mode_group.value == "page_count":
                # 按页数拆分模式
                try:
                    pages_per_file = int(self.page_count_field.value or "0")
                    if pages_per_file <= 0:
                        raise ValueError("页数必须大于0")
                except ValueError:
                    self.show_status("请输入有效的页数", success=False)
                    return
                for i in range(0, total_pages, pages_per_file):
                    end = min(i + pages_per_file, total_pages)
                    output_file = os.path.join(
                        self.output_dir,
                        f"{base_name}_p{i+1}-{end}.pdf"
                    )
                    chunks.append((output_file, i, end))
                file_desc = f"共拆分 {total_pages} 页为 {len(chunks)} 个文件"
            else:
                # 按范围拆分模式
                range_str = (self.range_field.value or "").strip()
                if not range_str:
                    self.show_status("请输入有效的页码范围", success=False)
                    return
                try:
                    page_indices = self.parse_page_ranges(range_str, total_pages)
                    if not page_indices:
                        raise ValueError("没有有效的页面被选择")
                except ValueError as err:
                    self.show_status(f"页码范围无效: {err}", success=False)
                    return
                # 将连续页面分组
                groups = []
                current_group = [page_indices[0]]
                for i in range(1, len(page_indices)):
                    if page_indices[i] == page_indices[i - 1] + 1:
                        current_group.append(page_indices[i])
                    else:
                        groups.append(current_group)
                        current_group = [page_indices[i]]
                groups.append(current_group)
                for group in groups:
                    start_index = group[0]
                    end_index = group[-1] + 1
                    start_page = start_index + 1
                    end_page = end_index
                    output_file = os.path.join(
                        self.output_dir,
                        f"{base_name}_range_{start_page}-{end_page}.pdf"
                    )
                    chunks.append((output_file, start_index, end_index))
                file_desc = f"共提取 {len(page_indices)} 页为 {len(groups)} 个文件"

            # 重置进度条并在后台线程处理分块
            total_chunks = len(chunks)
            self.progress.value = 0
            self.progress.visible = True
            self.progress_text.value = f"0/{total_chunks}"
            self.split_button.disabled = True
            self.show_status("正在拆分...")

            threading.Thread(
                target=self._run_split,
                args=(chunks, total_chunks, file_desc),
                daemon=True,
            ).start()
        except Exception as err:
            self.show_status(f"拆分失败: {err}", success=False)

    def _run_split(self, chunks, total_chunks, file_desc):
        """后台线程执行拆分任务"""
        try:
            self._process_chunks(chunks, total_chunks)
            self.progress.value = 1
            self.progress_text.value = f"{total_chunks}/{total_chunks}"
            self.progress.update()
            self.progress_text.update()
            self.show_status("PDF拆分完成")
            self.show_info("成功", f"PDF拆分完成!\n{file_desc}")
        except Exception as err:
            self.show_status(f"拆分失败: {err}", success=False)
        finally:
            self.split_button.disabled = False
            self.split_button.update()

    def _process_chunks(self, chunks, total_chunks):
        """顺序处理PDF分块写入，只打开源文件一次，且按连续页区间复制，避免大量 Python 级对象分配。"""
        file_count = 0
        update_every = max(1, total_chunks // 100)
        with pikepdf.open(self.input_file) as src:
            for output_file, start_index, end_index in chunks:
                dst = pikepdf.new()
                dst.pages.extend(src.pages[start_index:end_index])

                tmp_path = f"{output_file}.tmp"
                dst.save(tmp_path)
                os.replace(tmp_path, output_file)

                file_count += 1
                if file_count % update_every == 0 or file_count == total_chunks:
                    self._update_progress(file_count, total_chunks)

    def _update_progress(self, done, total):
        """更新进度条与进度文本，避免每个小文件都频繁刷新UI导致固定成本被放大。"""
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
    app = PDFSplitterApp()
    ft.app(target=app.build)
