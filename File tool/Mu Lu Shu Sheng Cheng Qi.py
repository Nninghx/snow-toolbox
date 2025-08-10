# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import json
from pathlib import Path
from tkinter import *
from tkinter import filedialog, messagebox
import os

from os.path import dirname, join
sys.path.insert(0, join(dirname(__file__), "..", "Core"))
from BangZhu import get_help_system


def load_font_family():
    try:
        # 获取当前文件的目录，然后找到Core/ziti.json
        current_dir = Path(__file__).parent
        font_path = current_dir.parent / "Core" / "ziti.json"
        with open(font_path, 'r', encoding='utf-8') as f:
            font_data = json.load(f)
        return font_data.get('family', 'Arial')  # 默认使用Arial
    except Exception as e:
        print(f"加载字体配置出错: {e}")
        return 'Arial'  # 出错时使用默认字体

from os.path import dirname, join
sys.path.insert(0, join(dirname(dirname(__file__)), "Tool module"))
from BangZhu import get_help_system

def generate_dir_tree(path='.', ignore=None, prefix=''):
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
        # 添加当前项到结果
        result += prefix + ('└── ' if is_last else '├── ') + item + '\n'
        # 如果是目录，递归处理
        if os.path.isdir(full_path):
            new_prefix = prefix + ('    ' if is_last else '│   ')
            result += generate_dir_tree(full_path, ignore, new_prefix)
    return result
class DirTreeGUI:
    def __init__(self, root):
        self.root = root
        self.font_family = load_font_family()  # 加载字体配置
        self.root.title("目录树生成器")
        
        # 设置窗口图标
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "..", "Image", "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"加载图标失败: {e}")
        
        # 设置窗口大小并居中显示
        window_width = 800
        window_height = 600
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        # 定义字体设置
        self.base_font = (self.font_family, 12)
        self.button_font = (self.font_family, 12)
        self.mono_font = ('Courier New', 10)  # 输出框保持等宽字体
        self.create_widgets()
    def create_widgets(self):
        # 目录选择框架
        dir_frame = Frame(self.root)
        dir_frame.pack(pady=10, padx=10, fill=X)
        self.dir_entry = Entry(dir_frame, font=self.base_font)
        self.dir_entry.pack(side=LEFT, expand=True, fill=X)
        browse_btn = Button(dir_frame, text="浏览", command=self.browse_directory, width=8, font=self.button_font)
        browse_btn.pack(side=LEFT, padx=5)
        # 按钮框架
        btn_frame = Frame(self.root)
        btn_frame.pack(pady=10)
        generate_btn = Button(btn_frame, text="生成目录树", command=self.generate_tree, width=15, font=self.button_font)
        generate_btn.pack(side=LEFT, padx=5)
        save_btn = Button(btn_frame, text="保存文本", command=self.save_result, width=10, font=self.button_font)
        save_btn.pack(side=LEFT, padx=5)
        save_mindmap_btn = Button(btn_frame, text="导出思维导图", command=self.save_mindmap, width=12, font=self.button_font)
        save_mindmap_btn.pack(side=LEFT, padx=5)
        clear_btn = Button(btn_frame, text="清空", command=self.clear_output, width=10, font=self.button_font)
        clear_btn.pack(side=LEFT, padx=5)
        help_btn = Button(btn_frame, text="帮助", command=self.show_help, width=8, font=self.button_font)
        help_btn.pack(side=LEFT, padx=5)
        # 输出框架
        output_frame = Frame(self.root)
        output_frame.pack(pady=10, padx=10, fill=BOTH, expand=True)
        # 创建带滚动条的文本框
        output_scrollbar = Scrollbar(output_frame)
        output_scrollbar.pack(side=RIGHT, fill=Y)
        self.output_text = Text(output_frame, wrap=NONE, yscrollcommand=output_scrollbar.set, font=self.mono_font)
        self.output_text.pack(side=LEFT, fill=BOTH, expand=True)
        output_scrollbar.config(command=self.output_text.yview)
    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_entry.delete(0, END)
            self.dir_entry.insert(0, directory)
    def generate_tree(self):
        directory = self.dir_entry.get()
        if not os.path.isdir(directory):
            self.output_text.delete('1.0', END)
            self.output_text.insert(END, "请输入有效的目录路径")
            return
        self.output_text.delete('1.0', END)
        ignore_list = ['.git', '__pycache__', '.DS_Store']
        result = generate_dir_tree(directory, ignore=ignore_list)
        self.output_text.insert(END, f"目录结构（忽略: {', '.join(ignore_list)}）:\n\n")
        self.output_text.insert(END, result)
    def save_result(self):
        result = self.output_text.get('1.0', END)
        if not result.strip():
            messagebox.showwarning("警告", "没有可保存的内容")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", ".txt"), ("所有文件", ".*")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(result)
                messagebox.showinfo("成功", "结果已保存")
            except Exception as e:
                messagebox.showerror("错误", f"保存文件时出错: {str(e)}")

    def save_mindmap(self):
        directory = self.dir_entry.get()
        if not os.path.isdir(directory):
            messagebox.showwarning("警告", "请先选择有效目录并生成目录树")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown文件", ".md"), ("所有文件", ".*")]
        )
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("# 目录结构思维导图\n\n")
                f.write("```markmap\n")
                f.write("{\n")
                f.write('  "text": "' + os.path.basename(directory) + '",\n')
                f.write('  "children": [\n')
                self._write_mindmap_items(directory, f, 1)
                f.write("  ]\n")
                f.write("}\n")
                f.write("```\n")
            messagebox.showinfo("成功", "思维导图文件已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存思维导图时出错: {str(e)}")

    def _write_mindmap_items(self, path, file, depth):
        items = sorted(os.listdir(path))
        for i, item in enumerate(items):
            full_path = os.path.join(path, item)
            is_last = i == len(items) - 1
            
            indent = "    " * depth
            file.write(indent + '{\n')
            file.write(indent + '  "text": "' + item + '",\n')
            
            if os.path.isdir(full_path):
                file.write(indent + '  "children": [\n')
                self._write_mindmap_items(full_path, file, depth + 1)
                file.write(indent + '  ]\n')
            
            file.write(indent + '}' + ('' if is_last else ',') + '\n')
    def clear_output(self):
        self.output_text.delete('1.0', END)
        self.dir_entry.delete(0, END)
    def show_help(self):
        help_system = get_help_system()
        help_system.show_help("目录树生成器")
        
if __name__ == '__main__':
    root = Tk()
    app = DirTreeGUI(root)
    root.mainloop()