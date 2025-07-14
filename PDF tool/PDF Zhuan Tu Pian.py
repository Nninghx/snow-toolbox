# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import fitz  
from PIL import Image, ImageTk
import tempfile
import shutil
from pathlib import Path

from os.path import dirname, join
sys.path.insert(0, join(dirname(dirname(__file__)), "Tool module"))
from BangZhu import get_help_system

class PDFToImageApp:
    """PDF转图片应用程序主类"""
    
    def __init__(self, root):
        """初始化应用程序"""
        self.root = root
        self.root.title("PDF转图片工具Alpha1.0.1")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # 设置应用程序图标
        # self.root.iconbitmap("icon.ico")  # 如果有图标文件，可以取消注释
        
        # 应用程序变量
        self.pdf_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.output_format = tk.StringVar(value="png")
        self.dpi = tk.IntVar(value=300)
        self.quality = tk.IntVar(value=90)
        self.selected_pages = []
        self.all_pages = tk.BooleanVar(value=True)
        self.total_pages = 0
        self.pdf_document = None
        self.preview_images = []
        self.temp_dir = tempfile.mkdtemp()
        
        # 设置样式
        self.style = ttk.Style()
        self.style.configure("TButton", padding=6, relief="flat", background="#ccc")
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TLabel", background="#f0f0f0")
        self.style.configure("TCheckbutton", background="#f0f0f0")
        self.style.configure("TRadiobutton", background="#f0f0f0")
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建界面组件
        self._create_file_section()
        self._create_preview_section()
        self._create_settings_section()
        self._create_action_section()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # 设置拖放功能（如果tkinterdnd2可用）
        try:
            from tkinterdnd2 import DND_FILES
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self._on_drop)
        except ImportError:
            print("警告: tkinterdnd2模块未安装，拖放功能将不可用")
    
    def _create_file_section(self):
        """创建文件选择区域"""
        file_frame = ttk.LabelFrame(self.main_frame, text="文件选择")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 文件选择按钮和路径显示
        ttk.Button(file_frame, text="选择PDF文件", command=self._select_pdf).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Entry(file_frame, textvariable=self.pdf_path, width=50, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        # 输出目录选择
        ttk.Button(file_frame, text="选择输出目录", command=self._select_output_dir).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Entry(file_frame, textvariable=self.output_dir, width=30, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
    
    def _create_preview_section(self):
        """创建预览区域"""
        preview_frame = ttk.LabelFrame(self.main_frame, text="PDF预览")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 预览控制区
        control_frame = ttk.Frame(preview_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Checkbutton(control_frame, text="全部页面", variable=self.all_pages, command=self._toggle_page_selection).pack(side=tk.LEFT, padx=5)
        ttk.Label(control_frame, text="页面选择:").pack(side=tk.LEFT, padx=5)
        self.page_info = ttk.Label(control_frame, text="未选择PDF文件")
        self.page_info.pack(side=tk.LEFT, padx=5)
        
        # 预览区域 - 使用Canvas和Scrollbar
        self.preview_canvas_frame = ttk.Frame(preview_frame)
        self.preview_canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.preview_canvas = tk.Canvas(self.preview_canvas_frame, bg="white")
        self.preview_scrollbar = ttk.Scrollbar(self.preview_canvas_frame, orient=tk.HORIZONTAL, command=self.preview_canvas.xview)
        
        self.preview_canvas.configure(xscrollcommand=self.preview_scrollbar.set)
        self.preview_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.preview_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 创建预览内容框架
        self.preview_content = ttk.Frame(self.preview_canvas)
        self.preview_canvas.create_window((0, 0), window=self.preview_content, anchor=tk.NW)
        self.preview_content.bind("<Configure>", lambda e: self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox("all")))
    
    def _create_settings_section(self):
        """创建设置区域"""
        settings_frame = ttk.LabelFrame(self.main_frame, text="转换设置")
        settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建两列布局
        left_frame = ttk.Frame(settings_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        right_frame = ttk.Frame(settings_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧 - 格式选择
        format_frame = ttk.LabelFrame(left_frame, text="输出格式")
        format_frame.pack(fill=tk.X, padx=5, pady=5)
        
        formats = [("PNG", "png"), ("JPEG", "jpg"), ("TIFF", "tiff"), ("BMP", "bmp")]
        for text, value in formats:
            ttk.Radiobutton(format_frame, text=text, value=value, variable=self.output_format).pack(anchor=tk.W, padx=5, pady=2)
        
        # 右侧 - 质量设置
        quality_frame = ttk.LabelFrame(right_frame, text="图像质量")
        quality_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # DPI设置
        dpi_frame = ttk.Frame(quality_frame)
        dpi_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(dpi_frame, text="DPI:").pack(side=tk.LEFT, padx=5)
        dpi_values = [72, 96, 150, 300, 600]
        dpi_combo = ttk.Combobox(dpi_frame, textvariable=self.dpi, values=dpi_values, width=5)
        dpi_combo.pack(side=tk.LEFT, padx=5)
        
        # 质量设置 (仅对JPEG有效)
        quality_scale_frame = ttk.Frame(quality_frame)
        quality_scale_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(quality_scale_frame, text="JPEG质量:").pack(side=tk.LEFT, padx=5)
        quality_scale = ttk.Scale(quality_scale_frame, from_=1, to=100, variable=self.quality, orient=tk.HORIZONTAL)
        quality_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.quality_label = ttk.Label(quality_scale_frame, text="90%")
        self.quality_label.pack(side=tk.LEFT, padx=5)
        
        # 更新质量标签
        self.quality.trace_add("write", self._update_quality_label)
    
    def _create_action_section(self):
        """创建操作区域"""
        action_frame = ttk.Frame(self.main_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 状态信息
        self.status_var = tk.StringVar(value="准备就绪")
        status_label = ttk.Label(action_frame, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 进度条
        self.progress = ttk.Progressbar(action_frame, orient=tk.HORIZONTAL, length=300, mode='determinate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        # 帮助和更新日志按钮
        ttk.Button(action_frame, text="帮助", command=self._show_help).pack(side=tk.RIGHT, padx=5, pady=5)
        ttk.Button(action_frame, text="更新日志", command=self._show_changelog).pack(side=tk.RIGHT, padx=5, pady=5)
        
        # 转换按钮
        self.convert_btn = ttk.Button(action_frame, text="开始转换", command=self._start_conversion)
        self.convert_btn.pack(side=tk.RIGHT, padx=5, pady=5)
    
    def _select_pdf(self):
        """选择PDF文件"""
        file_path = filedialog.askopenfilename(
            title="选择PDF文件",
            filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")]
        )
        
        if file_path:
            self.pdf_path.set(file_path)
            self._load_pdf(file_path)
    
    def _select_output_dir(self):
        """选择输出目录"""
        dir_path = filedialog.askdirectory(title="选择输出目录")
        if dir_path:
            self.output_dir.set(dir_path)
    
    def _load_pdf(self, pdf_path):
        """加载PDF文件并生成预览"""
        try:
            # 关闭之前打开的文档
            if self.pdf_document:
                self.pdf_document.close()
            
            # 打开新文档
            self.pdf_document = fitz.open(pdf_path)
            self.total_pages = len(self.pdf_document)
            
            # 更新页面信息
            self.page_info.config(text=f"共 {self.total_pages} 页")
            
            # 清除之前的预览
            for widget in self.preview_content.winfo_children():
                widget.destroy()
            
            # 清除之前的预览图像
            self.preview_images.clear()
            
            # 重置页面选择
            self.selected_pages = list(range(self.total_pages))
            self.all_pages.set(True)
            
            # 生成预览
            self._generate_previews()
            
            # 设置默认输出目录为PDF所在目录
            if not self.output_dir.get():
                self.output_dir.set(os.path.dirname(pdf_path))
            
            self.status_var.set(f"已加载: {os.path.basename(pdf_path)}")
        
        except Exception as e:
            messagebox.showerror("错误", f"无法加载PDF文件: {str(e)}")
            self.status_var.set("加载PDF失败")
    
    def _generate_previews(self):
        """生成PDF页面预览"""
        if not self.pdf_document:
            return
        
        # 清理临时目录
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        
        # 创建预览框架
        preview_frames = []
        
        # 为每一页创建预览
        for page_num in range(self.total_pages):
            # 创建页面框架
            page_frame = ttk.Frame(self.preview_content)
            page_frame.pack(side=tk.LEFT, padx=5, pady=5)
            
            # 获取页面
            page = self.pdf_document[page_num]
            
            # 渲染页面为图像
            pix = page.get_pixmap(matrix=fitz.Matrix(0.2, 0.2))
            
            # 保存为临时图像
            temp_img_path = os.path.join(self.temp_dir, f"preview_{page_num}.png")
            pix.save(temp_img_path)
            
            # 使用PIL加载图像
            img = Image.open(temp_img_path)
            img_tk = ImageTk.PhotoImage(img)
            
            # 保存引用以防止垃圾回收
            self.preview_images.append(img_tk)
            
            # 创建图像标签
            img_label = ttk.Label(page_frame, image=img_tk)
            img_label.pack(padx=2, pady=2)
            
            # 创建复选框
            var = tk.BooleanVar(value=True)
            check = ttk.Checkbutton(
                page_frame, 
                text=f"第 {page_num + 1} 页", 
                variable=var,
                command=lambda pn=page_num, v=var: self._toggle_page(pn, v.get())
            )
            check.pack(padx=2, pady=2)
            
            preview_frames.append((page_frame, var))
        
        # 更新Canvas滚动区域
        self.preview_canvas.update_idletasks()
        self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox("all"))
    
    def _toggle_page_selection(self):
        """切换全部页面/选择页面模式"""
        all_pages = self.all_pages.get()
        
        # 更新所有页面的选择状态
        for widget in self.preview_content.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, ttk.Checkbutton):
                    if all_pages:
                        child.state(['selected'])
                    else:
                        child.state(['!selected'])
        
        # 更新选择的页面列表
        if all_pages:
            self.selected_pages = list(range(self.total_pages))
        else:
            self.selected_pages = []
    
    def _toggle_page(self, page_num, selected):
        """切换单个页面的选择状态"""
        if selected and page_num not in self.selected_pages:
            self.selected_pages.append(page_num)
        elif not selected and page_num in self.selected_pages:
            self.selected_pages.remove(page_num)
        
        # 更新全选复选框状态
        if len(self.selected_pages) == self.total_pages:
            self.all_pages.set(True)
        else:
            self.all_pages.set(False)
    
    def _update_quality_label(self, *args):
        """更新质量标签"""
        self.quality_label.config(text=f"{self.quality.get()}%")
    
    def _start_conversion(self):
        """开始转换过程"""
        # 检查是否已选择PDF文件
        if not self.pdf_path.get():
            messagebox.showwarning("警告", "请先选择PDF文件")
            return
        
        # 检查是否已选择输出目录
        if not self.output_dir.get():
            messagebox.showwarning("警告", "请选择输出目录")
            return
        
        # 检查是否已选择页面
        if not self.selected_pages:
            messagebox.showwarning("警告", "请至少选择一个页面进行转换")
            return
        
        # 禁用转换按钮
        self.convert_btn.config(state=tk.DISABLED)
        
        # 在新线程中执行转换
        threading.Thread(target=self._convert_pdf_to_images, daemon=True).start()
    
    def _convert_pdf_to_images(self):
        """将PDF转换为图像"""
        try:
            # 获取设置
            pdf_path = self.pdf_path.get()
            output_dir = self.output_dir.get()
            img_format = self.output_format.get()
            dpi = self.dpi.get()
            quality = self.quality.get()
            
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 获取PDF文件名（不含扩展名）
            pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
            
            # 创建输出子目录
            output_subdir = os.path.join(output_dir, f"{pdf_name}_images")
            os.makedirs(output_subdir, exist_ok=True)
            
            # 设置进度条
            total_pages = len(self.selected_pages)
            self.progress["maximum"] = total_pages
            self.progress["value"] = 0
            
            # 计算缩放因子
            zoom = dpi / 72  # 默认PDF DPI是72
            
            # 转换选定的页面
            for i, page_num in enumerate(sorted(self.selected_pages)):
                # 更新状态
                self.status_var.set(f"正在转换第 {page_num + 1} 页 ({i + 1}/{total_pages})")
                self.root.update_idletasks()
                
                # 获取页面
                page = self.pdf_document[page_num]
                
                # 渲染页面为图像
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                
                # 确定输出文件名
                output_filename = f"{pdf_name}_page_{page_num + 1}.{img_format}"
                output_path = os.path.join(output_subdir, output_filename)
                
                # 保存图像
                if img_format.lower() == "jpg":
                    # 对于JPEG，我们需要特殊处理以应用质量设置
                    pix.save(output_path, output_format="jpeg", jpg_quality=quality)
                else:
                    pix.save(output_path)
                
                # 更新进度条
                self.progress["value"] = i + 1
                self.root.update_idletasks()
            
            # 完成
            self.status_var.set(f"转换完成! 已保存 {total_pages} 个图像到 {output_subdir}")
            messagebox.showinfo("完成", f"已成功将 {total_pages} 页转换为图像\n保存位置: {output_subdir}")
            
            # 在文件资源管理器中打开输出目录
            self._open_output_folder(output_subdir)
        
        except Exception as e:
            messagebox.showerror("错误", f"转换过程中出错: {str(e)}")
            self.status_var.set("转换失败")
        
        finally:
            # 重新启用转换按钮
            self.convert_btn.config(state=tk.NORMAL)
            # 重置进度条
            self.progress["value"] = 0
    
    def _open_output_folder(self, folder_path):
        """在文件资源管理器中打开输出文件夹"""
        try:
            if sys.platform == 'win32':
                os.startfile(folder_path)
            elif sys.platform == 'darwin':  # macOS
                os.system(f'open "{folder_path}"')
            else:  # Linux
                os.system(f'xdg-open "{folder_path}"')
        except Exception as e:
            print(f"无法打开输出文件夹: {str(e)}")
    
    def _show_help(self):
        """显示帮助信息"""
        help_system = get_help_system()
        help_system.show_help("PDF转图片")
    
    def _show_changelog(self):
        """显示更新日志"""
        changelog = """版本更新日志
        
版本 Alpha1.0.0 (2025-05-31)
- 1.初始版本发布
- 2.支持PDF转多种图片格式
- 3.支持DPI和质量设置
- 4.支持页面预览和选择
版本 Alpha1.0.1 (2025-06-07)
- 1.对帮助文档调用进行拆分，简化代码长度
- 2.禁止生成 .pyc 文件

"""
        messagebox.showinfo("更新日志", changelog)
    
    def _on_drop(self, event):
        """处理文件拖放"""
        file_path = event.data
        
        # 在Windows上，路径可能包含大括号和引号
        if sys.platform == 'win32':
            file_path = file_path.replace('{', '').replace('}', '')
            # 移除引号
            if file_path.startswith('"') and file_path.endswith('"'):
                file_path = file_path[1:-1]
        
        # 检查是否是PDF文件
        if file_path.lower().endswith('.pdf'):
            self.pdf_path.set(file_path)
            self._load_pdf(file_path)
        else:
            messagebox.showwarning("警告", "请拖放PDF文件")
    
    def _on_closing(self):
        """关闭应用程序时的清理工作"""
        # 关闭PDF文档
        if self.pdf_document:
            self.pdf_document.close()
        
        # 清理临时目录
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass
        
        # 关闭窗口
        self.root.destroy()


def main():
    """主函数"""
    # 检查是否可以使用tkinterdnd2
    try:
        # 尝试导入tkinterdnd2以支持拖放
        from tkinterdnd2 import TkinterDnD, DND_FILES
        root = TkinterDnD.Tk()
        has_dnd = True
    except ImportError:
        # 如果导入失败，使用普通的Tk
        root = tk.Tk()
        has_dnd = False
        print("警告: tkinterdnd2模块未安装，拖放功能将不可用")
    
    # 创建应用程序
    app = PDFToImageApp(root)
    
    # 如果没有tkinterdnd2，禁用拖放相关功能
    if not has_dnd:
        # 移除拖放绑定
        app.root.drop_target_register = lambda *args: None
        app.root.dnd_bind = lambda *args: None
    
    # 运行主循环
    root.mainloop()


if __name__ == "__main__":
    main()