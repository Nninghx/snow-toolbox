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


class EnglishCaseConverterApp(PDFToolBase):
    def __init__(self, root):
        super().__init__(root)
        if not root.winfo_exists():
            return
        self.root = root
        self.root.title("英文大小写转换")
        self._build_ui()

    def _build_ui(self):
        """Create and run the GUI interface"""
        # Input frame
        input_frame = ttk.Frame(self.root, padding="10")
        input_frame.pack(fill='x')

        ttk.Label(input_frame, text="输入文本:").pack(anchor='w')
        self.text_input = tk.Text(input_frame, height=5, width=50)
        self.text_input.pack(fill='x')

        # Options frame
        options_frame = ttk.Frame(self.root, padding="10")
        options_frame.pack(fill='x')

        self.case_var = tk.StringVar(value="upper")
        ttk.Radiobutton(options_frame, text="全部大写", variable=self.case_var, value="upper").pack(anchor='w')
        ttk.Radiobutton(options_frame, text="全部小写", variable=self.case_var, value="lower").pack(anchor='w')
        ttk.Radiobutton(options_frame, text="首字母大写", variable=self.case_var, value="title").pack(anchor='w')
        ttk.Radiobutton(options_frame, text="大小写反转", variable=self.case_var, value="reverse").pack(anchor='w')

        # Output frame
        output_frame = ttk.Frame(self.root, padding="10")
        output_frame.pack(fill='x')

        ttk.Label(output_frame, text="转换结果:").pack(anchor='w')
        self.text_output = tk.Text(output_frame, height=5, width=50, state='disabled')
        self.text_output.pack(fill='x')

        # Button frame
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.pack(fill='x')

        ttk.Button(button_frame, text="转换", command=self.convert_text).pack(side='left')
        ttk.Button(button_frame, text="清空", command=lambda: self.text_input.delete("1.0", tk.END)).pack(side='left')
        ttk.Button(button_frame, text="复制结果", command=self.copy_result).pack(side='left')
        ttk.Button(button_frame, text="退出", command=self.root.quit).pack(side='right')

    def convert_text(self):
        """Handle text conversion"""
        input_text = self.text_input.get("1.0", tk.END).strip()
        if not input_text:
            return

        if self.case_var.get() == "upper":
            result = to_upper(input_text)
        elif self.case_var.get() == "lower":
            result = to_lower(input_text)
        elif self.case_var.get() == "title":
            result = to_title(input_text)
        else:
            result = reverse_case(input_text)

        self.text_output.config(state='normal')
        self.text_output.delete("1.0", tk.END)
        self.text_output.insert("1.0", result)
        self.text_output.config(state='disabled')

    def copy_result(self):
        """Copy result to clipboard"""
        result = self.text_output.get("1.0", tk.END).strip()
        if result:
            self.root.clipboard_clear()
            self.root.clipboard_append(result)


if __name__ == '__main__':
    root = tk.Tk()
    app = EnglishCaseConverterApp(root)
    if root.winfo_exists():
        root.mainloop()