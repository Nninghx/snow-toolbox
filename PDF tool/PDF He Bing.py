# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image, ImageTk
import sys

from os.path import dirname, join
sys.path.insert(0, join(dirname(dirname(__file__)), "Tool module"))
from BangZhu import get_help_system

class PDFMergerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF页面合并工具Alpha-1.0.3")
        self.root.geometry("300x500")
         # self.root.minsize(500, 700)
        
        self.input_files = []
        self.selected_pages = {}
        
        # 主布局
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # 文件选择区域
        self.file_frame = tk.LabelFrame(root, text="PDF文件")
        self.file_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        self.file_frame.grid_columnconfigure(0, weight=1)
        
        self.file_listbox = tk.Listbox(self.file_frame, height=5)
        self.file_listbox.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        tk.Button(self.file_frame, text="添加文件", command=self.add_file).grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        tk.Button(self.file_frame, text="移除文件", command=self.remove_file).grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        # 页面预览区域
        self.preview_frame = tk.LabelFrame(root, text="页面预览与选择")
        self.preview_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        self.canvas = tk.Canvas(self.preview_frame)
        self.scrollbar = ttk.Scrollbar(self.preview_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        
        self.preview_frame.grid_rowconfigure(0, weight=1)
        self.preview_frame.grid_columnconfigure(0, weight=1)
        
        # 添加鼠标滚轮支持
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # 操作按钮区域
        self.action_frame = tk.Frame(root)
        self.action_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        self.action_frame.grid_columnconfigure(0, weight=1)
        self.action_frame.grid_columnconfigure(1, weight=1)
        self.action_frame.grid_columnconfigure(2, weight=1)
        
        tk.Button(self.action_frame, text="帮助", command=self.show_help).grid(row=0, column=0, sticky="ew", padx=5)
        tk.Button(self.action_frame, text="更新日志", command=self.show_changelog).grid(row=0, column=1, sticky="ew", padx=5)
        tk.Button(self.action_frame, text="合并PDF", command=self.merge_pdfs).grid(row=0, column=2, sticky="ew", padx=5)
    
    def add_file(self):
        files = filedialog.askopenfilenames(
            title="选择PDF文件",
            filetypes=[("PDF文件", "*.pdf")]
        )
        if files:
            for file in files:
                if file not in self.input_files:
                    self.input_files.append(file)
                    self.file_listbox.insert(tk.END, os.path.basename(file))
                    self.selected_pages[file] = []
            self.show_preview()
    
    def remove_file(self):
        selection = self.file_listbox.curselection()
        if selection:
            file = self.input_files[selection[0]]
            del self.input_files[selection[0]]
            del self.selected_pages[file]
            self.file_listbox.delete(selection[0])
            self.show_preview()
    
    def show_preview(self, force_refresh=False):
        # 仅当不是强制刷新时才清除现有预览
        if not force_refresh:
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
        
        # 显示每个PDF的页面缩略图
        for file in self.input_files:
            try:
                reader = PdfReader(file)
                
                # 查找是否已有该文件的frame
                file_frame = None
                if force_refresh:
                    for widget in self.scrollable_frame.winfo_children():
                        if hasattr(widget, 'file_path') and widget.file_path == file:
                            file_frame = widget
                            break
                
                # 如果没有找到或不是强制刷新，创建新的frame
                if not file_frame or not force_refresh:
                    file_frame = ttk.LabelFrame(self.scrollable_frame, text=os.path.basename(file))
                    file_frame.pack(fill=tk.X, padx=5, pady=5)
                    file_frame.file_path = file
                    
                    # 添加全选和清空选择按钮
                    select_all_frame = ttk.Frame(file_frame)
                    select_all_frame.pack(fill=tk.X)
                    tk.Button(
                        select_all_frame,
                        text="全选",
                        command=lambda f=file, r=reader: self.select_all_pages(f, r)
                    ).pack(side=tk.LEFT, padx=5)
                    tk.Button(
                        select_all_frame,
                        text="清空选择",
                        command=lambda f=file: self.clear_selection(f)
                    ).pack(side=tk.LEFT, padx=5)
                    
                    for i, page in enumerate(reader.pages):
                        page_frame = ttk.Frame(file_frame)
                        page_frame.pack(fill=tk.X)
                        
                        # 显示页码和选择框
                        var = tk.IntVar(value=1 if i in self.selected_pages[file] else 0)
                        cb = tk.Checkbutton(
                            page_frame, 
                            text=f"第 {i+1} 页",
                            variable=var,
                            command=lambda f=file, p=i: self.toggle_page(f, p)
                        )
                        cb.pack(side=tk.LEFT)
                        cb.var = var
                        cb.page = i
                        cb.file = file
                        
                        if i in self.selected_pages[file]:
                            cb.select()
                else:
                    # 强制刷新时，只更新选择状态
                    for widget in file_frame.winfo_children():
                        if isinstance(widget, ttk.Frame):  # 跳过按钮frame
                            for child in widget.winfo_children():
                                if hasattr(child, 'var') and hasattr(child, 'page'):
                                    child.var.set(1 if child.page in self.selected_pages[file] else 0)
            except Exception as e:
                messagebox.showerror("错误", f"无法读取文件 {file}: {str(e)}")
    
    def toggle_page(self, file, page):
        if page in self.selected_pages[file]:
            self.selected_pages[file].remove(page)
        else:
            self.selected_pages[file].append(page)
    
    def select_all_pages(self, file, reader):
        """选择当前文件的所有页面"""
        self.selected_pages[file] = list(range(len(reader.pages)))
        # 强制刷新界面以确保复选框状态更新
        self.show_preview(force_refresh=True)
    
    def clear_selection(self, file):
        """清空当前文件的所有选择"""
        self.selected_pages[file] = []
        self.show_preview()
    
    def show_changelog(self):
        changelog = """PDF页面合并工具 - 更新日志
版本 Alpha1.0.0 (2025-05-18)
- 1.初始版本发布
- 2.基本PDF合并功能
- 3.页面预览与选择功能
版本 Alpha1.0.1 (2025-05-20)
- 1.进行了一些代码优化
版本 Alpha1.0.2 (2025-05-26)
- 1.- 添加更新日志和帮助
版本 Alpha1.0.3 (2025-06-7)
- 1.对帮助文档调用进行拆分，简化代码长度
- 2.禁止生成 .pyc 文件

"""
        messagebox.showinfo("更新日志", changelog)

    def show_help(self):
        help_system = get_help_system()
        help_system.show_help("PDF合并")

    def _on_mousewheel(self, event):
        """处理鼠标滚轮事件,滚动Canvas"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def merge_pdfs(self):
        if not self.input_files:
            messagebox.showwarning("警告", "请先添加PDF文件")
            return
        
        output_file = filedialog.asksaveasfilename(
            title="保存合并后的PDF",
            defaultextension=".pdf",
            filetypes=[("PDF文件", "*.pdf")]
        )
        
        if output_file:
            try:
                writer = PdfWriter()
                for file in self.input_files:
                    reader = PdfReader(file)
                    for page_num in sorted(self.selected_pages[file]):
                        writer.add_page(reader.pages[page_num])
                
                with open(output_file, 'wb') as f:
                    writer.write(f)
                
                messagebox.showinfo("成功", f"PDF合并完成!\n保存到: {output_file}")
            except Exception as e:
                messagebox.showerror("错误", f"合并失败: {str(e)}")

if __name__ == '__main__':
    root = tk.Tk()
    app = PDFMergerApp(root)
    root.mainloop()
