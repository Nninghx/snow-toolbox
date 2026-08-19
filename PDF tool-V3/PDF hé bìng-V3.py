# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PyPDF2 import PdfReader, PdfWriter

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


class PDFMergerApp(PDFToolBase):
    def __init__(self, root):
        super().__init__(root)
        if not root.winfo_exists():
            return
        
        self.root.title("PDF合并工具")
        self.root.geometry("600x400")
        self.build_ui()

    def build_ui(self):
        """构建用户界面"""
        self.input_files = []
        self.selected_pages = {}
        
        # 配置样式
        style = ttk.Style()
        style.configure("Treeview", font=self.current_font, rowheight=25)
        style.configure("Treeview.Heading", font=(self.current_font[0], 10, "bold"))
    
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
            font=(self.current_font[0], 9)
        )
        clear_link.pack(side=tk.RIGHT, padx=5)
        clear_link.bind("<Button-1>", lambda e: self.clear_all_files())
        
    
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
                        self.selected_pages[file] = list(range(len(reader.pages)))
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