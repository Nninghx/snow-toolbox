# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import os
import re
import threading
import importlib.util
from pathlib import Path

import flet as ft

import tkinter as tk
from tkinter import filedialog as tk_filedialog, messagebox as tk_messagebox, ttk as tk_ttk
from PIL import Image, ImageTk


def get_project_root():
    """返回项目根目录。"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def _resolve_base_class_path():
    """解析公共基类文件路径，打包后自动使用 .pyc 字节码"""
    base_py = get_project_root() / 'Core' / 'Public base class.py'
    if getattr(sys, 'frozen', False):
        return Path(importlib.util.cache_from_source(str(base_py)))
    return base_py


def run_startup_preflight():
    """执行启动前置检查：加载公共基类并验证字体可用性。"""
    base_file = _resolve_base_class_path()

    spec = importlib.util.spec_from_file_location('public_base_class', str(base_file))
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载公共基类：{base_file}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    try:
        base = module.PDFToolBase(root)
        if not root.winfo_exists():
            raise RuntimeError("授权或窗口初始化失败")

        current_font = getattr(base, 'current_font', None)
        if not current_font:
            raise RuntimeError("公共基类未成功加载字体")

        return current_font[0]
    except Exception as exc:
        if root.winfo_exists():
            root.destroy()
        raise RuntimeError(f"启动前置检查失败：无法使用项目自带字体。{exc}") from exc
    finally:
        if root.winfo_exists():
            root.destroy()


APP_FONT_FAMILY = run_startup_preflight()

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif", ".tif", ".tiff"}


def natural_sort_key(value: str):
    parts = re.split(r"(\d+)", value)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def _clamp_box(box, width, height):
    """将裁剪框限制在图片范围内，并保证最小为 1 像素。"""
    left, top, right, bottom = box
    left = max(0, min(left, width - 1))
    top = max(0, min(top, height - 1))
    right = max(left + 1, min(right, width))
    bottom = max(top + 1, min(bottom, height))
    return (left, top, right, bottom)


# ─────────────────────────────────────────────
# CropDialog：保留 Tkinter 实现（Flet 无等价鼠标拖拽 Canvas 选区能力）
# ─────────────────────────────────────────────

class CropDialog(tk.Toplevel):
    """在第一张图片上用鼠标框选裁剪区域，确定后返回原图像素坐标 (left, top, right, bottom)。"""

    def __init__(self, parent, image_path, font_family):
        super().__init__(parent)
        self.title("裁剪参考图 — 拖拽鼠标框选要保留的区域")
        self.transient(parent)
        self.resizable(False, False)

        self.font_family = font_family
        self.image_path = Path(image_path)
        self.result_box = None
        self._img = None

        try:
            self._img = Image.open(self.image_path)
            self._img.load()
        except Exception as exc:
            tk_messagebox.showerror("错误", f"无法打开图片：{exc}")
            self.destroy()
            return

        self.orig_w, self.orig_h = self._img.size
        if self.orig_w <= 0 or self.orig_h <= 0:
            tk_messagebox.showerror("错误", "图片尺寸无效")
            self.destroy()
            return

        self._photo = None
        self._box_disp = None
        self._mode = None
        self._drag_start = (0, 0)
        self._move_off = (0, 0)
        self._syncing = False

        self._build_ui()
        self._setup_events()

        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 3
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        f = self.font_family

        tk.Label(
            self,
            text=f"文件：{self.image_path.name}   原始尺寸：{self.orig_w} × {self.orig_h}    （鼠标左键拖拽框选，点击已选区域可整体移动）",
            font=(f, 10),
        ).pack(padx=12, pady=(10, 4), anchor="w")

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

    def _setup_events(self):
        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

    def _img_from_disp(self, dx, dy):
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
            self._box_disp = (min(sx, x), min(sy, y), max(sx, x), max(sy, y))
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

    def preview_crop(self):
        box = self._current_img_box()
        if not box:
            tk_messagebox.showinfo("提示", "请先框选一个裁剪区域")
            return
        try:
            cropped = self._img.crop(box)
        except Exception as exc:
            tk_messagebox.showerror("错误", f"裁剪失败：{exc}")
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
            tk_messagebox.showinfo("提示", "请先在图片上拖拽框选要保留的区域")
            return
        self.result_box = box
        self.destroy()


# ─────────────────────────────────────────────
# ImageBatchCropApp：Flet 主界面
# ─────────────────────────────────────────────

class ImageBatchCropApp:
    def __init__(self):
        self.page = None
        self.font_family = APP_FONT_FAMILY
        self.files = []
        self.crop_box = None
        self.ref_size = None
        self._busy = False
        self._tk_root = None  # 延迟创建，用于 CropDialog

    def build(self, page: ft.Page):
        self.page = page
        page.title = "图片批量裁剪"
        page.window.width = 700
        page.window.height = 780
        page.window.center()
        page.padding = 16
        page.theme_mode = ft.ThemeMode.LIGHT

        # 设置窗口图标
        icon_path = get_project_root() / 'Image' / 'icon.ico'
        if icon_path.exists():
            page.window.icon = str(icon_path)

        # 目录选择器
        self.dir_input_picker = ft.FilePicker(on_result=self.on_dir_input_picked)
        self.dir_output_picker = ft.FilePicker(on_result=self.on_dir_output_picked)
        page.overlay.extend([self.dir_input_picker, self.dir_output_picker])

        # 输入目录
        self.input_text = ft.Text(
            "未选择目录",
            size=13,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
            expand=True,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        input_card = self._make_card(
            "输入目录",
            ft.Row(
                [
                    ft.Icon(ft.Icons.FOLDER, size=18, color=ft.Colors.BLUE_GREY_400),
                    self.input_text,
                    ft.ElevatedButton("选择目录", icon=ft.Icons.FOLDER_OPEN, on_click=self.browse_input),
                    ft.ElevatedButton("刷新列表", icon=ft.Icons.REFRESH, on_click=self.refresh_list),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
        )

        # 输出目录
        self.output_text = ft.Text(
            "未选择目录（默认输出到输入目录下的「裁剪结果_crop」）",
            size=13,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
            expand=True,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        output_card = self._make_card(
            "输出目录",
            ft.Row(
                [
                    ft.Icon(ft.Icons.FOLDER_OPEN, size=18, color=ft.Colors.BLUE_GREY_400),
                    self.output_text,
                    ft.ElevatedButton("选择目录", icon=ft.Icons.FOLDER_OPEN, on_click=self.browse_output),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
        )

        # 裁剪模式
        self.mode_group = ft.RadioGroup(
            value="0",
            content=ft.Row(
                [
                    ft.Radio(value="0", label="自动",
                             label_style=ft.TextStyle(font_family=self.font_family, size=14)),
                    ft.Radio(value="1", label="固定像素",
                             label_style=ft.TextStyle(font_family=self.font_family, size=14)),
                    ft.Radio(value="2", label="相对比例",
                             label_style=ft.TextStyle(font_family=self.font_family, size=14)),
                ],
                spacing=16,
            ),
        )
        self.recursive_check = ft.Checkbox(
            label="包含子目录",
            label_style=ft.TextStyle(font_family=self.font_family, size=14),
        )
        mode_card = self._make_card(
            "裁剪模式",
            ft.Row(
                [self.mode_group, ft.Container(expand=True), self.recursive_check],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
        )

        # 图片列表
        self.file_list_view = ft.ListView(height=200, spacing=2)
        self.empty_hint = ft.Text(
            "请选择输入目录并点击「刷新列表」载入图片",
            size=12,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
            text_align=ft.TextAlign.CENTER,
        )
        list_card = self._make_card(
            "图片列表（点击行可设为裁剪参考图）",
            ft.Column([self.file_list_view, self.empty_hint], spacing=4, expand=False),
        )

        # 裁剪参考信息
        self.ref_info_text = ft.Text(
            "未设置裁剪区域（点击「裁剪第一张」在参考图上框选）",
            size=12,
            color=ft.Colors.ORANGE_800,
            font_family=self.font_family,
        )
        ref_card = self._make_card("裁剪参考", self.ref_info_text)

        # 操作日志
        self.log_field = ft.TextField(
            multiline=True,
            read_only=True,
            value="使用步骤：\n 1. 选择输入目录，点击「刷新列表」载入图片；\n 2. 点击「裁剪第一张」，在弹出窗口中拖拽鼠标框选要保留的区域并确定；\n 3. 选择输出目录，点击「开始批量裁剪」。\n",
            min_lines=5,
            max_lines=8,
            border_radius=8,
            text_size=12,
            text_style=ft.TextStyle(font_family="Consolas", size=12),
            content_padding=ft.padding.all(8),
        )
        log_card = self._make_card("操作日志", self.log_field)

        # 进度条与按钮
        self.crop_first_btn = ft.ElevatedButton(
            "裁剪第一张",
            icon=ft.Icons.CROP,
            on_click=self.crop_first_image,
            height=36,
        )
        self.start_batch_btn = ft.ElevatedButton(
            "开始批量裁剪",
            icon=ft.Icons.CONTENT_CUT,
            on_click=self.start_batch,
            height=40,
        )
        self.progress = ft.ProgressBar(
            visible=False,
            color=ft.Colors.BLUE,
            bgcolor=ft.Colors.GREY_200,
            bar_height=6,
            border_radius=4,
            expand=True,
        )
        self.progress_text = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)

        # 状态栏
        self.status_text = ft.Text("就绪", size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)

        page.add(
            ft.Row(
                [
                    ft.Icon(ft.Icons.CONTENT_CUT, size=32, color=ft.Colors.BLUE),
                    ft.Text("图片批量裁剪", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            ft.Divider(thickness=1, opacity=0.3),
            input_card,
            output_card,
            mode_card,
            list_card,
            ref_card,
            log_card,
            ft.Row(
                [self.progress, self.progress_text],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            ft.Row(
                [self.crop_first_btn, ft.Container(expand=True), self.start_batch_btn],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Container(
                content=self.status_text,
                padding=ft.padding.symmetric(vertical=8, horizontal=12),
                bgcolor=ft.Colors.BLUE_GREY_50,
                border_radius=8,
                border=ft.border.all(1, ft.Colors.GREY_300),
            ),
        )
        return page

    def _make_card(self, title, content):
        """创建统一的白色卡片容器。"""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        title,
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_GREY_700,
                        font_family=self.font_family,
                    ),
                    content,
                ],
                spacing=8,
            ),
            padding=ft.padding.all(12),
            border_radius=10,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )

    def _get_tk_root(self):
        """获取或创建隐藏的 Tk root（用于 CropDialog）。"""
        if self._tk_root is None or not self._tk_root.winfo_exists():
            self._tk_root = tk.Tk()
            self._tk_root.withdraw()
        return self._tk_root

    def browse_input(self, e):
        self.dir_input_picker.get_directory_path(dialog_title="选择包含待裁剪图片的目录")

    def on_dir_input_picked(self, e):
        if not e.path:
            return
        self.input_text.value = e.path
        self.input_text.color = ft.Colors.BLUE_GREY_900
        self.page.update()
        self.refresh_list(None)

    def browse_output(self, e):
        self.dir_output_picker.get_directory_path(dialog_title="选择裁剪结果输出目录")

    def on_dir_output_picked(self, e):
        if not e.path:
            return
        self.output_text.value = e.path
        self.output_text.color = ft.Colors.BLUE_GREY_900
        self.page.update()

    def refresh_list(self, e):
        """扫描输入目录并填充文件列表。"""
        folder = self.input_text.value
        if not folder or folder == "未选择目录" or not Path(folder).exists():
            self.show_status("请先选择有效的输入目录", success=False)
            return

        recursive = self.recursive_check.value
        files = []
        if recursive:
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

        self.file_list_view.controls.clear()
        for index, fpath in enumerate(files):
            row = ft.Container(
                content=ft.Row(
                    [
                        ft.Text(
                            fpath.name,
                            size=12,
                            font_family=self.font_family,
                            expand=True,
                            no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.IconButton(
                            ft.Icons.CROP_SQUARE,
                            icon_size=16,
                            tooltip="设为裁剪参考图",
                            on_click=lambda e, idx=index: self._open_crop_dialog_for(idx),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                ),
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                border_radius=6,
                bgcolor=ft.Colors.BLUE_GREY_50,
                on_click=lambda e, idx=index: self._open_crop_dialog_for(idx),
            )
            self.file_list_view.controls.append(row)

        self.empty_hint.visible = len(files) == 0
        suffix = "（含子目录）" if recursive else ""
        self.log(f"扫描到 {len(files)} 张图片{suffix}")
        self.page.update()

    def _open_crop_dialog_for(self, index):
        """打开 CropDialog 为指定图片设置裁剪参考。"""
        if index < 0 or index >= len(self.files):
            return
        path = self.files[index]
        tk_root = self._get_tk_root()
        dialog = CropDialog(tk_root, str(path), self.font_family)
        tk_root.wait_window(dialog)
        if dialog._img is not None:
            dialog._img.close()
        box = dialog.result_box
        if not box:
            return
        with Image.open(str(path)) as probe:
            self.ref_size = probe.size
        self.crop_box = box
        l, t, r, b = box
        self.ref_info_text.value = (
            f"参考图：{Path(path).name}（{self.ref_size[0]}×{self.ref_size[1]}）  "
            f"裁剪区域：Left={l} Top={t} Right={r} Bottom={b}（宽 {r - l}px × 高 {b - t}px）"
        )
        self.ref_info_text.color = ft.Colors.GREEN_800
        self.ref_info_text.update()
        self.log(f"已记录裁剪区域（来自 {Path(path).name}）：({l}, {t}, {r}, {b})")

    def crop_first_image(self, e):
        if not self.files:
            self.show_status("列表为空，请先选择输入目录并刷新列表", success=False)
            return
        self._open_crop_dialog_for(0)

    def start_batch(self, e):
        if self._busy:
            return
        if not self.crop_box or not self.ref_size:
            self.show_status("请先点击「裁剪第一张」，框选并确定裁剪区域", success=False)
            return
        if not self.files:
            self.show_status("图片列表为空，请先选择输入目录并刷新列表", success=False)
            return

        input_dir = self.input_text.value
        if not input_dir or input_dir == "未选择目录":
            self.show_status("请先选择输入目录", success=False)
            return

        output_raw = self.output_text.value
        if not output_raw or output_raw.startswith("未选择"):
            output_raw = str(Path(input_dir) / "裁剪结果_crop")
            self.output_text.value = output_raw
            self.output_text.color = ft.Colors.BLUE_GREY_900
            self.log(f"输出目录为空，将输出到：{output_raw}")

        out_dir = Path(output_raw)
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            self.show_status(f"无法创建输出目录：{exc}", success=False)
            return

        self._busy = True
        self.start_batch_btn.disabled = True
        self.crop_first_btn.disabled = True
        self.progress.value = 0
        self.progress.visible = True
        total = len(self.files)
        self.progress_text.value = f"0/{total}"
        self.log(f"开始批量裁剪，共 {total} 张图片，输出目录：{out_dir}")

        threading.Thread(
            target=self._worker,
            args=(list(self.files), out_dir),
            daemon=True,
        ).start()

    def _worker(self, files, out_dir):
        ok = 0
        failed = []
        for index, path in enumerate(files, start=1):
            try:
                with Image.open(str(path)) as img:
                    width, height = img.size
                    box = self._compute_box(width, height)
                    cropped = img.crop(box)
                    suffix = path.suffix.lower() or ".png"
                    out_path = self._unique_out_path(out_dir, path.stem, suffix)
                    self._save_cropped(cropped, out_path)
                ok += 1
                msg = f"[{index}/{len(files)}] {path.name}  ({width}x{height} -> {cropped.width}x{cropped.height})"
            except Exception as exc:
                failed.append(str(path))
                msg = f"[{index}/{len(files)}] {path.name}  失败：{exc}"
            self._append_log(msg)
            self._update_progress(index, len(files))

        self._finish_batch(ok, failed, out_dir)

    def _compute_box(self, width, height):
        """根据参考框与所选模式，计算当前尺寸图片的裁剪框。"""
        l, t, r, b = self.crop_box
        ref_w, ref_h = self.ref_size
        mode = int(self.mode_group.value)
        if mode == 1:  # 固定像素
            box = (l, t, r, b)
        elif mode == 2:  # 相对比例
            box = (
                round(l / ref_w * width),
                round(t / ref_h * height),
                round(r / ref_w * width),
                round(b / ref_h * height),
            )
        else:  # 自动
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

    @staticmethod
    def _unique_out_path(out_dir, stem, suffix):
        candidate = out_dir / f"{stem}_crop{suffix}"
        counter = 1
        while candidate.exists():
            candidate = out_dir / f"{stem}_crop_{counter}{suffix}"
            counter += 1
        return candidate

    @staticmethod
    def _save_cropped(img, out_path):
        suffix = out_path.suffix.lower()
        save_img = img
        if suffix in (".jpg", ".jpeg") and img.mode not in ("RGB", "L"):
            save_img = img.convert("RGB")
        save_img.save(out_path)

    def _update_progress(self, done, total):
        self.progress.value = done / total
        self.progress_text.value = f"{done}/{total}"
        self.progress.update()
        self.progress_text.update()

    def _finish_batch(self, ok, failed, out_dir):
        self._busy = False
        self.start_batch_btn.disabled = False
        self.crop_first_btn.disabled = False
        self.progress.value = 0
        self.progress.visible = False
        self.progress.update()
        self.progress_text.update()

        msg = f"批量裁剪完成：成功 {ok} 张"
        if failed:
            msg += f"，失败 {len(failed)} 张"
        self.log(msg)
        self.show_status(msg)

        summary = f"批量裁剪完成！成功 {ok} 张"
        if failed:
            summary += f"\n失败 {len(failed)} 张："
            for item in failed[:10]:
                summary += f"\n  {item}"
        summary += f"\n\n输出目录：\n{out_dir}"
        self.show_info("完成", summary)

    def _append_log(self, message):
        """线程安全地追加日志。"""
        current = self.log_field.value or ""
        self.log_field.value = current + message + "\n"
        self.log_field.update()

    def log(self, message):
        self._append_log(message)

    def show_status(self, message: str, success: bool = True):
        """更新状态栏并显示全局提示消息。"""
        self.status_text.value = message
        self.page.snack_bar = ft.SnackBar(
            ft.Text(message, font_family=self.font_family),
            bgcolor=ft.Colors.GREEN if success else ft.Colors.RED,
            open=True,
        )
        self.page.update()

    def show_info(self, title: str, message: str):
        """显示结果弹窗。"""
        self.page.dialog = ft.AlertDialog(
            title=ft.Text(title, font_family=self.font_family),
            content=ft.Text(message, font_family=self.font_family),
            actions=[ft.TextButton("关闭", on_click=lambda e: self.close_dialog())],
        )
        self.page.dialog.open = True
        self.page.update()

    def close_dialog(self, e=None):
        """关闭当前对话框。"""
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()


if __name__ == '__main__':
    app = ImageBatchCropApp()
    ft.app(target=app.build)
