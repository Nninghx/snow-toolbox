# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PyPDF2 import PdfReader, PdfWriter
import sys
import os.path

from os.path import dirname, join
sys.path.insert(0, join(dirname(dirname(__file__)), "Tool module"))
from BangZhu import get_help_system

class PDFSplitterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF拆分工具Alpha-1.0.3")
        self.root.geometry("400x300")
        self.input_file = None
        self.output_dir = None
        # 主布局
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        # 文件选择区域
        self.file_frame = tk.LabelFrame(root, text="PDF文件")
        self.file_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        self.file_label = tk.Label(self.file_frame, text="未选择文件")
        self.file_label.pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(self.file_frame, text="选择文件", command=self.select_file).pack(side=tk.RIGHT, padx=5)
        # 输出目录区域
        self.output_frame = tk.LabelFrame(root, text="输出目录")
        self.output_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        self.output_label = tk.Label(self.output_frame, text="未选择目录")
        self.output_label.pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(self.output_frame, text="选择目录", command=self.select_output_dir).pack(side=tk.RIGHT, padx=5)
        # 拆分选项区域
        self.option_frame = tk.LabelFrame(root, text="拆分选项")
        self.option_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        # 拆分模式选择
        self.mode_var = tk.StringVar(value="page_count")
        tk.Radiobutton(
            self.option_frame, 
            text="按页数拆分", 
            variable=self.mode_var, 
            value="page_count"
        ).grid(row=0, column=0, sticky="w", padx=5)
        tk.Radiobutton(
            self.option_frame, 
            text="按范围拆分", 
            variable=self.mode_var, 
            value="page_range"
        ).grid(row=1, column=0, sticky="w", padx=5)
        # 按页数拆分选项
        self.page_count_frame = tk.Frame(self.option_frame)
        self.page_count_frame.grid(row=0, column=1, sticky="w")
        tk.Label(self.page_count_frame, text="每份页数:").pack(side=tk.LEFT)
        self.page_entry = tk.Entry(self.page_count_frame, width=10)
        self.page_entry.pack(side=tk.LEFT)
        self.page_entry.insert(0, "1")
        # 按范围拆分选项
        self.page_range_frame = tk.Frame(self.option_frame)
        self.page_range_frame.grid(row=1, column=1, sticky="w")
        tk.Label(self.page_range_frame, text="页码范围(如1-3,5,7-9):").pack(side=tk.LEFT)
        self.range_entry = tk.Entry(self.page_range_frame, width=20)
        self.range_entry.pack(side=tk.LEFT)
        # 操作按钮区域
        self.action_frame = tk.Frame(root)
        self.action_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
        tk.Button(self.action_frame, text="帮助", command=self.show_help).pack(side=tk.LEFT, padx=5)
        tk.Button(self.action_frame, text="拆分PDF", command=self.split_pdf).pack(side=tk.RIGHT, padx=5)
    def select_file(self):
        file = filedialog.askopenfilename(
            title="选择PDF文件",
            filetypes=[("PDF文件", "*.pdf")]
        )
        if file:
            if not os.path.exists(file):
                messagebox.showerror("错误", "文件不存在")
                return
            if not file.lower().endswith('.pdf'):
                messagebox.showerror("错误", "请选择PDF文件")
                return
            self.input_file = file
            self.file_label.config(text=os.path.basename(file))
    def select_output_dir(self):
        dir = filedialog.askdirectory(title="选择输出目录")
        if dir:
            self.output_dir = dir
            self.output_label.config(text=dir)
    def show_help(self):
        """
        显示帮助信息，使用统一的帮助系统
        """
        help_system = get_help_system()
        help_system.show_help("PDF拆分")
    def parse_page_ranges(self, range_str, total_pages):
        """解析页码范围字符串，返回页面索引列表"""
        ranges = []
        parts = range_str.split(',')
        for part in parts:
            if '-' in part:
                start, end = map(int, part.split('-'))
                ranges.extend(range(start-1, min(end, total_pages)))
            else:
                page = int(part)
                if page <= total_pages:
                    ranges.append(page-1)
        return sorted(list(set(ranges)))  # 去重并排序
    def split_pdf(self):
        if not self.input_file:
            messagebox.showwarning("警告", "请先选择PDF文件")
            return
        if not self.output_dir:
            messagebox.showwarning("警告", "请先选择输出目录")
            return
        try:
            # 验证PDF文件有效性
            if not os.path.exists(self.input_file):
                messagebox.showerror("错误", "PDF文件不存在")
                return   
            try:
                reader = PdfReader(self.input_file)
                if len(reader.pages) == 0:
                    messagebox.showerror("错误", "PDF文件没有有效页面")
                    return
                total_pages = len(reader.pages)
            except Exception as e:
                messagebox.showerror("错误", f"无效的PDF文件: {str(e)}")
                return        
            base_name = os.path.splitext(os.path.basename(self.input_file))[0]
            if self.mode_var.get() == "page_count":
                # 按页数拆分模式
                try:
                    pages_per_file = int(self.page_entry.get())
                    if pages_per_file <= 0:
                        raise ValueError("页数必须大于0")
                except ValueError:
                    messagebox.showerror("错误", "请输入有效的页数")
                    return
                file_count = 0
                for i in range(0, total_pages, pages_per_file):
                    writer = PdfWriter()
                    end = min(i + pages_per_file, total_pages)
                    for j in range(i, end):
                        writer.add_page(reader.pages[j])
                    output_file = os.path.join(
                        self.output_dir,
                        f"{base_name}_p{i+1}-{end}.pdf"
                    )
                    with open(output_file, 'wb') as f:
                        writer.write(f)
                    file_count += 1
                message = f"PDF拆分完成!\n共拆分 {total_pages} 页为 {file_count} 个文件"
            else:
                # 按范围拆分模式
                range_str = self.range_entry.get().strip()
                if not range_str:
                    messagebox.showwarning("警告", "请输入有效的页码范围")
                    return
                try:
                    page_indices = self.parse_page_ranges(range_str, total_pages)
                    if not page_indices:
                        raise ValueError("没有有效的页面被选择")
                except ValueError as e:
                    messagebox.showerror("错误", f"页码范围无效: {str(e)}")
                    return
                # 将连续页面分组
                groups = []
                current_group = [page_indices[0]]
                for i in range(1, len(page_indices)):
                    if page_indices[i] == page_indices[i-1] + 1:
                        current_group.append(page_indices[i])
                    else:
                        groups.append(current_group)
                        current_group = [page_indices[i]]
                groups.append(current_group)
                # 为每个分组创建PDF文件
                for i, group in enumerate(groups):
                    writer = PdfWriter()
                    for page_idx in group:
                        writer.add_page(reader.pages[page_idx])
                    start_page = group[0] + 1
                    end_page = group[-1] + 1
                    output_file = os.path.join(
                        self.output_dir,
                        f"{base_name}_range_{start_page}-{end_page}.pdf"
                    )
                    with open(output_file, 'wb') as f:
                        writer.write(f)
                message = f"PDF拆分完成!\n共提取 {len(page_indices)} 页为 {len(groups)} 个文件"
            messagebox.showinfo("成功", message)
        except Exception as e:
            messagebox.showerror("错误", f"拆分失败: {str(e)}")
if __name__ == '__main__':
    root = tk.Tk()
    app = PDFSplitterApp(root)
    root.mainloop()