# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import re
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


# 单位分类字典
UNIT_CATEGORIES = {
    '公制单位': ['m', 'km', 'dm', 'cm', 'mm', 'μm', 'nm', 'pm', 'fm'],
    '英制单位': ['inch', 'foot', 'yard', 'fath', 'furlong', 'mile'],
    '中国传统单位': ['里', '丈', '尺', '寸', '分', '厘', '毫', '寻', '仞', '步', '常', '跬'],
    '天文单位': ['AU', 'ly', 'pc'],
    '航海单位': ['nmi', 'cable']
}

# 单位显示名称映射
UNIT_DISPLAY_NAMES = {
    'AU': '天文单位',
    'ly': '光年',
    'pc': '秒差距',
    'nmi': '海里',
    'cable': '链'
}

# 单位换算字典（相对米）
UNITS = {
    # 公制单位
    'm': 1,
    'km': 1000,
    'dm': 0.1,
    'cm': 0.01,
    'mm': 0.001,
    'μm': 1e-6,
    'nm': 1e-9,
    'pm': 1e-12,
    'fm': 1e-15,
    # 英制单位
    'inch': 0.0254,
    'foot': 0.3048,
    'yard': 0.9144,
    'fath': 1.8288,
    'furlong': 201.168,
    'mile': 1609.344,
    # 中国传统单位
    '里': 500,
    '丈': 3.3333,
    '尺': 0.3333,
    '寸': 0.0333,
    '分': 0.0033,
    '厘': 0.0003,
    '毫': 0.00003,
    '寻': 1.6,
    '仞': 1.8,
    '步': 1.5,
    '常': 2.4,
    '跬': 0.8,
    # 天文单位
    'AU': 149597870700,
    'ly': 9460730472580800,
    'pc': 30856775814913672.8,
    # 航海单位
    'nmi': 1852,
    'cable': 185.2
}


def build_unit_options():
    """生成带分类的单位下拉选项列表"""
    options = []
    for category, unit_list in UNIT_CATEGORIES.items():
        options.append(f'────── {category} ──────')
        for unit in unit_list:
            display_name = UNIT_DISPLAY_NAMES.get(unit, unit)
            options.append(f"{display_name}({unit})")
        options.append('')
    return options


def get_unit_from_display(display):
    """从显示文本中提取单位符号"""
    if not display or display.startswith('────'):
        return None
    match = re.search(r'\(([^)]+)\)', display)
    if match:
        return match.group(1)
    return display


class LengthConverterApp:
    """长度单位换算 Flet 应用"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.font_family = APP_FONT_FAMILY
        self.conversion_history = []

        page.title = "长度单位换算"
        page.window.width = 780
        page.window.height = 720
        page.window.min_width = 600
        page.window.min_height = 560
        page.padding = 0
        page.bgcolor = ft.Colors.GREY_100
        page.theme = ft.Theme(font_family=self.font_family)

        # 窗口图标由公共基类解析，直接使用
        page.window.icon = APP_ICON_PATH

        unit_options = build_unit_options()
        default_index = unit_options.index("m(m)") if "m(m)" in unit_options else 0

        self.value_field = ft.TextField(
            label="数值",
            hint_text="请输入数值",
            text_size=13,
            content_padding=ft.padding.all(10),
            border_radius=8,
            expand=2,
        )

        self.decimal_field = ft.TextField(
            label="小数位",
            value="6",
            text_size=13,
            content_padding=ft.padding.all(10),
            border_radius=8,
            width=100,
        )

        self.combo_from = ft.Dropdown(
            label="从",
            options=[ft.dropdown.Option(u) for u in unit_options],
            value=unit_options[default_index],
            text_size=13,
            border_radius=8,
            expand=1,
        )

        self.combo_to = ft.Dropdown(
            label="到",
            options=[ft.dropdown.Option(u) for u in unit_options],
            value=unit_options[default_index],
            text_size=13,
            border_radius=8,
            expand=1,
        )

        self.result_text = ft.Text(
            "请先输入要转换的数值",
            size=15,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_GREY_800,
            text_align=ft.TextAlign.CENTER,
            font_family=self.font_family,
        )

        self.history_view = ft.ListView(
            spacing=2,
            height=180,
            padding=ft.padding.all(6),
        )

        self.status_text = ft.Text("就绪", size=12, color=ft.Colors.BLUE_GREY_700,
                                    font_family=self.font_family)

        self._build_ui()

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
        # 输入区
        input_row1 = ft.Row([self.value_field, self.decimal_field], spacing=8)
        input_row2 = ft.Row([self.combo_from, self.combo_to], spacing=8)
        input_card = self._make_card(
            "转换设置",
            ft.Column([input_row1, input_row2], spacing=8),
        )

        # 按钮
        btn_convert = ft.ElevatedButton(
            "转换",
            icon=ft.Icons.SWAP_HORIZ,
            bgcolor=ft.Colors.BLUE_600,
            color=ft.Colors.WHITE,
            on_click=self.on_convert,
        )
        btn_swap = ft.OutlinedButton("交换单位", icon=ft.Icons.SWAP_VERT, on_click=self.on_swap)
        btn_clear_history = ft.OutlinedButton(
            "清除历史", icon=ft.Icons.DELETE_SWEEP, on_click=self.on_clear_history
        )
        button_row = ft.Row([btn_convert, btn_swap, btn_clear_history], spacing=8, wrap=True)

        # 结果
        result_container = ft.Container(
            content=self.result_text,
            padding=ft.padding.all(16),
            border_radius=8,
            bgcolor=ft.Colors.BLUE_GREY_50,
            alignment=ft.alignment.center,
        )
        result_card = self._make_card("转换结果", result_container)

        # 历史
        history_card = self._make_card("历史记录", self.history_view)

        status_bar = ft.Container(
            content=self.status_text,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            bgcolor=ft.Colors.WHITE,
            border=ft.border.only(top=ft.BorderSide(1, ft.Colors.GREY_200)),
        )

        self.page.add(
            ft.Container(
                content=ft.Column(
                    [input_card, button_row, result_card, history_card],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
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

    def format_number(self, num, decimal_points):
        """格式化数字，始终使用完整浮点数表示"""
        try:
            return f"{num:.{decimal_points}f}"
        except Exception:
            return str(num)

    def update_history(self, value, from_unit, to_unit, result, decimal_points):
        """更新历史记录"""
        formatted_value = self.format_number(value, decimal_points)
        formatted_result = self.format_number(result, decimal_points)
        entry = f"{formatted_value} {from_unit} → {formatted_result} {to_unit}"
        self.conversion_history.append(entry)
        self.history_view.controls.append(
            ft.Container(
                content=ft.Text(entry, size=12, font_family=self.font_family,
                                 color=ft.Colors.BLUE_GREY_800),
                padding=ft.padding.symmetric(horizontal=6, vertical=3),
                border_radius=4,
                bgcolor=ft.Colors.GREY_50,
            )
        )

    def on_swap(self, e):
        """交换源和目标单位"""
        from_val = self.combo_from.value
        to_val = self.combo_to.value
        self.combo_from.value = to_val
        self.combo_to.value = from_val
        self.show_status("已交换单位", success=True)

    def on_clear_history(self, e):
        self.conversion_history = []
        self.history_view.controls.clear()
        self.page.update()
        self.show_status("历史记录已清除", success=True)

    def on_convert(self, e):
        try:
            value_str = (self.value_field.value or "").strip()
            if not value_str:
                self.result_text.value = "错误: 请输入数值"
                self.page.update()
                return

            value = float(value_str)
            from_display = self.combo_from.value
            to_display = self.combo_to.value

            from_unit = get_unit_from_display(from_display)
            to_unit = get_unit_from_display(to_display)

            if from_unit is None or to_unit is None:
                self.result_text.value = "错误: 请选择有效的单位（不要选择分隔行）"
                self.page.update()
                return
            if from_unit not in UNITS:
                self.result_text.value = f"错误: 无效的源单位 '{from_unit}'"
                self.page.update()
                return
            if to_unit not in UNITS:
                self.result_text.value = f"错误: 无效的目标单位 '{to_unit}'"
                self.page.update()
                return

            try:
                decimal_points = int((self.decimal_field.value or "6").strip())
                if decimal_points < 0:
                    raise ValueError("小数位数不能为负数")
            except ValueError as ve:
                self.result_text.value = f"错误: {ve}" if str(ve) else "错误: 请输入有效的小数位数"
                self.page.update()
                return

            result = round(value * UNITS[from_unit] / UNITS[to_unit], decimal_points)
            formatted_result = self.format_number(result, decimal_points)
            self.result_text.value = f"{value} {from_unit} = {formatted_result} {to_unit}"
            self.update_history(value, from_unit, to_unit, result, decimal_points)
            self.show_status("转换完成", success=True)

        except ValueError:
            self.result_text.value = "错误: 请输入有效的数字"
            self.page.update()
        except ZeroDivisionError:
            self.result_text.value = "错误: 不能除以零"
            self.page.update()
        except Exception as ex:
            self.result_text.value = f"错误: 转换过程中出现问题 - {ex}"
            self.page.update()


def main(page: ft.Page):
    LengthConverterApp(page)


if __name__ == "__main__":
    ft.app(target=main)
