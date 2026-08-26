# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
try:
    import pikepdf
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pikepdf'])
    import pikepdf
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

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


def _write_chunk(args):
    """模块级函数，用于在线程中写入单个PDF分块（pikepdf C++操作会释放GIL）"""
    input_file, output_file, page_indices = args
    with pikepdf.open(input_file) as src:
        dst = pikepdf.new()
        dst.pages.extend(src.pages[i] for i in page_indices)
        dst.save(output_file)
    return output_file


class PDFSplitterApp(PDFToolBase):
    def __init__(self, root):
        super().__init__(root)
        if not root.winfo_exists():
            return
        
        self.root.title("PDF拆分")
        self.root.geometry("400x350")
        self.input_file = None
        self.output_dir = None
        
        # 主布局
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        self.build_ui()
        self.apply_font_to_widgets(self._get_all_widgets())

    def build_ui(self):
        """构建用户界面"""
        root = self.root
        
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
        self.split_button = tk.Button(self.action_frame, text="拆分PDF", command=self.split_pdf)
        self.split_button.pack(side=tk.RIGHT, padx=5)
        
        # 进度条
        self.progress = ttk.Progressbar(root, mode='determinate')
        self.progress.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 10))

    def _get_all_widgets(self):
        """获取所有需要设置字体的控件"""
        return [
            self.file_label, self.output_label,
            *self.file_frame.winfo_children(),
            *self.output_frame.winfo_children(),
            *self.option_frame.winfo_children(),
            *self.action_frame.winfo_children()
        ]

    def _update_progress(self, done, total):
        """在主线程更新进度条"""
        pct = int(done / total * 100)
        self.root.after(0, lambda: self.progress.configure(value=pct))

    def _process_chunks(self, chunks, total_chunks, base_name):
        """并行处理PDF分块写入，利用pikepdf C++释放GIL实现多线程加速"""
        file_count = 0
        max_workers = min(4, total_chunks)
        if max_workers > 1:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(_write_chunk, chunk): chunk for chunk in chunks}
                for future in as_completed(futures):
                    future.result()
                    file_count += 1
                    self._update_progress(file_count, total_chunks)
        else:
            for chunk in chunks:
                _write_chunk(chunk)
                file_count += 1
                self._update_progress(file_count, total_chunks)

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
                with pikepdf.open(self.input_file) as pdf:
                    total_pages = len(pdf.pages)
                if total_pages == 0:
                    messagebox.showerror("错误", "PDF文件没有有效页面")
                    return
            except Exception as e:
                messagebox.showerror("错误", f"无效的PDF文件: {str(e)}")
                return

            base_name = os.path.splitext(os.path.basename(self.input_file))[0]
            chunks = []  # (input_file, output_file, page_indices) 列表

            if self.mode_var.get() == "page_count":
                # 按页数拆分模式
                try:
                    pages_per_file = int(self.page_entry.get())
                    if pages_per_file <= 0:
                        raise ValueError("页数必须大于0")
                except ValueError:
                    messagebox.showerror("错误", "请输入有效的页数")
                    return
                for i in range(0, total_pages, pages_per_file):
                    end = min(i + pages_per_file, total_pages)
                    output_file = os.path.join(
                        self.output_dir,
                        f"{base_name}_p{i+1}-{end}.pdf"
                    )
                    chunks.append((self.input_file, output_file, list(range(i, end))))
                file_desc = f"共拆分 {total_pages} 页为 {len(chunks)} 个文件"
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
                for group in groups:
                    start_page = group[0] + 1
                    end_page = group[-1] + 1
                    output_file = os.path.join(
                        self.output_dir,
                        f"{base_name}_range_{start_page}-{end_page}.pdf"
                    )
                    chunks.append((self.input_file, output_file, group))
                file_desc = f"共提取 {len(page_indices)} 页为 {len(groups)} 个文件"

            # 重置进度条并处理分块
            total_chunks = len(chunks)
            self.progress['value'] = 0
            self.progress['maximum'] = 100
            self.split_button.config(state='disabled')

            self._process_chunks(chunks, total_chunks, base_name)

            self.progress['value'] = 100
            self.split_button.config(state='normal')
            messagebox.showinfo("成功", f"PDF拆分完成!\n{file_desc}")
        except Exception as e:
            messagebox.showerror("错误", f"拆分失败: {str(e)}")
        finally:
            self.split_button.config(state='normal')
if __name__ == '__main__':
    root = tk.Tk()
    app = PDFSplitterApp(root)
    # 只有在授权验证通过后才启动主循环
    # 如果授权失败，__init__ 中会调用 root.destroy()
    if app and root.winfo_exists():
        root.mainloop()