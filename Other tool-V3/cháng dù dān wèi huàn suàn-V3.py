# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

# 导入公共基类
import importlib.util
_base_spec = importlib.util.spec_from_file_location(
    "public_base_class",
    Path(__file__).resolve().parent.parent / "Core" / "Public base class.py"
)
_base_module = importlib.util.module_from_spec(_base_spec)
_base_spec.loader.exec_module(_base_module)
PDFToolBase = _base_module.PDFToolBase
del _base_spec, _base_module

# 单位字典定义为全局常量
# 单位分类字典
UNIT_CATEGORIES = {
    '公制单位': ['m', 'km', 'dm', 'cm', 'mm', 'μm', 'nm', 'pm', 'fm'],
    '英制单位': ['inch', 'foot', 'yard', 'fath', 'furlong', 'mile'],
    '中国传统单位': ['里', '丈', '尺', '寸', '分', '厘', '毫', '寻', '仞', '步', '常', '跬'],
    '天文单位': ['AU', 'ly', 'pc'],  # 使用简单符号
    '航海单位': ['nmi', 'cable']      # 使用简单符号
}

# 单位显示名称映射
UNIT_DISPLAY_NAMES = {
    'AU': '天文单位',
    'ly': '光年',
    'pc': '秒差距',
    'nmi': '海里',
    'cable': '链'
}

# 单位换算字典，如果换算结果有问题在这里修改
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
    'fath': 1.8288,  # 英寻
    'furlong': 201.168,  # 浪
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

class LengthConverterApp(PDFToolBase):
    def __init__(self, root):
        super().__init__(root)
        if not root.winfo_exists():
            return
        self.root = root
        self.root.title("长度单位换算")
        self.root.minsize(400, 400)

        # 历史记录数据
        self.conversion_history = []

        self._build_ui()

        # 设置权重使控件可伸缩
        self.input_frame.columnconfigure(1, weight=1)
        main_frame = self.root.nametowidget(self.root.winfo_children()[0])
        main_frame.columnconfigure(0, weight=1)

    def _build_ui(self):
        # 使用Frame容器
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 输入区域
        self.input_frame = ttk.LabelFrame(main_frame, text="转换设置", padding=(10, 5))
        self.input_frame.pack(fill=tk.X, pady=5)

        # 数值输入
        ttk.Label(self.input_frame, text="数值:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.entry_value = ttk.Entry(self.input_frame, width=15)
        self.entry_value.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)

        # 小数点位数选择
        ttk.Label(self.input_frame, text="小数位:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.decimal_places = ttk.Spinbox(self.input_frame, from_=0, to=30, width=5)
        self.decimal_places.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        self.decimal_places.set(6)  # 默认6位小数

        # 单位选择
        # 生成单位选择列表
        units = []
        for category, unit_list in UNIT_CATEGORIES.items():
            units.append(f'────── {category} ──────')
            for unit in unit_list:
                if unit in UNIT_DISPLAY_NAMES:
                    display_name = UNIT_DISPLAY_NAMES[unit]
                    units.append(f"{display_name}({unit})")
                else:
                    units.append(f"{unit}({unit})")
            units.append('')

        m_index = units.index("m(m)")

        ttk.Label(self.input_frame, text="从:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.combo_from = ttk.Combobox(self.input_frame, values=units, width=13)
        self.combo_from.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        self.combo_from.current(m_index)

        ttk.Label(self.input_frame, text="到:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.combo_to = ttk.Combobox(self.input_frame, values=units, width=13)
        self.combo_to.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)
        self.combo_to.current(m_index)

        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        convert_btn = ttk.Button(button_frame, text="转换", command=self.convert_and_display)
        convert_btn.pack(side=tk.LEFT, padx=5, ipadx=20, ipady=5)

        # 结果显示区域
        result_frame = ttk.LabelFrame(main_frame, text="转换结果", padding=(10, 5))
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.label_result = ttk.Label(result_frame, text="请先输入要转换的数值", anchor=tk.CENTER)
        self.label_result.pack(fill=tk.BOTH, expand=True)

        # 历史记录区域
        history_frame = ttk.LabelFrame(main_frame, text="历史记录", padding=(10, 5))
        history_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # 历史记录文本框
        self.history_text = tk.Text(history_frame, height=8, state=tk.DISABLED)
        self.history_text.pack(fill=tk.BOTH, expand=True)

        # 历史记录控制按钮
        history_btn_frame = ttk.Frame(history_frame)
        history_btn_frame.pack(fill=tk.X, pady=5)

        clear_history_btn = ttk.Button(history_btn_frame, text="清除历史", command=self.clear_history)
        clear_history_btn.pack(side=tk.LEFT, padx=5)

    def convert_and_display(self):
        try:
            value = float(self.entry_value.get())
            from_display = self.combo_from.get()
            to_display = self.combo_to.get()

            def get_unit(display):
                """从显示文本中提取单位符号"""
                if display.startswith('────'):
                    return None
                if '(' in display:
                    import re
                    match = re.search(r'\(([^)]+)\)', display)
                    if match:
                        return match.group(1)
                return display

            def get_display_name(unit):
                return UNIT_DISPLAY_NAMES.get(unit, unit)

            from_unit = get_unit(from_display)
            to_unit = get_unit(to_display)

            if from_unit is None or to_unit is None:
                self.label_result.config(text="错误: 请选择有效的单位（不要选择分隔行）")
                return
            if from_unit not in UNITS:
                self.label_result.config(text=f"错误: 无效的源单位 '{from_unit}'")
                return
            if to_unit not in UNITS:
                self.label_result.config(text=f"错误: 无效的目标单位 '{to_unit}'")
                return

            try:
                decimal_points = int(self.decimal_places.get())
                if decimal_points < 0:
                    raise ValueError("小数位数不能为负数")
            except ValueError as e:
                if "小数位数不能为负数" in str(e):
                    self.label_result.config(text="错误: 小数位数不能为负数")
                else:
                    self.label_result.config(text="错误: 请输入有效的小数位数")
                return

            result = round(value * UNITS[from_unit] / UNITS[to_unit], decimal_points)
            from_display_name = get_display_name(from_unit)
            to_display_name = get_display_name(to_unit)
            formatted_value = str(value)
            formatted_result = self.format_number(result, decimal_points)
            result_text = (
                f"{formatted_value} {from_unit} [{from_unit}] = "
                f"{formatted_result} {to_unit} [{to_unit}]"
            )
            self.label_result.config(text=result_text)
            self.update_history(value, from_unit, to_unit, result)

        except ValueError as e:
            if str(e):
                self.label_result.config(text=f"错误: {str(e)}")
            else:
                self.label_result.config(text="错误: 请输入有效的数字")
        except ZeroDivisionError:
            self.label_result.config(text="错误: 不能除以零")
        except Exception as e:
            self.label_result.config(text=f"错误: 转换过程中出现问题 - {str(e)}")

    def format_number(self, num, decimal_points):
        """格式化数字，始终使用完整浮点数表示"""
        return f"{num:.{decimal_points}f}"

    def update_history(self, value, from_unit, to_unit, result):
        """更新历史记录"""
        try:
            decimal_points = int(self.decimal_places.get())
        except ValueError:
            decimal_points = 6

        formatted_value = self.format_number(value, decimal_points)
        formatted_result = self.format_number(result, decimal_points)

        entry = f"{formatted_value} {from_unit} → {formatted_result} {to_unit}"
        self.conversion_history.append(entry)
        self.history_text.config(state=tk.NORMAL)
        self.history_text.insert(tk.END, entry + "\n")
        self.history_text.config(state=tk.DISABLED)
        self.history_text.see(tk.END)

    def clear_history(self):
        """清除历史记录"""
        self.conversion_history = []
        self.history_text.config(state=tk.NORMAL)
        self.history_text.delete(1.0, tk.END)
        self.history_text.config(state=tk.DISABLED)


if __name__ == "__main__":
    root = tk.Tk()
    app = LengthConverterApp(root)
    if root.winfo_exists():
        root.mainloop()