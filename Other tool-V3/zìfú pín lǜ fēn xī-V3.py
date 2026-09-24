# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import re
import importlib.util
from pathlib import Path
from collections import Counter

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


class CharacterFrequencyApp:
    """字符频率分析 Flet 应用"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.font_family = APP_FONT_FAMILY

        page.title = "字符频率分析"
        page.window.width = 900
        page.window.height = 780
        page.window.min_width = 720
        page.window.min_height = 600
        page.padding = 0
        page.bgcolor = ft.Colors.GREY_100
        page.theme = ft.Theme(font_family=self.font_family)

        # 窗口图标由公共基类解析，直接使用
        page.window.icon = APP_ICON_PATH

        # 当前分析结果
        self.current_hanzi = []
        self.current_letter = []
        self.current_digit = []

        # 文件选择器
        self.file_picker = ft.FilePicker(on_result=self.on_file_picked)
        self.save_picker = ft.FilePicker(on_result=self.on_save_path_picked)
        page.overlay.extend([self.file_picker, self.save_picker])

        # 文本输入
        self.text_input = ft.TextField(
            label="输入文本或选择文件",
            multiline=True,
            min_lines=8,
            max_lines=12,
            text_size=13,
            content_padding=ft.padding.all(10),
            border_radius=8,
        )

        # 统计选项
        self.hanzi_check = ft.Checkbox(label="统计汉字", value=True)
        self.letter_check = ft.Checkbox(label="统计字母", value=True)
        self.digit_check = ft.Checkbox(label="统计数字", value=True)

        # 结果 DataTables
        self.hanzi_table = self._build_result_table("汉字")
        self.letter_table = self._build_result_table("字母")
        self.digit_table = self._build_result_table("数字")

        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=200,
            expand=True,
            tabs=[
                ft.Tab(text="汉字频率", content=self._wrap_table(self.hanzi_table)),
                ft.Tab(text="字母频率", content=self._wrap_table(self.letter_table)),
                ft.Tab(text="数字频率", content=self._wrap_table(self.digit_table)),
            ],
        )

        self.status_text = ft.Text("就绪", size=12, color=ft.Colors.BLUE_GREY_700,
                                    font_family=self.font_family)

        self._build_ui()

    def _build_result_table(self, char_label):
        """构建结果表格"""
        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text(char_label, size=13, weight=ft.FontWeight.BOLD,
                                       font_family=self.font_family)),
                ft.DataColumn(ft.Text("出现次数", size=13, weight=ft.FontWeight.BOLD,
                                       font_family=self.font_family), numeric=True),
            ],
            rows=[],
            column_spacing=24,
            heading_row_height=36,
            data_row_min_height=30,
            data_row_max_height=34,
            border=ft.border.all(1, ft.Colors.GREY_200),
            border_radius=6,
            expand=True,
        )

    def _wrap_table(self, table):
        return ft.Container(
            content=ft.Column([table], scroll=ft.ScrollMode.AUTO, expand=True),
            padding=ft.padding.all(8),
            expand=True,
        )

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
        option_row = ft.Row(
            [self.hanzi_check, self.letter_check, self.digit_check],
            spacing=16,
        )

        input_card = self._make_card(
            "文本输入",
            ft.Column([self.text_input, option_row], spacing=8),
        )

        btn_analyze = ft.ElevatedButton(
            "分析频率",
            icon=ft.Icons.ANALYTICS,
            bgcolor=ft.Colors.BLUE_600,
            color=ft.Colors.WHITE,
            on_click=self.on_analyze,
        )
        btn_load = ft.OutlinedButton("加载文件", icon=ft.Icons.FOLDER_OPEN,
                                       on_click=lambda e: self.file_picker.pick_files(
                                           allow_multiple=False,
                                           allowed_extensions=["txt", "md", "log", "csv", "json"]
                                       ))
        btn_export = ft.OutlinedButton("导出当前表格", icon=ft.Icons.DOWNLOAD,
                                         on_click=self.on_export)
        button_row = ft.Row([btn_analyze, btn_load, btn_export], spacing=8, wrap=True)

        result_card = ft.Container(
            content=ft.Column([
                ft.Text("分析结果", size=13, weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_GREY_700, font_family=self.font_family),
                self.tabs,
            ], spacing=8, expand=True),
            padding=ft.padding.all(12),
            border_radius=10,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
            expand=True,
        )

        status_bar = ft.Container(
            content=self.status_text,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            bgcolor=ft.Colors.WHITE,
            border=ft.border.only(top=ft.BorderSide(1, ft.Colors.GREY_200)),
        )

        self.page.add(
            ft.Container(
                content=ft.Column(
                    [input_card, button_row, result_card],
                    spacing=10,
                    expand=True,
                ),
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

    def on_file_picked(self, e: ft.FilePickerResultEvent):
        if not e.files:
            return
        file_path = e.files[0].path
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.text_input.value = content
            self.page.update()
            self.show_status(f"已加载文件：{Path(file_path).name}", success=True)
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="gbk") as f:
                    content = f.read()
                self.text_input.value = content
                self.page.update()
                self.show_status(f"已加载文件（GBK）：{Path(file_path).name}", success=True)
            except Exception as ex:
                self.show_status(f"读取文件失败：{ex}", success=False)
        except Exception as ex:
            self.show_status(f"读取文件失败：{ex}", success=False)

    def on_analyze(self, e):
        text = self.text_input.value or ""
        if not text.strip():
            self.show_status("请先输入文本或加载文件", success=False)
            return

        self.current_hanzi = []
        self.current_letter = []
        self.current_digit = []

        if self.hanzi_check.value:
            hanzi_list = re.compile(r'[\u4e00-\u9fff]').findall(text)
            self.current_hanzi = sorted(Counter(hanzi_list).items(),
                                          key=lambda x: x[1], reverse=True)
            self._fill_table(self.hanzi_table, self.current_hanzi)

        if self.letter_check.value:
            letter_list = re.compile(r'[a-zA-Z]').findall(text)
            self.current_letter = sorted(Counter(letter_list).items(),
                                            key=lambda x: x[1], reverse=True)
            self._fill_table(self.letter_table, self.current_letter)

        if self.digit_check.value:
            digit_list = re.compile(r'[0-9]').findall(text)
            self.current_digit = sorted(Counter(digit_list).items(),
                                           key=lambda x: x[1], reverse=True)
            self._fill_table(self.digit_table, self.current_digit)

        total = len(self.current_hanzi) + len(self.current_letter) + len(self.current_digit)
        self.show_status(f"分析完成，共 {total} 条唯一字符", success=True)

    def _fill_table(self, table, data):
        """填充 DataTable"""
        table.rows.clear()
        for char, count in data:
            table.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(char, size=13, font_family=self.font_family)),
                    ft.DataCell(ft.Text(str(count), size=13, font_family=self.font_family)),
                ])
            )

    def on_export(self, e):
        """导出当前显示的标签页数据为 CSV"""
        tab_index = self.tabs.selected_index
        if tab_index == 0:
            data = self.current_hanzi
            header = "汉字,出现次数"
            default_name = "hanzi_frequency.csv"
        elif tab_index == 1:
            data = self.current_letter
            header = "字母,出现次数"
            default_name = "letter_frequency.csv"
        else:
            data = self.current_digit
            header = "数字,出现次数"
            default_name = "digit_frequency.csv"

        if not data:
            self.show_status("当前没有可导出的数据，请先执行分析", success=False)
            return

        self._pending_export = (header, data)
        self.save_picker.save_file(
            dialog_title="导出频率数据",
            file_name=default_name,
            allowed_extensions=["csv"],
        )

    def on_save_path_picked(self, e: ft.FilePickerResultEvent):
        if not e.path:
            return
        try:
            header, data = self._pending_export
            with open(e.path, "w", encoding="utf-8-sig", newline="") as f:
                f.write(header + "\n")
                for char, count in data:
                    f.write(f"{char},{count}\n")
            self.show_status(f"数据已导出到：{e.path}", success=True)
        except Exception as ex:
            self.show_status(f"导出失败：{ex}", success=False)


def main(page: ft.Page):
    CharacterFrequencyApp(page)


if __name__ == "__main__":
    ft.app(target=main)
