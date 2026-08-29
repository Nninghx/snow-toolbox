# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image
import fitz  # PyMuPDF

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


class ImageToPDFApp(PDFToolBase):
    """图片转PDF应用程序主类"""
    
    def __init__(self, root):
        """初始化应用程序"""
        super().__init__(root)
        if not root.winfo_exists():
            return
        
        self.root.title("图片转PDF工具")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        self.build_ui()

    def build_ui(self):
        """构建用户界面"""
        # 配置样式
        style = ttk.Style()
        style.configure(".", font=self.current_font)
        
        # 应用程序变量
        self.image_paths = []
        self.output_path = tk.StringVar()
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建界面组件
        self._create_file_section()
        self._create_list_section()
        self._create_action_section()
    
    def _create_file_section(self):
        """创建文件选择区域"""
        file_frame = ttk.LabelFrame(self.main_frame, text="文件选择")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 添加图片按钮
        ttk.Button(file_frame, text="添加图片", command=self._add_images).pack(side=tk.LEFT, padx=5, pady=5)
        
        # 清空列表按钮
        ttk.Button(file_frame, text="清空列表", command=self._clear_list).pack(side=tk.LEFT, padx=5, pady=5)
        
        # 输出路径选择
        ttk.Button(file_frame, text="选择输出PDF", command=self._select_output_pdf).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Entry(file_frame, textvariable=self.output_path, width=50, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
    
    def _create_list_section(self):
        """创建图片列表区域"""
        list_frame = ttk.LabelFrame(self.main_frame, text="图片列表")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建滚动条和列表框
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            selectmode=tk.EXTENDED
        )
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar.config(command=self.listbox.yview)
        
        # 绑定右键菜单
        self.listbox.bind("<Button-3>", self._show_context_menu)
    
    def _create_action_section(self):
        """创建操作区域"""
        action_frame = ttk.Frame(self.main_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 状态信息
        self.status_var = tk.StringVar(value="准备就绪")
        status_label = ttk.Label(action_frame, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 进度条（转换时实时显示）
        self.progress = ttk.Progressbar(action_frame, mode='determinate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        # 转换按钮（保存引用以便处理中禁用）
        self.convert_btn = ttk.Button(action_frame, text="开始转换", command=self._start_conversion)
        self.convert_btn.pack(side=tk.RIGHT, padx=5, pady=5)
    
    def _add_images(self):
        """添加图片到列表"""
        filetypes = [
            ("图片文件", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff"),
            ("所有文件", "*.*")
        ]
        
        files = filedialog.askopenfilenames(
            title="选择图片文件",
            filetypes=filetypes
        )
        
        if files:
            self.image_paths.extend(files)
            self._update_listbox()
            self.status_var.set(f"已添加 {len(files)} 张图片")
    
    def _clear_list(self):
        """清空图片列表"""
        self.image_paths = []
        self.listbox.delete(0, tk.END)
        self.status_var.set("已清空图片列表")
    
    def _select_output_pdf(self):
        """选择输出PDF文件路径"""
        file = filedialog.asksaveasfilename(
            title="保存PDF文件",
            defaultextension=".pdf",
            filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")]
        )
        
        if file:
            self.output_path.set(file)
    
    def _update_listbox(self):
        """更新列表框内容"""
        self.listbox.delete(0, tk.END)
        for path in self.image_paths:
            self.listbox.insert(tk.END, os.path.basename(path))
    
    def _show_context_menu(self, event):
        """显示右键菜单"""
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="移除选中项", command=self._remove_selected)
        menu.post(event.x_root, event.y_root)
    
    def _remove_selected(self):
        """移除选中的图片"""
        selected = self.listbox.curselection()
        if selected:
            # 从后往前删除，避免索引变化
            for i in reversed(selected):
                self.image_paths.pop(i)
            self._update_listbox()
            self.status_var.set(f"已移除 {len(selected)} 张图片")
    
    def _start_conversion(self):
        """开始转换过程"""
        # 检查是否有图片
        if not self.image_paths:
            messagebox.showwarning("警告", "请先添加图片")
            return
        
        # 检查是否已选择输出路径
        if not self.output_path.get():
            messagebox.showwarning("警告", "请选择输出PDF文件路径")
            return
        
        # 后台线程执行转换，避免阻塞 UI
        self.convert_btn.config(state=tk.DISABLED)
        self.progress['value'] = 0
        self.progress['maximum'] = len(self.image_paths)
        # 快照当前参数，避免线程中读取 UI 变量
        threading.Thread(
            target=self._do_convert,
            args=(list(self.image_paths), self.output_path.get()),
            daemon=True
        ).start()
    
    def _update_progress(self, done, total, text=None):
        """在主线程更新进度条与状态"""
        def _update():
            self.progress.configure(value=done)
            if text:
                self.status_var.set(text)
        self.root.after(0, _update)
    
    def _do_convert(self, image_paths, output_path):
        """后台线程：按顺序将图片插入PDF（fitz C++ 操作释放 GIL）"""
        failed = 0
        try:
            # 创建PDF文档（懒删除：无页面时不落盘）
            pdf_document = fitz.open()
            
            # 按顺序添加图片到PDF（PDF页面顺序必须串行插入）
            for i, img_path in enumerate(image_paths):
                try:
                    # 一次性读入内存，避免 PIL 和 fitz 重复打开文件（PIL 懒加载只读头部获取尺寸）
                    with open(img_path, 'rb') as f:
                        img_data = f.read()
                    with Image.open(img_path) as img:
                        width, height = img.size
                    
                    # 创建PDF页面
                    pdf_page = pdf_document.new_page(width=width, height=height)
                    
                    # 用字节流插入图片，跳过磁盘重复读取开销
                    pdf_page.insert_image(
                        fitz.Rect(0, 0, width, height),
                        stream=img_data
                    )
                except Exception as e:
                    failed += 1
                    self.root.after(0, lambda p=os.path.basename(img_path), err=str(e):
                        messagebox.showwarning("警告", f"无法处理图片 {p}: {err}"))
                self._update_progress(i + 1, len(image_paths),
                    f"正在处理 ({i + 1}/{len(image_paths)})")
            
            # 保存PDF
            if len(pdf_document) == 0:
                self.root.after(0, lambda: messagebox.showerror("错误", "没有可转换的图片"))
                return
            pdf_document.save(output_path)
            pdf_document.close()
            
            # 完成提示（在主线程弹窗）
            done_count = len(image_paths) - failed
            self.root.after(0, lambda: messagebox.showinfo(
                "完成", f"已成功将 {done_count} 张图片转换为PDF\n保存位置: {output_path}"))
            self._update_progress(len(image_paths), len(image_paths), "转换完成")
            
            # 在文件资源管理器中打开输出目录
            self.root.after(0, lambda: self._open_output_folder(os.path.dirname(output_path)))
        
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"转换过程中出错: {str(e)}"))
            self.root.after(0, lambda: self.status_var.set("转换失败"))
        finally:
            self.root.after(0, lambda: self.convert_btn.config(state=tk.NORMAL))
    
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
    

def main():
    """主函数"""
    root = tk.Tk()
    app = ImageToPDFApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
