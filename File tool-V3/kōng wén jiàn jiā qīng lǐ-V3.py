# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
from pathlib import Path
import tkinter as tk
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


class EmptyFolderCleaner(PDFToolBase):
    def __init__(self, root):
        super().__init__(root)
        if not root.winfo_exists():
            return
        self.setup_ui()
    
    def setup_ui(self):
        self.root.title("空文件夹清理工具")
        self.root.geometry("400x200")
        
        tk.Label(self.root, text="选择要清理的目录:").pack(pady=10)
        
        self.path_var = tk.StringVar()
        tk.Entry(self.root, textvariable=self.path_var, width=40).pack()
        
        tk.Button(self.root, text="浏览", command=self.browse_directory).pack(pady=5)
        tk.Button(self.root, text="清理空文件夹", command=self.clean_empty_folders).pack(pady=10)
        
        self.apply_font_to_widgets(self._get_all_widgets())
        
    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.path_var.set(directory)
            
    def clean_empty_folders(self):
        target_dir = self.path_var.get()
        if not target_dir:
            messagebox.showerror("错误", "请先选择目录")
            return
            
        try:
            count = self._remove_empty_folders(target_dir)
            messagebox.showinfo("完成", f"已删除 {count} 个空文件夹")
        except Exception as e:
            messagebox.showerror("错误", str(e))
            
    def _remove_empty_folders(self, folder):
        count = 0
        for root, dirs, files in os.walk(folder, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        count += 1
                except Exception:
                    continue
        return count

    def _get_all_widgets(self):
        """获取所有需要应用字体的控件"""
        widgets = []
        for child in self.root.winfo_children():
            widgets.append(child)
            for sub_child in child.winfo_children():
                widgets.append(sub_child)
        return widgets

if __name__ == "__main__":
    root = tk.Tk()
    app = EmptyFolderCleaner(root)
    root.mainloop()