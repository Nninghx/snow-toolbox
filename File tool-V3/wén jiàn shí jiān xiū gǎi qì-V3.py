# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import os
import time
import random
import subprocess
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


class TimeModifierApp:
    def __init__(self):
        self.page = None
        self.target_path = None
        self.font_family = APP_FONT_FAMILY
        self._busy = False

    def build(self, page: ft.Page):
        self.page = page
        page.title = "文件时间修改器"
        page.window.width = 680
        page.window.height = 700
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

        # 目标选择卡片
        self.path_text = ft.Text(
            "未选择目标",
            size=13,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
            expand=True,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        target_card = self._make_card(
            "选择目标",
            ft.Row(
                [
                    ft.Icon(ft.Icons.INSERT_DRIVE_FILE, size=18, color=ft.Colors.BLUE_GREY_400),
                    self.path_text,
                    ft.ElevatedButton("文件", icon=ft.Icons.INSERT_DRIVE_FILE, on_click=self.browse_file, height=36),
                    ft.ElevatedButton("文件夹", icon=ft.Icons.FOLDER, on_click=self.browse_folder, height=36),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
        )

        # 时间设置卡片
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.create_time_field = ft.TextField(
            label="创建时间",
            value=now_str,
            width=200,
            border_radius=8,
            content_padding=ft.padding.all(10),
            text_size=14,
            text_style=ft.TextStyle(font_family=self.font_family),
        )
        self.modify_time_field = ft.TextField(
            label="修改时间",
            value=now_str,
            width=200,
            border_radius=8,
            content_padding=ft.padding.all(10),
            text_size=14,
            text_style=ft.TextStyle(font_family=self.font_family),
        )
        self.access_time_field = ft.TextField(
            label="访问时间",
            value=now_str,
            width=200,
            border_radius=8,
            content_padding=ft.padding.all(10),
            text_size=14,
            text_style=ft.TextStyle(font_family=self.font_family),
        )
        time_card = self._make_card(
            "时间设置 (格式: YYYY-MM-DD HH:MM:SS)",
            ft.Column(
                [
                    ft.Row(
                        [
                            self.create_time_field,
                            ft.ElevatedButton("现在", on_click=lambda e: self.set_now(self.create_time_field), height=32),
                            ft.ElevatedButton("随机", on_click=lambda e: self.set_random(self.create_time_field), height=32),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        [
                            self.modify_time_field,
                            ft.ElevatedButton("现在", on_click=lambda e: self.set_now(self.modify_time_field), height=32),
                            ft.ElevatedButton("随机", on_click=lambda e: self.set_random(self.modify_time_field), height=32),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        [
                            self.access_time_field,
                            ft.ElevatedButton("现在", on_click=lambda e: self.set_now(self.access_time_field), height=32),
                            ft.ElevatedButton("随机", on_click=lambda e: self.set_random(self.access_time_field), height=32),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=10,
            ),
        )

        # 选项卡片
        self.recursive_check = ft.Checkbox(
            label="递归处理子文件夹",
            label_style=ft.TextStyle(font_family=self.font_family, size=14),
        )
        self.apply_create_check = ft.Checkbox(
            value=True,
            label="应用创建时间",
            label_style=ft.TextStyle(font_family=self.font_family, size=14),
        )
        self.apply_modify_check = ft.Checkbox(
            value=True,
            label="应用修改时间",
            label_style=ft.TextStyle(font_family=self.font_family, size=14),
        )
        self.apply_access_check = ft.Checkbox(
            value=True,
            label="应用访问时间",
            label_style=ft.TextStyle(font_family=self.font_family, size=14),
        )
        options_card = self._make_card(
            "选项",
            ft.Row(
                [self.recursive_check, self.apply_create_check, self.apply_modify_check, self.apply_access_check],
                spacing=16,
                wrap=True,
            ),
        )

        # 操作按钮与进度条
        self.start_button = ft.ElevatedButton(
            "开始修改",
            icon=ft.Icons.SCHEDULE,
            on_click=self.start_modification,
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

        # 状态栏
        self.status_text = ft.Text("就绪", size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)
        self.stats_text = ft.Text(size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)

        page.add(
            ft.Row(
                [
                    ft.Icon(ft.Icons.SCHEDULE, size=32, color=ft.Colors.BLUE),
                    ft.Text("文件时间修改器", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            ft.Divider(thickness=1, opacity=0.3),
            target_card,
            time_card,
            options_card,
            ft.Row(
                [self.progress, self.stats_text],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            ft.Row([self.start_button], alignment=ft.MainAxisAlignment.END),
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

    def browse_file(self, e):
        self.file_picker.pick_files(dialog_title="选择文件", allow_multiple=False)

    def on_file_picked(self, e):
        if not e.files:
            return
        self.target_path = e.files[0].path
        self.path_text.value = os.path.basename(self.target_path)
        self.path_text.color = ft.Colors.BLUE_GREY_900
        self.page.update()

    def browse_folder(self, e):
        self.dir_picker.get_directory_path(dialog_title="选择文件夹")

    def on_dir_picked(self, e):
        if not e.path:
            return
        self.target_path = e.path
        self.path_text.value = e.path
        self.path_text.color = ft.Colors.BLUE_GREY_900
        self.page.update()

    def set_now(self, field):
        """设置字段为当前时间。"""
        field.value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        field.update()

    def set_random(self, field):
        """设置字段为随机时间（前后一年内）。"""
        offset = random.randint(-31536000, 31536000)
        random_time = datetime.fromtimestamp(time.time() + offset)
        field.value = random_time.strftime("%Y-%m-%d %H:%M:%S")
        field.update()

    def _validate_time(self, time_str):
        """验证时间格式。"""
        try:
            datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            return True
        except ValueError:
            return False

    def _parse_time(self, time_str):
        """解析时间字符串为时间戳。"""
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return dt.timestamp()

    def start_modification(self, e):
        if self._busy:
            return

        if not self.target_path or not os.path.exists(self.target_path):
            self.show_status("请先选择有效的文件或文件夹", success=False)
            return

        # 验证时间格式
        if self.apply_create_check.value:
            if not self._validate_time(self.create_time_field.value):
                self.show_status("创建时间格式不正确，请使用 YYYY-MM-DD HH:MM:SS", success=False)
                return
        if self.apply_modify_check.value:
            if not self._validate_time(self.modify_time_field.value):
                self.show_status("修改时间格式不正确，请使用 YYYY-MM-DD HH:MM:SS", success=False)
                return
        if self.apply_access_check.value:
            if not self._validate_time(self.access_time_field.value):
                self.show_status("访问时间格式不正确，请使用 YYYY-MM-DD HH:MM:SS", success=False)
                return

        create_time = self._parse_time(self.create_time_field.value) if self.apply_create_check.value else None
        modify_time = self._parse_time(self.modify_time_field.value) if self.apply_modify_check.value else None
        access_time = self._parse_time(self.access_time_field.value) if self.apply_access_check.value else None

        self._busy = True
        self.start_button.disabled = True
        self.progress.visible = True
        self.progress.value = 0.5
        self.show_status("正在处理...")

        threading.Thread(
            target=self._execute_modification,
            args=(self.target_path, create_time, modify_time, access_time),
            daemon=True,
        ).start()

    def _execute_modification(self, path, create_time, modify_time, access_time):
        """执行文件时间修改。"""
        try:
            results = self._process_files(path, create_time, modify_time, access_time)
            self.progress.value = 1
            self.progress.update()
            msg = f"完成 - 成功: {results['success']}, 失败: {results['failed']}"
            self.stats_text.value = msg
            self.stats_text.update()
            self.show_status(msg)
            if results['failed'] == 0:
                self.show_info("完成", f"所有 {results['success']} 个项目已成功修改！")
            else:
                self.show_info("完成", f"处理完成！\n成功: {results['success']}\n失败: {results['failed']}")
        except Exception as err:
            self.show_status(f"处理失败: {err}", success=False)
        finally:
            self._busy = False
            self.start_button.disabled = False
            self.progress.visible = False
            self.start_button.update()
            self.progress.update()

    def _process_files(self, path, create_time, modify_time, access_time):
        """处理文件或文件夹。"""
        results = {"success": 0, "failed": 0}

        if os.path.isfile(path):
            ok, _ = self._modify_single(path, create_time, modify_time, access_time)
            results["success" if ok else "failed"] += 1
        elif os.path.isdir(path):
            if self.recursive_check.value:
                for root, dirs, files in os.walk(path):
                    for name in files:
                        file_path = os.path.join(root, name)
                        ok, _ = self._modify_single(file_path, create_time, modify_time, access_time)
                        results["success" if ok else "failed"] += 1
                    # 也修改文件夹本身
                    ok, _ = self._modify_single(root, create_time, modify_time, access_time)
                    results["success" if ok else "failed"] += 1
            else:
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    if os.path.isfile(item_path):
                        ok, _ = self._modify_single(item_path, create_time, modify_time, access_time)
                        results["success" if ok else "failed"] += 1
        return results

    def _modify_single(self, file_path, create_time, modify_time, access_time):
        """修改单个文件/文件夹的时间属性。"""
        try:
            # 修改访问和修改时间
            if access_time is not None or modify_time is not None:
                stat = os.stat(file_path)
                atime = access_time if access_time is not None else stat.st_atime
                mtime = modify_time if modify_time is not None else stat.st_mtime
                os.utime(file_path, (atime, mtime))

            # Windows 创建时间通过 PowerShell 修改
            if create_time is not None:
                create_str = datetime.fromtimestamp(create_time).strftime("%Y-%m-%dT%H:%M:%S")
                cmd = (
                    f'powershell -Command "(Get-Item \'{file_path}\').CreationTime=\'{create_str}\'"'
                )
                subprocess.run(
                    cmd, shell=True, capture_output=True, text=True,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            return True, "成功"
        except Exception as e:
            return False, str(e)

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
    app = TimeModifierApp()
    ft.app(target=app.build)
