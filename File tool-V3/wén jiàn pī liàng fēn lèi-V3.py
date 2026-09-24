# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import os
import shutil
import threading
import importlib.util
from pathlib import Path
from datetime import datetime

import flet as ft


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

# 按扩展名分类的预设映射
EXT_CATEGORIES = {
    '图片': {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.svg', '.ico'},
    '文档': {'.doc', '.docx', '.pdf', '.txt', '.xls', '.xlsx', '.ppt', '.pptx', '.csv', '.md', '.rtf'},
    '视频': {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'},
    '音频': {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'},
    '压缩包': {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'},
    '代码': {'.py', '.js', '.java', '.c', '.cpp', '.h', '.css', '.html', '.json', '.xml', '.yaml', '.yml'},
}


class FileClassifierApp:
    def __init__(self):
        self.page = None
        self.source_dir = None
        self.font_family = APP_FONT_FAMILY
        self.preview_result = []

    def build(self, page: ft.Page):
        self.page = page
        page.title = "文件批量分类工具"
        page.window.width = 680
        page.window.height = 750
        page.window.center()
        page.padding = 0
        page.theme_mode = ft.ThemeMode.LIGHT
        page.theme = ft.Theme(font_family=self.font_family)

        # 设置窗口图标
        icon_path = get_project_root() / 'Image' / 'icon.ico'
        if icon_path.exists():
            page.window.icon = str(icon_path)

        # 目录选择器
        self.dir_picker = ft.FilePicker(on_result=self.on_dir_picked)
        page.overlay.append(self.dir_picker)

        # --- 目录选择卡片 ---
        self.dir_text = ft.Text(
            "未选择目录", size=13, color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family, expand=True,
            no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
        )
        dir_card = self._make_card(
            "选择源目录",
            ft.Row(
                [
                    ft.Icon(ft.Icons.FOLDER, size=18, color=ft.Colors.BLUE_GREY_400),
                    self.dir_text,
                    ft.ElevatedButton("浏览", icon=ft.Icons.FOLDER_OPEN,
                                      on_click=self.browse_directory),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
        )

        # --- 分类模式卡片 ---
        self.mode_group = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="ext", label="按扩展名分类（图片/文档/视频/音频/压缩包/代码）"),
                ft.Radio(value="date", label="按日期分类（按修改时间的年-月归档）"),
                ft.Radio(value="size", label="按大小分类（小文件 <1MB / 中等 / 大文件 >100MB）"),
                ft.Radio(value="custom", label="自定义规则分类（文件名关键词 → 目标文件夹）"),
            ], spacing=4),
            value="ext",
            on_change=self.on_mode_changed,
        )

        # 自定义规则编辑区（默认隐藏）
        self.rules_field = ft.TextField(
            hint_text="每行一条规则，格式：关键词→目标文件夹\n例如：\n发票→财务\n合同→合同文件\n报告→报告归档",
            multiline=True,
            min_lines=4,
            max_lines=6,
            visible=False,
            text_style=ft.TextStyle(font_family=self.font_family),
            border_radius=8,
        )
        self.rules_container = ft.Container(content=self.rules_field, visible=False)

        # 大小阈值设置（仅在 size 模式下显示）
        self.size_small_field = ft.TextField(
            label="小文件上限 (MB)", value="1", width=140,
            text_style=ft.TextStyle(font_family=self.font_family),
            border_radius=8,
        )
        self.size_large_field = ft.TextField(
            label="大文件下限 (MB)", value="100", width=140,
            text_style=ft.TextStyle(font_family=self.font_family),
            border_radius=8,
        )
        self.size_container = ft.Container(
            content=ft.Row([self.size_small_field, self.size_large_field], spacing=16),
            visible=False,
        )

        mode_card = self._make_card("分类模式", ft.Column([
            self.mode_group,
            self.size_container,
            self.rules_container,
        ], spacing=8))

        # --- 预览区卡片 ---
        self.preview_list = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO)
        self.preview_container = ft.Container(
            content=ft.Column([
                ft.Text("分类预览", size=13, weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_GREY_700, font_family=self.font_family),
                ft.Container(
                    content=self.preview_list,
                    height=200,
                ),
            ], spacing=8),
            padding=ft.padding.all(12),
            border_radius=10,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
            visible=False,
        )

        # --- 按钮 + 进度条 ---
        self.preview_button = ft.ElevatedButton(
            "预览分类结果", icon=ft.Icons.PREVIEW, on_click=self.do_preview, height=40,
        )
        self.execute_button = ft.ElevatedButton(
            "执行移动", icon=ft.Icons.DRIVE_FILE_MOVE,
            on_click=self.do_execute, height=40, disabled=True,
            color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE,
        )
        self.progress = ft.ProgressBar(
            visible=False, color=ft.Colors.BLUE,
            bgcolor=ft.Colors.GREY_200, bar_height=6, border_radius=4, expand=True,
        )

        # --- 状态栏 ---
        self.status_text = ft.Text(
            "就绪", size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family,
        )

        # --- 组装页面 ---
        page.add(
            ft.Container(
                content=ft.Column([
                    # 标题
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.DRIVE_FILE_MOVE, size=32, color=ft.Colors.BLUE),
                            ft.Text("文件批量分类", size=28, weight=ft.FontWeight.BOLD,
                                    font_family=self.font_family),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Divider(thickness=1, opacity=0.3),
                    dir_card,
                    mode_card,
                    self.preview_container,
                    self.progress,
                    ft.Row(
                        [self.preview_button, self.execute_button],
                        alignment=ft.MainAxisAlignment.END,
                        spacing=12,
                    ),
                ], spacing=12, scroll=ft.ScrollMode.AUTO),
                expand=True,
                padding=ft.padding.all(16),
            ),
            ft.Container(
                content=self.status_text,
                padding=ft.padding.symmetric(vertical=8, horizontal=12),
                bgcolor=ft.Colors.BLUE_GREY_50,
                border_radius=8,
                border=ft.border.all(1, ft.Colors.GREY_300),
                margin=ft.margin.symmetric(horizontal=16, vertical=8),
            ),
        )
        return page

    # ======================== 辅助方法 ========================

    def _make_card(self, title, content):
        """创建统一的白色卡片容器。"""
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=13, weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_GREY_700, font_family=self.font_family),
                content,
            ], spacing=8),
            padding=ft.padding.all(12),
            border_radius=10,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )

    # ======================== 事件处理 ========================

    def browse_directory(self, e):
        self.dir_picker.get_directory_path(dialog_title="选择要分类的目录")

    def on_dir_picked(self, e):
        if not e.path:
            return
        self.source_dir = e.path
        self.dir_text.value = e.path
        self.dir_text.color = ft.Colors.BLUE_GREY_900
        self.preview_container.visible = False
        self.execute_button.disabled = True
        self.preview_result.clear()
        self.page.update()

    def on_mode_changed(self, e):
        mode = e.control.value
        self.rules_container.visible = (mode == "custom")
        self.size_container.visible = (mode == "size")
        self.preview_container.visible = False
        self.execute_button.disabled = True
        self.preview_result.clear()
        self.page.update()

    # ======================== 分类引擎 ========================

    def _classify_by_ext(self, filename):
        """按扩展名分类，返回目标子目录名。"""
        ext = os.path.splitext(filename)[1].lower()
        for category, extensions in EXT_CATEGORIES.items():
            if ext in extensions:
                return category
        return "其他"

    def _classify_by_date(self, filepath):
        """按修改时间的年-月分类。"""
        mtime = os.path.getmtime(filepath)
        dt = datetime.fromtimestamp(mtime)
        return f"{dt.year}-{dt.month:02d}"

    def _classify_by_size(self, filepath):
        """按文件大小分三档。"""
        try:
            small_mb = float(self.size_small_field.value or "1")
            large_mb = float(self.size_large_field.value or "100")
        except ValueError:
            small_mb, large_mb = 1.0, 100.0
        size = os.path.getsize(filepath)
        small_bytes = small_mb * 1024 * 1024
        large_bytes = large_mb * 1024 * 1024
        if size < small_bytes:
            return "小文件"
        elif size > large_bytes:
            return "大文件"
        return "中等文件"

    def _parse_custom_rules(self):
        """解析自定义规则文本，返回 [(关键词, 目标文件夹), ...]。"""
        rules = []
        text = self.rules_field.value or ""
        for line in text.strip().split('\n'):
            line = line.strip()
            if not line or '→' not in line:
                continue
            parts = line.split('→', 1)
            if len(parts) == 2:
                keyword = parts[0].strip()
                folder = parts[1].strip()
                if keyword and folder:
                    rules.append((keyword, folder))
        return rules

    def _classify_by_custom(self, filename, rules):
        """按自定义规则分类，首个匹配生效，无匹配归入其他。"""
        for keyword, folder in rules:
            if keyword in filename:
                return folder
        return "其他"

    def _classify_all(self):
        """对所有文件执行分类，返回 [(源路径, 目标路径), ...]。"""
        mode = self.mode_group.value
        source = self.source_dir
        results = []

        if mode == "custom":
            rules = self._parse_custom_rules()
            if not rules:
                raise ValueError("自定义规则为空或格式不正确")

        for entry in os.scandir(source):
            if not entry.is_file():
                continue
            if entry.name.startswith('.'):
                continue

            if mode == "ext":
                sub_dir = self._classify_by_ext(entry.name)
            elif mode == "date":
                sub_dir = self._classify_by_date(entry.path)
            elif mode == "size":
                sub_dir = self._classify_by_size(entry.path)
            elif mode == "custom":
                sub_dir = self._classify_by_custom(entry.name, rules)
            else:
                continue

            dest_path = os.path.join(source, sub_dir, entry.name)
            results.append((entry.path, dest_path))

        return results

    # ======================== 预览 ========================

    def do_preview(self, e):
        if not self.source_dir:
            self.show_status("请先选择目录", success=False)
            return

        if self.mode_group.value == "custom":
            rules = self._parse_custom_rules()
            if not rules:
                self.show_status("请填写至少一条自定义规则", success=False)
                return

        try:
            self.preview_result = self._classify_all()
        except ValueError as err:
            self.show_status(str(err), success=False)
            return

        if not self.preview_result:
            self.show_status("目录下没有找到可分类的文件", success=False)
            return

        # 构建预览列表
        self.preview_list.controls.clear()
        for src, dst in self.preview_result:
            src_name = os.path.basename(src)
            dst_sub = os.path.relpath(dst, self.source_dir)
            self.preview_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.INSERT_DRIVE_FILE, size=14,
                                color=ft.Colors.BLUE_GREY_400),
                        ft.Text(src_name, size=12, font_family=self.font_family,
                                width=200, no_wrap=True,
                                overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Icon(ft.Icons.ARROW_FORWARD, size=14,
                                color=ft.Colors.GREEN_400),
                        ft.Text(dst_sub, size=12, font_family=self.font_family,
                                color=ft.Colors.BLUE, no_wrap=True,
                                overflow=ft.TextOverflow.ELLIPSIS),
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.symmetric(vertical=3, horizontal=6),
                    border_radius=4,
                    bgcolor=ft.Colors.GREY_50,
                )
            )

        self.preview_container.visible = True
        self.execute_button.disabled = False
        self.show_status(f"预览完成：共 {len(self.preview_result)} 个文件待分类")
        self.preview_container.update()
        self.execute_button.update()

    # ======================== 执行移动 ========================

    def do_execute(self, e):
        if not self.source_dir or not self.preview_result:
            self.show_status("请先预览分类结果", success=False)
            return

        self.preview_button.disabled = True
        self.execute_button.disabled = True
        self.progress.visible = True
        self.progress.value = 0
        self.show_status("正在移动文件...")
        self.progress.update()
        self.preview_button.update()
        self.execute_button.update()

        threading.Thread(target=self._run_move, daemon=True).start()

    def _run_move(self):
        total = len(self.preview_result)
        success_count = 0
        fail_count = 0

        try:
            for i, (src, dst) in enumerate(self.preview_result):
                dst_dir = os.path.dirname(dst)
                os.makedirs(dst_dir, exist_ok=True)

                # 目标已存在同名文件时追加序号
                if os.path.exists(dst):
                    base, ext = os.path.splitext(dst)
                    counter = 1
                    while os.path.exists(f"{base}({counter}){ext}"):
                        counter += 1
                    dst = f"{base}({counter}){ext}"

                try:
                    shutil.move(src, dst)
                    success_count += 1
                except Exception:
                    fail_count += 1

                self.progress.value = (i + 1) / total
                self.progress.update()

            self.show_status(
                f"移动完成：成功 {success_count} 个"
                + (f"，失败 {fail_count} 个" if fail_count else "")
            )
            self.show_info(
                "完成",
                f"成功移动 {success_count} 个文件"
                + (f"\n失败 {fail_count} 个文件" if fail_count else ""),
            )
        except Exception as err:
            self.show_status(f"移动出错: {err}", success=False)
        finally:
            self.preview_button.disabled = False
            self.execute_button.disabled = True
            self.progress.visible = False
            self.preview_result.clear()
            self.preview_container.visible = False
            self.preview_button.update()
            self.execute_button.update()
            self.progress.update()
            self.preview_container.update()

    # ======================== UI 反馈 ========================

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
    app = FileClassifierApp()
    ft.app(target=app.build)
