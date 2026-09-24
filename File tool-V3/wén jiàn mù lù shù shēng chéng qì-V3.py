# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import os
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

        return current_font[0]
    except Exception as exc:
        if root.winfo_exists():
            root.destroy()
        raise RuntimeError(f"启动前置检查失败：无法使用项目自带字体。{exc}") from exc
    finally:
        if root.winfo_exists():
            root.destroy()


APP_FONT_FAMILY = run_startup_preflight()


def generate_dir_tree(path='.', ignore=None, prefix=''):
    """递归生成目录树文本。"""
    if ignore is None:
        ignore = ['.git', '__pycache__', '.DS_Store']
    try:
        items = sorted(os.listdir(path))
    except PermissionError:
        return f"无法访问 {path}：权限不足\n"
    result = ""
    for i, item in enumerate(items):
        if item in ignore:
            continue
        full_path = os.path.join(path, item)
        is_last = i == len(items) - 1
        result += prefix + ('└── ' if is_last else '├── ') + item + '\n'
        if os.path.isdir(full_path):
            new_prefix = prefix + ('    ' if is_last else '│   ')
            result += generate_dir_tree(full_path, ignore, new_prefix)
    return result


class DirTreeApp:
    def __init__(self):
        self.page = None
        self.font_family = APP_FONT_FAMILY
        self._tree_result = ""
        self._current_dir = ""

    def build(self, page: ft.Page):
        self.page = page
        page.title = "文件目录树生成器"
        page.window.width = 800
        page.window.height = 620
        page.window.center()
        page.padding = 16
        page.theme_mode = ft.ThemeMode.LIGHT

        # 设置窗口图标
        icon_path = get_project_root() / 'Image' / 'icon.ico'
        if icon_path.exists():
            page.window.icon = str(icon_path)

        # 文件选择器
        self.dir_picker = ft.FilePicker(on_result=self.on_dir_picked)
        self.save_txt_picker = ft.FilePicker(on_result=self.on_save_txt_picked)
        self.save_md_picker = ft.FilePicker(on_result=self.on_save_md_picked)
        page.overlay.extend([self.dir_picker, self.save_txt_picker, self.save_md_picker])

        # 目录选择卡片
        self.dir_text = ft.Text(
            "未选择目录",
            size=13,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
            expand=True,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        dir_card = self._make_card(
            "选择目录",
            ft.Row(
                [
                    ft.Icon(ft.Icons.ACCOUNT_TREE, size=18, color=ft.Colors.BLUE_GREY_400),
                    self.dir_text,
                    ft.ElevatedButton("浏览", icon=ft.Icons.FOLDER_OPEN, on_click=self.browse_directory),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
        )

        # 操作按钮卡片
        self.generate_btn = ft.ElevatedButton(
            "生成目录树", icon=ft.Icons.CHEVRON_RIGHT, on_click=self.generate_tree, height=36,
        )
        self.save_txt_btn = ft.TextButton("保存文本", icon=ft.Icons.SAVE, on_click=self.save_result)
        self.save_md_btn = ft.TextButton("导出思维导图", icon=ft.Icons.MAP, on_click=self.save_mindmap)
        self.clear_btn = ft.TextButton("清空", icon=ft.Icons.CLEAR_ALL, on_click=self.clear_output)
        btn_card = self._make_card(
            "操作",
            ft.Row(
                [self.generate_btn, self.save_txt_btn, self.save_md_btn, self.clear_btn],
                spacing=8,
                wrap=True,
            ),
        )

        # 输出区域
        self.output_field = ft.TextField(
            multiline=True,
            read_only=True,
            min_lines=12,
            max_lines=20,
            border_radius=8,
            text_size=12,
            text_style=ft.TextStyle(font_family="Consolas", size=12),
            content_padding=ft.padding.all(10),
        )
        output_card = self._make_card("目录树输出", self.output_field)

        # 状态栏
        self.status_text = ft.Text("就绪", size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)

        page.add(
            ft.Row(
                [
                    ft.Icon(ft.Icons.ACCOUNT_TREE, size=32, color=ft.Colors.BLUE),
                    ft.Text("文件目录树生成器", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            ft.Divider(thickness=1, opacity=0.3),
            dir_card,
            btn_card,
            output_card,
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

    def browse_directory(self, e):
        self.dir_picker.get_directory_path(dialog_title="选择目录")

    def on_dir_picked(self, e):
        if not e.path:
            return
        self._current_dir = e.path
        self.dir_text.value = e.path
        self.dir_text.color = ft.Colors.BLUE_GREY_900
        self.page.update()

    def generate_tree(self, e):
        if not self._current_dir or not os.path.isdir(self._current_dir):
            self.show_status("请先选择有效的目录", success=False)
            return

        ignore_list = ['.git', '__pycache__', '.DS_Store', '.venv', 'node_modules']
        result = generate_dir_tree(self._current_dir, ignore=ignore_list)
        header = f"目录结构（忽略: {', '.join(ignore_list)}）:\n\n"
        self._tree_result = header + result
        self.output_field.value = self._tree_result
        self.output_field.update()
        self.show_status("目录树生成完成")

    def on_save_txt_picked(self, e):
        if not e.path:
            return
        try:
            with open(e.path, 'w', encoding='utf-8') as f:
                f.write(self._tree_result)
            self.show_status("文本已保存")
            self.show_info("成功", f"结果已保存到:\n{e.path}")
        except Exception as err:
            self.show_status(f"保存失败: {err}", success=False)

    def save_result(self, e):
        if not self._tree_result.strip():
            self.show_status("没有可保存的内容", success=False)
            return
        self.save_txt_picker.save_file(
            dialog_title="保存目录树",
            file_name="目录树.txt",
            allowed_extensions=["txt"],
        )

    def on_save_md_picked(self, e):
        if not e.path:
            return
        try:
            with open(e.path, 'w', encoding='utf-8') as f:
                f.write("# 目录结构思维导图\n\n")
                f.write("```markmap\n")
                f.write("{\n")
                f.write(f'  "text": "{os.path.basename(self._current_dir)}",\n')
                f.write('  "children": [\n')
                self._write_mindmap_items(self._current_dir, f, 1)
                f.write("  ]\n")
                f.write("}\n")
                f.write("```\n")
            self.show_status("思维导图已保存")
            self.show_info("成功", f"思维导图已保存到:\n{e.path}")
        except Exception as err:
            self.show_status(f"保存失败: {err}", success=False)

    def save_mindmap(self, e):
        if not self._current_dir or not os.path.isdir(self._current_dir):
            self.show_status("请先选择有效目录并生成目录树", success=False)
            return
        self.save_md_picker.save_file(
            dialog_title="导出思维导图",
            file_name="目录结构.md",
            allowed_extensions=["md"],
        )

    def _write_mindmap_items(self, path, file, depth):
        """递归写入 markmap JSON 节点。"""
        try:
            items = sorted(os.listdir(path))
        except PermissionError:
            return
        for i, item in enumerate(items):
            full_path = os.path.join(path, item)
            is_last = i == len(items) - 1
            indent = "    " * depth
            file.write(indent + '{\n')
            file.write(indent + f'  "text": "{item}",\n')
            if os.path.isdir(full_path):
                file.write(indent + '  "children": [\n')
                self._write_mindmap_items(full_path, file, depth + 1)
                file.write(indent + '  ]\n')
            file.write(indent + '}' + ('' if is_last else ',') + '\n')

    def clear_output(self, e):
        self._tree_result = ""
        self.output_field.value = ""
        self.output_field.update()
        self.show_status("已清空")

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
    app = DirTreeApp()
    ft.app(target=app.build)
