# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import re
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from PIL import Image, ImageTk

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

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif", ".tif", ".tiff"}


def natural_sort_key(value: str):
    parts = re.split(r"(\d+)", value)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def _clamp_box(box, width, height):
    """将裁剪框限制在图片范围内，并保证最小为 1 像素"""
    left, top, right, bottom = box
    left = max(0, min(left, width - 1))
    top = max(0, min(top, height - 1))
    right = max(left + 1, min(right, width))
    bottom = max(top + 1, min(bottom, height))
    return (left, top, right, bottom)


class CropDialog(tk.Toplevel):
    """在第一张图片上用鼠标框选裁剪区域，确定后返回原图像素坐标 (left, top, right, bottom)"""

    def __init__(self, parent, image_path, font_family):
        super().__init__(parent)
        self.title("裁剪参考图 — 拖拽鼠标框选要保留的区域")
        self.transient(parent)
        self.resizable(False, False)

        self.font_family = font_family
        self.image_path = Path(image_path)
        self.result_box = None      # 原图像素坐标 (left, top, right, bottom)
        self._img = None

        try:
            self._img = Image.open(self.image_path)
            self._img.load()
        except Exception as exc:
            messagebox.showerror("错误", f"无法打开图片：{exc}")
            self.destroy()
            return

        self.orig_w, self.orig_h = self._img.size
        if self.orig_w <= 0 or self.orig_h <= 0:
            messagebox.showerror("错误", "图片尺寸无效")
            self.destroy()
            return

        # 画布 / 缩放相关状态
        self._photo = None
        self._box_disp = None       # 画布坐标系下的框 (dl, dt, dr, db)
        self._mode = None           # "draw" / "move"
        self._drag_start = (0, 0)   # draw 起点
        self._move_off = (0, 0)     # move 偏移

        self._syncing = False

        self._build_ui()
        self._setup_events()

        # 窗口居中
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 3
        self.geometry(f"+{x}+{y}")

    # ---------- UI ----------
    def _build_ui(self):
        f = self.font_family

        tk.Label(
            self,
            text=f"文件：{self.image_path.name}   原始尺寸：{self.orig_w} × {self.orig_h}    （鼠标左键拖拽框选，点击已选区域可整体移动）",
            font=(f, 10),
        ).pack(padx=12, pady=(10, 4), anchor="w")

        # 自适应缩放显示
        max_w, max_h = 940, 600
        scale = min(max_w / self.orig_w, max_h / self.orig_h, 5.0)
        self.scale = scale
        disp_w = max(1, round(self.orig_w * scale))
        disp_h = max(1, round(self.orig_h * scale))
        self.disp_w, self.disp_h = disp_w, disp_h

        resized = self._img.resize((disp_w, disp_h), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(resized)

        canvas_frame = tk.Frame(self)
        canvas_frame.pack(padx=12, pady=4)
        self.canvas = tk.Canvas(
            canvas_frame, width=disp_w, height=disp_h,
            bg="#202020", highlightthickness=1,
            highlightbackground="#888888", cursor="crosshair",
        )
        self.canvas.pack()
        self.canvas.create_image(0, 0, image=self._photo, anchor=tk.NW, tags="bg")

        # 坐标微调区
        edit_frame = tk.Frame(self)
        edit_frame.pack(padx=12, pady=(6, 2), fill=tk.X)

        tk.Label(edit_frame, text="裁剪区域（原图像素）：", font=(f, 10)).pack(side=tk.LEFT)

        self.l_var = tk.StringVar(value="0")
        self.t_var = tk.StringVar(value="0")
        self.w_var = tk.StringVar(value=str(self.orig_w))
        self.h_var = tk.StringVar(value=str(self.orig_h))

        for text, var, unit in (
            ("左:", self.l_var, None),
            ("上:", self.t_var, None),
            ("宽:", self.w_var, "px"),
            ("高:", self.h_var, "px"),
        ):
            tk.Label(edit_frame, text=text, font=(f, 10)).pack(side=tk.LEFT, padx=(8, 2))
            ent = tk.Entry(edit_frame, textvariable=var, width=7, font=(f, 10))
            ent.pack(side=tk.LEFT)
            if unit:
                tk.Label(edit_frame, text=unit, font=(f, 10)).pack(side=tk.LEFT)
        self.l_var.trace_add("write", self._on_entry_change)
        self.t_var.trace_add("write", self._on_entry_change)
        self.w_var.trace_add("write", self._on_entry_change)
        self.h_var.trace_add("write", self._on_entry_change)

        self.info_var = tk.StringVar(value="尚未框选区域")
        tk.Label(self, textvariable=self.info_var, font=(f, 10), fg="#1a73e8").pack(padx=12, pady=2, anchor="w")

        btn_frame = tk.Frame(self)
        btn_frame.pack(padx=12, pady=(4, 12))
        tk.Button(btn_frame, text="预览效果", command=self.preview_crop, font=(f, 10), width=12).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="重置区域", command=self.reset_box, font=(f, 10), width=12).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="取消", command=self.destroy, font=(f, 10), width=12).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="确定使用此区域", command=self.apply_box, font=(f, 10), width=16).pack(side=tk.LEFT, padx=6)

    # ---------- 鼠标交互 ----------
    def _setup_events(self):
        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

    def _img_from_disp(self, dx, dy):
        """画布坐标 -> 原图坐标（取整并限制范围）"""
        ix = round(dx / self.scale)
        iy = round(dy / self.scale)
        ix = max(0, min(ix, self.orig_w))
        iy = max(0, min(iy, self.orig_h))
        return ix, iy

    def _disp_from_img(self, ix, iy):
        dx = round(ix * self.scale)
        dy = round(iy * self.scale)
        return dx, dy

    def _on_press(self, event):
        x, y = event.x, event.y
        if self._box_disp:
            dl, dt, dr, db = self._box_disp
            if dl <= x <= dr and dt <= y <= db:
                self._mode = "move"
                self._move_off = (x - dl, y - dt)
                return
        self._mode = "draw"
        self._drag_start = (x, y)
        self._box_disp = (x, y, x, y)
        self._redraw()

    def _on_motion(self, event):
        x, y = event.x, event.y
        if self._mode == "draw":
            sx, sy = self._drag_start
            self._box_disp = (
                min(sx, x), min(sy, y),
                max(sx, x), max(sy, y),
            )
            self._redraw()
        elif self._mode == "move" and self._box_disp:
            ox, oy = self._move_off
            w = self._box_disp[2] - self._box_disp[0]
            h = self._box_disp[3] - self._box_disp[1]
            dl = max(0, min(x - ox, self.disp_w - w))
            dt = max(0, min(y - oy, self.disp_h - h))
            self._box_disp = (dl, dt, dl + w, dt + h)
            self._redraw()

    def _on_release(self, *_):
        self._mode = None
        if self._box_disp:
            dl, dt, dr, db = self._box_disp
            if dr - dl < 4 or db - dt < 4:
                self._box_disp = None
                self._redraw()
                return
            self._sync_to_entries()

    # ---------- 绘制与数值同步 ----------
    def _redraw(self):
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self._photo, anchor=tk.NW)
        if self._box_disp:
            dl, dt, dr, db = self._box_disp
            self.canvas.create_rectangle(
                dl, dt, dr, db,
                outline="#ff3b30", width=2, dash=(6, 3), tags="sel",
            )
            self.canvas.create_text(
                dl + 6, dt + 6, anchor="nw",
                text=f"{dr - dl} × {db - dt} px",
                fill="#ff3b30", font=("Consolas", 10, "bold"),
            )
        box = self._current_img_box()
        if box:
            left, top, right, bottom = box
            self.info_var.set(
                f"裁剪区域：Left={left}  Top={top}  Right={right}  Bottom={bottom}  "
                f"（宽 {right - left}px × 高 {bottom - top}px）"
            )
        else:
            self.info_var.set("尚未框选区域")

    def _current_img_box(self):
        """当前画布框 -> 原图坐标；无有效框返回 None"""
        if not self._box_disp:
            return None
        dl, dt, dr, db = self._box_disp
        left, top = self._img_from_disp(dl, dt)
        right, bottom = self._img_from_disp(dr, db)
        box = (left, top, right, bottom)
        return _clamp_box(box, self.orig_w, self.orig_h)

    def _on_entry_change(self, *_):
        if self._syncing:
            return
        try:
            left = int(self.l_var.get())
            top = int(self.t_var.get())
            width = int(self.w_var.get())
            height = int(self.h_var.get())
        except ValueError:
            return
        if width < 1 or height < 1:
            return
        box = _clamp_box((left, top, left + width, top + height), self.orig_w, self.orig_h)
        dl, dt = self._disp_from_img(box[0], box[1])
        dr, db = self._disp_from_img(box[2], box[3])
        self._box_disp = (dl, dt, dr, db)
        self._redraw()

    def _sync_to_entries(self):
        box = self._current_img_box()
        if not box:
            return
        self._syncing = True
        try:
            self.l_var.set(str(box[0]))
            self.t_var.set(str(box[1]))
            self.w_var.set(str(box[2] - box[0]))
            self.h_var.set(str(box[3] - box[1]))
        finally:
            self._syncing = False

    def reset_box(self):
        self._box_disp = None
        self._redraw()

    # ---------- 预览 / 确定 ----------
    def preview_crop(self):
        box = self._current_img_box()
        if not box:
            messagebox.showinfo("提示", "请先框选一个裁剪区域")
            return
        try:
            cropped = self._img.crop(box)
        except Exception as exc:
            messagebox.showerror("错误", f"裁剪失败：{exc}")
            return

        win = tk.Toplevel(self)
        win.title(f"裁剪效果预览  {self.image_path.name}")
        win.transient(self)
        thumb = cropped.copy()
        thumb.thumbnail((600, 600), Image.LANCZOS)
        photo = ImageTk.PhotoImage(thumb)
        label = tk.Label(win, image=photo)
        label.image = photo
        label.pack(padx=8, pady=8)
        tk.Label(
            win,
            text=f"裁剪后尺寸：{cropped.width} × {cropped.height}",
            font=(self.font_family, 10),
        ).pack(pady=(0, 8))

    def apply_box(self):
        box = self._current_img_box()
        if not box:
            messagebox.showinfo("提示", "请先在图片上拖拽框选要保留的区域")
            return
        self.result_box = box
        self.destroy()


class ImageBatchCropApp(PDFToolBase):
    def __init__(self, root):
        super().__init__(root)
        if not root.winfo_exists():
            return
        self.root = root
        self.root.title("图片批量裁剪（第一张框选，其余跟随）")

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.mode_var = tk.IntVar(value=0)      # 0 自动 1 固定像素 2 相对比例
        self.recursive_var = tk.BooleanVar(value=False)

        self.files = []                         # 待处理图片路径列表
        self.crop_box = None                    # 参考裁剪框（原图像素）
        self.ref_size = None                    # 参考图 (w, h)
        self._busy = False

        self.build_ui()

    # ---------- 主界面 ----------
    def build_ui(self):
        f = self.current_font[0]

        # 输入目录
        tk.Label(self.root, text="输入目录:", font=(f, 10)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(self.root, textvariable=self.input_var, width=46, font=(f, 10)).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(self.root, text="浏览...", command=self.browse_input, font=(f, 10)).grid(row=0, column=2, padx=5, pady=5)

        # 输出目录
        tk.Label(self.root, text="输出目录:", font=(f, 10)).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(self.root, textvariable=self.output_var, width=46, font=(f, 10)).grid(row=1, column=1, padx=5, pady=5)
        tk.Button(self.root, text="浏览...", command=self.browse_output, font=(f, 10)).grid(row=1, column=2, padx=5, pady=5)

        # 模式与子目录选项
        opt_frame = tk.Frame(self.root)
        opt_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=2, sticky="w")
        tk.Radiobutton(opt_frame, text="自动（尺寸相同用固定像素，不同则按比例）", variable=self.mode_var, value=0, font=(f, 10)).pack(side=tk.LEFT, padx=(0, 10))
        tk.Radiobutton(opt_frame, text="固定像素", variable=self.mode_var, value=1, font=(f, 10)).pack(side=tk.LEFT, padx=(0, 10))
        tk.Radiobutton(opt_frame, text="相对比例", variable=self.mode_var, value=2, font=(f, 10)).pack(side=tk.LEFT)
        tk.Checkbutton(opt_frame, text="包含子目录", variable=self.recursive_var, font=(f, 10)).pack(side=tk.LEFT, padx=(20, 0))

        # 图片列表 + 按钮
        list_frame = tk.Frame(self.root)
        list_frame.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        self.root.grid_rowconfigure(3, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        sb = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.file_list = tk.Listbox(list_frame, selectmode=tk.EXTENDED, yscrollcommand=sb.set,
                                    font=("Consolas", 9), exportselection=False)
        sb.config(command=self.file_list.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.file_list.bind("<Double-Button-1>", self._on_double_click)

        right_col = tk.Frame(list_frame)
        right_col.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 0))
        tk.Label(right_col, text="操作", font=(f, 10, "bold")).pack(pady=(0, 4))
        tk.Button(right_col, text="刷新列表", command=self.refresh_list, font=(f, 10), width=14).pack(pady=2)
        tk.Button(right_col, text="移除所选", command=self.remove_selected, font=(f, 10), width=14).pack(pady=2)

        # 裁剪参考区
        self.ref_info = tk.Label(
            self.root,
            text="未设置裁剪区域（点击“裁剪第一张”在参考图上框选，或双击列表中的任意图片重新选择参考图）",
            font=(f, 10), fg="#b26a00", wraplength=700, justify="left",
        )
        self.ref_info.grid(row=4, column=0, columnspan=3, padx=5, pady=2, sticky="w")

        # 日志区
        self.log_area = scrolledtext.ScrolledText(self.root, height=8, font=("Consolas", 9), wrap=tk.WORD)
        self.log_area.grid(row=5, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        self.log_area.insert(tk.END, "使用步骤：\n")
        self.log_area.insert(tk.END, " 1. 选择输入目录，点击“刷新列表”载入图片；\n")
        self.log_area.insert(tk.END, " 2. 点击“裁剪第一张”，在弹出窗口中拖拽鼠标框选要保留的区域并确定；\n")
        self.log_area.insert(tk.END, " 3. 选择输出目录，点击“开始批量裁剪”，其余图片将按第一张的裁剪区域批量处理。\n")
        self.log_area.configure(state=tk.DISABLED)

        # 底部按钮 + 进度
        bottom = tk.Frame(self.root)
        bottom.grid(row=6, column=0, columnspan=3, padx=5, pady=(0, 8), sticky="ew")
        self.progress = ttk.Progressbar(bottom, orient="horizontal", mode="determinate")
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        tk.Button(bottom, text="裁剪第一张", command=self.crop_first_image, font=(f, 10)).pack(side=tk.LEFT, padx=4)
        tk.Button(bottom, text="开始批量裁剪", command=self.start_batch, font=(f, 10)).pack(side=tk.LEFT, padx=4)

    # ---------- 目录与列表 ----------
    def browse_input(self):
        path = filedialog.askdirectory(title="选择包含待裁剪图片的目录")
        if path:
            self.input_var.set(path)
            self.refresh_list()

    def browse_output(self):
        path = filedialog.askdirectory(title="选择裁剪结果输出目录")
        if path:
            self.output_var.set(path)

    def refresh_list(self):
        folder = self.input_var.get().strip()
        if not folder or not Path(folder).exists():
            messagebox.showwarning("提示", "请先选择有效的输入目录")
            return
        files = []
        if self.recursive_var.get():
            for base, _, names in os.walk(folder):
                for name in names:
                    p = Path(base) / name
                    if p.suffix.lower() in SUPPORTED_EXTS:
                        files.append(p)
        else:
            for p in Path(folder).iterdir():
                if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
                    files.append(p)
        files.sort(key=lambda p: natural_sort_key(p.name))
        self.files = files

        self.file_list.delete(0, tk.END)
        for p in files:
            self.file_list.insert(tk.END, p.name)
        self.log(f"扫描到 {len(files)} 张图片" + ("（含子目录）" if self.recursive_var.get() else ""))

    def remove_selected(self):
        for sel in reversed(self.file_list.curselection()):
            self.file_list.delete(sel)
            self.files.pop(sel)
        self.log(f"剩余 {len(self.files)} 张图片")

    # ---------- 参考图裁剪 ----------
    def crop_first_image(self):
        if not self.files:
            messagebox.showinfo("提示", "列表为空，请先选择输入目录并刷新列表")
            return
        path = self.files[0]
        if self.file_list.curselection():
            index = self.file_list.curselection()[0]
            path = self.files[index]
        self._open_crop_dialog(path)

    def _on_double_click(self, event):
        index = self.file_list.nearest(event.y)
        if 0 <= index < len(self.files):
            self._open_crop_dialog(self.files[index])

    def _open_crop_dialog(self, path):
        dialog = CropDialog(self.root, path, self.current_font[0])
        self.root.wait_window(dialog)
        if dialog._img is not None:
            dialog._img.close()
        box = dialog.result_box
        if not box:
            return
        with Image.open(path) as probe:
            self.ref_size = probe.size
        self.crop_box = box
        l, t, r, b = box
        self.ref_info.config(
            text=f"参考图：{Path(path).name}（{self.ref_size[0]}×{self.ref_size[1]}）  "
                 f"裁剪区域：Left={l} Top={t} Right={r} Bottom={b}（宽 {r - l}px × 高 {b - t}px）\n"
                 f"点击“开始批量裁剪”后，其余图片将按照此区域{(l, t, r, b)}处理。",
            fg="#0a7a2f",
        )
        self.log(f"已记录裁剪区域（来自 {Path(path).name}）：({l}, {t}, {r}, {b})")

    # ---------- 批量裁剪 ----------
    def _compute_box(self, width, height):
        """根据参考框与所选模式，计算当前尺寸图片的裁剪框"""
        l, t, r, b = self.crop_box
        ref_w, ref_h = self.ref_size
        mode = self.mode_var.get()
        if mode == 1:                                   # 固定像素
            box = (l, t, r, b)
        elif mode == 2:                                 # 相对比例
            box = (
                round(l / ref_w * width),
                round(t / ref_h * height),
                round(r / ref_w * width),
                round(b / ref_h * height),
            )
        else:                                           # 自动
            if (width, height) == (ref_w, ref_h):
                box = (l, t, r, b)
            else:
                box = (
                    round(l / ref_w * width),
                    round(t / ref_h * height),
                    round(r / ref_w * width),
                    round(b / ref_h * height),
                )
        return _clamp_box(box, width, height)

    def _unique_out_path(self, out_dir, stem, suffix):
        candidate = out_dir / f"{stem}_crop{suffix}"
        counter = 1
        while candidate.exists():
            candidate = out_dir / f"{stem}_crop_{counter}{suffix}"
            counter += 1
        return candidate

    def _save_cropped(self, img, out_path):
        suffix = out_path.suffix.lower()
        save_img = img
        if suffix in (".jpg", ".jpeg") and img.mode not in ("RGB", "L"):
            save_img = img.convert("RGB")
        save_img.save(out_path)

    def start_batch(self):
        if self._busy:
            return
        if not self.crop_box or not self.ref_size:
            messagebox.showinfo("提示", "请先点击“裁剪第一张”，框选并确定裁剪区域")
            return
        if not self.files:
            messagebox.showinfo("提示", "图片列表为空，请先选择输入目录并刷新列表")
            return

        input_dir = Path(self.input_var.get().strip())
        output_raw = self.output_var.get().strip()
        if not output_raw:
            output_raw = str(input_dir / "裁剪结果_crop")
            self.output_var.set(output_raw)
            self.log(f"输出目录为空，将输出到：{output_raw}")
        out_dir = Path(output_raw)
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            messagebox.showerror("错误", f"无法创建输出目录：{exc}")
            return

        self._busy = True
        self.progress["maximum"] = len(self.files)
        self.progress["value"] = 0
        self.log(f"开始批量裁剪，共 {len(self.files)} 张图片，输出目录：{out_dir}")
        threading.Thread(target=self._worker, args=(list(self.files), out_dir), daemon=True).start()

    def _worker(self, files, out_dir):
        ok = 0
        failed = []
        for index, path in enumerate(files, start=1):
            try:
                with Image.open(path) as img:
                    width, height = img.size
                    box = self._compute_box(width, height)
                    cropped = img.crop(box)
                    suffix = path.suffix.lower() or ".png"
                    out_path = self._unique_out_path(out_dir, path.stem, suffix)
                    self._save_cropped(cropped, out_path)
                ok += 1
                msg = f"✓ [{index}/{len(files)}] {path.name}  ({width}×{height} → {cropped.width}×{cropped.height})"
            except Exception as exc:
                failed.append(str(path))
                msg = f"✗ [{index}/{len(files)}] {path.name}  失败：{exc}"
            self.root.after(0, lambda m=msg: self.log(m))
            self.root.after(0, lambda i=index: self._update_progress(i))
        self.root.after(0, lambda: self._finish_batch(ok, failed, out_dir))

    def _update_progress(self, value):
        self.progress["value"] = value

    def _finish_batch(self, ok, failed, out_dir):
        self._busy = False
        self.progress["value"] = 0
        self.log(f"批量裁剪完成：成功 {ok} 张" + (f"，失败 {len(failed)} 张" if failed else "") + f"，输出目录：{out_dir}")
        summary = f"批量裁剪完成！成功 {ok} 张"
        if failed:
            summary += f"\n失败 {len(failed)} 张："
            for item in failed[:10]:
                summary += f"\n  {item}"
            if len(failed) > 10:
                summary += f"\n  ... 等 {len(failed)} 张"
        summary += f"\n\n输出目录：\n{out_dir}"
        messagebox.showinfo("完成", summary)

    # ---------- 工具 ----------
    def log(self, message):
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.configure(state=tk.DISABLED)


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageBatchCropApp(root)
    if root.winfo_exists():
        root.mainloop()
