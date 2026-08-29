from __future__ import annotations
# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import io
import os
import shutil
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
try:
    import pikepdf
    from PIL import Image
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pikepdf', 'Pillow'])
    import pikepdf
    from PIL import Image

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


class PDFCompressApp(PDFToolBase):
    # 压缩档位：(最大边长限制, JPEG 质量)；无损档不处理图片
    LEVELS = {
        'lossless': (None, None),
        'standard': (2500, 75),
        'extreme': (1600, 50),
    }

    def __init__(self, root):
        super().__init__(root)
        if not root.winfo_exists():
            return

        self.root.title("PDF压缩工具")
        self.root.geometry("660x520")
        self.build_ui()

    def build_ui(self):
        """构建用户界面"""
        self.input_files = []
        self.compressing = False

        # 配置样式
        style = ttk.Style()
        style.configure("Treeview", font=self.current_font, rowheight=25)
        style.configure("Treeview.Heading", font=(self.current_font[0], 10, "bold"))

        # 主布局
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # 文件表格区域
        self.file_frame = ttk.Frame(self.root)
        self.file_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.file_frame.grid_columnconfigure(0, weight=1)
        self.file_frame.grid_rowconfigure(0, weight=1)

        # 创建文件表格
        self.file_tree = ttk.Treeview(
            self.file_frame,
            columns=("name", "origin", "result", "ratio", "status"),
            show="headings",
            selectmode="browse"
        )
        self.file_tree.heading("name", text="文件名")
        self.file_tree.heading("origin", text="原大小")
        self.file_tree.heading("result", text="压缩后")
        self.file_tree.heading("ratio", text="压缩率")
        self.file_tree.heading("status", text="状态")
        self.file_tree.column("name", width=240, anchor="w")
        self.file_tree.column("origin", width=80, anchor="center")
        self.file_tree.column("result", width=80, anchor="center")
        self.file_tree.column("ratio", width=70, anchor="center")
        self.file_tree.column("status", width=120, anchor="center")
        self.file_tree.grid(row=0, column=0, sticky="nsew")

        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.file_frame, orient="vertical", command=self.file_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.file_tree.configure(yscrollcommand=scrollbar.set)

        # 设置区域
        self.option_frame = ttk.LabelFrame(self.root, text="压缩设置")
        self.option_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

        self.level_var = tk.StringVar(value='standard')
        ttk.Radiobutton(self.option_frame, text="无损压缩", value='lossless',
                        variable=self.level_var).grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")
        ttk.Radiobutton(self.option_frame, text="标准压缩", value='standard',
                        variable=self.level_var).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ttk.Radiobutton(self.option_frame, text="极限压缩", value='extreme',
                        variable=self.level_var).grid(row=0, column=2, padx=5, pady=5, sticky="w")

        self.output_var = tk.StringVar(value='same')
        ttk.Radiobutton(self.option_frame, text="保存到原目录（添加 _compressed 后缀）", value='same',
                        variable=self.output_var).grid(row=1, column=0, columnspan=3, padx=10, pady=(0, 5), sticky="w")
        ttk.Radiobutton(self.option_frame, text="保存到指定目录", value='custom',
                        variable=self.output_var).grid(row=2, column=0, columnspan=3, padx=10, pady=(0, 5), sticky="w")

        # 底部按钮区域
        self.bottom_frame = ttk.Frame(self.root)
        self.bottom_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

        ttk.Button(self.bottom_frame, text="添加文件",
                   command=self.add_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.bottom_frame, text="移除选中",
                   command=self.remove_file).pack(side=tk.LEFT, padx=5)
        self.compress_btn = ttk.Button(self.bottom_frame, text="开始压缩",
                                       command=self.start_compress)
        self.compress_btn.pack(side=tk.LEFT, padx=5)

        clear_link = tk.Label(
            self.bottom_frame,
            text="清空列表",
            fg="gray",
            cursor="hand2",
            font=(self.current_font[0], 9)
        )
        clear_link.pack(side=tk.RIGHT, padx=5)
        clear_link.bind("<Button-1>", lambda e: self.clear_all_files())

        # 进度条区域
        self.progress_frame = ttk.Frame(self.root)
        self.progress_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.progress_frame.grid_columnconfigure(0, weight=1)
        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.grid(row=0, column=0, sticky="w")
        self.progress = ttk.Progressbar(self.progress_frame, mode='determinate')
        self.progress.grid(row=1, column=0, sticky="ew")

    @staticmethod
    def _format_size(size):
        """格式化文件大小"""
        for unit in ('B', 'KB', 'MB', 'GB'):
            if size < 1024 or unit == 'GB':
                return f"{size:.1f} {unit}"
            size /= 1024

    def _set_item_values(self, item, values):
        """在主线程更新表格某一行"""
        self.root.after(0, lambda: self.file_tree.item(item, values=values))

    def add_file(self):
        if self.compressing:
            return
        files = filedialog.askopenfilenames(title="选择PDF文件", filetypes=[("PDF文件", "*.pdf")])
        if files:
            for file in files:
                if file not in self.input_files:
                    self.input_files.append(file)
                    self.file_tree.insert("", "end", values=(
                        os.path.basename(file),
                        self._format_size(os.path.getsize(file)),
                        "-", "-", "等待压缩"
                    ))

    def remove_file(self):
        if self.compressing:
            return
        selection = self.file_tree.selection()
        if selection:
            index = self.file_tree.index(selection[0])
            if 0 <= index < len(self.input_files):
                del self.input_files[index]
            self.file_tree.delete(selection[0])

    def clear_all_files(self):
        if self.compressing:
            return
        if self.input_files:
            if messagebox.askyesno("确认", "确定要清空文件列表吗？"):
                self.input_files.clear()
                self.file_tree.delete(*self.file_tree.get_children())

    def _get_output_path(self, src, out_dir):
        """生成输出文件路径，避免覆盖同名文件"""
        if out_dir:
            return os.path.join(out_dir, os.path.basename(src))
        stem, ext = os.path.splitext(src)
        path = f"{stem}_compressed{ext}"
        counter = 1
        while os.path.exists(path):
            path = f"{stem}_compressed({counter}){ext}"
            counter += 1
        return path

    def start_compress(self):
        if self.compressing:
            return
        if not self.input_files:
            messagebox.showwarning("警告", "请先添加PDF文件")
            return

        out_dir = None
        if self.output_var.get() == 'custom':
            out_dir = filedialog.askdirectory(title="选择输出目录")
            if not out_dir:
                return

        self.compressing = True
        self.compress_btn.config(state='disabled')
        self.progress['value'] = 0
        self.progress_label.config(text="正在压缩...")
        threading.Thread(
            target=self._do_compress,
            args=(list(self.input_files), out_dir, self.level_var.get()),
            daemon=True
        ).start()

    def _do_compress(self, files, out_dir, level):
        """执行实际的压缩操作（后台线程）"""
        items = self.file_tree.get_children()
        success = 0
        try:
            max_dim, quality = self.LEVELS[level]
            total = len(files)
            for i, (src, item) in enumerate(zip(files, items)):
                self._set_item_values(item, (
                    os.path.basename(src), self._format_size(os.path.getsize(src)),
                    "-", "-", "压缩中..."))
                tmp_path = None
                try:
                    tmp_path = self._compress_one(src, out_dir, max_dim, quality)
                    new_size = os.path.getsize(tmp_path)
                    old_size = os.path.getsize(src)
                    ratio = (1 - new_size / old_size) * 100 if old_size else 0
                    # 压缩成功，将临时文件重命名为正式输出文件
                    final_path = tmp_path[:-4] if tmp_path.endswith('.tmp') else tmp_path
                    os.replace(tmp_path, final_path)
                    tmp_path = None
                    self._set_item_values(item, (
                        os.path.basename(src), self._format_size(old_size),
                        self._format_size(new_size), f"{ratio:.1f}%", "完成"))
                    success += 1
                except Exception as e:
                    self._set_item_values(item, (
                        os.path.basename(src), self._format_size(os.path.getsize(src)),
                        "-", "-", "失败"))
                    print(f"压缩失败 {src}: {e}")
                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass
                self.root.after(0, lambda n=i + 1: self.progress.configure(value=int(n / total * 100)))
                self.root.after(0, lambda n=i + 1: self.progress_label.config(
                    text=f"正在压缩 {n}/{total} ..."))

            self.root.after(0, lambda: messagebox.showinfo(
                "成功", f"PDF压缩完成！\n成功 {success}/{total} 个文件"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(
                "错误", f"压缩失败: {str(e)}"))
        finally:
            self.root.after(0, self._finish)

    def _finish(self):
        """恢复按钮状态"""
        self.compressing = False
        self.compress_btn.config(state='normal')
        self.progress_label.config(text="压缩完成")

    def _compress_one(self, src, out_dir, max_dim, quality):
        """压缩单个文件，返回临时输出路径"""
        tmp_path = self._get_output_path(src, out_dir) + ".tmp"
        pdf = pikepdf.open(src)
        try:
            if max_dim is not None:
                self._downsample_images(pdf, max_dim, quality)
            pdf.save(
                tmp_path,
                compress_streams=True,
                recompress_flate=True,
                stream_decode_level=pikepdf.StreamDecodeLevel.generalized,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
            )
        finally:
            pdf.close()

        # 压缩后反而变大时，直接复制原文件
        if os.path.getsize(tmp_path) >= os.path.getsize(src):
            os.remove(tmp_path)
            shutil.copy2(src, tmp_path)
        return tmp_path

    def _downsample_images(self, pdf, max_dim, quality):
        """对超过尺寸限制的光栅图片重新编码为 JPEG"""
        for page in pdf.pages:
            resources = page.get('/Resources')
            if resources is None:
                continue
            xobjects = resources.get('/XObject')
            if xobjects is None:
                continue
            for key in list(xobjects.keys()):
                obj = xobjects.get(key)
                if obj is None or obj.get('/Subtype') != '/Image':
                    continue
                # 带透明通道或蒙版的图片跳过，避免破坏显示效果
                if obj.get('/SMask') is not None or obj.get('/Mask') is not None:
                    continue
                try:
                    pdfimage = pikepdf.PdfImage(obj)
                    if pdfimage.width <= max_dim and pdfimage.height <= max_dim:
                        continue
                    image = pdfimage.as_pil_image()
                    # 按最大边等比缩放
                    scale = max_dim / max(image.width, image.height)
                    new_size = (max(1, int(image.width * scale)),
                                max(1, int(image.height * scale)))
                    image = image.resize(new_size, Image.LANCZOS)
                    if image.mode not in ('RGB', 'L'):
                        image = image.convert('RGB')
                    buf = io.BytesIO()
                    image.save(buf, format='JPEG', quality=quality, optimize=True)
                    obj.write(buf.getvalue(), filter=pikepdf.Name.DCTDecode)
                except Exception:
                    # 单张图片处理失败不影响整体压缩
                    continue


if __name__ == '__main__':
    root = tk.Tk()
    app = PDFCompressApp(root)
    root.mainloop()
