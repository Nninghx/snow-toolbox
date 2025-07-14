# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image
import fitz  # PyMuPDF
from pathlib import Path

from os.path import dirname, join
sys.path.insert(0, join(dirname(dirname(__file__)), "Tool module"))
from BangZhu import get_help_system

class ImageToPDFApp:
    """图片转PDF应用程序主类"""
    
    def __init__(self, root):
        """初始化应用程序"""
        self.root = root
        self.root.title("图片转PDF工具Alpha1.0.1")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
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
        
        # 帮助和更新日志按钮
        ttk.Button(action_frame, text="帮助", command=self._show_help).pack(side=tk.RIGHT, padx=5, pady=5)
        ttk.Button(action_frame, text="更新日志", command=self._show_changelog).pack(side=tk.RIGHT, padx=5, pady=5)
        
        # 转换按钮
        ttk.Button(action_frame, text="开始转换", command=self._start_conversion).pack(side=tk.RIGHT, padx=5, pady=5)
    
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
        
        try:
            # 创建PDF文档
            pdf_document = fitz.open()
            
            # 按顺序添加图片到PDF
            for img_path in self.image_paths:
                try:
                    # 使用Pillow打开图片
                    img = Image.open(img_path)
                    
                    # 创建PDF页面
                    pdf_page = pdf_document.new_page(
                        width=img.width,
                        height=img.height
                    )
                    
                    # 插入图片到PDF页面
                    pdf_page.insert_image(
                        fitz.Rect(0, 0, img.width, img.height),
                        filename=img_path
                    )
                    
                except Exception as e:
                    messagebox.showwarning("警告", f"无法处理图片 {os.path.basename(img_path)}: {str(e)}")
                    continue
            
            # 保存PDF
            pdf_document.save(self.output_path.get())
            pdf_document.close()
            
            # 完成提示
            messagebox.showinfo("完成", f"已成功将 {len(self.image_paths)} 张图片转换为PDF\n保存位置: {self.output_path.get()}")
            self.status_var.set("转换完成")
            
            # 在文件资源管理器中打开输出目录
            self._open_output_folder(os.path.dirname(self.output_path.get()))
        
        except Exception as e:
            messagebox.showerror("错误", f"转换过程中出错: {str(e)}")
            self.status_var.set("转换失败")
    
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
        help_system.show_help("图片转PDF")
    
    def _show_changelog(self):
        """显示更新日志"""
        changelog = """版本更新日志
        
版本 Alpha1.0.0  (2025-06-01)
- 初始版本发布
- 支持多种图片格式转PDF
- 支持图片列表管理
- 支持右键移除图片
版本 Alpha1.0.1 (2025-6-7)
- 1.对帮助文档调用进行拆分，简化代码长度
- 2.禁止生成 .pyc 文件


"""
        messagebox.showinfo("更新日志", changelog)


def main():
    """主函数"""
    root = tk.Tk()
    app = ImageToPDFApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
