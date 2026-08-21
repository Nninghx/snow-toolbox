# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
from pathlib import Path
from tkinter import *
from tkinter import filedialog, messagebox

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
class DirTreeGUI(PDFToolBase):
    def __init__(self, root):
        super().__init__(root)
        if not root.winfo_exists():
            return
        
        self.root.title("文件目录树生成器")
        
        # 设置窗口大小并居中显示
        window_width = 800
        window_height = 600
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 定义字体设置
        self.font_family = self.current_font[0]
        self.button_font = (self.font_family, 12)
        self.mono_font = ('Courier New', 10)  # 输出框保持等宽字体
        
        self.create_widgets()
        self.apply_font_to_widgets(self._get_all_widgets())

    def create_widgets(self):
        # 目录选择框架
        dir_frame = Frame(self.root)
        dir_frame.pack(pady=10, padx=10, fill=X)
        self.dir_entry = Entry(dir_frame, font=self.current_font)
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
        license_btn = Button(btn_frame, text="项目开源协议", command=self.show_license, width=10, font=self.button_font)
        license_btn.pack(side=LEFT, padx=5)
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
                f.write("``markmap\n")
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

    def show_license(self):
        """显示开源协议文档"""
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        CORE_DIR = PROJECT_ROOT / "Core"
        license_path = CORE_DIR / "LICENSE.txt"
        
        if not license_path.exists():
            messagebox.showerror("错误", f"找不到开源协议文件：{license_path}")
            return
        
        try:
            with open(license_path, 'r', encoding='utf-8') as f:
                license_content = f.read()
            
            # 创建只读窗口显示协议内容
            license_window = Toplevel(self.root)
            license_window.title("Apache-2.0 License")
            
            # 设置窗口大小
            window_width = 700
            window_height = 500
            screen_width = license_window.winfo_screenwidth()
            screen_height = license_window.winfo_screenheight()
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            license_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
            
            # 创建文本框和滚动条
            text_frame = Frame(license_window)
            text_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
            
            scrollbar = Scrollbar(text_frame)
            scrollbar.pack(side=RIGHT, fill=Y)
            
            text_widget = Text(text_frame, wrap=WORD, yscrollcommand=scrollbar.set, 
                             font=self.current_font, state=NORMAL)
            text_widget.pack(side=LEFT, fill=BOTH, expand=True)
            scrollbar.config(command=text_widget.yview)
            
            # 插入协议内容并设置为只读
            text_widget.insert('1.0', license_content)
            text_widget.config(state=DISABLED)
            
        except Exception as e:
            messagebox.showerror("错误", f"读取开源协议时出错: {str(e)}")

    def _get_all_widgets(self):
        """获取所有需要应用字体的控件"""
        widgets = []
        for child in self.root.winfo_children():
            widgets.append(child)
            for sub_child in child.winfo_children():
                widgets.append(sub_child)
        return widgets

if __name__ == '__main__':
    root = Tk()
    app = DirTreeGUI(root)
    root.mainloop()