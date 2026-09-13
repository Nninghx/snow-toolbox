# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import threading
import importlib.util
from datetime import datetime
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


# 标准 PDF 元数据字段定义：(PDF key, 显示名, 图标, 是否日期)
METADATA_FIELDS = [
    ('/Title', '标题', ft.Icons.TITLE, False),
    ('/Author', '作者', ft.Icons.PERSON, False),
    ('/Subject', '主题', ft.Icons.SUBJECT, False),
    ('/Keywords', '关键词', ft.Icons.LABEL, False),
    ('/Creator', '创建程序', ft.Icons.BUILD, False),
    ('/Producer', '生成程序', ft.Icons.SMART_DISPLAY, False),
    ('/CreationDate', '创建时间', ft.Icons.CALENDAR_TODAY, True),
    ('/ModDate', '修改时间', ft.Icons.UPDATE, True),
]


def parse_pdf_date(date_str):
    """将 PDF 日期字符串解析为可读格式，如 D:20230905143022 -> 2023-09-05 14:30:22"""
    if not date_str:
        return ""
    s = str(date_str)
    # 去掉 D: 前缀
    if s.startswith('D:'):
        s = s[2:]
    # 去掉时区后缀 (+08'00' 或 Z 等)
    for ch in ('+', '-', 'Z'):
        if ch in s[14:]:
            s = s[:s.index(ch, 14)]
            break
    # 尝试解析
    for fmt in ('%Y%m%d%H%M%S', '%Y%m%d%H%M', '%Y%m%d'):
        try:
            dt = datetime.strptime(s[:len(fmt.replace('%', '').replace('Y', '4').replace('m', '2').replace('d', '2').replace('H', '2').replace('M', '2').replace('S', '2'))], fmt)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, IndexError):
            continue
    return str(date_str)


def format_pdf_date(date_str):
    """将用户输入的日期字符串转为 PDF 日期格式，如 2023-09-05 14:30:22 -> D:20230905143022"""
    if not date_str or not date_str.strip():
        return None
    s = date_str.strip()
    # 如果已经是 D: 格式直接返回
    if s.startswith('D:'):
        return s
    # 尝试解析常见日期格式
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d', '%Y/%m/%d %H:%M:%S', '%Y/%m/%d'):
        try:
            dt = datetime.strptime(s, fmt)
            return f"D:{dt.strftime('%Y%m%d%H%M%S')}"
        except ValueError:
            continue
    raise ValueError(f"日期格式无效: {s}，请使用 YYYY-MM-DD HH:MM:SS 格式")


class PDFMetadataApp:
    def __init__(self):
        self.page = None
        self.input_file = None
        self.total_pages = 0
        self.processing = False
        self.font_family = APP_FONT_FAMILY
        self.metadata_fields = {}  # key -> TextField
        self.original_metadata = {}  # 原始元数据用于对比

    def build(self, page: ft.Page):
        self.page = page
        page.title = "PDF元数据"
        page.window.width = 680
        page.window.height = 720
        page.window.min_width = 600
        page.window.min_height = 600
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

        # 元数据字段卡片（动态生成）
        self.metadata_column = ft.Column(spacing=8)
        for key, label, icon, is_date in METADATA_FIELDS:
            field = ft.TextField(
                label=label,
                hint_text=f"输入{label}" if not is_date else "YYYY-MM-DD HH:MM:SS",
                prefix_icon=icon,
                read_only=True,
                border_radius=8,
                content_padding=ft.padding.all(10),
                text_size=14,
                text_style=ft.TextStyle(font_family=self.font_family),
            )
            self.metadata_fields[key] = field
            self.metadata_column.controls.append(field)

        metadata_card = self._make_card(
            "文档属性",
            ft.Column(
                [
                    self.metadata_column,
                    ft.Text(
                        "选择文件后自动读取元数据，点击「编辑模式」可修改。",
                        size=12,
                        color=ft.Colors.BLUE_GREY_500,
                        font_family=self.font_family,
                    ),
                ],
                spacing=8,
            ),
        )

        # 操作按钮
        self.edit_btn = ft.ElevatedButton(
            "编辑模式",
            icon=ft.Icons.EDIT,
            on_click=self.toggle_edit_mode,
            height=40,
            disabled=True,
        )
        self.save_btn = ft.ElevatedButton(
            "保存修改",
            icon=ft.Icons.SAVE,
            on_click=self.save_metadata,
            height=40,
            disabled=True,
        )
        self.reset_btn = ft.TextButton(
            "重置",
            icon=ft.Icons.REFRESH,
            on_click=self.reset_fields,
        )

        # 进度条
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
            ft.Column(
                [
                    # 顶部标题栏
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.INFO_OUTLINE, size=32, color=ft.Colors.BLUE),
                            ft.Text("PDF元数据", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Divider(thickness=1, opacity=0.3),
                    file_card,
                    metadata_card,
                    ft.Row(
                        [self.progress, self.progress_text],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Row(
                        [self.reset_btn, self.edit_btn, self.save_btn],
                        alignment=ft.MainAxisAlignment.END,
                        spacing=10,
                    ),
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
        """创建白色圆角卡片"""
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
        self._load_metadata()
        self.page.update()

    def _load_metadata(self):
        """读取 PDF 元数据并填充到界面"""
        try:
            with pikepdf.open(self.input_file) as pdf:
                self.total_pages = len(pdf.pages)
                self.stats_text.value = f"共 {self.total_pages} 页"

                # 读取文档信息字典
                docinfo = {}
                if pdf.docinfo:
                    for key, value in pdf.docinfo.items():
                        docinfo[key] = str(value) if value else ""

                self.original_metadata = dict(docinfo)

                # 填充字段
                for key, label, icon, is_date in METADATA_FIELDS:
                    field = self.metadata_fields[key]
                    raw_value = docinfo.get(key, "")
                    if is_date and raw_value:
                        field.value = parse_pdf_date(raw_value)
                    else:
                        field.value = raw_value

                # 默认只读模式
                self._set_fields_readonly(True)
                self.edit_btn.disabled = False
                self.save_btn.disabled = True
                self.show_status("元数据读取完成")
        except Exception as err:
            self.show_status(f"读取元数据失败: {err}", success=False)

    def _set_fields_readonly(self, readonly):
        """设置所有元数据字段的只读状态"""
        for key, label, icon, is_date in METADATA_FIELDS:
            self.metadata_fields[key].read_only = readonly

    def toggle_edit_mode(self, e):
        """切换编辑/查看模式"""
        current_readonly = self.metadata_fields['/Title'].read_only
        if current_readonly:
            # 进入编辑模式
            self._set_fields_readonly(False)
            self.edit_btn.text = "查看模式"
            self.edit_btn.icon = ft.Icons.VISIBILITY
            self.save_btn.disabled = False
            self.show_status("已进入编辑模式，修改后点击「保存修改」")
        else:
            # 回到查看模式
            self._set_fields_readonly(True)
            self.edit_btn.text = "编辑模式"
            self.edit_btn.icon = ft.Icons.EDIT
            self.save_btn.disabled = True
            self.show_status("已切换为查看模式")
        self.page.update()

    def reset_fields(self, e):
        """重置为原始元数据"""
        for key, label, icon, is_date in METADATA_FIELDS:
            field = self.metadata_fields[key]
            raw_value = self.original_metadata.get(key, "")
            if is_date and raw_value:
                field.value = parse_pdf_date(raw_value)
            else:
                field.value = raw_value
        self.show_status("已重置为原始值")
        self.page.update()

    def save_metadata(self, e):
        """保存修改后的元数据"""
        if self.processing:
            return
        if not self.input_file:
            self.show_status("请先选择PDF文件", success=False)
            return

        # 校验日期字段格式
        for key, label, icon, is_date in METADATA_FIELDS:
            if is_date:
                value = (self.metadata_fields[key].value or "").strip()
                if value:
                    try:
                        format_pdf_date(value)
                    except ValueError as err:
                        self.show_status(str(err), success=False)
                        return

        base_name = os.path.splitext(os.path.basename(self.input_file))[0]
        self.save_picker.save_file(
            dialog_title="保存修改后的PDF",
            file_name=f"{base_name}_edited.pdf",
            allowed_extensions=["pdf"],
        )

    def on_save_picked(self, e):
        if not e.path:
            return
        output_path = e.path
        if not output_path.lower().endswith('.pdf'):
            output_path += '.pdf'

        # 收集当前字段值
        new_metadata = {}
        for key, label, icon, is_date in METADATA_FIELDS:
            value = (self.metadata_fields[key].value or "").strip()
            if value:
                if is_date:
                    try:
                        new_metadata[key] = format_pdf_date(value)
                    except ValueError:
                        continue
                else:
                    new_metadata[key] = value

        # 后台线程保存，避免阻塞 UI
        self.processing = True
        self.save_btn.disabled = True
        self.progress.value = 0
        self.progress.visible = True
        self.progress_text.value = "保存中..."
        self.show_status("正在保存元数据...")

        threading.Thread(
            target=self._do_save,
            args=(output_path, new_metadata),
            daemon=True,
        ).start()

    def _do_save(self, output_path, new_metadata):
        """后台线程：写入修改后的元数据"""
        try:
            with pikepdf.open(self.input_file) as pdf:
                # 更新文档信息字典
                for key, value in new_metadata.items():
                    pdf.docinfo[key] = value

                # 同时删除用户清空的字段
                for key, label, icon, is_date in METADATA_FIELDS:
                    value = (self.metadata_fields[key].value or "").strip()
                    if not value and key in pdf.docinfo:
                        del pdf.docinfo[key]

                tmp_path = f"{output_path}.tmp"
                pdf.save(tmp_path)
            os.replace(tmp_path, output_path)

            self.progress.value = 1
            self.progress_text.value = "完成"
            self.progress.update()
            self.progress_text.update()

            # 统计修改了多少个字段
            changed = sum(
                1 for key in new_metadata
                if new_metadata.get(key) != self.original_metadata.get(key, "")
            )
            self.show_status("元数据保存成功")
            self.show_info(
                "成功",
                f"元数据保存成功!\n"
                f"共修改 {changed} 个字段\n"
                f"保存到: {output_path}",
            )

            # 更新原始元数据为当前值
            self.original_metadata = dict(new_metadata)
        except Exception as err:
            self.show_status(f"保存失败: {err}", success=False)
        finally:
            self.processing = False
            self.save_btn.disabled = False
            self.save_btn.update()

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
    app = PDFMetadataApp()
    ft.app(target=app.build)
