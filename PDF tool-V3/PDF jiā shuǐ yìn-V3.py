# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

from PyPDF2 import PdfReader, PdfWriter
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import subprocess
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io
from fontTools.ttLib import TTFont


class PDFWatermarkApp:
    def __init__(self, master):
        self.master = master
        
        # 首先检查授权
        if not self.check_license():
            messagebox.showerror(
                "错误", 
                "缺少授权！无法使用！请先获取授权！\n"
            )
            master.destroy()
            return
        
        self.master.title("PDF加水印")
        
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
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.PDFWatermarkApp")
            except Exception:
                pass

        # 尝试设置ICO图标
        if icon_ico_path.exists():
            try:
                self.master.iconbitmap(default=str(icon_ico_path))
            except Exception:
                try:
                    self.master.iconbitmap(str(icon_ico_path))
                except Exception:
                    pass

        # 尝试设置PNG图标
        if hasattr(self.master, "iconphoto") and icon_png_path.exists():
            try:
                self.icon_image = tk.PhotoImage(file=str(icon_png_path))
                self.master.iconphoto(True, self.icon_image)
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
            self.master.destroy()
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
        self.master.option_add("*Font", self.current_font)

    def build_ui(self):
        """构建用户界面"""
        # 配置样式
        style = ttk.Style()
        style.configure(".", font=self.current_font)
        style.configure("TButton", font=self.current_font)
        style.configure("TLabel", font=self.current_font)
        style.configure("TEntry", font=self.current_font)
        style.configure("TRadiobutton", font=self.current_font)
        style.configure("TFrame", font=self.current_font)
        style.configure("TLabelFrame", font=self.current_font)
        style.configure("TSpinbox", font=self.current_font)
        
        # 主框架
        self.main_frame = ttk.Frame(self.master)
        self.main_frame.pack(padx=10, pady=10)
        
        # PDF文件选择
        self.pdf_frame = ttk.LabelFrame(self.main_frame, text="PDF文件")
        self.pdf_frame.pack(fill="x", padx=5, pady=5)
        
        self.pdf_path = tk.StringVar()
        ttk.Entry(self.pdf_frame, textvariable=self.pdf_path, width=50).pack(side="left", padx=5)
        ttk.Button(self.pdf_frame, text="选择PDF", command=self.select_pdf).pack(side="left", padx=5)
        
        # 水印选项
        self.options_frame = ttk.LabelFrame(self.main_frame, text="水印选项")
        self.options_frame.pack(fill="x", padx=5, pady=5)
        
        # 水印设置
        self.text_frame = ttk.Frame(self.options_frame)
        self.text_frame.pack(fill="x", pady=5)
        
        ttk.Label(self.text_frame, text="水印文字:").pack(side="left", padx=5)
        self.watermark_text = tk.StringVar(value="机密")
        ttk.Entry(self.text_frame, textvariable=self.watermark_text, width=20).pack(side="left")
        
        ttk.Label(self.text_frame, text="字体大小:").pack(side="left", padx=5)
        self.font_size = tk.IntVar(value=36)
        ttk.Spinbox(self.text_frame, from_=10, to=72, textvariable=self.font_size, 
                   width=5).pack(side="left")
        
        ttk.Label(self.text_frame, text="透明度:").pack(side="left", padx=5)
        self.opacity = tk.DoubleVar(value=0.5)
        ttk.Scale(self.text_frame, from_=0.1, to=1.0, variable=self.opacity, 
                 orient="horizontal", length=100).pack(side="left")
        
        # 水印位置
        self.position_frame = ttk.Frame(self.options_frame)
        self.position_frame.pack(fill="x", pady=5)
        
        ttk.Label(self.position_frame, text="位置:").pack(side="left", padx=5)
        self.position = tk.StringVar(value="center")
        positions = [("居中", "center"), ("左上", "topleft"), ("右上", "topright"), 
                    ("左下", "bottomleft"), ("右下", "bottomright")]
        for text, value in positions:
            ttk.Radiobutton(self.position_frame, text=text, variable=self.position, 
                          value=value).pack(side="left", padx=5)
        
        # 操作按钮
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill="x", padx=5, pady=10)
        
        ttk.Button(self.button_frame, text="添加水印", command=self.add_watermark).pack(side="right", padx=5)

    
    def select_pdf(self):
        file_path = filedialog.askopenfilename(
            title="选择PDF文件",
            filetypes=[("PDF文件", "*.pdf")]
        )
        if file_path:
            self.pdf_path.set(file_path)
    
    def create_text_watermark(self):
        """创建文本水印PDF"""
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        can.setFillColorRGB(0.5, 0.5, 0.5, self.opacity.get())
        can.setFont(self.current_font[0], self.font_size.get())
        
        text = self.watermark_text.get()
        width, height = letter
        
        # 根据位置设置文本坐标
        position = self.position.get()
        if position == "center":
            x, y = width/2, height/2
            can.drawCentredString(x, y, text)
        elif position == "topleft":
            x, y = 50, height - 50
            can.drawString(x, y, text)
        elif position == "topright":
            x, y = width - 50, height - 50
            can.drawRightString(x, y, text)
        elif position == "bottomleft":
            x, y = 50, 50
            can.drawString(x, y, text)
        elif position == "bottomright":
            x, y = width - 50, 50
            can.drawRightString(x, y, text)
        
        can.save()
        packet.seek(0)
        return PdfReader(packet)
    
    def add_watermark(self):
        """添加水印到PDF"""
        pdf_path = self.pdf_path.get()
        if not pdf_path:
            messagebox.showwarning("警告", "请先选择PDF文件")
            return
        
        try:
            # 读取原始PDF
            pdf = PdfReader(pdf_path)
            if len(pdf.pages) == 0:
                messagebox.showerror("错误", "PDF文件没有有效页面")
                return
            
            # 获取文本水印
            watermark = self.create_text_watermark()
            
            # 创建PDF写入器
            writer = PdfWriter()
            
            # 为每一页添加水印
            for page in pdf.pages:
                page.merge_page(watermark.pages[0])
                writer.add_page(page)
            
            # 保存文件
            output_path = filedialog.asksaveasfilename(
                title="保存加水印的PDF",
                defaultextension=".pdf",
                filetypes=[("PDF文件", "*.pdf")]
            )
            
            if output_path:
                with open(output_path, "wb") as output_file:
                    writer.write(output_file)
                messagebox.showinfo("成功", f"PDF加水印完成!\n保存到: {output_path}")
        
        except Exception as e:
            messagebox.showerror("错误", f"加水印过程中发生错误: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = PDFWatermarkApp(root)
    root.mainloop()
