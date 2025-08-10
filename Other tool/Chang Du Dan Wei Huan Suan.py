import tkinter as tk
from tkinter import ttk, messagebox

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

def length_converter(value, from_unit, to_unit):
    """长度单位换算函数"""
    try:
        result = value * UNITS[from_unit] / UNITS[to_unit]
        return round(result, 6)
    except KeyError as e:
        raise ValueError(f"无效的单位: {str(e)}")
    except Exception as e:
        raise ValueError(f"转换错误: {str(e)}")

def convert_and_display():
    try:
        value = float(entry_value.get())
        from_display = combo_from.get()
        to_display = combo_to.get()
        
        def get_unit(display):
            """从显示文本中提取单位符号"""
            if display.startswith('────'):
                return None  # 分隔行不参与转换
            if '(' in display:
                import re
                match = re.search(r'\(([^)]+)\)', display)
                if match:
                    return match.group(1)
            return display
        
        def get_display_name(unit):
            """获取单位的显示名称"""
            return UNIT_DISPLAY_NAMES.get(unit, unit)
            
        from_unit = get_unit(from_display)
        to_unit = get_unit(to_display)
        
        # 输入验证
        if from_unit is None or to_unit is None:
            label_result.config(text="错误: 请选择有效的单位（不要选择分隔行）")
            return
            
        if from_unit not in UNITS:
            label_result.config(text=f"错误: 无效的源单位 '{from_unit}'")
            return
            
        if to_unit not in UNITS:
            label_result.config(text=f"错误: 无效的目标单位 '{to_unit}'")
            return
            
        # 获取用户选择的小数位数
        try:
            decimal_points = int(decimal_places.get())
            if decimal_points < 0:
                raise ValueError("小数位数不能为负数")
        except ValueError as e:
            if "小数位数不能为负数" in str(e):
                label_result.config(text="错误: 小数位数不能为负数")
            else:
                label_result.config(text="错误: 请输入有效的小数位数")
            return
            
        # 执行转换
        result = round(value * UNITS[from_unit] / UNITS[to_unit], decimal_points)
        
        # 使用友好的显示名称
        from_display_name = get_display_name(from_unit)
        to_display_name = get_display_name(to_unit)
        
        # 格式化结果显示，输入值保持原样，只对结果应用精度处理
        formatted_value = str(value)  # 保持输入值原样
        formatted_result = format_number(result, decimal_points)
        
        result_text = (
            f"{formatted_value} {from_unit} [{from_unit}] = "
            f"{formatted_result} {to_unit} [{to_unit}]"
        )
        label_result.config(text=result_text)
        
        # 更新历史记录
        update_history(value, from_unit, to_unit, result)
        
    except ValueError as e:
        if str(e):
            label_result.config(text=f"错误: {str(e)}")
        else:
            label_result.config(text="错误: 请输入有效的数字")
    except ZeroDivisionError:
        label_result.config(text="错误: 不能除以零")
    except Exception as e:
        label_result.config(text=f"错误: 转换过程中出现问题 - {str(e)}")

# 创建主窗口
root = tk.Tk()
root.title("长度单位换算")
root.minsize(400, 400)  # 增大窗口尺寸以容纳历史记录
# 设置窗口图标
try:
    root.iconbitmap('Image/icon.ico')
except Exception as e:
    print(f"图标加载失败: {str(e)}")

# 设置字体
try:
    import json
    import os
    from tkinter import font
    
    # 检查字体文件是否存在
    font_path = 'Core/ziti.json'
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"字体配置文件 {font_path} 不存在")
    
    # 读取字体配置(使用UTF-8编码)
    with open(font_path, encoding='utf-8') as f:
        font_config = json.load(f)
    
    font_name = font_config.get('family', 'System')
    
    # 验证字体是否可用
    available_fonts = list(font.families())
    if font_name not in available_fonts:
        raise ValueError(f"字体 '{font_name}' 未安装在系统中")
    
    # 设置字体
    custom_font = (font_name, 10)
    root.option_add('*Font', custom_font)
    print(f"成功设置字体: {font_name}")
except Exception as e:
    error_msg = f"字体设置失败: {str(e)}\n可用字体: {', '.join(font.families()[:5])}..."
    print(error_msg)
    messagebox.showwarning("字体设置", error_msg)

# 使用Frame容器
main_frame = ttk.Frame(root, padding="10")
main_frame.pack(fill=tk.BOTH, expand=True)

# 输入区域
input_frame = ttk.LabelFrame(main_frame, text="转换设置", padding=(10, 5))
input_frame.pack(fill=tk.X, pady=5)

# 数值输入
ttk.Label(input_frame, text="数值:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
entry_value = ttk.Entry(input_frame, width=15)
entry_value.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)

# 小数点位数选择
ttk.Label(input_frame, text="小数位:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
decimal_places = ttk.Spinbox(input_frame, from_=0, to=30, width=5)
decimal_places.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
decimal_places.set(6)  # 默认6位小数

# 单位选择
# 生成单位选择列表
units = []
for category, unit_list in UNIT_CATEGORIES.items():
    units.append(f'────── {category} ──────')
    for unit in unit_list:
        if unit in UNIT_DISPLAY_NAMES:
            # 使用显示名称映射的单位
            display_name = UNIT_DISPLAY_NAMES[unit]
            units.append(f"{display_name}({unit})")
        else:
            # 普通单位，使用单位符号作为显示名称
            units.append(f"{unit}({unit})")
    units.append('')

# 计算"m"在units列表中的位置
m_index = units.index("m(m)")

ttk.Label(input_frame, text="从:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
combo_from = ttk.Combobox(input_frame, values=units, width=13)
combo_from.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
combo_from.current(m_index)

ttk.Label(input_frame, text="到:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
combo_to = ttk.Combobox(input_frame, values=units, width=13)
combo_to.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)
combo_to.current(m_index)

# 按钮区域
button_frame = ttk.Frame(main_frame)
button_frame.pack(fill=tk.X, pady=10)
convert_btn = ttk.Button(button_frame, text="转换", command=convert_and_display)
convert_btn.pack(side=tk.LEFT, padx=5, ipadx=20, ipady=5)

help_btn = ttk.Button(button_frame, text="帮助", command=lambda: show_help())
help_btn.pack(side=tk.LEFT, padx=5, ipadx=20, ipady=5)

# 结果显示区域
result_frame = ttk.LabelFrame(main_frame, text="转换结果", padding=(10, 5))
result_frame.pack(fill=tk.BOTH, expand=True, pady=5)
label_result = ttk.Label(result_frame, text="请先输入要转换的数值", anchor=tk.CENTER)
label_result.pack(fill=tk.BOTH, expand=True)

# 历史记录区域
history_frame = ttk.LabelFrame(main_frame, text="历史记录", padding=(10, 5))
history_frame.pack(fill=tk.BOTH, expand=True, pady=5)

# 历史记录文本框
history_text = tk.Text(history_frame, height=8, state=tk.DISABLED)
history_text.pack(fill=tk.BOTH, expand=True)

# 历史记录控制按钮
history_btn_frame = ttk.Frame(history_frame)
history_btn_frame.pack(fill=tk.X, pady=5)

clear_history_btn = ttk.Button(history_btn_frame, text="清除历史", command=lambda: clear_history())
clear_history_btn.pack(side=tk.LEFT, padx=5)

# 历史记录数据
conversion_history = []

def format_number(num, decimal_points):
    """格式化数字，始终使用完整浮点数表示"""
    return f"{num:.{decimal_points}f}"

def update_history(value, from_unit, to_unit, result):
    """更新历史记录"""
    # 使用与显示相同的小数位数
    try:
        decimal_points = int(decimal_places.get())
    except ValueError:
        decimal_points = 6  # 默认值
    
    # 使用相同的格式化逻辑
    formatted_value = format_number(value, decimal_points)
    formatted_result = format_number(result, decimal_points)
    
    entry = f"{formatted_value} {from_unit} → {formatted_result} {to_unit}"
    conversion_history.append(entry)
    history_text.config(state=tk.NORMAL)
    history_text.insert(tk.END, entry + "\n")
    history_text.config(state=tk.DISABLED)
    history_text.see(tk.END)

def show_help():
    """显示帮助信息"""
    help_text = """
    长度单位换算工具使用说明
    
    1. 在数值框中输入要转换的数值
    2. 从下拉列表中选择源单位和目标单位
    3. 设置结果的小数位数
    4. 点击"转换"按钮获取结果
    
    注意：
    - 单位名称后括号内的是单位符号
    - 分隔线表示单位分类
    - 历史记录会自动保存

    提示:
- 作者:叁垣伍瑞肆凶廿捌宿宿
- 联系方式:https://space.bilibili.com/556216088
- 版权:Apache-2.0 License

    """
    messagebox.showinfo("帮助", help_text)

def clear_history():
    """清除历史记录"""
    global conversion_history
    conversion_history = []
    history_text.config(state=tk.NORMAL)
    history_text.delete(1.0, tk.END)
    history_text.config(state=tk.DISABLED)

# 设置权重使控件可伸缩
input_frame.columnconfigure(1, weight=1)
main_frame.columnconfigure(0, weight=1)

root.mainloop()