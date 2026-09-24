# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import time
import datetime
import threading
import importlib.util
from pathlib import Path

import flet as ft


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

        font_family = current_font[0]
        icon_path = str(base._get_project_root() / 'Image' / 'icon.ico')
        return font_family, icon_path
    finally:
        try:
            if root.winfo_exists():
                root.destroy()
        except Exception:
            pass


APP_FONT_FAMILY, APP_ICON_PATH = run_startup_preflight()


# ==================== 配置 ====================

KEY_INTERVAL = 0.3               # 按键间隔（秒）

# ============================================


# ---------- 微信操作核心 ----------

def _import_automation():
    """延迟导入自动化依赖，未安装时给出清晰提示"""
    try:
        import pyautogui
        import pyperclip
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1
        return pyautogui, pyperclip
    except ImportError as e:
        raise RuntimeError(f"缺少依赖：{e}。请先执行 pip install pyautogui pyperclip")


def ensure_wechat_focused():
    """尝试激活微信窗口"""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, "微信")
        if hwnd:
            SW_RESTORE = 9
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, SW_RESTORE)
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.5)
            return True
    except Exception:
        pass
    return False


def search_and_open_group(pyautogui, pyperclip, group_name: str):
    """在微信中搜索并打开指定群聊"""
    pyautogui.hotkey("ctrl", "f")
    time.sleep(KEY_INTERVAL)

    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyperclip.copy(group_name)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(KEY_INTERVAL + 0.3)

    pyautogui.press("enter")
    time.sleep(KEY_INTERVAL + 0.3)
    pyautogui.press("enter")
    time.sleep(KEY_INTERVAL + 0.3)


def send_text_to_current_chat(pyautogui, pyperclip, message: str):
    """在当前聊天窗口发送消息"""
    pyperclip.copy(message)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(KEY_INTERVAL)
    pyautogui.press("enter")
    time.sleep(KEY_INTERVAL)


def send_to_group(pyautogui, pyperclip, group_name: str, message: str) -> bool:
    """向指定群聊发消息（内部调用，不操作 GUI）"""
    search_and_open_group(pyautogui, pyperclip, group_name)
    send_text_to_current_chat(pyautogui, pyperclip, message)
    return True


# ---------- GUI 应用 ----------

class WeChatSenderApp:
    """VX群聊消息发送 Flet 应用"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.font_family = APP_FONT_FAMILY

        page.title = "VX群聊消息发送"
        page.window.width = 820
        page.window.height = 780
        page.window.min_width = 640
        page.window.min_height = 600
        page.padding = 0
        page.bgcolor = ft.Colors.GREY_100
        page.theme = ft.Theme(font_family=self.font_family)

        # 窗口图标由公共基类解析，直接使用
        page.window.icon = APP_ICON_PATH

        self.groups = []
        self.selected_indices = set()
        self.running = False
        self.stop_flag = False
        self.worker_thread = None

        # 输入控件
        self.group_entry = ft.TextField(
            label="群聊名称",
            hint_text="输入群名后回车或点击添加",
            text_size=13,
            content_padding=ft.padding.all(10),
            border_radius=8,
            on_submit=lambda e: self._add_group(),
            expand=True,
        )

        self.msg_text = ft.TextField(
            label="消息内容",
            value="大家好，这是自动发送的测试消息！",
            multiline=True,
            min_lines=4,
            max_lines=8,
            text_size=13,
            content_padding=ft.padding.all(10),
            border_radius=8,
        )

        self.mode_group = ft.RadioGroup(
            value="once",
            content=ft.Row([
                ft.Radio(value="once", label="立即发送一次"),
                ft.Radio(value="interval", label="间隔发送"),
                ft.Radio(value="daily", label="每天定时"),
            ], spacing=12, wrap=True),
            on_change=self._on_mode_change,
        )

        self.interval_entry = ft.TextField(
            label="间隔(分钟)", value="30", width=140,
            text_size=13, border_radius=8, content_padding=ft.padding.all(10),
        )
        self.time_entry = ft.TextField(
            label="定时(HH:MM)", value="09:00", width=140,
            text_size=13, border_radius=8, content_padding=ft.padding.all(10),
        )

        # 群聊列表容器
        self.group_list_view = ft.ListView(spacing=4, height=140, padding=ft.padding.all(4))

        # 日志区
        self.log_view = ft.ListView(spacing=2, expand=True, padding=ft.padding.all(6),
                                       auto_scroll=True)

        self.status_text = ft.Text("就绪 - 请先添加群聊", size=12,
                                    color=ft.Colors.BLUE_GREY_700,
                                    font_family=self.font_family)

        # 参数行的可见性容器
        self.interval_row = ft.Row(
            [ft.Text("间隔设置：", size=12, font_family=self.font_family), self.interval_entry],
            spacing=6, visible=False,
        )
        self.daily_row = ft.Row(
            [ft.Text("定时设置：", size=12, font_family=self.font_family), self.time_entry],
            spacing=6, visible=False,
        )

        self.btn_start = ft.ElevatedButton(
            "▶  开始发送",
            icon=ft.Icons.PLAY_ARROW,
            bgcolor=ft.Colors.GREEN_600,
            color=ft.Colors.WHITE,
            on_click=self._start_send,
            expand=1,
        )
        self.btn_stop = ft.ElevatedButton(
            "■  停止",
            icon=ft.Icons.STOP,
            bgcolor=ft.Colors.RED_600,
            color=ft.Colors.WHITE,
            on_click=self._stop_send,
            disabled=True,
            expand=1,
        )

        self._build_ui()

        # 关闭窗口时停止后台线程
        def on_close(e):
            self.stop_flag = True
            self.running = False
            try:
                self.page.window.destroy()
            except Exception:
                pass
        page.window.on_close = on_close

    def _make_card(self, title, content):
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=13, weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_GREY_700, font_family=self.font_family),
                content,
            ], spacing=8),
            padding=ft.padding.all(12),
            border_radius=10,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )

    def _build_ui(self):
        # 群聊管理卡片
        btn_add = ft.ElevatedButton(
            "添加", icon=ft.Icons.ADD,
            bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE,
            on_click=lambda e: self._add_group(),
        )
        btn_remove = ft.OutlinedButton(
            "删除选中", icon=ft.Icons.DELETE, on_click=self._remove_selected,
        )
        btn_clear_all = ft.OutlinedButton(
            "清空", icon=ft.Icons.DELETE_SWEEP, on_click=self._clear_groups,
        )
        input_row = ft.Row([self.group_entry, btn_add], spacing=8)
        action_row = ft.Row([btn_remove, btn_clear_all], spacing=8)
        group_card = self._make_card(
            "目标群聊",
            ft.Column([input_row, self.group_list_view, action_row], spacing=8),
        )

        # 消息内容卡片
        msg_card = self._make_card("消息内容", self.msg_text)

        # 发送模式卡片
        mode_card = self._make_card(
            "发送模式",
            ft.Column([self.mode_group, self.interval_row, self.daily_row], spacing=8),
        )

        # 按钮行
        button_row = ft.Row([self.btn_start, self.btn_stop], spacing=8)

        # 日志卡片
        log_container = ft.Container(
            content=self.log_view,
            height=180,
            border_radius=8,
            bgcolor=ft.Colors.BLACK,
            padding=ft.padding.all(4),
        )
        log_card = self._make_card("运行日志", log_container)

        status_bar = ft.Container(
            content=self.status_text,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            bgcolor=ft.Colors.WHITE,
            border=ft.border.only(top=ft.BorderSide(1, ft.Colors.GREY_200)),
        )

        self.page.add(
            ft.Container(
                content=ft.Column(
                    [group_card, msg_card, mode_card, button_row, log_card],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
                padding=12,
                expand=True,
            ),
        )
        self.page.add(status_bar)

    # ----- 群聊管理 -----

    def _add_group(self):
        name = (self.group_entry.value or "").strip()
        if not name:
            return
        if name in self.groups:
            self.group_entry.value = ""
            self.page.update()
            self._set_status(f"群聊 [{name}] 已存在")
            return
        self.groups.append(name)
        self.group_entry.value = ""
        self._refresh_group_list()
        self._update_status()

    def _remove_selected(self):
        if not self.selected_indices:
            self._set_status("请先选中要删除的群聊", error=True)
            return
        # 从大到小删除以避免索引错位
        for idx in sorted(self.selected_indices, reverse=True):
            if 0 <= idx < len(self.groups):
                self.groups.pop(idx)
        self.selected_indices.clear()
        self._refresh_group_list()
        self._update_status()

    def _clear_groups(self):
        self.groups.clear()
        self.selected_indices.clear()
        self._refresh_group_list()
        self._update_status()

    def _toggle_selection(self, idx, selected):
        if selected:
            self.selected_indices.add(idx)
        else:
            self.selected_indices.discard(idx)

    def _refresh_group_list(self):
        """重建群聊列表 UI"""
        self.group_list_view.controls.clear()
        for idx, name in enumerate(self.groups):
            self.group_list_view.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Checkbox(
                            value=idx in self.selected_indices,
                            on_change=lambda e, i=idx: self._toggle_selection(
                                i, e.control.value
                            ),
                        ),
                        ft.Text(name, size=13, font_family=self.font_family,
                                 color=ft.Colors.BLUE_GREY_800, expand=True),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            icon_size=16,
                            icon_color=ft.Colors.RED_400,
                            tooltip="移除",
                            on_click=lambda e, i=idx: self._remove_at(i),
                        ),
                    ], spacing=4),
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    border_radius=6,
                    bgcolor=ft.Colors.GREY_50,
                )
            )
        self.page.update()

    def _remove_at(self, idx):
        if 0 <= idx < len(self.groups):
            self.groups.pop(idx)
            self.selected_indices = {i if i < idx else i - 1
                                       for i in self.selected_indices if i != idx}
            self._refresh_group_list()
            self._update_status()

    # ----- 模式切换 -----

    def _on_mode_change(self, e=None):
        mode = self.mode_group.value
        self.interval_row.visible = (mode == "interval")
        self.daily_row.visible = (mode == "daily")
        self.page.update()

    # ----- 日志与状态 -----

    def _log(self, text: str):
        """线程安全地写日志"""
        def _write():
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self.log_view.controls.append(
                ft.Text(f"[{timestamp}] {text}",
                         size=11,
                         color=ft.Colors.GREEN_300,
                         font_family="Consolas",
                         selectable=True)
            )
            self.page.update()
        try:
            self.page.run_thread(lambda: _write())
        except Exception:
            _write()

    def _set_status(self, text: str, error: bool = False):
        def _do():
            self.status_text.value = text
            self.status_text.color = ft.Colors.RED_700 if error else ft.Colors.BLUE_GREY_700
            if error:
                self.page.snack_bar = ft.SnackBar(
                    ft.Text(text, font_family=self.font_family),
                    bgcolor=ft.Colors.RED,
                    open=True,
                )
            self.page.update()
        try:
            self.page.run_thread(lambda: _do())
        except Exception:
            _do()

    def _set_buttons(self, running: bool):
        def _do():
            self.btn_start.disabled = running
            self.btn_stop.disabled = not running
            self.page.update()
        try:
            self.page.run_thread(lambda: _do())
        except Exception:
            _do()

    def _update_status(self):
        if not self.groups:
            self._set_status("就绪 - 请先添加群聊")
        else:
            self._set_status(f"就绪 - 已配置 {len(self.groups)} 个群聊")

    # ----- 发送逻辑 -----

    def _do_send_once(self, pyautogui, pyperclip, message: str):
        """发送一轮消息（在后台线程中运行）"""
        if not self.groups:
            self._log("⚠ 没有配置群聊，请先添加")
            return

        self._log(f"开始发送，共 {len(self.groups)} 个群聊...")

        focused = ensure_wechat_focused()
        if not focused:
            self._log("⚠ 无法自动激活微信，请手动点击微信窗口！")
            self._set_status("等待用户点击微信窗口...")
            time.sleep(3)

        success = 0
        for g in list(self.groups):
            if self.stop_flag:
                self._log("用户手动停止")
                break
            try:
                send_to_group(pyautogui, pyperclip, g, message)
                self._log(f"✓ [{g}] 发送成功")
                success += 1
            except pyautogui.FailSafeException:
                self._log("⚠ 触发安全停止（鼠标移到屏幕角落）")
                break
            except Exception as e:
                self._log(f"✗ [{g}] 发送失败: {e}")
            time.sleep(0.8)

        self._log(f"本轮完成: {success}/{len(self.groups)} 发送成功")

    def _start_send(self, e):
        if self.running:
            return

        if not self.groups:
            self._set_status("请先添加目标群聊", error=True)
            return

        message = (self.msg_text.value or "").strip()
        if not message:
            self._set_status("请输入要发送的消息内容", error=True)
            return

        # 延迟导入 pyautogui / pyperclip
        try:
            pyautogui, pyperclip = _import_automation()
        except RuntimeError as ex:
            self._set_status(str(ex), error=True)
            self._log(f"✗ {ex}")
            return

        mode = self.mode_group.value
        self.stop_flag = False
        self.running = True
        self._set_buttons(True)

        if mode == "once":
            self._log("=" * 40)
            self._log("模式: 立即发送一次")
            self._log("倒计时 3 秒，请点击微信窗口...")
            self._set_status("倒计时中，请点击微信窗口...")

            def run():
                time.sleep(3)
                self._do_send_once(pyautogui, pyperclip, message)
                self.running = False
                self._set_buttons(False)
                self._set_status("发送完成")
                self._log("全部完成")

            self.worker_thread = threading.Thread(target=run, daemon=True)
            self.worker_thread.start()

        elif mode == "interval":
            try:
                interval_min = int((self.interval_entry.value or "30").strip())
            except ValueError:
                interval_min = 30
            interval_sec = max(1, interval_min * 60)

            self._log("=" * 40)
            self._log(f"模式: 每 {interval_min} 分钟发送一次")
            self._log("倒计时 3 秒，请点击微信窗口...")
            self._set_status(f"每 {interval_min} 分钟发送一次")

            def run_interval():
                time.sleep(3)
                while not self.stop_flag:
                    self._do_send_once(pyautogui, pyperclip, message)
                    if self.stop_flag:
                        break
                    self._set_status(f"等待 {interval_min} 分钟后发送下一轮...")
                    for _ in range(interval_sec):
                        if self.stop_flag:
                            break
                        time.sleep(1)
                self.running = False
                self._set_buttons(False)
                self._set_status("已停止")
                self._log("已停止")

            self.worker_thread = threading.Thread(target=run_interval, daemon=True)
            self.worker_thread.start()

        elif mode == "daily":
            time_str = (self.time_entry.value or "").strip()
            if not time_str or ":" not in time_str:
                self._set_status("请输入正确的时间格式，如 09:00", error=True)
                self.running = False
                self._set_buttons(False)
                return
            try:
                target_h, target_m = map(int, time_str.split(":"))
                if not (0 <= target_h <= 23 and 0 <= target_m <= 59):
                    raise ValueError
            except Exception:
                self._set_status("时间格式无效，请输入 HH:MM（24 小时制）", error=True)
                self.running = False
                self._set_buttons(False)
                return

            self._log("=" * 40)
            self._log(f"模式: 每天 {time_str} 定时发送")
            self._set_status(f"等待到达 {time_str} 自动发送...")

            def run_daily():
                while not self.stop_flag:
                    now = datetime.datetime.now()
                    target_time = now.replace(hour=target_h, minute=target_m,
                                                 second=0, microsecond=0)
                    if target_time <= now:
                        target_time += datetime.timedelta(days=1)

                    wait_sec = (target_time - now).total_seconds()
                    self._log(
                        f"下次发送时间: {target_time.strftime('%Y-%m-%d %H:%M')} "
                        f"(等待 {wait_sec / 60:.0f} 分钟)"
                    )

                    while wait_sec > 0 and not self.stop_flag:
                        sleep_chunk = min(60, wait_sec)
                        time.sleep(sleep_chunk)
                        wait_sec -= sleep_chunk

                    if self.stop_flag:
                        break

                    self._do_send_once(pyautogui, pyperclip, message)
                    # 发送完等 61 秒，防止同一分钟重复触发
                    for _ in range(61):
                        if self.stop_flag:
                            break
                        time.sleep(1)

                self.running = False
                self._set_buttons(False)
                self._set_status("已停止")
                self._log("已停止")

            self.worker_thread = threading.Thread(target=run_daily, daemon=True)
            self.worker_thread.start()

    def _stop_send(self, e):
        self._log("正在停止...")
        self.stop_flag = True
        self.running = False
        self._set_buttons(False)
        self._set_status("已停止")


def main(page: ft.Page):
    WeChatSenderApp(page)


if __name__ == "__main__":
    ft.app(target=main)
