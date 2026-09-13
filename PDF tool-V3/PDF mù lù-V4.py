# -*- coding: utf-8 -*-
# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import threading
import importlib.util
from pathlib import Path
from math import ceil

import flet as ft

FONT_TTF_NAME = 'AlibabaPuHuiTi-3-55-RegularL3.ttf'


def get_project_root():
    """获取项目根目录"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def run_startup_preflight():
    """复用 Core 公共基类执行启动前置流程：授权检查 -> 窗口图标 -> 字体加载；失败时直接报错"""
    base_file = get_project_root() / 'Core' / 'Public base class.py'
    if not base_file.exists():
        raise FileNotFoundError(f"缺少公共基类：{base_file}")

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

        font_family = current_font[0]
        return True, font_family
    except Exception as exc:
        if root.winfo_exists():
            root.destroy()
        raise RuntimeError(f"启动前置检查失败：无法使用项目自带字体。{exc}") from exc
    finally:
        if root.winfo_exists():
            root.destroy()


STARTUP_OK, APP_FONT_FAMILY = run_startup_preflight()
if not STARTUP_OK:
    raise RuntimeError("启动前置检查失败：项目自带字体无法使用")

# PyMuPDF：读取书签、创建目录页、插入内部跳转链接（本地已安装）
import fitz


def get_font_file_path():
    """项目自带字体文件路径（用于 PDF 内文本绘制）"""
    return get_project_root() / 'Image' / FONT_TTF_NAME


class PDFTOCApp:
    """PDF目录：读取 PDF 书签，在文档最前生成可点击跳转的目录页"""

    PREVIEW_LIMIT = 500   # 界面书签预览最多显示的条目数
    MAX_INDENT_LEVEL = 5  # 目录缩进最多应用的层级深度

    def __init__(self):
        self.page = None
        self.input_file = None
        self.bookmarks = []          # [(lvl, title, page), ...]
        self.font_family = APP_FONT_FAMILY
        self.processing = False
        self._fitz_font = None

    # ---------- 界面 ----------
    def build(self, page: ft.Page):
        self.page = page
        page.title = "PDF目录"
        page.window.width = 680
        page.window.height = 760
        page.window.min_width = 600
        page.window.min_height = 640
        page.window.center()
        page.padding = 16
        page.theme_mode = ft.ThemeMode.LIGHT

        # 设置窗口图标
        icon_path = get_project_root() / 'Image' / 'icon.ico'
        if icon_path.exists():
            page.window.icon = str(icon_path)

        # 文件选择 / 保存对话框
        self.file_picker = ft.FilePicker(on_result=self.on_file_picked)
        self.save_picker = ft.FilePicker(on_result=self.on_save_picked)
        page.overlay.extend([self.file_picker, self.save_picker])

        # PDF文件选择卡片
        self.file_text = ft.Text(
            "未选择文件",
            size=13,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
            expand=True,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        file_card = self._make_card(
            "PDF文件",
            ft.Row(
                [
                    ft.Icon(ft.Icons.INSERT_DRIVE_FILE, size=18, color=ft.Colors.BLUE_GREY_400),
                    self.file_text,
                    ft.ElevatedButton("选择文件", icon=ft.Icons.UPLOAD_FILE, on_click=self.select_file),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
        )

        # 书签信息与预览卡片
        self.bookmark_stat = ft.Text(
            "请选择 PDF 文件后自动读取书签",
            size=13,
            color=ft.Colors.BLUE_GREY_700,
            font_family=self.font_family,
        )
        self.preview_col = ft.Column(spacing=2)
        preview_box = ft.Container(
            content=ft.Column(
                [self.preview_col],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            height=180,
            padding=ft.padding.all(10),
            border_radius=8,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )
        bookmarks_card = self._make_card(
            "书签内容（将生成可点击的目录）",
            ft.Column(
                [self.bookmark_stat, preview_box],
                spacing=8,
            ),
        )

        # 目录样式设置卡片
        self.title_field = ft.TextField(
            label="目录标题",
            value="目录",
            border_radius=8,
            content_padding=ft.padding.all(10),
            text_size=14,
            text_style=ft.TextStyle(font_family=self.font_family),
        )
        self.size_drop = ft.Dropdown(
            label="字体大小",
            value="11",
            border_radius=8,
            content_padding=ft.padding.symmetric(horizontal=10),
            text_size=14,
            options=[ft.dropdown.Option(str(v)) for v in (9, 10, 11, 12, 13, 14)],
        )
        self.show_page_switch = ft.Switch(
            label="目录项右侧显示页码",
            value=True,
            active_color=ft.Colors.BLUE,
        )
        options_card = self._make_card(
            "目录样式",
            ft.Column(
                [
                    ft.Row([self.title_field, self.size_drop], spacing=12),
                    self.show_page_switch,
                ],
                spacing=6,
            ),
        )

        # 进度条与操作按钮
        self.progress = ft.ProgressBar(
            visible=False,
            color=ft.Colors.BLUE,
            bgcolor=ft.Colors.GREY_200,
            bar_height=6,
            border_radius=4,
            expand=True,
        )
        self.progress_text = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)
        self.gen_button = ft.ElevatedButton(
            "生成目录",
            icon=ft.Icons.MENU_BOOK,
            on_click=self.generate_toc,
            height=40,
        )

        # 底部状态栏
        self.status_text = ft.Text("就绪", size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)
        self.stats_text = ft.Text(size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)

        page.add(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.MENU_BOOK, size=32, color=ft.Colors.BLUE),
                            ft.Text("PDF目录", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Divider(thickness=1, opacity=0.3),
                    file_card,
                    bookmarks_card,
                    options_card,
                    ft.Row(
                        [self.progress, self.progress_text],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Row([self.gen_button], alignment=ft.MainAxisAlignment.END),
                    ft.Container(
                        content=ft.Row(
                            [self.status_text, self.stats_text],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=ft.padding.symmetric(vertical=8, horizontal=12),
                        bgcolor=ft.Colors.BLUE_GREY_50,
                        border_radius=8,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                    ),
                ],
                expand=True,
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            )
        )

    def _make_card(self, title, content):
        """创建白色圆角卡片（与主程序工具卡片风格一致）"""
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

    # ---------- 文件选择与书签读取 ----------
    def select_file(self, e):
        self.file_picker.pick_files(
            dialog_title="选择PDF文件",
            allow_multiple=False,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["pdf"],
        )

    def on_file_picked(self, e):
        if not e.files:
            return
        file = e.files[0].path
        if not os.path.exists(file):
            self.show_status("文件不存在", success=False)
            return
        if not file.lower().endswith('.pdf'):
            self.show_status("请选择PDF文件", success=False)
            return
        self.input_file = file
        self.bookmarks = []
        self.file_text.value = os.path.basename(file)
        self.file_text.color = ft.Colors.BLUE_GREY_900
        self.file_text.tooltip = file
        self.stats_text.value = ""
        self._reset_preview("正在读取书签...")
        self.page.update()
        threading.Thread(target=self._load_bookmarks, daemon=True).start()

    def _reset_preview(self, text):
        self.bookmark_stat.value = text
        self.preview_col.controls.clear()

    def _load_bookmarks(self):
        """后台线程读取 PDF 书签并刷新预览"""
        try:
            doc = fitz.open(self.input_file)
            if doc.needs_pass:
                doc.close()
                self.show_status("PDF 已加密，请先解除密码保护", success=False)
                return
            total_pages = doc.page_count
            toc = doc.get_toc(simple=True)  # [[level, title, page], ...]，page 从 1 开始
            doc.close()
        except Exception as err:
            self.show_status(f"读取书签失败: {err}", success=False)
            return

        self.bookmarks = toc
        if not toc:
            self._reset_preview("该 PDF 没有书签，无法从书签生成目录。")
            self.show_status("未找到书签，无法生成目录", success=False)
            return

        max_level = max((item[0] for item in toc), default=1)
        self.bookmark_stat.value = f"共 {total_pages} 页 · 发现 {len(toc)} 个书签 · 最大 {max_level} 级"
        rows = []
        for idx, item in enumerate(toc[:self.PREVIEW_LIMIT]):
            level = max(1, int(item[0]))
            title = str(item[1]).replace('\n', ' ').replace('\r', ' ').strip() or "(无标题)"
            page_num = int(item[2])
            indent = '　' * min(level - 1, self.MAX_INDENT_LEVEL)
            rows.append(
                ft.Text(
                    f"{indent}{title}   · 第 {page_num} 页",
                    size=12,
                    color=ft.Colors.BLUE_GREY_800,
                    font_family=self.font_family,
                    no_wrap=False,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                )
            )
        if len(toc) > self.PREVIEW_LIMIT:
            rows.append(
                ft.Text(
                    f"… 共 {len(toc)} 项，仅预览前 {self.PREVIEW_LIMIT} 项",
                    size=12,
                    color=ft.Colors.BLUE_GREY_500,
                    font_family=self.font_family,
                )
            )
        self.preview_col.controls = rows
        self.show_status(f"已读取 {len(toc)} 个书签，点击\"生成目录\"开始")
        self.page.update()

    # ---------- 生成目录 ----------
    def generate_toc(self, e):
        if self.processing:
            return
        if not self.input_file:
            self.show_status("请先选择PDF文件", success=False)
            return
        if not os.path.exists(self.input_file):
            self.show_status("PDF文件不存在", success=False)
            return
        if not self.bookmarks:
            self.show_status("该 PDF 没有书签，无法从书签生成目录", success=False)
            return

        base_name = os.path.splitext(os.path.basename(self.input_file))[0]
        self.save_picker.save_file(
            dialog_title="保存带目录的PDF",
            file_name=f"{base_name}_目录.pdf",
            allowed_extensions=["pdf"],
        )

    def on_save_picked(self, e):
        if not e.path:
            return
        output_path = e.path
        if not output_path.lower().endswith('.pdf'):
            output_path += '.pdf'

        # 后台线程执行生成，避免阻塞 UI；PyMuPDF 处理时会释放 GIL
        self.processing = True
        self.gen_button.disabled = True
        self.progress.value = 0
        self.progress.visible = True
        self.progress_text.value = ""
        self.show_status("正在生成目录...")

        threading.Thread(
            target=self._do_generate,
            args=(output_path,),
            daemon=True,
        ).start()

    def _load_font(self):
        """懒加载 PyMuPDF 字体对象（仅在工作线程内使用）"""
        if self._fitz_font is None:
            font_path = get_font_file_path()
            if not font_path.exists():
                raise FileNotFoundError(f"项目自带字体不存在：{font_path}")
            self._fitz_font = fitz.Font(fontfile=str(font_path))
        return self._fitz_font

    @staticmethod
    def _truncate_by_width(text, max_w, font, font_size):
        """按像素宽度截断文本并追加省略号，避免目录项溢出页面"""
        if max_w <= 8:
            return text[:1]
        if font.text_length(text, fontsize=font_size) <= max_w:
            return text
        suffix = '…'
        low, high = 1, len(text)
        while low < high:
            mid = (low + high + 1) // 2
            if font.text_length(text[:mid] + suffix, fontsize=font_size) <= max_w:
                low = mid
            else:
                high = mid - 1
        cut = max(low, 1)
        return text[:cut] + suffix

    def _do_generate(self, output_path):
        """核心逻辑：读取书签 -> 生成目录页 -> 插入文档最前 -> 添加可点击跳转链接 -> 保存"""
        try:
            title_text = (self.title_field.value or "").strip() or "目录"
            font_size = float(self.size_drop.value or "11")
            show_pages = bool(self.show_page_switch.value)

            doc = fitz.open(self.input_file)
            try:
                if doc.needs_pass:
                    raise RuntimeError("PDF 已加密，请先解除密码保护")
                if doc.page_count == 0:
                    raise RuntimeError("PDF 文件没有有效页面")
                toc = doc.get_toc(simple=True)
                if not toc:
                    raise RuntimeError("未找到书签，无法生成目录")

                # 页面布局参数（以文档首页尺寸为准）
                page_rect = doc[0].rect
                page_w, page_h = page_rect.width, page_rect.height
                font = self._load_font()
                margin_x, margin_y = 55.0, 45.0
                header_size = font_size + 5.0
                header_y = margin_y + 14.0 + header_size
                divider_y = header_y + 10.0
                line_h = max(font_size * 1.9, font_size + 13.0)
                content_start = divider_y + line_h * 0.55
                usable_bottom = page_h - margin_y

                # 每页可容纳的目录行数（保证首尾留白）
                rows_per_page = max(1, int((usable_bottom - content_start) // line_h))

                # 组装展示行：缩进 + 截断标题（按像素宽度自适应）
                inner_w = page_w - 2 * margin_x
                rows = []
                for item in toc:
                    level = max(1, int(item[0]))
                    raw_title = str(item[1]).replace('\n', ' ').replace('\r', ' ').strip() or "(无标题)"
                    page_num = max(1, int(item[2]))
                    indent_w = min(level - 1, self.MAX_INDENT_LEVEL) * (font_size * 1.6)
                    page_str = str(page_num)
                    page_w_chars_w = font.text_length(page_str, fontsize=font_size) + 14.0
                    avail_title_w = inner_w - indent_w - (page_w_chars_w if show_pages else 0.0)
                    rows.append({
                        'level': level,
                        'indent': indent_w,
                        'title': self._truncate_by_width(raw_title, avail_title_w, font, font_size),
                        'page': page_num,
                        'page_str': page_str,
                    })

                total_items = len(rows)
                dir_page_count = max(1, ceil(total_items / rows_per_page))

                # 在文档最前连续插入目录页（按索引递增插入保证顺序）
                for i in range(dir_page_count):
                    doc.new_page(pno=i, width=page_w, height=page_h)
                    self._update_progress(0.4 * (i + 1) / dir_page_count,
                                          f"插入目录页 {i + 1}/{dir_page_count}")

                # 逐页绘制目录内容，并记录每个条目的可点击区域
                links = []  # (目录页索引, 矩形, 目标页码1-based)
                body_color = (0.10, 0.16, 0.28)      # 深蓝灰正文
                page_color = (0.45, 0.52, 0.62)      # 页码灰蓝
                divider_color = (0.55, 0.62, 0.72)
                for di in range(dir_page_count):
                    pg = doc[di]
                    header_text = title_text if di == 0 else f"{title_text}（续）"

                    # 标题区：居中标题 + 分隔线（正文与页码分用两个 TextWriter 实现不同颜色）
                    tw_body = fitz.TextWriter(pg.rect, color=body_color)
                    tw_pages = fitz.TextWriter(pg.rect, color=page_color)
                    h_w = font.text_length(header_text, fontsize=header_size)
                    tw_body.append(((page_w - h_w) / 2, header_y), header_text,
                                   font=font, fontsize=header_size)
                    pg.draw_line(
                        fitz.Point(margin_x, divider_y),
                        fitz.Point(page_w - margin_x, divider_y),
                        color=divider_color,
                        width=0.8,
                    )

                    start = di * rows_per_page
                    end = min(start + rows_per_page, total_items)
                    y = content_start
                    for row in rows[start:end]:
                        x0 = margin_x + row['indent']
                        rect_top = y - font_size
                        rect_bottom = y + (font_size * 0.9)
                        if show_pages:
                            pw = font.text_length(row['page_str'], fontsize=font_size)
                            tw_pages.append((page_w - margin_x - pw, y), row['page_str'],
                                            font=font, fontsize=font_size)
                        tw_body.append((x0, y), row['title'], font=font, fontsize=font_size)
                        # 整行区域可点击，跳转到对应章节
                        links.append((di, fitz.Rect(margin_x, rect_top, page_w - margin_x, rect_bottom),
                                      row['page']))
                        y += line_h
                    tw_pages.write_text(pg)
                    tw_body.write_text(pg)
                    self._update_progress(
                        0.4 + 0.5 * (di + 1) / dir_page_count,
                        f"绘制目录 {di + 1}/{dir_page_count}",
                    )

                # 添加可点击跳转链接：目录页在前，正文整体后移 dir_page_count 页
                total_pages = doc.page_count
                fixed = 0
                for di, rect, target_1based in links:
                    dest = dir_page_count + target_1based - 1
                    if dest < dir_page_count:
                        dest = dir_page_count
                    dest = min(dest, total_pages - 1)
                    pg = doc[di]
                    pg.insert_link({
                        "kind": fitz.LINK_GOTO,
                        "from": rect,
                        "page": dest,
                        "to": fitz.Point(0.0, 0.0),
                        "zoom": 0.0,
                    })
                    fixed += 1

                self._update_progress(0.93, "保存文件...")
                # 保持原始对象不压缩、原样继承原文档书签；仅做基础清理
                doc.save(output_path, garbage=4, deflate=True)
                doc.close()
                self._update_progress(1.0, f"共 {fixed} 个跳转链接")

                self.processing = False
                self.gen_button.disabled = False
                self.gen_button.update()
                self.show_status("PDF目录生成完成")
                self.show_info(
                    "成功",
                    f"PDF目录生成完成!\n"
                    f"书签条目：{total_items} 项\n"
                    f"目录页数：{dir_page_count} 页（已插入文档最前）\n"
                    f"跳转链接：{fixed} 个\n"
                    f"保存到: {output_path}",
                    open_folder=os.path.dirname(output_path) if output_path else None,
                )
            except Exception as err:
                try:
                    doc.close()
                except Exception:
                    pass
                raise
        except Exception as err:
            self.show_status(f"生成目录失败: {err}", success=False)
        finally:
            self.processing = False
            self.gen_button.disabled = False
            self.gen_button.update()

    # ---------- 工具方法 ----------
    def _update_progress(self, value, text=""):
        """更新进度条与进度文本"""
        self.progress.value = max(0.0, min(1.0, value))
        if text:
            self.progress_text.value = text
        self.progress.update()
        self.progress_text.update()

    def show_status(self, message: str, success: bool = True):
        """显示状态消息（底部状态栏 + SnackBar）"""
        self.status_text.value = message
        self.page.snack_bar = ft.SnackBar(
            ft.Text(message, font_family=self.font_family),
            bgcolor=ft.Colors.GREEN if success else ft.Colors.RED,
            open=True,
        )
        self.page.update()

    def show_info(self, title: str, message: str, open_folder: str = None):
        """显示信息对话框，可选附带\"打开文件夹\"按钮"""
        actions = []
        if open_folder:
            def _open(e, path=open_folder):
                try:
                    os.startfile(path)
                except Exception:
                    pass
                self.close_dialog()
            actions.append(ft.TextButton("打开所在文件夹", on_click=_open))
        actions.append(ft.TextButton("关闭", on_click=lambda e: self.close_dialog()))
        self.page.dialog = ft.AlertDialog(
            title=ft.Text(title, font_family=self.font_family),
            content=ft.Text(message, font_family=self.font_family),
            actions=actions,
        )
        self.page.dialog.open = True
        self.page.update()

    def close_dialog(self, e=None):
        """关闭对话框"""
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()


if __name__ == '__main__':
    app = PDFTOCApp()
    ft.app(target=app.build)
