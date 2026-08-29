# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pdf2docx import Converter
import os
import logging
import threading
import traceback
from pathlib import Path
from typing import Callable, Optional

# 降低 pdf2docx 日志级别：其默认输出大量逐页 INFO 日志，是官方已知的性能开销源之一，
# 提升日志级别可显著加快大文件转换速度（pdf2docx 官方建议）
try:
    from pdf2docx import settings as _pdf2docx_settings
    if hasattr(_pdf2docx_settings, 'logging_level'):
        _pdf2docx_settings.logging_level = logging.WARNING
except Exception:
    pass

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


class ConfigManager:
    """配置管理类，存储应用程序的配置信息"""
    # 应用名称
    TITLE = "PDF转Word工具"

class ErrorHandler:
    """错误处理类，提供统一的错误处理机制"""
    
    @staticmethod
    def handle_error(error: Exception, status_callback: Callable[[str], None]) -> str:
        """处理错误并返回用户友好的错误消息
        
        Args:
            error: 捕获的异常
            status_callback: 更新状态栏的回调函数
            
        Returns:
            用户友好的错误消息
        """
        error_message = str(error)
        status_callback("转换失败!")
        
        # 映射常见错误到用户友好的消息
        if "Permission denied" in error_message:
            return "无法访问输出文件，请确保文件未被其他程序占用且有写入权限。"
        elif "not found" in error_message.lower():
            return "找不到指定的PDF文件，请确保文件路径正确。"
        elif "index out of range" in error_message.lower():
            return "PDF文件格式异常，无法正确读取页面内容。"
        elif "memory" in error_message.lower():
            return "内存不足，请尝试转换较小的PDF文件或关闭其他应用程序后重试。"
        else:
            # 记录详细错误信息到日志（这里简化为打印）
            print(f"Error details: {traceback.format_exc()}")
            return f"转换过程中发生错误:\n{error_message}"
    
    @staticmethod
    def show_error(message: str):
        """显示错误消息对话框
        
        Args:
            message: 要显示的错误消息
        """
        messagebox.showerror("错误", message)


class PDFConverter:
    """PDF转换类，处理PDF到Word的转换逻辑"""
    
    def __init__(self, master: tk.Tk, update_status: Callable[[str], None],
                 update_ui: Callable[[], None],
                 on_success: Callable[[str], None], on_done: Callable[[], None]):
        """初始化PDF转换器
        
        Args:
            master: tkinter主窗口，用于线程安全的 UI 调度
            update_status: 更新状态栏的回调函数（线程安全）
            update_ui: 更新UI的回调函数（线程安全）
            on_success: 转换成功回调，接收输出文件路径（线程安全）
            on_done: 转换结束回调（无论成败），用于恢复按钮状态（线程安全）
        """
        self.master = master
        self.update_status = update_status
        self.update_ui = update_ui
        self.on_success = on_success
        self.on_done = on_done
        self.cv = None
    
    def convert(self, pdf_path: str, output_path: str) -> bool:
        """将PDF转换为Word文档（在后台线程执行，避免阻塞 UI）
        
        Args:
            pdf_path: PDF文件路径
            output_path: 输出Word文件路径
            
        Returns:
            转换任务是否成功启动（实际结果通过回调通知）
        """
        try:
            self.update_status("正在准备转换...")
            self.update_ui()
            
            # 转换在后台线程执行；多进程并行由 pdf2docx 内部处理
            threading.Thread(
                target=self._convert_in_background,
                args=(pdf_path, output_path),
                daemon=True
            ).start()
            return True
            
        except Exception as e:
            error_message = ErrorHandler.handle_error(e, self.update_status)
            ErrorHandler.show_error(error_message)
            return False
    
    def _convert_in_background(self, pdf_path: str, output_path: str):
        """后台线程：执行实际的 PDF 到 Word 转换"""
        try:
            self.cv = Converter(pdf_path)
            total_pages = len(self.cv.pages)
            self.update_status(f"正在转换（共 {total_pages} 页，多进程并行）...")
            
            # 优先启用多进程并行转换（pdf2docx 官方加速开关）；
            # 旧版本不支持该参数时自动回退到单进程模式
            try:
                self.cv.convert(output_path, multi_processing=True, worker_count=4)
            except TypeError:
                self.cv.convert(output_path)
            
            self.update_status(f"转换完成! 共 {total_pages} 页")
            self.master.after(0, lambda: self.on_success(output_path))
        except Exception as e:
            error_message = ErrorHandler.handle_error(e, self.update_status)
            self.master.after(0, lambda: ErrorHandler.show_error(error_message))
        finally:
            if self.cv:
                try:
                    self.cv.close()
                except Exception:
                    pass
            self.master.after(0, self.on_done)


class UIComponents:
    """UI组件类，管理应用程序的界面元素"""
    
    def __init__(self, master: tk.Tk, app_instance):
        """初始化UI组件
        
        Args:
            master: tkinter主窗口
            app_instance: 应用程序实例，用于回调
        """
        self.master = master
        self.app = app_instance
        self.pdf_path = tk.StringVar()
        self.status_var = tk.StringVar()
        self.status_var.set("准备就绪")
    
    def create_widgets(self):
        """创建所有UI组件"""
        self.create_file_frame()
        self.create_action_frame()
        self.create_status_bar()
    
    def create_file_frame(self):
        """创建文件选择区域"""
        file_frame = tk.LabelFrame(self.master, text="PDF文件")
        file_frame.pack(padx=10, pady=5, fill="x")
        
        tk.Entry(file_frame, textvariable=self.pdf_path, width=50).pack(side="left", padx=5)
        tk.Button(file_frame, text="选择PDF", command=self.app.select_pdf).pack(side="left", padx=5)
    
    def create_action_frame(self):
        """创建操作按钮区域"""
        action_frame = tk.Frame(self.master)
        action_frame.pack(padx=10, pady=5, fill="x")
        
        # 不定长进度条（pdf2docx 无逐页回调，用滚动动画展示转换进行中）
        self.progress = ttk.Progressbar(action_frame, mode='indeterminate')
        self.progress.pack(side="left", fill="x", expand=True, padx=5)
        
        self.convert_btn = tk.Button(action_frame, text="转换为Word", command=self.app.convert_to_word)
        self.convert_btn.pack(side="right", padx=5)
    
    def set_converting(self, converting: bool):
        """切换转换中/就绪状态：禁用按钮 + 控制进度条动画"""
        if converting:
            self.convert_btn.config(state='disabled')
            self.progress.start(10)
        else:
            self.progress.stop()
            self.convert_btn.config(state='normal')
    
    def create_status_bar(self):
        """创建状态栏"""
        tk.Label(
            self.master, 
            textvariable=self.status_var, 
            bd=1, 
            relief=tk.SUNKEN, 
            anchor=tk.W
        ).pack(side=tk.BOTTOM, fill=tk.X)
    
    def update_status(self, message: str):
        """更新状态栏消息（线程安全，可在后台线程调用）
        
        Args:
            message: 状态消息
        """
        self.master.after(0, lambda: self.status_var.set(message))
    
    def update_ui(self):
        """强制更新UI（线程安全，委托主线程处理待刷新事件）"""
        self.master.after(0, self.master.update_idletasks)


class PDFtoWordApp(PDFToolBase):
    """PDF转Word应用程序主类"""
    
    def __init__(self, master: tk.Tk):
        """初始化应用程序"""
        super().__init__(master)
        if not master.winfo_exists():
            return
        
        self.master = master  # 别名，基类已设置 self.root
        self.master.title(ConfigManager.TITLE)
        self.build_ui()

    def build_ui(self):
        """构建用户界面"""
        # 初始化UI组件
        self.ui = UIComponents(self.master, self)
        self.ui.create_widgets()
        
        # 初始化PDF转换器（注入线程安全的成功/结束回调）
        self.converter = PDFConverter(
            self.master,
            self.ui.update_status,
            self.ui.update_ui,
            on_success=self._on_convert_success,
            on_done=self._on_convert_done
        )

    def _on_convert_success(self, output_path: str):
        """转换成功回调（主线程）"""
        messagebox.showinfo("成功", f"PDF转换完成!\n保存到: {output_path}")

    def _on_convert_done(self):
        """转换结束回调（主线程，无论成败恢复按钮与进度条）"""
        self.ui.set_converting(False)

    def select_pdf(self):
        """选择PDF文件"""
        file_path = filedialog.askopenfilename(
            title="选择PDF文件",
            filetypes=[("PDF文件", "*.pdf")]
        )
        if file_path:
            self.ui.pdf_path.set(file_path)
            self.ui.update_status(f"已选择: {os.path.basename(file_path)}")
    
    def convert_to_word(self):
        """将PDF转换为Word文档"""
        pdf_path = self.ui.pdf_path.get()
        if not pdf_path:
            messagebox.showwarning("警告", "请先选择PDF文件")
            return
        
        output_path = filedialog.asksaveasfilename(
            title="保存Word文档",
            defaultextension=".docx",
            filetypes=[("Word文档", "*.docx")]
        )
        
        if not output_path:
            return
        
        # 启动后台转换；结果通过回调通知，期间禁用按钮并显示进度动画
        if self.converter.convert(pdf_path, output_path):
            self.ui.set_converting(True)


def main():
    """应用程序入口点"""
    root = tk.Tk()
    app = PDFtoWordApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()