# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

try:
    import pikepdf
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pikepdf'])
    import pikepdf
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io

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


class PDFWatermarkApp(PDFToolBase):
    def __init__(self, master):
        super().__init__(master)
        if not master.winfo_exists():
            return
        
        self.master = master  # 别名，基类已设置 self.root
        self.master.title("PDF加水印")
        self.build_ui()

    def build_ui(self):
        """构建用户界面"""
        # 配置样式（字体已通过基类全局设置）
        style = ttk.Style()
        
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
        
        # 操作按钮与进度条（拆分工具同款交互）
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill="x", padx=5, pady=10)
        
        self.wm_button = ttk.Button(self.button_frame, text="添加水印", command=self.add_watermark)
        self.wm_button.pack(side="right", padx=5)
        self.progress = ttk.Progressbar(self.button_frame, mode='determinate')
        self.progress.pack(side="right", fill="x", expand=True, padx=5)

    
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
        return pikepdf.open(packet)
    
    def add_watermark(self):
        """添加水印到PDF"""
        pdf_path = self.pdf_path.get()
        if not pdf_path:
            messagebox.showwarning("警告", "请先选择PDF文件")
            return
        
        # 先选择保存路径，避免处理过程中弹窗阻塞
        output_path = filedialog.asksaveasfilename(
            title="保存加水印的PDF",
            defaultextension=".pdf",
            filetypes=[("PDF文件", "*.pdf")]
        )
        if not output_path:
            return
        
        try:
            # 读取原始PDF（pikepdf C++ 解析，速度快）
            pdf = pikepdf.open(pdf_path)
            if len(pdf.pages) == 0:
                pdf.close()
                messagebox.showerror("错误", "PDF文件没有有效页面")
                return
            
            # 获取文本水印
            watermark = self.create_text_watermark()
            
            # 后台线程执行加水印，避免阻塞 UI
            self.wm_button.config(state='disabled')
            self.progress['value'] = 0
            threading.Thread(
                target=self._do_add_watermark,
                args=(pdf, watermark, output_path),
                daemon=True
            ).start()
        
        except Exception as e:
            messagebox.showerror("错误", f"加水印过程中发生错误: {str(e)}")

    def _update_progress(self, done, total):
        """在主线程更新进度条"""
        pct = int(done / total * 100)
        self.master.after(0, lambda: self.progress.configure(value=pct))

    def _do_add_watermark(self, pdf, watermark, output_path):
        """后台线程：为每一页叠加水印并保存（pikepdf C++ 操作释放 GIL）"""
        total_pages = len(pdf.pages)
        try:
            result = pikepdf.new()
            wm_page = watermark.pages[0]
            for i, page in enumerate(pdf.pages):
                # 复制原页面后叠加水印层（保留原始页面内容不丢失）
                new_page = result.pages.append(result.copy_foreign(page))
                new_page.add_overlay(watermark.copy_foreign(wm_page))
                self._update_progress(i + 1, total_pages + 1)
            result.save(output_path)
            self.master.after(0, lambda: messagebox.showinfo(
                "成功", f"PDF加水印完成!\n保存到: {output_path}"))
        except Exception as e:
            self.master.after(0, lambda: messagebox.showerror(
                "错误", f"加水印过程中发生错误: {str(e)}"))
        finally:
            try:
                pdf.close()
                watermark.close()
            except Exception:
                pass
            self.master.after(0, lambda: self.wm_button.config(state='normal'))


if __name__ == "__main__":
    root = tk.Tk()
    app = PDFWatermarkApp(root)
    root.mainloop()
