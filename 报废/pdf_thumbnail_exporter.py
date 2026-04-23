import os
import fitz  # PyMuPDF
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading

class PDFThumbnailExporter:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF缩略图导出工具")
        self.root.geometry("700x500")
        
        self.pdf_files = []  # 存储多个PDF文件路径
        self.output_dir = tk.StringVar()
        self.image_format = tk.StringVar(value="png")
        self.progress = tk.DoubleVar()
        
        self.setup_ui()
        
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # PDF文件选择
        ttk.Label(main_frame, text="PDF文件:").grid(row=0, column=0, sticky=tk.W, pady=5)
        pdf_frame = ttk.Frame(main_frame)
        pdf_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        
        # 修改为支持批量选择的UI
        ttk.Button(pdf_frame, text="添加PDF文件", command=self.select_pdfs).pack(side=tk.LEFT)
        ttk.Button(pdf_frame, text="添加PDF文件夹", command=self.select_pdf_folder).pack(side=tk.LEFT, padx=(5,0))
        ttk.Button(pdf_frame, text="移除选中", command=self.remove_selected).pack(side=tk.LEFT, padx=(5,0))
        ttk.Button(pdf_frame, text="清空列表", command=self.clear_list).pack(side=tk.LEFT, padx=(5,0))
        
        # 添加PDF文件列表
        list_frame = ttk.Frame(main_frame)
        list_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 文件列表
        self.file_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, yscrollcommand=scrollbar.set)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.file_listbox.yview)
        
        # 输出目录选择
        ttk.Label(main_frame, text="输出目录:").grid(row=3, column=0, sticky=tk.W, pady=(10,5))
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Entry(output_frame, textvariable=self.output_dir, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(output_frame, text="浏览", command=self.select_output_dir).pack(side=tk.LEFT, padx=(5,0))
        
        # 参数设置
        params_frame = ttk.LabelFrame(main_frame, text="导出参数", padding="10")
        params_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        # 图片格式
        ttk.Label(params_frame, text="图片格式:").grid(row=0, column=0, sticky=tk.W)
        format_frame = ttk.Frame(params_frame)
        format_frame.grid(row=0, column=1, sticky=tk.W, padx=(10,0))
        
        ttk.Radiobutton(format_frame, text="PNG", variable=self.image_format, value="png").pack(side=tk.LEFT)
        ttk.Radiobutton(format_frame, text="JPEG", variable=self.image_format, value="jpeg").pack(side=tk.LEFT, padx=(10,0))
        
        
        # 进度条
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress, maximum=100)
        self.progress_bar.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=20)
        
        # 状态标签
        self.status_label = ttk.Label(main_frame, text="请添加PDF文件和选择输出目录")
        self.status_label.grid(row=7, column=0, columnspan=2, pady=5)
        
        # 导出按钮
        self.export_button = ttk.Button(main_frame, text="导出缩略图", command=self.start_export)
        self.export_button.grid(row=8, column=0, columnspan=2, pady=20)
        
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)  # 文件列表可以扩展
        
    
    # 新增批量选择PDF文件的方法
    def select_pdfs(self):
        file_paths = filedialog.askopenfilenames(
            title="选择PDF文件",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if file_paths:
            for file_path in file_paths:
                if file_path not in self.pdf_files:
                    self.pdf_files.append(file_path)
            self.update_file_list()
            if not self.output_dir.get():
                # 默认输出目录为第一个PDF文件所在目录
                self.output_dir.set(os.path.dirname(self.pdf_files[0]))
                
    # 新增选择PDF文件夹的方法
    def select_pdf_folder(self):
        folder_path = filedialog.askdirectory(title="选择包含PDF文件的文件夹")
        if folder_path:
            pdf_files_in_folder = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        pdf_files_in_folder.append(os.path.join(root, file))
            
            added_count = 0
            for file_path in pdf_files_in_folder:
                if file_path not in self.pdf_files:
                    self.pdf_files.append(file_path)
                    added_count += 1
                    
            self.update_file_list()
            if not self.output_dir.get() and self.pdf_files:
                # 默认输出目录为第一个PDF文件所在目录
                self.output_dir.set(os.path.dirname(self.pdf_files[0]))
                
            messagebox.showinfo("文件夹导入", f"从文件夹中找到 {len(pdf_files_in_folder)} 个PDF文件，新增 {added_count} 个文件到列表中。")
    
    def update_file_list(self):
        self.file_listbox.delete(0, tk.END)
        for file_path in self.pdf_files:
            self.file_listbox.insert(tk.END, os.path.basename(file_path))
            
    def remove_selected(self):
        selected_indices = list(self.file_listbox.curselection())
        # 从后往前删除，避免索引变化问题
        for i in reversed(selected_indices):
            del self.pdf_files[i]
        self.update_file_list()
        
    def clear_list(self):
        self.pdf_files.clear()
        self.update_file_list()
            
    def select_output_dir(self):
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            self.output_dir.set(directory)
            
    def start_export(self):
        if not self.pdf_files:
            messagebox.showerror("错误", "请至少选择一个PDF文件")
            return
            
        if not self.output_dir.get():
            messagebox.showerror("错误", "请选择输出目录")
            return
            
        # 检查所有PDF文件是否存在
        for pdf_file in self.pdf_files:
            if not os.path.exists(pdf_file):
                messagebox.showerror("错误", f"PDF文件不存在: {pdf_file}")
                return
            
        if not os.path.exists(self.output_dir.get()):
            try:
                os.makedirs(self.output_dir.get())
            except Exception as e:
                messagebox.showerror("错误", f"无法创建输出目录: {str(e)}")
                return
                
        # 在后台线程中执行导出操作
        self.export_button.config(state=tk.DISABLED)
        self.status_label.config(text="正在导出...")
        threading.Thread(target=self.export_thumbnails, daemon=True).start()
        
    def export_thumbnails(self):
        try:
            total_files = len(self.pdf_files)
            processed_files = 0
            
            # 设置进度条
            self.progress.set(0)
            self.root.update_idletasks()
            
            
                # 处理每个PDF文件
            for idx, pdf_path in enumerate(self.pdf_files):
                    # 更新状态
                    self.status_label.config(text=f"正在处理 ({idx+1}/{total_files}): {os.path.basename(pdf_path)}")
                    
                    # 打开PDF文件
                    pdf_document = fitz.open(pdf_path)
                    
                    # 只导出第一页
                    page_num = 0
                    page = pdf_document[page_num]
                    
                    
                    # 使用默认DPI渲染页面为图片
                    pix = page.get_pixmap()
                    
                    # 转换为PIL图像
                    img_data = pix.tobytes(self.image_format.get())
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    # 生成输出文件名 - 使用与PDF相同的文件名
                    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
                    # 修改: 使用原始文件名而不是添加页码
                    output_filename = f"{base_name}.{self.image_format.get()}"
                    output_path = os.path.join(self.output_dir.get(), output_filename)
                    
                    # 保存图片
                    if self.image_format.get() == "jpeg":
                        img.save(output_path, "JPEG", quality=95)
                    else:
                        img.save(output_path, "PNG")
                    
                    pdf_document.close()
                    
                    
                    # 更新进度
                    processed_files += 1
                    progress_value = (processed_files / total_files) * 100
                    self.progress.set(progress_value)
                    self.root.update_idletasks()
                
            # 完成
            self.status_label.config(text=f"导出完成！共导出 {total_files} 个文件的首页")
            self.export_button.config(state=tk.NORMAL)
            
            # 询问是否打开输出目录
            if messagebox.askyesno("导出完成", f"成功导出 {total_files} 个文件的首页!\n是否打开输出目录?"):
                os.startfile(self.output_dir.get())
                
        except Exception as e:
            self.status_label.config(text="导出失败")
            self.export_button.config(state=tk.NORMAL)
            messagebox.showerror("错误", f"导出过程中发生错误:\n{str(e)}")
    

    

def main():
    root = tk.Tk()
    app = PDFThumbnailExporter(root)
    root.mainloop()

if __name__ == "__main__":
    main()