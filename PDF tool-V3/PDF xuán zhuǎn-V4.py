# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import threading
import importlib.util
from pathlib import Path

import flet as ft
import pikepdf


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


class PDFRotatorApp:
    def __init__(self):
        self.page = None
        self.input_file = None
        self.total_pages = 0
        self.processing = False
        self.font_family = APP_FONT_FAMILY

    def build(self, page: ft.Page):
        self.page = page
        page.title = "PDF旋转"
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

        # 旋转角度卡片
        self.angle_group = ft.RadioGroup(
            value="90",
            content=ft.Row(
                [
                    ft.Radio(value="90", label="顺时针 90°"),
                    ft.Radio(value="180", label="旋转 180°"),
                    ft.Radio(value="270", label="逆时针 90°"),
                ],
                spacing=14,
            ),
        )
        for radio in self.angle_group.content.controls:
            radio.label_style = ft.TextStyle(font_family=self.font_family, size=14)
        angle_card = self._make_card(
            "旋转角度",
            ft.Column(
                [self.angle_group, ft.Text(
                    "以页面当前方向为基准累加旋转；若 PDF 原页面已有旋转，会在此基础上叠加。",
                    size=12,
                    color=ft.Colors.BLUE_GREY_500,
                    font_family=self.font_family,
                )],
                spacing=8,
            ),
        )

        # 旋转范围卡片
        self.scope_group = ft.RadioGroup(
            value="all",
            on_change=self.on_scope_change,
            content=ft.Row(
                [
                    ft.Radio(value="all", label="全部页面"),
                    ft.Radio(value="range", label="指定页面"),
                ],
                spacing=14,
            ),
        )
        for radio in self.scope_group.content.controls:
            radio.label_style = ft.TextStyle(font_family=self.font_family, size=14)
        self.range_field = ft.TextField(
            label="页码范围",
            hint_text="如 1-3,5,7-9",
            expand=True,
            border_radius=8,
            content_padding=ft.padding.all(10),
            text_size=14,
            text_style=ft.TextStyle(font_family=self.font_family),
        )
        self.range_row = ft.Row([self.range_field], visible=False)
        scope_card = self._make_card(
            "旋转范围",
            ft.Column([self.scope_group, self.range_row], spacing=8),
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
        self.rotate_btn = ft.ElevatedButton(
            "旋转PDF",
            icon=ft.Icons.ROTATE_RIGHT,
            on_click=self.rotate_pdf,
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
                            ft.Icon(ft.Icons.ROTATE_RIGHT, size=32, color=ft.Colors.BLUE),
                            ft.Text("PDF旋转", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Divider(thickness=1, opacity=0.3),
                    file_card,
                    angle_card,
                    scope_card,
                    ft.Row(
                        [self.progress, self.progress_text],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Row([self.rotate_btn], alignment=ft.MainAxisAlignment.END),
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

    def on_scope_change(self, e):
        """旋转范围切换：全部页面 / 指定页面"""
        is_all = self.scope_group.value == "all"
        self.range_row.visible = not is_all
        self.page.update()

    def parse_page_indices(self, range_str, total_pages):
        """解析页码范围字符串（1基），返回去重排序的 0 基索引列表。"""
        indices = []
        for part in range_str.split(','):
            if not part.strip():
                continue
            if '-' in part:
                start, end = map(int, part.split('-', 1))
                indices.extend(range(max(start - 1, 0), min(end, total_pages)))
            else:
                page = int(part)
                if 1 <= page <= total_pages:
                    indices.append(page - 1)
        return sorted(set(indices))

    def rotate_pdf(self, e):
        """校验输入后弹出保存对话框"""
        if self.processing:
            return
        if not self.input_file:
            self.show_status("请先选择PDF文件", success=False)
            return
        if not os.path.exists(self.input_file):
            self.show_status("PDF文件不存在", success=False)
            return

        # 提前校验指定页面范围是否合法
        if self.scope_group.value == "range":
            range_str = (self.range_field.value or "").strip()
            if not range_str:
                self.show_status("请输入页码范围", success=False)
                return
            try:
                indices = self.parse_page_indices(range_str, self.total_pages)
                if not indices:
                    raise ValueError("没有有效的页面被选择")
            except ValueError as err:
                self.show_status(f"页码范围无效: {err}", success=False)
                return

        angle = int(self.angle_group.value)
        base_name = os.path.splitext(os.path.basename(self.input_file))[0]
        self.save_picker.save_file(
            dialog_title="保存旋转后的PDF",
            file_name=f"{base_name}_旋转{angle}.pdf",
            allowed_extensions=["pdf"],
        )

    def on_save_picked(self, e):
        if not e.path:
            return
        output_path = e.path
        if not output_path.lower().endswith('.pdf'):
            output_path += '.pdf'

        angle = int(self.angle_group.value)
        if self.scope_group.value == "range":
            range_str = (self.range_field.value or "").strip()
            try:
                page_indices = self.parse_page_indices(range_str, self.total_pages)
            except Exception:
                page_indices = None
        else:
            page_indices = None

        # 后台线程执行旋转，避免阻塞 UI；pikepdf C++ 操作会释放 GIL
        self.processing = True
        self.rotate_btn.disabled = True
        self.progress.value = 0
        self.progress.visible = True
        self.progress_text.value = ""
        self.show_status("正在旋转...")

        threading.Thread(
            target=self._do_rotate,
            args=(output_path, angle, page_indices),
            daemon=True,
        ).start()

    def _do_rotate(self, output_path, angle, page_indices):
        """后台线程：设置页面旋转属性并保存（pikepdf C++ 操作释放 GIL）"""
        try:
            with pikepdf.open(self.input_file) as pdf:
                if page_indices is None:
                    indices = list(range(len(pdf.pages)))
                else:
                    indices = page_indices
                total = len(indices)
                if total == 0:
                    raise RuntimeError("没有可旋转的页面")

                update_every = max(1, total // 100)
                for i, page_index in enumerate(indices):
                    page = pdf.pages[page_index]
                    # 以页面当前方向为基准累加旋转（若原 PDF 已有 /Rotate 则叠加）
                    current = int(page.get('/Rotate', 0) or 0)
                    page['/Rotate'] = (current + angle) % 360
                    if (i + 1) % update_every == 0 or (i + 1) == total:
                        self._update_progress(i + 1, total)

                # 先写临时文件再原子替换，避免输出覆盖失败损坏数据
                tmp_path = f"{output_path}.tmp"
                pdf.save(tmp_path)
            os.replace(tmp_path, output_path)
            self._update_progress(total, total)
            self.show_status("PDF旋转完成")
            angle_desc = {90: "顺时针90°", 180: "180°", 270: "逆时针90°"}.get(angle, f"{angle}°")
            self.show_info(
                "成功",
                f"PDF旋转完成!\n共旋转 {total} 页（{angle_desc}）\n保存到: {output_path}",
            )
        except Exception as err:
            self.show_status(f"旋转失败: {err}", success=False)
        finally:
            self.processing = False
            self.rotate_btn.disabled = False
            self.rotate_btn.update()

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
    app = PDFRotatorApp()
    ft.app(target=app.build)
