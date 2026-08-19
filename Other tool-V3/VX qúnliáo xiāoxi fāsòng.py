import os
import subprocess
import datetime
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
import pyautogui
import pyperclip
from fontTools.ttLib import TTFont

# ==================== 配置 ====================

KEY_INTERVAL = 0.3               # 按键间隔（秒）
pyautogui.FAILSAFE = True        # 鼠标移到左上角紧急停止
pyautogui.PAUSE = 0.1

# ============================================


# ---------- 微信操作核心 ----------

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


def search_and_open_group(group_name: str):
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


def send_text_to_current_chat(message: str):
    """在当前聊天窗口发送消息"""
    pyperclip.copy(message)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(KEY_INTERVAL)
    pyautogui.press("enter")
    time.sleep(KEY_INTERVAL)


def send_to_group(group_name: str, message: str) -> bool:
    """向指定群聊发消息（内部调用，不操作 GUI）"""
    search_and_open_group(group_name)
    send_text_to_current_chat(message)
    return True


# ---------- GUI 应用 ----------

class WeChatSenderApp:
    def __init__(self, root: tk.Tk):
        self.root = root

        # 首先检查开源协议文档是否存在并验证完整性
        if not self.check_license():
            messagebox.showerror(
                "错误", 
                "缺少授权！无法使用！请先获取授权！\n"
            )
            root.destroy()
            return

        self.root.title("VX群聊消息发送")
        self.root.geometry("620x580")
        self.root.resizable(True, True)
        self.root.minsize(520, 480)

        # 设置窗口图标、加载字体
        self.set_window_icon()
        self.load_font()

        self.running = False
        self.stop_flag = False
        self.worker_thread = None

        self._build_ui()
        self._center_window()

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
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.WeChatSender")
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
        """从配置文件加载字体设置"""
        # 定义项目根目录和图片目录
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

        self.current_font = (font_name, 10)
        self.root.option_add("*Font", self.current_font)

    def _center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"+{x}+{y}")

    # ----- UI 构建 -----

    def _build_ui(self):
        # 主容器
        main_frame = ttk.Frame(self.root, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 群聊管理 ---
        group_frame = ttk.LabelFrame(main_frame, text="目标群聊", padding=8)
        group_frame.pack(fill=tk.X, pady=(0, 8))

        top_row = ttk.Frame(group_frame)
        top_row.pack(fill=tk.X)
        ttk.Label(top_row, text="群聊名称:").pack(side=tk.LEFT)
        self.group_entry = ttk.Entry(top_row)
        self.group_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 4))
        self.group_entry.bind("<Return>", lambda e: self._add_group())
        ttk.Button(top_row, text="添加", command=self._add_group, width=6).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(top_row, text="删除选中", command=self._remove_group, width=8).pack(side=tk.LEFT)

        # 群聊列表
        list_frame = ttk.Frame(group_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.group_listbox = tk.Listbox(list_frame, height=4, selectmode=tk.EXTENDED,
                                        exportselection=False)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.group_listbox.yview)
        self.group_listbox.configure(yscrollcommand=scrollbar.set)
        self.group_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        # 右键菜单
        self.group_listbox.bind("<Delete>", lambda e: self._remove_group())

        # --- 消息内容 ---
        msg_frame = ttk.LabelFrame(main_frame, text="消息内容", padding=8)
        msg_frame.pack(fill=tk.X, pady=(0, 8))
        self.msg_text = tk.Text(msg_frame, height=4, wrap=tk.WORD)
        self.msg_text.pack(fill=tk.X)
        self.msg_text.insert("1.0", "大家好，这是自动发送的测试消息！")

        # --- 发送模式 ---
        mode_frame = ttk.LabelFrame(main_frame, text="发送模式", padding=8)
        mode_frame.pack(fill=tk.X, pady=(0, 8))

        self.mode_var = tk.StringVar(value="once")

        mode_row1 = ttk.Frame(mode_frame)
        mode_row1.pack(fill=tk.X)
        ttk.Radiobutton(mode_row1, text="立即发送一次", variable=self.mode_var,
                        value="once", command=self._on_mode_change).pack(side=tk.LEFT)
        ttk.Radiobutton(mode_row1, text="间隔发送", variable=self.mode_var,
                        value="interval", command=self._on_mode_change).pack(side=tk.LEFT, padx=(20, 0))
        ttk.Radiobutton(mode_row1, text="每天定时", variable=self.mode_var,
                        value="daily", command=self._on_mode_change).pack(side=tk.LEFT, padx=(20, 0))

        # 定时参数行
        param_frame = ttk.Frame(mode_frame)
        param_frame.pack(fill=tk.X, pady=(8, 0))

        self.interval_label = ttk.Label(param_frame, text="间隔(分钟):")
        self.interval_entry = ttk.Entry(param_frame, width=6)
        self.interval_entry.insert(0, "30")

        self.time_label = ttk.Label(param_frame, text="定时(HH:MM):")
        self.time_entry = ttk.Entry(param_frame, width=6)
        self.time_entry.insert(0, "09:00")

        # 初始隐藏定时参数
        self._on_mode_change()

        # --- 操作按钮 ---
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 8))

        self.send_btn = ttk.Button(btn_frame, text="▶  开始发送", command=self._start_send)
        self.send_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self.stop_btn = ttk.Button(btn_frame, text="■  停止", command=self._stop_send, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 状态栏
        self.status_var = tk.StringVar(value="就绪 - 请先添加群聊")
        ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN,
                  anchor=tk.W, padding=(6, 2)).pack(fill=tk.X, pady=(0, 6))

        # --- 日志区域 ---
        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding=4)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_area = scrolledtext.ScrolledText(log_frame, height=8, state=tk.DISABLED,
                                                   wrap=tk.WORD, font=("Consolas", 9))
        self.log_area.pack(fill=tk.BOTH, expand=True)

    # ----- 群聊管理 -----

    def _add_group(self):
        name = self.group_entry.get().strip()
        if not name:
            return
        # 去重
        existing = self.group_listbox.get(0, tk.END)
        if name in existing:
            self.group_entry.delete(0, tk.END)
            return
        self.group_listbox.insert(tk.END, name)
        self.group_entry.delete(0, tk.END)
        self._update_status()

    def _remove_group(self):
        selected = self.group_listbox.curselection()
        for idx in reversed(selected):
            self.group_listbox.delete(idx)
        self._update_status()

    def _get_groups(self):
        return list(self.group_listbox.get(0, tk.END))

    # ----- 模式切换 -----

    def _on_mode_change(self):
        mode = self.mode_var.get()
        # 先隐藏所有
        for w in [self.interval_label, self.interval_entry, self.time_label, self.time_entry]:
            w.pack_forget()

        if mode == "interval":
            self.interval_label.pack(side=tk.LEFT)
            self.interval_entry.pack(side=tk.LEFT, padx=(4, 20))
        elif mode == "daily":
            self.time_label.pack(side=tk.LEFT)
            self.time_entry.pack(side=tk.LEFT, padx=(4, 20))

    # ----- 日志 -----

    def _log(self, text: str):
        """线程安全地写日志"""
        def _write():
            self.log_area.configure(state=tk.NORMAL)
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self.log_area.insert(tk.END, f"[{timestamp}] {text}\n")
            self.log_area.see(tk.END)
            self.log_area.configure(state=tk.DISABLED)
        self.root.after(0, _write)

    def _set_status(self, text: str):
        self.root.after(0, lambda: self.status_var.set(text))

    def _set_buttons(self, running: bool):
        def _do():
            if running:
                self.send_btn.configure(state=tk.DISABLED)
                self.stop_btn.configure(state=tk.NORMAL)
            else:
                self.send_btn.configure(state=tk.NORMAL)
                self.stop_btn.configure(state=tk.DISABLED)
        self.root.after(0, _do)

    def _update_status(self):
        groups = self._get_groups()
        if not groups:
            self._set_status("就绪 - 请先添加群聊")
        else:
            self._set_status(f"就绪 - 已配置 {len(groups)} 个群聊")

    # ----- 发送逻辑 -----

    def _do_send_once(self, message: str):
        """发送一轮消息（在后台线程中运行）"""
        groups = self._get_groups()
        if not groups:
            self._log("⚠ 没有配置群聊，请先添加")
            return

        self._log(f"开始发送，共 {len(groups)} 个群聊...")

        # 激活微信
        focused = ensure_wechat_focused()
        if not focused:
            self._log("⚠ 无法自动激活微信，请手动点击微信窗口！")
            self._set_status("等待用户点击微信窗口...")
            time.sleep(3)

        success = 0
        for g in groups:
            if self.stop_flag:
                self._log("用户手动停止")
                break
            try:
                send_to_group(g, message)
                self._log(f"✓ [{g}] 发送成功")
                success += 1
            except pyautogui.FailSafeException:
                self._log("⚠ 触发安全停止（鼠标移到屏幕角落）")
                break
            except Exception as e:
                self._log(f"✗ [{g}] 发送失败: {e}")
            time.sleep(0.8)

        self._log(f"本轮完成: {success}/{len(groups)} 发送成功")

    # ----- 开始 / 停止 -----

    def _start_send(self):
        groups = self._get_groups()
        if not groups:
            messagebox.showwarning("提示", "请先添加目标群聊")
            return

        message = self.msg_text.get("1.0", tk.END).strip()
        if not message:
            messagebox.showwarning("提示", "请输入要发送的消息内容")
            return

        mode = self.mode_var.get()
        self.stop_flag = False
        self.running = True
        self._set_buttons(True)

        # 立即模式
        if mode == "once":
            self._log("=" * 40)
            self._log("模式: 立即发送一次")
            self._log(f"倒计时 3 秒，请点击微信窗口...")
            self._set_status("倒计时中，请点击微信窗口...")

            def run():
                time.sleep(3)
                self._do_send_once(message)
                self.running = False
                self._set_buttons(False)
                self._set_status("发送完成")
                self._log("全部完成\n")

            self.worker_thread = threading.Thread(target=run, daemon=True)
            self.worker_thread.start()

        # 间隔模式
        elif mode == "interval":
            try:
                interval_min = int(self.interval_entry.get().strip())
            except ValueError:
                interval_min = 30
            interval_sec = interval_min * 60

            self._log("=" * 40)
            self._log(f"模式: 每 {interval_min} 分钟发送一次")
            self._log(f"倒计时 3 秒，请点击微信窗口...")
            self._set_status(f"每 {interval_min} 分钟发送一次")

            def run_interval():
                time.sleep(3)
                while not self.stop_flag:
                    self._do_send_once(message)
                    if self.stop_flag:
                        break
                    self._set_status(f"等待 {interval_min} 分钟后发送下一轮...")
                    # 分段等待，以便及时响应停止
                    for _ in range(interval_sec):
                        if self.stop_flag:
                            break
                        time.sleep(1)
                self.running = False
                self._set_buttons(False)
                self._set_status("已停止")
                self._log("已停止\n")

            self.worker_thread = threading.Thread(target=run_interval, daemon=True)
            self.worker_thread.start()

        # 每天定时模式
        elif mode == "daily":
            time_str = self.time_entry.get().strip()
            if not time_str or ":" not in time_str:
                messagebox.showwarning("提示", "请输入正确的时间格式，如 09:00")
                self._set_buttons(False)
                self.running = False
                return

            self._log("=" * 40)
            self._log(f"模式: 每天 {time_str} 定时发送")
            self._set_status(f"等待到达 {time_str} 自动发送...")

            def run_daily():
                while not self.stop_flag:
                    now = datetime.datetime.now()
                    target_h, target_m = map(int, time_str.split(":"))
                    target_time = now.replace(hour=target_h, minute=target_m, second=0, microsecond=0)
                    if target_time <= now:
                        target_time += datetime.timedelta(days=1)

                    wait_sec = (target_time - now).total_seconds()
                    self._log(f"下次发送时间: {target_time.strftime('%Y-%m-%d %H:%M')} (等待 {wait_sec/60:.0f} 分钟)")

                    # 分段等待
                    while wait_sec > 0 and not self.stop_flag:
                        sleep_chunk = min(60, wait_sec)
                        time.sleep(sleep_chunk)
                        wait_sec -= sleep_chunk

                    if self.stop_flag:
                        break

                    self._do_send_once(message)
                    # 发送完等 61 秒，防止同一分钟重复触发
                    for _ in range(61):
                        if self.stop_flag:
                            break
                        time.sleep(1)

                self.running = False
                self._set_buttons(False)
                self._set_status("已停止")
                self._log("已停止\n")

            self.worker_thread = threading.Thread(target=run_daily, daemon=True)
            self.worker_thread.start()

    def _stop_send(self):
        self._log("正在停止...")
        self.stop_flag = True
        self.running = False
        self._set_buttons(False)
        self._set_status("已停止")


def main():
    root = tk.Tk()
    app = WeChatSenderApp(root)
    # 如果许可验证失败，窗口已被销毁，直接返回
    try:
        root.winfo_exists()
    except tk.TclError:
        return
    root.protocol("WM_DELETE_WINDOW", lambda: (app._stop_send(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
