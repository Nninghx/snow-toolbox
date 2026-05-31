import os
import sys
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from fontTools.ttLib import TTFont
import re


def set_window_icon(root):
    """设置应用程序窗口图标"""
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    IMAGE_DIR = PROJECT_ROOT / "Image"
    
    icon_ico_path = IMAGE_DIR / "icon.ico"
    icon_png_path = IMAGE_DIR / "icon.png"

    # Windows系统设置应用ID
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.RMBConverter")
        except Exception:
            pass

    # 尝试设置ICO图标
    if icon_ico_path.exists():
        try:
            root.iconbitmap(default=str(icon_ico_path))
        except Exception:
            try:
                root.iconbitmap(str(icon_ico_path))
            except Exception:
                pass

    # 尝试设置PNG图标
    if hasattr(root, "iconphoto") and icon_png_path.exists():
        try:
            icon_image = tk.PhotoImage(file=str(icon_png_path))
            root.iconphoto(True, icon_image)
            # 保存引用防止垃圾回收
            root._icon_image = icon_image
        except Exception:
            pass


def check_license():
    """检查开源协议文档是否存在并验证完整性"""
    # 如果通过主程序启动（环境变量已设置），则跳过授权验证
    if os.environ.get('MAIN_APP_AUTHORIZED') == '1':
        return True
    
    try:
        # 验证授权
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        CORE_DIR = PROJECT_ROOT / "Core"
        license_exe_path = CORE_DIR / "LICENSE.exe"
        if license_exe_path.exists():
            result = subprocess.run(
                [str(license_exe_path), '--quiet'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
    except Exception as e:
        print(f"许可证验证异常: {e}")
        return False


def load_font():
    """从配置文件加载字体设置"""
    # 定义项目根目录和图片目录
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    IMAGE_DIR = PROJECT_ROOT / "Image"
    
    font_path = IMAGE_DIR / "AlibabaPuHuiTi-3-55-RegularL3.ttf"
    
    if not font_path.exists():
        messagebox.showerror("错误", f"找不到字体文件：{font_path}")
        return None
    
    # 使用 fonttools 获取字体名称
    tt = TTFont(str(font_path))
    font_name = None
    for record in tt['name'].names:
        if record.nameID == 1:  # Font Family
            font_name = record.toUnicode()
            break
    if not font_name:
        raise RuntimeError(f"无法从字体文件获取字体名称：{font_path}")
    tt.close()
    
    # 使用 Windows API 注册字体
    if os.name == 'nt':
        import ctypes
        GDI32 = ctypes.windll.gdi32
        font_path_str = str(font_path).encode('utf-16-le') + b'\x00'
        GDI32.AddFontResourceW(font_path_str)
        print(f"成功加载自定义字体: {font_path}")
    
    from tkinter import font as tkfont
    current_font = (font_name, 10)
    return current_font


class RMBConverter:
    def __init__(self, root):
        self.root = root
        
        # 加载字体
        try:
            self.current_font = load_font()
            if not self.current_font:
                self.current_font = ("", 10)
        except Exception as e:
            print(f"字体加载失败: {e}")
            self.current_font = ("", 10)

        # 数字到中文大写的映射
        self.num_map = {
            '0': '零', '1': '壹', '2': '贰', '3': '叁', '4': '肆',
            '5': '伍', '6': '陆', '7': '柒', '8': '捌', '9': '玖'
        }
        
        # 整数部分的单位
        self.int_units = ['', '拾', '佰', '仟']
        
        # 大单位，从个位开始，每4位一个大单位
        self.big_units = ['', '万', '亿', '兆', '京', '垓']
        
        # 小数部分的单位
        self.decimal_units = ['角', '分', '厘', '毫', '丝', '忽', '微']
        
        self.setup_gui()

    def setup_gui(self):
        self.root.title('数字小写转大写')
        self.root.geometry('900x600')
        
        # 创建样式
        style = ttk.Style()
        title_font = (self.current_font[0], 16, 'bold')
        default_font = self.current_font
        style.configure('Title.TLabel', font=title_font)
        style.configure('TLabel', font=default_font)
        style.configure('TEntry', font=default_font)
        style.configure('TButton', font=default_font)
        
        # 创建标题
        title_frame = ttk.Frame(self.root, padding="10")
        title_frame.pack(fill=tk.X)
        ttk.Label(title_frame, text="数字小写转大写", style='Title.TLabel').pack()
        
        # 创建说明文字
        desc_frame = ttk.Frame(self.root, padding="10")
        desc_frame.pack(fill=tk.X)
        desc_text = "支持范围：整数部分最多21位（到垓），小数部分最多7位（到微）"
        ttk.Label(desc_frame, text=desc_text, wraplength=800).pack()
        
        # 创建输入框和标签
        input_frame = ttk.Frame(self.root, padding="10")
        input_frame.pack(fill=tk.X)
        
        ttk.Label(input_frame, text="请输入金额：").pack(side=tk.LEFT)
        self.input_var = tk.StringVar()
        self.input_var.trace_add('write', self.on_input_change)
        self.entry = ttk.Entry(input_frame, textvariable=self.input_var, width=60)
        self.entry.pack(side=tk.LEFT, padx=5)
        
        # 创建按钮
        btn_frame = ttk.Frame(self.root, padding="10")
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="清除", command=self.clear_input).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="复制结果", command=self.copy_result).pack(side=tk.LEFT, padx=5)
        
        # 创建结果显示区域
        result_frame = ttk.Frame(self.root, padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(result_frame, text="转换结果：").pack(anchor=tk.W)
        result_font = (self.current_font[0], 14)
        self.result_text = tk.Text(result_frame, font=result_font, wrap=tk.WORD, height=12)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)


    def validate_input(self, num_str):
        """验证输入是否有效"""
        # 检查是否为空
        if not num_str:
            return None
            
        # 使用正则表达式检查格式
        pattern = r'^\d{1,30}(\.\d{1,7})?$'
        if not re.match(pattern, num_str):
            return "请输入正确的数字格式（小数点后最多7位）"
            
        # 检查整数部分是否超过21位
        parts = num_str.split('.')
        int_part = parts[0].lstrip('0')
        if len(int_part) > 21:
            return "整数部分超过21位，请输入更小的数字"
            
        return None  # 验证通过

    def convert_integer_part(self, int_str):
        """转换整数部分"""
        # 去除前导零
        int_str = int_str.lstrip('0')
        if not int_str:
            return '零'
            
        # 确保数字不超过21位
        if len(int_str) > 21:
            int_str = int_str[-21:]
            
        # 从右到左每4位分成一组
        groups = []
        length = len(int_str)
        for i in range(0, length, 4):
            start = max(0, length - i - 4)
            end = length - i
            groups.insert(0, int_str[start:end])  # 插入到开头保持顺序
            
        result = []
        for i, group in enumerate(groups):
            # 跳过全为0的组，但保留最后一组（个位）如果它是0
            if group == '0' * len(group) and i < len(groups)-1:
                # 如果后面还有非零组，添加一个"零"
                if any(g != '0' * len(g) for g in groups[i+1:]):
                    if not (result and result[-1] == '零'):
                        result.append('零')
                continue
                
            # 处理每一组内的数字，确保完整转换"X仟X佰X拾X"形式
            group_result = []
            has_zero = False
            last_non_zero = None
            
            for j, digit in enumerate(group):
                unit_index = len(group) - j - 1
                
                if digit == '0':
                    has_zero = True
                else:
                    # 如果前面有零且不是组的开始，添加一个"零"
                    if has_zero and group_result:
                        group_result.append('零')
                    
                    # 添加数字和单位
                    group_result.append(self.num_map[digit])
                    if unit_index > 0:  # 不是个位数才加单位
                        group_result.append(self.int_units[unit_index])
                    
                    last_non_zero = digit
                    has_zero = False
                    
            # 处理末尾的零
            if has_zero and last_non_zero is not None:
                group_result.append('零')
            
            # 如果这组有内容，添加大单位（万、亿等）
            if group_result:
                result.extend(group_result)
                # 计算大单位索引，从右到左依次是万、亿、兆...
                big_unit_index = len(groups) - i - 1
                if big_unit_index < len(self.big_units):
                    result.append(self.big_units[big_unit_index])
        
        return ''.join(result) if result else '零'

    def convert_decimal_part(self, decimal_str):
        """转换小数部分"""
        result = []
        # 确保小数部分不超过7位，不足的补0
        decimal_str = (decimal_str + '0' * 7)[:7]
        
        last_non_zero = -1
        # 找到最后一个非零数字的位置
        for i in range(len(decimal_str)-1, -1, -1):
            if decimal_str[i] != '0':
                last_non_zero = i
                break
        
        # 只处理到最后一个非零数字
        for i, digit in enumerate(decimal_str[:last_non_zero + 1]):
            if digit != '0':
                result.append(self.num_map[digit])
                result.append(self.decimal_units[i])
            elif result and result[-1] not in self.decimal_units:
                # 如果前面有数字且不是以单位结尾，添加"零"
                result.append('零')
                
        return ''.join(result)

    def convert(self, num_str):
        """转换数字为中文大写"""
        try:
            # 分离整数和小数部分
            parts = num_str.split('.')
            integer_part = parts[0]
            decimal_part = parts[1] if len(parts) > 1 else ''
            
            # 转换整数和小数部分
            result = []
            int_result = self.convert_integer_part(integer_part)
            if int_result:
                result.append(int_result)
                result.append('元')
            
            dec_result = self.convert_decimal_part(decimal_part)
            if dec_result:
                result.append(dec_result)
            elif int_result:
                result.append('整')
                
            return ''.join(result)
        except Exception as e:
            return f'转换错误：{str(e)}'

    def on_input_change(self, *args):
        """输入变化时的处理函数"""
        input_text = self.input_var.get().strip()
        self.result_text.delete('1.0', tk.END)
        
        if not input_text:
            return
            
        error_msg = self.validate_input(input_text)
        if error_msg is None:
            try:
                result = self.convert(input_text)
                self.result_text.insert('1.0', result)
            except Exception as e:
                self.result_text.insert('1.0', f'转换出错：{str(e)}')
        else:
            self.result_text.insert('1.0', error_msg)

    def clear_input(self):
        """清除输入和结果"""
        self.input_var.set('')
        self.result_text.delete('1.0', tk.END)

    def copy_result(self):
        """复制结果到剪贴板"""
        result = self.result_text.get('1.0', tk.END).strip()
        if result:
            self.root.clipboard_clear()
            self.root.clipboard_append(result)
            messagebox.showinfo('提示', '结果已复制到剪贴板')

    def run(self):
        """运行程序"""
        self.root.mainloop()

if __name__ == '__main__':
    # 创建主窗口
    root = tk.Tk()

    # 首先检查开源协议文档是否存在并验证完整性
    if not check_license():
        messagebox.showerror(
            "错误", 
            "缺少授权！无法使用！请先获取授权！\n"
        )
        root.destroy()
        sys.exit(1)

    # 设置窗口图标
    set_window_icon(root)

    # 加载并注册字体
    try:
        custom_font = load_font()
        if custom_font:
            root.option_add('*Font', custom_font)
            print(f"成功设置字体: {custom_font[0]}")
    except Exception as e:
        error_msg = f"字体设置失败: {str(e)}"
        print(error_msg)
        messagebox.showwarning("字体设置", error_msg)

    app = RMBConverter(root)
    root.mainloop()