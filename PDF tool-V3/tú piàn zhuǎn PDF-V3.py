# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import sys
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image
import fitz  # PyMuPDF
from fontTools.ttLib import TTFont


class ImageToPDFApp:
    """图片转PDF应用程序主类"""
    
    def __init__(self, root):
        """初始化应用程序"""
        self.root = root
        
        # 首先检查授权
        if not self.check_license():
            messagebox.showerror(
                "错误", 
                "缺少授权！无法使用！请先获取授权！\n"
            )
            root.destroy()
            return
        
        self.root.title("图片转PDF工具")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # 设置窗口图标、加载字体并构建UI
        self.set_window_icon()
        self.load_font()
        self.build_ui()

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
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.ImageToPDFApp")
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
            # 验证授权
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
        """从 TTF 字体文件中加载字体"""
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
    
    def _apply_font_settings(self, font):
        """应用字体设置到所有UI组件"""
        self.root.option_add("*Font", font)
        style = ttk.Style()
        style.configure(".", font=font)
    
def main():
    """主函数"""
    root = tk.Tk()
    app = ImageToPDFApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
