import tkinter as tk
from tkinter import ttk
import json
import os

def to_upper(text):
    """Convert text to uppercase"""
    return text.upper()

def to_lower(text):
    """Convert text to lowercase"""
    return text.lower()

def to_title(text):
    """Convert text to title case (first letter of each word capitalized)"""
    return text.title()

def reverse_case(text):
    """Reverse the case of each character"""
    return text.swapcase()

def create_gui():
    """Create and run the GUI interface"""
    # Load font settings
    try:
        with open('Core/ziti.json', 'r', encoding='utf-8') as f:
            font_data = json.load(f)
        font_family = font_data['family']
    except Exception as e:
        print(f"无法加载字体设置: {e}")
        font_family = "Microsoft YaHei"  # Fallback font
    
    root = tk.Tk()
    root.title("英文大小写转换工具")
    # 设置窗口图标
    try:
        root.iconbitmap('Image/icon.ico')
    except Exception as e:
        print(f"图标加载失败: {str(e)}")
    
    # Set default font
    default_font = (font_family, 10)
    root.option_add('*Font', default_font)
    
    # Configure ttk style
    style = ttk.Style()
    style.configure('TRadiobutton', font=default_font)
    style.configure('TButton', font=default_font)
    
    # Input frame
    input_frame = ttk.Frame(root, padding="10")
    input_frame.pack(fill='x')
    
    ttk.Label(input_frame, text="输入文本:").pack(anchor='w')
    text_input = tk.Text(input_frame, height=5, width=50)
    text_input.pack(fill='x')
    
    # Options frame
    options_frame = ttk.Frame(root, padding="10")
    options_frame.pack(fill='x')
    
    case_var = tk.StringVar(value="upper")
    ttk.Radiobutton(options_frame, text="全部大写", variable=case_var, value="upper").pack(anchor='w')
    ttk.Radiobutton(options_frame, text="全部小写", variable=case_var, value="lower").pack(anchor='w')
    ttk.Radiobutton(options_frame, text="首字母大写", variable=case_var, value="title").pack(anchor='w')
    ttk.Radiobutton(options_frame, text="大小写反转", variable=case_var, value="reverse").pack(anchor='w')
    
    # Output frame
    output_frame = ttk.Frame(root, padding="10")
    output_frame.pack(fill='x')
    
    ttk.Label(output_frame, text="转换结果:").pack(anchor='w')
    text_output = tk.Text(output_frame, height=5, width=50, state='disabled')
    text_output.pack(fill='x')
    
    def convert_text():
        """Handle text conversion"""
        input_text = text_input.get("1.0", tk.END).strip()
        if not input_text:
            return
            
        if case_var.get() == "upper":
            result = to_upper(input_text)
        elif case_var.get() == "lower":
            result = to_lower(input_text)
        elif case_var.get() == "title":
            result = to_title(input_text)
        else:
            result = reverse_case(input_text)
            
        text_output.config(state='normal')
        text_output.delete("1.0", tk.END)
        text_output.insert("1.0", result)
        text_output.config(state='disabled')
    
    # Button frame
    button_frame = ttk.Frame(root, padding="10")
    button_frame.pack(fill='x')
    
    def show_help():
        """Show help information"""
        help_window = tk.Toplevel(root)
        help_window.title("帮助")
        help_text = tk.Text(help_window, height=10, width=50, wrap="word")
        help_text.pack(padx=10, pady=10)
        help_text.insert("1.0", "英文大小写转换工具使用说明：\n\n"
                              "1. 在输入框中输入需要转换的文本\n"
                              "2. 选择转换方式：\n"
                              "   - 全部大写：将文本转为全大写\n"
                              "   - 全部小写：将文本转为全小写\n"
                              "   - 首字母大写：将每个单词首字母大写\n"
                              "   - 大小写反转：反转当前大小写状态\n"
                              "3. 点击'转换'按钮执行转换\n"
                              "4. 结果将显示在下方输出框中")
        help_text.config(state='disabled')
    
    def copy_result():
        """Copy result to clipboard"""
        result = text_output.get("1.0", tk.END).strip()
        if result:
            root.clipboard_clear()
            root.clipboard_append(result)
    
    ttk.Button(button_frame, text="转换", command=convert_text).pack(side='left')
    ttk.Button(button_frame, text="清空", command=lambda: text_input.delete("1.0", tk.END)).pack(side='left')
    ttk.Button(button_frame, text="复制结果", command=copy_result).pack(side='left')
    ttk.Button(button_frame, text="帮助", command=show_help).pack(side='left')
    ttk.Button(button_frame, text="退出", command=root.quit).pack(side='right')
    
    root.mainloop()

if __name__ == '__main__':
    create_gui()