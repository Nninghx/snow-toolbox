# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, font
from PyPDF2 import PdfReader, PdfWriter
from pathlib import Path
from fontTools.ttLib import TTFont


class PDFSplitterApp:
    def __init__(self, root):
        self.root = root
        
        # 首先检查授权
        if not self.check_license():
            messagebox.showerror(
                "错误", 
                "缺少授权！无法使用！请先获取授权！\n"
            )
            root.destroy()
            return
        
        # 设置窗口图标
        self.set_window_icon()
        
        # 加载字体
        self.load_font()
        
        self.root.title("PDF拆分")
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
        tk.Button(self.action_frame, text="拆分PDF", command=self.split_pdf).pack(side=tk.RIGHT, padx=5)
        
        # 应用字体到所有控件
        self.apply_font()

    def set_window_icon(self):
        """设置应用程序窗口图标"""
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        IMAGE_DIR = PROJECT_ROOT / "Image"
        
        icon_ico_path = IMAGE_DIR / "icon.ico"
        icon_png_path = IMAGE_DIR / "icon.png"

        # Windows系统设置应用ID
        if os.name == 'nt':
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.PDFSplitter")
            except Exception:
                pass

        # 尝试设置ICO图标
        if icon_ico_path.exists():
            try:
                self.root.iconbitmap(default=str(icon_ico_path))
            except Exception:
                try:
                    self.root.iconbitmap(str(icon_ico_path))
                except Exception:
                    pass

        # 尝试设置PNG图标
        if hasattr(self.root, "iconphoto") and icon_png_path.exists():
            try:
                self.icon_image = tk.PhotoImage(file=str(icon_png_path))
                self.root.iconphoto(True, self.icon_image)
            except Exception:
                pass

    def check_license(self):
        """检查开源协议文档是否存在并验证完整性"""
        # 如果通过主程序启动（环境变量已设置），则跳过授权验证
        if os.environ.get('MAIN_APP_AUTHORIZED') == '1':
            return True
        
        try:
            import subprocess
            PROJECT_ROOT = Path(__file__).resolve().parent.parent
            CORE_DIR = PROJECT_ROOT / "Core"
            license_exe_path = CORE_DIR / "LICENSE.exe"
            if license_exe_path.exists():
                result = subprocess.run(
                    [str(license_exe_path), '--quiet'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.returncode == 0
        except Exception as e:
            print(f"许可证验证异常: {e}")
            return False

    def load_font(self):
        """从配置文件加载字体设置"""
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        IMAGE_DIR = PROJECT_ROOT / "Image"
        
        font_path = IMAGE_DIR / "AlibabaPuHuiTi-3-55-RegularL3.ttf"
        
        if not font_path.exists():
            messagebox.showerror("错误", f"找不到字体文件：{font_path}")
            self.root.destroy()
            return
        
        # 使用 fonttools 获取字体名称
        tt = TTFont(str(font_path))
        font_name = None
        for record in tt['name'].names:
            if record.nameID == 1:  # Font Family
                font_name = record.toUnicode()
                break
        if not font_name:
            raise RuntimeError(f"无法从字体文件获取字体名称：{font_path}")
        tt.close()
        
        # 使用 Windows API 注册字体
        if os.name == 'nt':
            import ctypes
            GDI32 = ctypes.windll.gdi32
            font_path_str = str(font_path).encode('utf-16-le') + b'\x00'
            GDI32.AddFontResourceW(font_path_str)
            print(f"成功加载自定义字体: {font_path}")
        
        from tkinter import font as tkfont
        self.current_font = (font_name, 10)
        self.root.option_add("*Font", self.current_font)

    def apply_font(self):
        """为已创建的控件应用字体"""
        # 获取所有需要设置字体的控件
        widgets = [
            self.file_label, self.output_label,
            *self.file_frame.winfo_children(),
            *self.output_frame.winfo_children(),
            *self.option_frame.winfo_children(),
            *self.action_frame.winfo_children()
        ]
        
        # 为每个控件设置字体
        for widget in widgets:
            try:
                if isinstance(widget, (tk.Label, tk.Button, tk.Radiobutton, tk.Entry)):
                    widget.config(font=(self.current_font[0], 10))
                elif isinstance(widget, tk.LabelFrame):
                    widget.config(font=(self.current_font[0], 10, "bold"))
            except:
                continue

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
    # 只有在授权验证通过后才启动主循环
    # 如果授权失败，__init__ 中会调用 root.destroy()
    if app and root.winfo_exists():
        root.mainloop()