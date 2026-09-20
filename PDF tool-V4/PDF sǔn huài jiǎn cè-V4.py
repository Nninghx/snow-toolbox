# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import threading
import importlib.util
from datetime import datetime
from pathlib import Path

import flet as ft

import pikepdf


def get_project_root():
    """获取项目根目录"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def _resolve_base_class_path():
    """解析公共基类文件路径，打包后自动使用 .pyc 字节码"""
    base_py = get_project_root() / 'Core' / 'Public base class.py'
    if getattr(sys, 'frozen', False):
        import importlib.util
        return Path(importlib.util.cache_from_source(str(base_py)))
    return base_py


def run_startup_preflight():
    """复用 Core 公共基类执行启动前置流程：授权检查 -> 窗口图标 -> 字体加载；失败时直接报错"""
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


# qpdf 语法检查中代表“结构已损坏”的关键信息
_SEVERE_HINTS = (
    'file is damaged',
    'can\'t find startxref',
    'unable to find trailer',
    'unable to recover',
    'expected endobj',
    'EOF after endobj',
)


class PDFDamageCheckApp:
    def __init__(self):
        self.page = None
        self.files = []  # [{'path','name','size','code','detail','…控件引用'}]
        self.processing = False
        self.font_family = APP_FONT_FAMILY

    # ---------- UI 构建 ----------
    def build(self, page: ft.Page):
        self.page = page
        page.title = "PDF损坏检测"
        page.window.width = 920
        page.window.height = 720
        page.window.min_width = 800
        page.window.min_height = 600
        page.window.center()
        page.padding = 16
        page.theme_mode = ft.ThemeMode.LIGHT

        # 设置窗口图标
        icon_path = get_project_root() / 'Image' / 'icon.ico'
        if icon_path.exists():
            page.window.icon = str(icon_path)

        # 文件选择 / 目录选择 / 报告保存对话框
        self.file_picker = ft.FilePicker(on_result=self.on_files_picked)
        self.dir_picker = ft.FilePicker(on_result=self.on_dir_picked)
        self.save_picker = ft.FilePicker(on_result=self.on_save_picked)
        page.overlay.extend([self.file_picker, self.dir_picker, self.save_picker])

        # 工具栏：添加文件 / 添加文件夹 / 清空列表 / 统计信息
        self.add_btn = ft.ElevatedButton(
            "添加文件",
            icon=ft.Icons.ADD_CIRCLE_OUTLINE,
            on_click=self.add_files,
            height=36,
        )
        self.add_dir_btn = ft.ElevatedButton(
            "添加文件夹",
            icon=ft.Icons.CREATE_NEW_FOLDER_OUTLINED,
            on_click=self.add_folder,
            height=36,
        )
        self.clear_btn = ft.TextButton(
            "清空列表",
            icon=ft.Icons.DELETE_SWEEP,
            on_click=self.confirm_clear,
        )
        self.stats_text = ft.Text(size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)
        toolbar_card = self._make_card(
            "文件操作",
            ft.Row(
                [
                    self.add_btn,
                    self.add_dir_btn,
                    self.clear_btn,
                    ft.Container(expand=True),
                    self.stats_text,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
        )

        # 待检测列表卡片（可扩展滚动）
        self.file_rows = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
        self.empty_hint = ft.Text(
            "暂无文件，点击「添加文件」或「添加文件夹」选择要检测的PDF",
            size=13,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
            text_align=ft.TextAlign.CENTER,
        )
        list_card = self._make_card(
            "待检测文件列表",
            ft.Column(
                [self._list_header_row(), self.file_rows, self.empty_hint],
                spacing=8,
                expand=True,
            ),
            expand=True,
        )

        # 检测设置卡片：深度检测开关
        self.deep_switch = ft.Switch(value=False, active_color=ft.Colors.BLUE)
        self.deep_switch.label_style = ft.TextStyle(font_family=self.font_family, size=14)
        setting_card = self._make_card(
            "检测设置",
            ft.Row(
                [
                    ft.Text("深度检测", size=14, font_family=self.font_family),
                    self.deep_switch,
                    ft.Text(
                        "开启后将逐页读取内容流，可发现结构完整但页面内容已损坏的文件（速度较慢）",
                        size=12,
                        color=ft.Colors.BLUE_GREY_500,
                        font_family=self.font_family,
                        expand=True,
                        no_wrap=True,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        tooltip="开启后将逐页读取内容流，可发现结构完整但页面内容已损坏的文件（速度较慢）",
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
        )

        # 进度条与按钮区
        self.progress = ft.ProgressBar(
            visible=False,
            color=ft.Colors.BLUE,
            bgcolor=ft.Colors.GREY_200,
            bar_height=6,
            border_radius=4,
            expand=True,
        )
        self.progress_text = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)
        self.export_btn = ft.TextButton(
            "导出报告",
            icon=ft.Icons.DOWNLOAD,
            disabled=True,
            on_click=self.export_report,
        )
        self.filter_drop = ft.Dropdown(
            width=130,
            value='all',
            dense=True,
            text_size=13,
            on_change=lambda e: self._refresh_file_list(),
            options=[
                ft.dropdown.Option('all', '全部结果'),
                ft.dropdown.Option('bad', '仅损坏'),
                ft.dropdown.Option('warn', '仅警告'),
                ft.dropdown.Option('ok', '仅正常'),
            ],
        )
        self.check_btn = ft.ElevatedButton(
            "开始检测",
            icon=ft.Icons.FACT_CHECK,
            on_click=self.start_check,
            height=40,
        )

        # 底部状态栏
        self.status_text = ft.Text("就绪", size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)

        page.add(
            ft.Column(
                [
                    # 顶部标题栏
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.HEALTH_AND_SAFETY, size=32, color=ft.Colors.BLUE),
                            ft.Text("PDF损坏检测", size=28, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Divider(thickness=1, opacity=0.3),
                    toolbar_card,
                    list_card,
                    setting_card,
                    ft.Row(
                        [self.progress, self.progress_text],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Row(
                        [
                            self.export_btn,
                            self.filter_drop,
                            ft.Container(expand=True),
                            self.check_btn,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    # 底部状态栏
                    ft.Container(
                        content=self.status_text,
                        padding=ft.padding.symmetric(vertical=8, horizontal=12),
                        bgcolor=ft.Colors.BLUE_GREY_50,
                        border_radius=8,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                    ),
                ],
                expand=True,
                spacing=10,
            )
        )
        self._refresh_file_list()

    def _make_card(self, title, content, expand=False):
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
                expand=bool(expand),
            ),
            padding=ft.padding.all(12),
            border_radius=10,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
            expand=expand,
        )

    def _list_header_row(self):
        """列表表头：序号 / 文件名 / 大小 / 结果 / 详情 / 操作"""
        style = ft.TextStyle(
            size=12,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_GREY_600,
            font_family=self.font_family,
        )
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(ft.Text("序号", style=style), width=34, alignment=ft.alignment.center),
                    ft.Text("文件名", style=style, expand=True),
                    ft.Container(ft.Text("大小", style=style), width=70, alignment=ft.alignment.center),
                    ft.Container(ft.Text("结果", style=style), width=60, alignment=ft.alignment.center),
                    ft.Container(ft.Text("详情", style=style), width=360, alignment=ft.alignment.center),
                    ft.Container(ft.Text("操作", style=style), width=30, alignment=ft.alignment.center),
                ],
                spacing=8,
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
        )

    def _build_file_row(self, index, item):
        """构建单个文件行：序号徽章 + 文件名 + 大小 + 结果 + 详情 + 删除按钮"""
        order_badge = ft.Container(
            content=ft.Text(
                str(index + 1),
                size=12,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.WHITE,
                font_family=self.font_family,
            ),
            width=24,
            height=24,
            border_radius=12,
            bgcolor=ft.Colors.BLUE,
            alignment=ft.alignment.center,
        )
        name_text = ft.Text(
            item['name'],
            size=13,
            font_family=self.font_family,
            expand=True,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
            tooltip=item['path'],
        )
        size_text = ft.Text(
            self._format_size(item['size']),
            size=12,
            color=ft.Colors.BLUE_GREY_700,
            font_family=self.font_family,
        )
        result_text = ft.Text(
            "待检测",
            size=12,
            color=ft.Colors.BLUE_GREY_600,
            font_family=self.font_family,
        )
        detail_text = ft.Text(
            "-",
            size=12,
            color=ft.Colors.BLUE_GREY_500,
            font_family=self.font_family,
            expand=False,
            width=360,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
            tooltip="",
        )
        del_btn = ft.IconButton(
            ft.Icons.DELETE_OUTLINE,
            icon_size=18,
            width=30,
            height=30,
            icon_color=ft.Colors.RED_400,
            tooltip="移除",
            disabled=self.processing,
            on_click=lambda e, i=index: self.remove_file(i),
        )
        # 保存行内动态控件引用，供后台检测线程更新
        item.update({
            'result_text': result_text,
            'detail_text': detail_text,
            'del_btn': del_btn,
        })
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(order_badge, width=34, alignment=ft.alignment.center),
                    name_text,
                    ft.Container(size_text, width=70, alignment=ft.alignment.center),
                    ft.Container(result_text, width=60, alignment=ft.alignment.center),
                    ft.Container(detail_text, width=360, alignment=ft.alignment.center),
                    ft.Container(del_btn, width=30),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            border_radius=8,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )

    def _refresh_file_list(self):
        """重建文件列表与统计信息（支持结果筛选）"""
        filter_mode = self.filter_drop.value if hasattr(self, 'filter_drop') else 'all'
        self.file_rows.controls.clear()
        shown = 0
        for index, item in enumerate(self.files):
            code = item.get('code', 'pending')
            if filter_mode != 'all' and code != filter_mode:
                continue
            self.file_rows.controls.append(self._build_file_row(index, item))
            shown += 1
        self.empty_hint.visible = not self.files
        if self.files:
            total_size = sum(item['size'] for item in self.files)
            count_text = f"共 {len(self.files)} 个文件，合计 {self._format_size(total_size)}"
            if filter_mode != 'all':
                count_text += f"（筛选显示 {shown} 个）"
            self.stats_text.value = count_text
        else:
            self.stats_text.value = ""
        self.page.update()

    # ---------- 文件 / 文件夹添加 ----------
    def add_files(self, e):
        if self.processing:
            return
        self.file_picker.pick_files(
            dialog_title="选择PDF文件",
            allow_multiple=True,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["pdf"],
        )

    def on_files_picked(self, e):
        if not e.files:
            return
        added, skipped = 0, 0
        existing_paths = {item['path'] for item in self.files}
        for picked in e.files:
            file = picked.path
            if self._append_file(file, os.path.basename(file), existing_paths):
                added += 1
            else:
                skipped += 1
        self._refresh_file_list()
        if added:
            self.show_status(f"已添加 {added} 个文件" + (f"，跳过 {skipped} 个" if skipped else ""))
        elif skipped:
            self.show_status("所选文件均无法添加", success=False)

    def add_folder(self, e):
        if self.processing:
            return
        self.dir_picker.get_directory_path(dialog_title="选择包含PDF文件的文件夹")

    def on_dir_picked(self, e):
        if not e.path:
            return
        folder = e.path
        self.show_status(f"正在扫描文件夹：{folder}...")
        threading.Thread(
            target=self._scan_and_add_folder,
            args=(folder,),
            daemon=True,
        ).start()

    def _scan_and_add_folder(self, folder):
        """后台线程：递归扫描文件夹中的全部 PDF 并加入列表"""
        existing_paths = {item['path'] for item in self.files}
        found = added = skipped = 0
        try:
            for root, dirs, names in os.walk(folder):
                # 跳过隐藏目录，减少无用扫描
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for name in names:
                    if not name.lower().endswith('.pdf'):
                        continue
                    found += 1
                    file = os.path.join(root, name)
                    rel = os.path.relpath(file, folder)
                    display = rel if os.sep in rel or '/' in rel else name
                    if self._append_file(file, display, existing_paths):
                        added += 1
                    else:
                        skipped += 1
        except Exception as err:
            self.show_status(f"扫描文件夹失败: {err}", success=False)
            return
        self._refresh_file_list()
        if added:
            self.show_status(f"文件夹扫描完成：找到 {found} 个PDF，已添加 {added} 个" +
                             (f"，跳过 {skipped} 个" if skipped else ""))
        else:
            self.show_status(f"未添加新文件：找到 {found} 个PDF，均已在列表中或无法添加", success=False)

    def _append_file(self, file, display_name, existing_paths):
        """向列表追加一个文件；无法添加/重复返回 False"""
        if not os.path.exists(file) or file in existing_paths:
            return False
        if not file.lower().endswith('.pdf'):
            return False
        try:
            size = os.path.getsize(file)
        except Exception:
            return False
        self.files.append({
            'path': file,
            'name': display_name,
            'size': size,
            'code': 'pending',
            'detail': None,
        })
        existing_paths.add(file)
        return True

    # ---------- 列表管理 ----------
    def remove_file(self, index):
        """移除单个文件"""
        if self.processing:
            return
        # 根据真实列表下标定位被移除项
        if 0 <= index < len(self.files):
            item = self.files.pop(index)
            self._refresh_file_list()
            self.show_status(f"已移除：{item['name']}")

    def confirm_clear(self, e):
        """清空列表前弹窗确认"""
        if self.processing or not self.files:
            return
        self.page.dialog = ft.AlertDialog(
            title=ft.Text("确认", font_family=self.font_family),
            content=ft.Text("确定要清空文件列表吗？", font_family=self.font_family),
            actions=[
                ft.TextButton("取消", on_click=lambda e: self.close_dialog()),
                ft.TextButton("确定", on_click=lambda e: self.do_clear()),
            ],
        )
        self.page.dialog.open = True
        self.page.update()

    def do_clear(self):
        """清空所有文件"""
        self.close_dialog()
        self.files.clear()
        self._refresh_file_list()
        self.export_btn.disabled = True
        self.show_status("已清空文件列表")

    @staticmethod
    def _format_size(size):
        """格式化文件大小"""
        for unit in ('B', 'KB', 'MB', 'GB'):
            if size < 1024 or unit == 'GB':
                return f"{size:.1f} {unit}"
            size /= 1024

    # ---------- 检测逻辑 ----------
    def start_check(self, e):
        """校验输入后开始后台检测"""
        if self.processing:
            return
        if not self.files:
            self.show_status("请先添加要检测的PDF文件", success=False)
            return
        deep = self.deep_switch.value

        self.processing = True
        self.check_btn.disabled = True
        self.add_btn.disabled = True
        self.add_dir_btn.disabled = True
        self.clear_btn.disabled = True
        self.deep_switch.disabled = True
        for item in self.files:
            item['del_btn'].disabled = True
            item['code'] = 'pending'
            item['detail'] = None
            self._update_row(item, result="待检测", detail="-",
                             color=ft.Colors.BLUE_GREY_600, detail_color=ft.Colors.BLUE_GREY_500)
        self.export_btn.disabled = True
        self.progress.value = 0
        self.progress.visible = True
        self.progress_text.value = ""
        self.page.update()
        self.show_status("正在检测PDF完整性...")

        threading.Thread(
            target=self._do_check,
            args=(deep,),
            daemon=True,
        ).start()

    def _do_check(self, deep):
        """执行实际检测（后台线程）"""
        total = len(self.files)
        counts = {'ok': 0, 'bad': 0, 'warn': 0}
        try:
            for i, item in enumerate(self.files):
                self._update_row(item, result="检测中...", color=ft.Colors.BLUE)
                code, result_label, detail = self._check_one(item['path'], deep)
                item['code'] = code
                item['detail'] = detail
                if code == 'ok':
                    color = ft.Colors.GREEN
                    counts['ok'] += 1
                elif code == 'bad':
                    color = ft.Colors.RED_400
                    counts['bad'] += 1
                else:
                    color = ft.Colors.ORANGE
                    counts['warn'] += 1
                detail_color = ft.Colors.BLUE_GREY_700 if code == 'ok' else color
                self._update_row(item, result=result_label, detail=detail, color=color, detail_color=detail_color)
                self._update_progress(i + 1, total)
            self._update_progress(total, total)

            summary = f"共 {total} 个：正常 {counts['ok']} · 损坏 {counts['bad']} · 警告 {counts['warn']}"
            self.show_status(summary)
            self.export_btn.disabled = False
            if counts['bad']:
                self.show_info("检测完成", f"{summary}\n\n存在无法正常打开的损坏PDF文件，建议导出报告查看明细。")
            elif counts['warn']:
                self.show_info("检测完成", f"{summary}\n\n部分文件存在警告（如加密或非标准PDF），建议导出报告查看明细。")
            else:
                self.show_status(summary)
        except Exception as err:
            self.show_status(f"检测失败: {err}", success=False)
        finally:
            self.processing = False
            self.check_btn.disabled = False
            self.add_btn.disabled = False
            self.add_dir_btn.disabled = False
            self.clear_btn.disabled = False
            self.deep_switch.disabled = False
            for item in self.files:
                item['del_btn'].disabled = False
            self.page.update()

    def _check_one(self, path, deep):
        """检测单个PDF，返回 (code, 结果文案, 详情说明)
        code: ok=正常 / bad=损坏无法打开 / warn=警告(加密、空文件、非PDF等)
        """
        try:
            # 空文件 / 明显非 PDF
            size = os.path.getsize(path)
            if size == 0:
                return 'bad', '损坏', '文件为空（0字节），无法打开'
            try:
                with open(path, 'rb') as f:
                    header = f.read(1024)
            except Exception:
                header = b''
            if not header.startswith(b'%PDF-'):
                return 'warn', '警告', '不是有效的PDF文件（缺少 %PDF- 文件头）'

            pdf = None
            try:
                try:
                    pdf = pikepdf.open(path)
                except pikepdf.PasswordError:
                    return 'warn', '警告', '加密PDF：需要密码，无法校验内容'
                except Exception as err:
                    return 'bad', '损坏', f'无法打开：{self._trim(str(err))}'

                try:
                    page_count = len(pdf.pages)
                except Exception as err:
                    return 'bad', '损坏', f'页面结构解析失败：{self._trim(str(err))}'

                # 深度检测：逐页读取内容流，检查内容数据是否完整可解码
                if deep and page_count > 0:
                    try:
                        for pg in pdf.pages:
                            contents = pg.obj.get('/Contents')
                            if contents is None:
                                continue
                            streams = contents if isinstance(contents, pikepdf.Array) else [contents]
                            for stream in streams:
                                if stream is not None:
                                    stream.read_bytes()
                    except Exception as err:
                        return 'bad', '损坏', f'页面内容损坏（无法解码内容流）：{self._trim(str(err))}'

                # 结构完整性检查（qpdf 语法检查），找出严重结构损坏
                problems = []
                try:
                    problems = list(pdf.check_pdf_syntax())
                except Exception as err:
                    problems = [str(err)]
                problems = problems + list(pdf.get_warnings())
                severe = next(
                    (p for p in problems if any(hint in p.lower() for hint in _SEVERE_HINTS)),
                    None,
                )
                if severe:
                    return 'bad', '损坏', f'结构损坏（{self._trim(severe)}）'
                return 'ok', '正常', f'{page_count} 页'
            finally:
                if pdf is not None:
                    try:
                        pdf.close()
                    except Exception:
                        pass
        except Exception as err:
            return 'bad', '损坏', f'检测过程出错：{self._trim(str(err))}'

    @staticmethod
    def _trim(message, limit=220):
        """截断过长的错误消息"""
        message = str(message).strip().replace('\n', ' ')
        return message if len(message) <= limit else message[:limit] + '...'

    # ---------- 导出报告 ----------
    def export_report(self, e):
        if self.processing:
            return
        if not self.files or all(item.get('code') in (None, 'pending') for item in self.files):
            self.show_status("请先执行检测后再导出报告", success=False)
            return
        self.save_picker.save_file(
            dialog_title="保存检测报告",
            file_name=f"PDF损坏检测报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            allowed_extensions=["txt"],
        )

    def on_save_picked(self, e):
        if not e.path:
            return
        path = e.path
        if not path.lower().endswith('.txt'):
            path += '.txt'
        try:
            lines = self._build_report_lines()
            # 使用 utf-8-sig 写入 BOM，避免记事本打开中文乱码
            with open(path, 'w', encoding='utf-8-sig') as f:
                f.write('\n'.join(lines))
            self.show_status(f"报告已导出：{path}")
        except Exception as err:
            self.show_status(f"导出报告失败: {err}", success=False)

    def _build_report_lines(self):
        """生成报告文本行"""
        counts = {'ok': 0, 'bad': 0, 'warn': 0, 'pending': 0}
        for item in self.files:
            code = item.get('code', 'pending')
            counts[code] = counts.get(code, 0) + 1
        lines = []
        lines.append("=" * 60)
        lines.append("PDF 损坏检测报告")
        lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"检测总数：{len(self.files)} 个")
        lines.append(f"  正常：{counts['ok']} 个")
        lines.append(f"  损坏：{counts['bad']} 个")
        lines.append(f"  警告：{counts['warn']} 个")
        lines.append(f"  未检测：{counts['pending']} 个")
        lines.append("=" * 60)

        def dump(code, label):
            lines.append(f"\n【{label}】")
            selected = [i for i in self.files if i.get('code') == code]
            if not selected:
                lines.append("  无")
                return
            for item in selected:
                lines.append(f"  [{label}] {item['name']}")
                lines.append(f"    路径：{item['path']}")
                lines.append(f"    大小：{self._format_size(item['size'])}")
                if item.get('detail'):
                    lines.append(f"    详情：{item['detail']}")

        dump('bad', '损坏')
        dump('warn', '警告')
        dump('ok', '正常')
        dump('pending', '未检测')
        return lines

    # ---------- 工具方法 ----------
    def _update_row(self, item, result=None, detail=None, color=None, detail_color=None):
        """后台线程中更新某一行的检测结果显示"""
        if result is not None:
            item['result_text'].value = result
        if color is not None:
            item['result_text'].color = color
        if detail is not None:
            item['detail_text'].value = detail
            item['detail_text'].tooltip = detail
        if detail_color is not None:
            item['detail_text'].color = detail_color
        item['result_text'].update()
        item['detail_text'].update()

    def _update_progress(self, done, total):
        """更新进度条与进度文本"""
        self.progress.value = done / total
        self.progress_text.value = f"{done}/{total}"
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

    def show_info(self, title: str, message: str):
        """显示信息对话框"""
        self.page.dialog = ft.AlertDialog(
            title=ft.Text(title, font_family=self.font_family),
            content=ft.Text(message, font_family=self.font_family),
            actions=[ft.TextButton("关闭", on_click=lambda e: self.close_dialog())],
        )
        self.page.dialog.open = True
        self.page.update()

    def close_dialog(self, e=None):
        """关闭对话框"""
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()


if __name__ == '__main__':
    app = PDFDamageCheckApp()
    ft.app(target=app.build)
