# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image, ImageTk
import sys

from os.path import dirname, join
sys.path.insert(0, join(dirname(__file__), "..", "Core"))
from BangZhu import get_help_system

def load_font_settings():
    """
    从ziti.json文件中读取字体设置
    返回字体族名称，如果读取失败则返回None
    """
    try:
        font_path = join(dirname(__file__), "..", "Core", "ziti.json")
        with open(font_path, 'r', encoding='utf-8') as f:
            font_data = json.load(f)
            return font_data.get("family")
    except Exception as e:
        print(f"读取字体设置失败: {str(e)}")
        return None

class PDFMergerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF合并工具")
        self.root.geometry("600x400")
        
        # 加载字体设置
        self.font_family = load_font_settings() or "TkDefaultFont"
        self.default_font = (self.font_family, 10)
        
        # 配置默认字体
        self.configure_fonts()
        
        self.input_files = []
        self.selected_pages = {}
        
        # 配置样式
        style = ttk.Style()
        style.configure("Treeview", font=self.default_font, rowheight=25)
        style.configure("Treeview.Heading", font=(self.font_family, 10, "bold"))
    
    def configure_fonts(self):
        """配置应用程序中使用的字体"""
        try:
            font_config = {"font": self.default_font}
            self.root.option_add("*Font", self.default_font)
            style = ttk.Style()
            style.configure("TLabel", font=self.default_font)
            style.configure("TButton", font=self.default_font)
            style.configure("TCheckbutton", font=self.default_font)
            style.configure("TLabelframe", font=self.default_font)
            style.configure("TLabelframe.Label", font=self.default_font)
        except Exception as e:
            print(f"配置字体失败: {str(e)}")
        
        # 主布局
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # 文件表格区域
        self.file_frame = ttk.Frame(self.root)
        self.file_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.file_frame.grid_columnconfigure(0, weight=1)
        
        # 创建文件表格
        self.file_tree = ttk.Treeview(
            self.file_frame,
            columns=("order", "name", "pages"),
            show="headings",
            selectmode="browse"
        )
        
        # 设置列标题
        self.file_tree.heading("order", text="合并顺序")
        self.file_tree.heading("name", text="文件名")
        self.file_tree.heading("pages", text="页数")
        
        # 设置列宽
        self.file_tree.column("order", width=80, anchor="center")
        self.file_tree.column("name", width=300, anchor="w")
        self.file_tree.column("pages", width=80, anchor="center")
        
        self.file_tree.grid(row=0, column=0, sticky="nsew")
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.file_frame, orient="vertical", command=self.file_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.file_tree.configure(yscrollcommand=scrollbar.set)
        
        # 配置主窗口网格权重
        self.root.grid_rowconfigure(1, weight=0)
        
        # 底部按钮区域
        self.bottom_frame = ttk.Frame(self.root)
        self.bottom_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        # 添加文件按钮
        add_btn = ttk.Button(
            self.bottom_frame, 
            text="添加文件", 
            command=self.add_file
        )
        add_btn.pack(side=tk.LEFT, padx=5)
        
        # 合并文件按钮
        merge_btn = ttk.Button(
            self.bottom_frame,
            text="合并文件",
            command=self.merge_pdfs
        )
        merge_btn.pack(side=tk.LEFT, padx=5)
        
        # 清空列表链接
        clear_link = tk.Label(
            self.bottom_frame,
            text="清空列表",
            fg="gray",
            cursor="hand2",
            font=(self.font_family, 9)
        )
        clear_link.pack(side=tk.RIGHT, padx=5)
        clear_link.bind("<Button-1>", lambda e: self.clear_all_files())
        
        # 帮助按钮
        help_btn = ttk.Button(
            self.bottom_frame,
            text="帮助",
            command=self.show_help
        )
        help_btn.pack(side=tk.RIGHT, padx=5)
        
    
    def clear_all_files(self):
        """清空所有文件"""
        if self.input_files:
            if messagebox.askyesno("确认", "确定要清空文件列表吗？"):
                self.input_files.clear()
                self.selected_pages.clear()
                self.file_tree.delete(*self.file_tree.get_children())
                self.show_preview()
    
    def add_file(self):
        files = filedialog.askopenfilenames(title="选择PDF文件", filetypes=[("PDF文件", "*.pdf")])
        if files:
            for file in files:
                if file not in self.input_files:
                    self.input_files.append(file)
                    try:
                        reader = PdfReader(file)
                        page_count = len(reader.pages)
                        # 添加文件到表格
                        self.file_tree.insert("", "end", values=(
                            len(self.input_files),
                            os.path.basename(file),
                            page_count
                        ))
                        self.selected_pages[file] = []
                    except Exception as e:
                        messagebox.showerror("错误", f"无法读取文件 {file}: {str(e)}")
    
    def remove_file(self, file_index=None):
        if file_index is None:
            selection = self.file_tree.selection()
            if selection:
                file_index = self.file_tree.index(selection[0])
        
        if file_index is not None and 0 <= file_index < len(self.input_files):
            file = self.input_files[file_index]
            del self.input_files[file_index]
            del self.selected_pages[file]
            self.file_tree.delete(self.file_tree.get_children()[file_index])
            # 更新剩余文件的序号
            for i, child in enumerate(self.file_tree.get_children()):
                values = list(self.file_tree.item(child, "values"))
                values[0] = i + 1
                self.file_tree.item(child, values=values)
    
    def toggle_page(self, file, page):
        if page in self.selected_pages[file]:
            self.selected_pages[file].remove(page)
        else:
            self.selected_pages[file].append(page)
    
    def select_all_pages(self, file, reader):
        """选择当前文件的所有页面"""
        self.selected_pages[file] = list(range(len(reader.pages)))
    
    def clear_selection(self, file):
        """清空当前文件的所有选择"""
        self.selected_pages[file] = []
    
    def show_help(self):
        help_system = get_help_system()
        help_system.show_help("PDF合并")


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
    # 设置窗口图标
    try:
        root.iconbitmap('Image/icon.ico')
    except Exception as e:
        print(f"图标加载失败: {str(e)}")
    app = PDFMergerApp(root)
    root.mainloop()