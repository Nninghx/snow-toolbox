# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import os
import ctypes
import subprocess
import threading
import importlib.util
from pathlib import Path

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

        font_family = current_font[0]
        icon_path = str(base._get_project_root() / 'Image' / 'icon.ico')
        return font_family, icon_path
    finally:
        try:
            if root.winfo_exists():
                root.destroy()
        except Exception:
            pass


APP_FONT_FAMILY, APP_ICON_PATH = run_startup_preflight()


CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0


def is_admin():
    """检查是否以管理员权限运行"""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _run_ps(command):
    """执行 PowerShell 命令，返回 (成功, 输出)"""
    try:
        result = subprocess.run(
            ['powershell', '-Command', command],
            capture_output=True,
            text=True,
            creationflags=CREATE_NO_WINDOW,
        )
        return result.returncode == 0, (result.stdout or "") + (result.stderr or "")
    except Exception as e:
        return False, str(e)


def get_memory_compression_status():
    """获取内存压缩状态"""
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             "Get-MMAgent | Select-Object -ExpandProperty MemoryCompression"],
            capture_output=True,
            text=True,
            creationflags=CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return result.stdout.strip().lower() == 'true'
        return None
    except Exception:
        return None


def enable_memory_compression():
    """启用内存压缩"""
    if is_admin():
        return _run_ps("Enable-MMAgent -MemoryCompression")
    ps_script = "Start-Process powershell -ArgumentList '-Command Enable-MMAgent -MemoryCompression' -Verb RunAs -Wait"
    return _run_ps(ps_script)


def disable_memory_compression():
    """禁用内存压缩"""
    if is_admin():
        return _run_ps("Disable-MMAgent -MemoryCompression")
    ps_script = "Start-Process powershell -ArgumentList '-Command Disable-MMAgent -MemoryCompression' -Verb RunAs -Wait"
    return _run_ps(ps_script)


class MemoryCompressionApp:
    """Windows 内存压缩管理 Flet 应用"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.font_family = APP_FONT_FAMILY
        self.is_admin = is_admin()

        page.title = "内存压缩管理工具"
        page.window.width = 640
        page.window.height = 620
        page.window.min_width = 520
        page.window.min_height = 520
        page.padding = 0
        page.bgcolor = ft.Colors.GREY_100
        page.theme = ft.Theme(font_family=self.font_family)

        # 窗口图标由公共基类解析，直接使用
        page.window.icon = APP_ICON_PATH

        self.status_text_value = ft.Text(
            "检测中...",
            size=16,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_GREY_700,
            font_family=self.font_family,
        )

        self.info_text = ft.Text(
            "",
            size=12,
            color=ft.Colors.BLUE_GREY_800,
            font_family=self.font_family,
            selectable=True,
        )

        self.status_text = ft.Text("就绪", size=12, color=ft.Colors.BLUE_GREY_700,
                                    font_family=self.font_family)

        self.btn_enable = ft.ElevatedButton(
            "启用内存压缩",
            icon=ft.Icons.PLAY_ARROW,
            bgcolor=ft.Colors.GREEN_600,
            color=ft.Colors.WHITE,
            on_click=self.on_enable,
            expand=1,
        )
        self.btn_disable = ft.ElevatedButton(
            "禁用内存压缩",
            icon=ft.Icons.STOP,
            bgcolor=ft.Colors.RED_600,
            color=ft.Colors.WHITE,
            on_click=self.on_disable,
            expand=1,
        )
        self.btn_refresh = ft.OutlinedButton(
            "刷新状态",
            icon=ft.Icons.REFRESH,
            on_click=self.on_refresh,
            expand=1,
        )

        self._build_ui()
        # 初始刷新（后台执行，避免阻塞 UI）
        threading.Thread(target=self.refresh_status, daemon=True).start()

    def _make_card(self, title, content):
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

    def _build_ui(self):
        # 标题卡片
        header = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.MEMORY, size=28, color=ft.Colors.BLUE_600),
                    ft.Text("Windows 内存压缩管理",
                             size=18,
                             weight=ft.FontWeight.BOLD,
                             color=ft.Colors.BLUE_GREY_800,
                             font_family=self.font_family),
                ], spacing=8),
                ft.Text(
                    "内存压缩可以将很少使用的内存页面压缩，释放物理 RAM 来改善性能。",
                    size=12,
                    color=ft.Colors.BLUE_GREY_600,
                    font_family=self.font_family,
                ),
            ], spacing=6),
            padding=ft.padding.all(14),
            border_radius=10,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )

        # 权限提示
        admin_hint = None
        if not self.is_admin:
            admin_hint = ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.WARNING_AMBER, size=16, color=ft.Colors.ORANGE_700),
                    ft.Text("提示: 部分操作可能需要管理员权限（将弹出 UAC 授权窗口）",
                             size=12, color=ft.Colors.ORANGE_800,
                             font_family=self.font_family),
                ], spacing=6),
                padding=ft.padding.all(10),
                border_radius=8,
                bgcolor=ft.Colors.ORANGE_50,
                border=ft.border.all(1, ft.Colors.ORANGE_200),
            )

        # 状态卡片
        status_card = self._make_card(
            "当前状态",
            ft.Container(
                content=self.status_text_value,
                padding=ft.padding.all(14),
                border_radius=8,
                bgcolor=ft.Colors.BLUE_GREY_50,
                alignment=ft.alignment.center,
            ),
        )

        # 详细信息卡片
        info_card = self._make_card("详细信息", self.info_text)

        # 按钮行
        button_row = ft.Row([self.btn_enable, self.btn_disable, self.btn_refresh], spacing=8)

        status_bar = ft.Container(
            content=self.status_text,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            bgcolor=ft.Colors.WHITE,
            border=ft.border.only(top=ft.BorderSide(1, ft.Colors.GREY_200)),
        )

        controls = [header]
        if admin_hint is not None:
            controls.append(admin_hint)
        controls.extend([status_card, button_row, info_card])

        self.page.add(
            ft.Container(
                content=ft.Column(controls, spacing=10, scroll=ft.ScrollMode.AUTO, expand=True),
                padding=12,
                expand=True,
            ),
        )
        self.page.add(status_bar)

    def show_status(self, message, success=True):
        self.status_text.value = message
        self.page.snack_bar = ft.SnackBar(
            ft.Text(message, font_family=self.font_family),
            bgcolor=ft.Colors.GREEN if success else ft.Colors.RED,
            open=True,
        )
        self.page.update()

    def refresh_status(self):
        """刷新内存压缩状态（可后台调用）"""
        status = get_memory_compression_status()
        if status is None:
            self.status_text_value.value = "无法获取状态"
            self.status_text_value.color = ft.Colors.GREY_600
            self.info_text.value = "无法获取内存压缩状态。\n请确保以管理员身份运行此程序。"
        elif status:
            self.status_text_value.value = "已启用"
            self.status_text_value.color = ft.Colors.GREEN_700
            self.info_text.value = "内存压缩功能当前已启用。\n这有助于优化内存使用。"
        else:
            self.status_text_value.value = "已禁用"
            self.status_text_value.color = ft.Colors.RED_700
            self.info_text.value = "内存压缩功能当前已禁用。\n启用后可释放更多物理内存。"
        self.page.update()

    def on_refresh(self, e):
        self.show_status("正在刷新状态...", success=True)
        threading.Thread(target=self.refresh_status, daemon=True).start()

    def _run_action(self, action_name, action_func):
        """在后台线程执行启用/禁用操作"""
        def worker():
            try:
                success, output = action_func()
                if success:
                    self.show_status(f"{action_name}成功", success=True)
                else:
                    self.show_status(f"{action_name}失败：{output.strip()[:200]}", success=False)
                self.refresh_status()
            except Exception as ex:
                self.show_status(f"{action_name}失败：{ex}", success=False)

        threading.Thread(target=worker, daemon=True).start()

    def on_enable(self, e):
        self._confirm_and_run("启用内存压缩", enable_memory_compression)

    def on_disable(self, e):
        self._confirm_and_run("禁用内存压缩", disable_memory_compression)

    def _confirm_and_run(self, action_name, action_func):
        """显示确认对话框后执行"""
        def do_close(e):
            self.page.dialog.open = False
            self.page.update()

        def do_confirm(e):
            do_close(e)
            self.show_status(f"正在{action_name}，请稍候...", success=True)
            self._run_action(action_name, action_func)

        msg = f"确定要{action_name}吗？"
        if not self.is_admin:
            msg += "\n\n当前非管理员权限运行，将弹出 UAC 授权窗口。"

        self.page.dialog = ft.AlertDialog(
            title=ft.Text("操作确认", font_family=self.font_family),
            content=ft.Text(msg, font_family=self.font_family),
            actions=[
                ft.TextButton("取消", on_click=do_close),
                ft.ElevatedButton(
                    "确定",
                    bgcolor=ft.Colors.BLUE_600,
                    color=ft.Colors.WHITE,
                    on_click=do_confirm,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog.open = True
        self.page.update()


def main(page: ft.Page):
    MemoryCompressionApp(page)


if __name__ == "__main__":
    ft.app(target=main)
