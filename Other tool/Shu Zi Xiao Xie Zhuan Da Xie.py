import tkinter as tk
from tkinter import ttk, messagebox
import re

class RMBConverter:
    def __init__(self):
        # 读取字体配置
        try:
            import json
            with open('Core/ziti.json', 'r', encoding='utf-8') as f:
                font_config = json.load(f)
            self.font_family = font_config['family']
        except Exception as e:
            print(f"字体配置读取失败，使用默认字体: {str(e)}")
            self.font_family = ''  # 空字符串表示使用系统默认字体

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
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title('数字小写转大写')
        self.root.geometry('900x600')
        # 设置窗口图标
        try:
            self.root.iconbitmap('Image/icon.ico')
        except Exception as e:
            print(f"图标加载失败: {str(e)}")
        
        # 创建样式
        style = ttk.Style()
        title_font = (self.font_family, 16, 'bold') if self.font_family else ('', 16, 'bold')
        default_font = (self.font_family, 12) if self.font_family else ('', 12)
        style.configure('Title.TLabel', font=title_font)
        style.configure('TLabel', font=default_font)
        style.configure('TEntry', font=default_font)
        style.configure('TButton', font=default_font)
        
        # 创建标题
        title_frame = ttk.Frame(self.root, padding="10")
        title_frame.pack(fill=tk.X)
        ttk.Label(title_frame, text="数字小写转大写Alpha1.0.0", style='Title.TLabel').pack()
        
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
        ttk.Button(btn_frame, text="帮助", command=self.show_help).pack(side=tk.LEFT, padx=5)
        
        # 创建结果显示区域
        result_frame = ttk.Frame(self.root, padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(result_frame, text="转换结果：").pack(anchor=tk.W)
        result_font = (self.font_family, 14) if self.font_family else ('', 14)
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

    def show_help(self):
        """显示帮助信息"""
        help_text = """数字小写转大写工具使用说明：
        
1. 在输入框中输入数字金额（支持小数）
2. 系统会自动实时转换并显示结果
3. 点击"清除"按钮清空输入和结果
4. 点击"复制结果"按钮将转换结果复制到剪贴板
5. 支持范围：整数部分最多21位，小数部分最多7位
提示:
- 作者:叁垣伍瑞肆凶廿捌宿宿
- 联系方式:https://space.bilibili.com/556216088
- 版权:Apache-2.0 License
"""
        messagebox.showinfo("帮助", help_text)

    def run(self):
        """运行程序"""
        self.root.mainloop()

if __name__ == '__main__':
    app = RMBConverter()
    app.run()