import sys
sys.dont_write_bytecode = True

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from tkinter import font as tkfont
import webbrowser
import threading
import time
import re
import collections
import random
import subprocess
import importlib.util
import json
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent

def get_temp_pools_path():
    return get_base_dir() / "temp_pools.json"

def load_default_pools_from_temp_file():
    temp_path = get_temp_pools_path()

    if not temp_path.exists():
        return []

    try:
        with temp_path.open("r", encoding="utf-8") as f:
            raw_data = json.load(f)

        pools = []
        if isinstance(raw_data, list):
            for item in raw_data:
                if isinstance(item, dict):
                    name = str(item.get("name", "")).strip()
                    items_id = str(item.get("items_id", item.get("id", ""))).strip()
                    if name and items_id.isdigit():
                        pools.append((name, items_id))
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    name = str(item[0]).strip()
                    items_id = str(item[1]).strip()
                    if name and items_id.isdigit():
                        pools.append((name, items_id))

        return pools
    except Exception:
        return []

# 自动检查并补齐运行时依赖，避免首次启动时缺包报错

def ensure_runtime_dependencies():
    required_modules = {
        "requests": "requests>=2.28",
        "pyautogui": "pyautogui>=0.9.53",
        "pyperclip": "pyperclip>=1.8.2",
        "selenium": "selenium>=4.0",
        "webdriver_manager": "webdriver-manager>=4.0",
    }

    missing = []
    for module_name, requirement in required_modules.items():
        if importlib.util.find_spec(module_name) is None:
            missing.append(requirement)

    if not missing:
        return True

    print(f"检测到缺失依赖，正在自动安装: {', '.join(missing)}")

    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", *missing],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("依赖安装完成")
        return True
    except Exception as exc:
        print(f"自动安装依赖失败: {exc}")
        return False

ensure_runtime_dependencies()

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import pyautogui
    import pyperclip
    WX_AUTOMATION_AVAILABLE = True
except ImportError:
    WX_AUTOMATION_AVAILABLE = False

KEY_INTERVAL = 0.3                        
if WX_AUTOMATION_AVAILABLE:
    pyautogui.FAILSAFE = True                 
    pyautogui.PAUSE = 0.1

_BROWSER_PROFILES = [
    {
        "name": "Chrome 120",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept_language": "zh-CN,zh;q=0.9,en;q=0.8",
    },
    {
        "name": "Chrome 122",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept_language": "zh-CN,zh;q=0.9,en;q=0.8",
    },
    {
        "name": "Chrome 124",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Google Chrome";v="124", "Chromium";v="124", "Not-A.Brand";v="99"',
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept_language": "zh-CN,zh;q=0.9,en;q=0.8",
    },
    {
        "name": "Edge 125",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
        "sec_ch_ua": '"Chromium";v="125", "Microsoft Edge";v="125", "Not.A/Brand";v="24"',
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept_language": "zh-CN,zh;q=0.9,en;q=0.8",
    },
    {
        "name": "Firefox 126",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
        "sec_ch_ua": None,                               
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "accept_language": "zh-CN, zh;q=0.8, en-US;q=0.5, en;q=0.3",
    },
]

# 生成一组稳定且不易被识别的浏览器请求头

def random_browser_fingerprint():
    profile = random.choice(_BROWSER_PROFILES)
    headers = {
        "User-Agent": profile["ua"],
        "Accept": profile["accept"],
        "Accept-Language": profile["accept_language"],
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

    if profile.get("sec_ch_ua"):
        headers.update({
            "sec-ch-ua": profile["sec_ch_ua"],
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        })
    return headers, profile

# 激活微信窗口，确保后续自动化操作落在正确聊天界面

def ensure_wechat_focused():
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

# 通过快捷键搜索并打开指定群聊，随后直接发送消息

def search_and_open_group(group_name: str):
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

# 把文本写入剪贴板并回车发送到当前聊天窗口

def send_text_to_current_chat(message: str):
    pyperclip.copy(message)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(KEY_INTERVAL)
    pyautogui.press("enter")
    time.sleep(KEY_INTERVAL)

def send_to_group(group_name: str, message: str) -> bool:
    search_and_open_group(group_name)
    send_text_to_current_chat(message)
    return True

# 监控主界面：负责池子状态、检测循环和日志输出

class PoolMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("辅助看池工具")
        self.root.geometry("900x800")
        self.load_font_config()
        self.monitoring = False
        self.monitor_thread = None
        self.monitor_log = []
        self.page_load_timeout = 8            
        self.log_dir = get_base_dir() / "logs"
        self.log_file_path = self.log_dir / f"bilibili_monitor_{datetime.now().strftime('%Y%m%d')}.log"
        self.event_log_file_path = self.log_dir / f"bilibili_pool_events_{datetime.now().strftime('%Y%m%d')}.log"  
        self.driver = None
        self.selenium_available = False                   
        self.detect_mode = "requests" if REQUESTS_AVAILABLE else "selenium"
        self.http_session = None
        self.browser_ua = None                                           
        self.fingerprint_profile = None         
        if REQUESTS_AVAILABLE:
            self._build_http_session()
        else:                             
            _, profile = random_browser_fingerprint()
            self.fingerprint_profile = profile
            self.browser_ua = profile["ua"]
        self.pools = {}                                                                                  
        self.pool_counter = 0
        self.pool_frames = {}                                                                        
        self.wx_notified = {}                                  
        self.wx_notify_enabled = True
        self.wx_group_name = "文件传输助手"
        self.wx_msg_queue = collections.deque()                
        self.wx_consumer_running = False
        self.wx_consumer_thread = None                    
        self.support_links = {}                           
        self._load_support_links()
        self.create_ui()       
        self._start_wx_consumer()    
        self.init_selenium()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _build_http_session(self):
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10, pool_maxsize=10,
            max_retries=1
        )
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        headers, profile = random_browser_fingerprint()
        session.headers.update(headers)
        self.browser_ua = profile["ua"]
        self.fingerprint_profile = profile
        self.http_session = session

    def _load_support_links(self):
        tsv_path = get_base_dir() / "support_links.tsv"
        if not tsv_path.exists():
            return
        try:
            with open(tsv_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("商品ID"):
                        continue
                    parts = line.split("\t")
                    if len(parts) >= 4:
                        items_id = parts[0].strip()
                        support_url = parts[3].strip()
                        if items_id and support_url:
                            self.support_links[items_id] = support_url
            if self.support_links:
                print(f"已加载 {len(self.support_links)} 条支持链接")
        except Exception as e:
            print(f"加载支持链接失败: {e}")

    def _get_support_link(self, pool_data):
        items_id = self._extract_items_id(pool_data["url"])
        if items_id and items_id in self.support_links:
            return self.support_links[items_id]
        return None

    def load_font_config(self):
        try:
            self.font_family = tkfont.nametofont("TkDefaultFont").actual("family")
        except Exception as e:
            print(f"字体加载错误: {str(e)}")
            self.font_family = "Microsoft YaHei"

        self.font_size = 10
        self.style = ttk.Style()
        self.style.configure('.', font=(self.font_family, self.font_size))

    def create_ui(self):

        url_frame = tk.LabelFrame(
            self.root,
            text="商品ID",
            padx=5,
            pady=5,
            font=(self.font_family, self.font_size)
        )
        url_frame.pack(fill="x", padx=10, pady=(10, 5))

        self.url_entry = tk.Entry(
            url_frame,
            font=(self.font_family, self.font_size)
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        btn_frame = tk.Frame(url_frame)
        btn_frame.pack(side="right")

        self.btn_open = tk.Button(
            btn_frame,
            text="打开链接",
            command=self.open_in_browser,
            font=(self.font_family, self.font_size - 2),
            width=10,
            bg="#00a1d6",
            fg="white"
        )
        self.btn_open.pack(side="left", padx=2)

        self.btn_copy = tk.Button(
            btn_frame,
            text="复制链接",
            command=self.copy_url,
            font=(self.font_family, self.font_size - 2),
            width=10
        )
        self.btn_copy.pack(side="left", padx=2)

        monitor_frame = tk.LabelFrame(
            self.root,
            text="页面看看设置",
            padx=10,
            pady=5,
            font=(self.font_family, self.font_size)
        )
        monitor_frame.pack(fill="x", padx=10, pady=5)

        self.monitor_enabled = tk.BooleanVar(value=False)
        self.monitor_check = tk.Checkbutton(
            monitor_frame,
            text="启用页面看看",
            variable=self.monitor_enabled,
            command=self.toggle_monitoring,
            font=(self.font_family, self.font_size)
        )
        self.monitor_check.pack(anchor="w")

        interval_frame = tk.Frame(monitor_frame)
        interval_frame.pack(fill="x", pady=5)

        tk.Label(
            interval_frame,
            text="检查间隔:",
            font=(self.font_family, self.font_size)
        ).pack(side="left", padx=(0, 5))

        self.monitor_interval_mode = tk.StringVar(value="random")
        tk.Radiobutton(
            interval_frame,
            text="3~15秒随机",
            variable=self.monitor_interval_mode,
            value="random",
            font=(self.font_family, self.font_size)
        ).pack(side="left", padx=5)
        tk.Radiobutton(
            interval_frame,
            text="1秒",
            variable=self.monitor_interval_mode,
            value="one_second",
            font=(self.font_family, self.font_size)
        ).pack(side="left", padx=5)
        tk.Radiobutton(
            interval_frame,
            text="1~3分钟",
            variable=self.monitor_interval_mode,
            value="one_to_three_minutes",
            font=(self.font_family, self.font_size)
        ).pack(side="left", padx=5)

        self.monitor_status = tk.StringVar(value="帮看未开始")
        self.monitor_status_label = tk.Label(
            monitor_frame,
            textvariable=self.monitor_status,
            font=(self.font_family, self.font_size - 2),
            fg="gray"
        )
        self.monitor_status_label.pack(anchor="w", pady=5)

        wx_notify_frame = tk.LabelFrame(
            monitor_frame,
            text="微信通知（内置自动化）",
            padx=10,
            pady=5,
            font=(self.font_family, self.font_size)
        )
        wx_notify_frame.pack(fill="x", pady=(8, 0))

        wx_toggle_row = tk.Frame(wx_notify_frame)
        wx_toggle_row.pack(fill="x")

        self.wx_notify_var = tk.BooleanVar(value=True)
        self.wx_notify_check = tk.Checkbutton(
            wx_toggle_row,
            text="状态变化时自动发送微信通知",
            variable=self.wx_notify_var,
            command=self._on_wx_notify_toggle,
            font=(self.font_family, self.font_size)
        )
        self.wx_notify_check.pack(anchor="w")

        wx_config_row = tk.Frame(wx_notify_frame)
        wx_config_row.pack(fill="x", pady=(5, 0))

        tk.Label(
            wx_config_row,
            text="目标群聊:",
            font=(self.font_family, self.font_size)
        ).pack(side="left", padx=(0, 5))

        self.wx_group_entry = tk.Entry(
            wx_config_row,
            font=(self.font_family, self.font_size),
            width=30,
            state="disabled"
        )
        self.wx_group_entry.insert(0, "文件传输助手")
        self.wx_group_entry.pack(side="left", fill="x", expand=True, padx=5)

        self.wx_notify_status = tk.StringVar(value="已启用")
        self.wx_status_label = tk.Label(
            wx_config_row,
            textvariable=self.wx_notify_status,
            font=(self.font_family, self.font_size - 2),
            fg="gray"
        )
        self.wx_status_label.pack(side="right", padx=5)

        elements_frame = tk.LabelFrame(
            self.root,
            text="池子帮看状态",
            padx=10,
            pady=5,
            font=(self.font_family, self.font_size)
        )
        elements_frame.pack(fill="x", padx=10, pady=5)

        self.pools_container = tk.Frame(elements_frame)
        self.pools_container.pack(fill="x", pady=5)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        self.create_log_tab()

        default_pools = load_default_pools_from_temp_file()
        for name, items_id in default_pools:
            self.add_pool(name, items_id)

        self.status_var = tk.StringVar(value="就绪")
        self.status_bar = tk.Label(
            self.root,
            textvariable=self.status_var,
            relief="sunken",
            font=(self.font_family, self.font_size - 2)
        )
        self.status_bar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))

        self.url_entry.bind("<Button-3>", lambda e: self.show_context_menu(e, self.url_entry))

    def create_log_tab(self):
        frame = tk.Frame(self.notebook)
        self.notebook.add(frame, text="帮看日志")

        log_frame = tk.Frame(frame)
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            font=(self.font_family, self.font_size),
            height=20,
            bg="#f5f5f5",
            relief="solid",
            borderwidth=1
        )
        self.log_text.pack(fill="both", expand=True)

        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.btn_clear_log = tk.Button(
            btn_frame,
            text="清空日志",
            command=self.clear_log,
            font=(self.font_family, self.font_size - 2)
        )
        self.btn_clear_log.pack(side="left")

        self.btn_export_log = tk.Button(
            btn_frame,
            text="导出日志",
            command=self.export_log,
            font=(self.font_family, self.font_size - 2)
        )
        self.btn_export_log.pack(side="left", padx=10)

        self.btn_speed_test = tk.Button(
            btn_frame,
            text="测速",
            command=self.speed_test,
            font=(self.font_family, self.font_size - 2),
            bg="#2196F3",
            fg="white"
        )
        self.btn_speed_test.pack(side="right")

        self.add_log("系统启动，等待开始帮看...")

    def _show_auto_popup(self, title, message, bg_color="#ffcccc", auto_close=1):
        popup = tk.Toplevel(self.root)
        popup.title(title)
        popup.configure(bg=bg_color)
        popup.attributes('-topmost', True)

        tk.Label(
            popup, text=message,
            font=(self.font_family, self.font_size),
            bg=bg_color, wraplength=350, justify="left",
            padx=15, pady=15
        ).pack()

        btn = tk.Button(
            popup, text="确定", command=popup.destroy,
            font=(self.font_family, self.font_size - 2), width=8
        )
        btn.pack(pady=(0, 10))

        popup.update_idletasks()
        w, h = popup.winfo_width(), popup.winfo_height()
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        popup.geometry(f"+{x}+{y}")

        popup.after(auto_close * 1000, popup.destroy)

    def _normalize_pool_url(self, value):
        raw = str(value).strip()
        if not raw:
            return ""
        if raw.startswith("http://") or raw.startswith("https://"):
            return raw
        if raw.isdigit():
            return (
                "https://mall.bilibili.com/neul-next/index.html"
                f"?page=magic-detail_detail&noTitleBar=1&itemsId={raw}"
            )
        raise ValueError("请输入正确的商品ID或完整链接")

    def add_pool(self, name=None, items_id=None):
        pool_name_entry = getattr(self, "pool_name_entry", None)
        pool_url_entry = getattr(self, "pool_url_entry", None)

        if name is None and pool_name_entry is not None:
            name = pool_name_entry.get().strip()
        if items_id is None and pool_url_entry is not None:
            items_id = pool_url_entry.get().strip()

        if not name:
            messagebox.showwarning("警告", "请输入池子名称")
            return

        if not items_id:
            messagebox.showwarning("警告", "请输入商品ID (itemsId) 或完整商品链接")
            return

        try:
            url = self._normalize_pool_url(items_id)
        except ValueError as exc:
            messagebox.showwarning("警告", str(exc))
            return

        if not url:
            messagebox.showwarning("警告", "请输入商品ID (itemsId) 或完整商品链接")
            return

        self.pool_counter += 1
        pool_id = self.pool_counter

        self.pools[pool_id] = {
            "name": name,
            "url": url,
            "exists": True,
            "confirmed_exists": None
        }

        card = tk.Frame(self.pools_container, relief="groove", borderwidth=2)
        card.pack(fill="x", pady=3, padx=3)

        name_label = tk.Label(
            card,
            text=name,
            font=(self.font_family, self.font_size, "bold"),
            width=12,
            anchor="w"
        )
        name_label.pack(side="left", padx=5)

        url_display = url if len(url) <= 40 else url[:37] + "..."
        url_label = tk.Label(
            card,
            text=url_display,
            font=(self.font_family, self.font_size - 2),
            fg="gray",
            width=35,
            anchor="w"
        )
        url_label.pack(side="left", padx=5)

        status_text = tk.StringVar(value="等待帮看")
        status_label = tk.Label(
            card,
            textvariable=status_text,
            font=(self.font_family, self.font_size + 2, "bold"),
            fg="gray",
            width=18
        )
        status_label.pack(side="right", padx=10)

        self.pool_frames[pool_id] = {
            "card": card,
            "status": status_text,
            "name_label": name_label
        }

        self.add_log(f"已添加池子: {name}")

        if pool_name_entry is not None:
            pool_name_entry.delete(0, "end")
            pool_name_entry.insert(0, f"池子{self.pool_counter + 1}")
        if pool_url_entry is not None:
            pool_url_entry.delete(0, "end")

    def delete_pool(self, pool_id):
        if pool_id not in self.pools:
            return

        pool_name = self.pools[pool_id]["name"]

        del self.pools[pool_id]

        if pool_id in self.pool_frames:
            self.pool_frames[pool_id]["card"].destroy()
            del self.pool_frames[pool_id]

        self.add_log(f"已删除池子: {pool_name}")

    def init_selenium(self):
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            if REQUESTS_AVAILABLE:
                self.selenium_available = True
                self.status_var.set("双模式可用 - requests + Selenium")
                self.add_log("requests 库已加载 (快速HTTP检测)")
                self.add_log("Selenium WebDriver 初始化成功 (降级备用)")
            else:
                self.selenium_available = True
                self.status_var.set("Selenium可用 - 支持动态页面")
                self.add_log("Selenium WebDriver 初始化成功")
                self.add_log("提示: 安装 requests 库可启用更快的HTTP检测模式")

            try:
                from webdriver_manager.chrome import ChromeDriverManager
                self.chrome_driver_manager = ChromeDriverManager
                self.add_log("webdriver-manager 已加载，自动匹配驱动版本")
            except ImportError:
                self.chrome_driver_manager = None
                self.add_log("提示: 可安装 webdriver-manager 自动管理驱动版本")

            self.selenium_module = {
                'webdriver': webdriver,
                'Options': Options,
                'Service': Service,
                'By': By,
                'WebDriverWait': WebDriverWait,
                'EC': EC
            }

        except ImportError:
            self.selenium_available = REQUESTS_AVAILABLE
            if REQUESTS_AVAILABLE:
                self.status_var.set("requests可用 - 快速HTTP检测模式")
                self.add_log("requests 库已加载，使用快速HTTP检测模式")
                self.add_log("Selenium未安装，仅支持HTTP检测模式")
            else:
                self.status_var.set("无可用检测方式")
                self.add_log("警告: requests 和 Selenium 均未安装")
                self.add_log("请运行: pip install requests 或 pip install selenium")

    def create_driver(self):
        try:
            self.root.after(0, self.add_log, "正在创建 WebDriver...")

            chrome_options = self.selenium_module['Options']()
            chrome_options.add_argument('--headless=new')             
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')

            chrome_options.add_argument('--blink-settings=imagesEnabled=false')        
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-application-cache')
            chrome_options.add_argument('--disable-background-networking')
            chrome_options.add_argument('--disable-client-side-phishing-detection')
            chrome_options.add_argument('--disable-default-apps')
            chrome_options.add_argument('--disable-sync')
            chrome_options.add_argument('--mute-audio')
            chrome_options.add_argument('--no-first-run')

            if self.browser_ua:
                chrome_options.add_argument(f'--user-agent={self.browser_ua}')

            chrome_options.page_load_strategy = 'eager'

            if self.chrome_driver_manager:
                try:
                    self.root.after(0, self.add_log, "尝试使用 webdriver-manager...")

                    chromedriver_path = self.chrome_driver_manager().install()
                    self.root.after(0, self.add_log, f"驱动路径: {chromedriver_path}")
                    service = self.selenium_module['Service'](chromedriver_path)
                    driver = self.selenium_module['webdriver'].Chrome(service=service, options=chrome_options)
                    self.root.after(0, self.add_log, "ChromeDriver 启动成功")
                    driver.set_page_load_timeout(30)
                    return driver
                except Exception as e:
                    self.root.after(0, self.add_log, f"webdriver-manager 失败: {str(e)}")

            try:
                self.root.after(0, self.add_log, "尝试使用 Selenium 内置驱动管理器...")

                driver = self.selenium_module['webdriver'].Chrome(options=chrome_options)
                self.root.after(0, self.add_log, "Selenium 驱动管理器 启动成功")
                driver.set_page_load_timeout(30)
                return driver
            except Exception as e:
                self.root.after(0, self.add_log, f"Selenium 内置驱动管理器失败: {str(e)}")

            chromedriver_path = get_base_dir() / "chromedriver.exe"
            if not chromedriver_path.exists():

                meipass = getattr(sys, '_MEIPASS', None)
                if meipass:
                    embedded = Path(meipass) / "chromedriver.exe"
                    if embedded.exists():
                        chromedriver_path = embedded
            self.root.after(0, self.add_log, f"尝试本地驱动: {chromedriver_path}")
            if chromedriver_path.exists():
                service = self.selenium_module['Service'](str(chromedriver_path))
                driver = self.selenium_module['webdriver'].Chrome(service=service, options=chrome_options)
                self.root.after(0, self.add_log, "本地 ChromeDriver 启动成功")
                driver.set_page_load_timeout(30)
                return driver
            else:
                self.root.after(0, self.add_log, "所有方法均失败")
                raise Exception("无法创建 WebDriver\n请确保已安装 Chrome 浏览器")

        except Exception as e:
            self.root.after(0, self.add_log, f"创建WebDriver失败: {str(e)}")
            return None

    def toggle_monitoring(self):
        if self.monitor_enabled.get():
            self.start_monitoring()
        else:
            self.stop_monitoring()

    def _on_wx_notify_toggle(self):
        if getattr(self, '_wx_toggle_guard', False):
            return
        self._wx_toggle_guard = True
        try:
            enabled = self.wx_notify_var.get()
            self.wx_notify_enabled = enabled
            if enabled:
                group_name = self.wx_group_entry.get().strip()
                if not group_name:
                    self.wx_group_entry.config(state="normal")
                    self.wx_notify_status.set("请输入目标群聊名称")
                    self.wx_notify_var.set(False)
                    self.wx_notify_enabled = False
                    return
                self.wx_group_name = group_name
                self.wx_group_entry.config(state="disabled")
                self.wx_notify_status.set("已启用")
                self.add_log(f"微信通知已启用，目标群聊: {group_name}")
                self._start_wx_consumer()
            else:
                self.wx_group_entry.config(state="normal")
                self.wx_notify_status.set("未启用")
                self.add_log("微信通知已禁用")
                self._stop_wx_consumer()
        finally:
            self._wx_toggle_guard = False

    def _start_wx_consumer(self):
        if self.wx_consumer_running:
            return
        self.wx_consumer_running = True
        self.wx_consumer_thread = threading.Thread(
            target=self._wx_consumer_loop, daemon=True
        )
        self.wx_consumer_thread.start()
        self.add_log("微信消息队列已启动")

    def _stop_wx_consumer(self):
        self.wx_consumer_running = False
        self.wx_msg_queue.clear()

    def _wx_consumer_loop(self):
        while self.wx_consumer_running:
            try:
                try:
                    msg = self.wx_msg_queue.popleft()
                except IndexError:
                    time.sleep(0.5)
                    continue

                group = msg["group"]
                message = msg["message"]

                self.root.after(0, self.add_log, f"正在向微信群「{group}」发送通知...")

                if not WX_AUTOMATION_AVAILABLE:
                    self.root.after(0, self.add_log, "⚠ 未安装 pyautogui/pyperclip，无法发送微信通知")
                else:
                    try:
                        if not ensure_wechat_focused():
                            self.root.after(0, self.add_log, "⚠ 无法激活微信窗口，发送失败")
                        else:
                            send_to_group(group, message)
                            self.root.after(0, self.add_log, f"微信通知已发送到群「{group}」")
                    except pyautogui.FailSafeException:
                        self.root.after(0, self.add_log, "⚠ 触发安全停止（鼠标移到屏幕角落），本次发送中断")
                    except Exception:
                        self.root.after(0, self.add_log, "⚠ 微信发送异常")

                time.sleep(1)

            except Exception:
                pass

    def _send_wx_notification(self, pool_name: str, pool_url: str, event_time: str, change_type: str):
        if not self.wx_notify_enabled:
            return
        group = self.wx_group_name.strip()
        if not group:
            return

        if change_type == "消失":
            title = "五发不重已消失！"
            time_label = "消失时间"
        else:
            title = "五发不重重新出现！"
            time_label = "出现时间"

        message = (
            f"【{pool_name}】{title}\n"
            f"━━━━━━━━━━━━━━\n"
            f"池子链接: {pool_url}\n"
            f"{time_label}: {event_time}\n"
            f"━━━━━━━━━━━━━━"
        )
        self.wx_msg_queue.append({"group": group, "message": message})
        self.add_log(f"消息已加入微信发送队列（当前排队: {len(self.wx_msg_queue)}）")

    def _send_wx_startup_notification(self, pool_results: dict, check_time: str):
        if not self.wx_notify_enabled:
            return
        group = self.wx_group_name.strip()
        if not group:
            return

        lines = ["帮看已启动，首轮检测结果："]
        lines.append(f"时间: {check_time}")
        lines.append("━━━━━━━━━━━━━━")

        for pool_id, has_5fa in pool_results.items():
            if pool_id not in self.pools:
                continue
            pool_data = self.pools[pool_id]
            status = "✓ 存在" if has_5fa else "✗ 不存在"
            lines.append(f"【{pool_data['name']}】{status}")
            lines.append(f"链接: {pool_data['url']}")
            support_url = self._get_support_link(pool_data)
            if support_url:
                lines.append(f"支持链接: {support_url}")
            else:
                lines.append("请联系作者新增支持链接(不影响使用)")

        message = "\n".join(lines)

        self.wx_msg_queue.append({"group": group, "message": message})
        self.add_log("帮看启动通知已加入微信发送队列")

    def _write_pool_event_log(self, pool_name, pool_url, check_time, change_type):
        title = "首次消失" if change_type == "消失" else "首次出现"
        event_line = (
            f"{check_time} - [{pool_name}] {title}\n"
            f"池子链接: {pool_url}\n"
        )
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            with self.event_log_file_path.open("a", encoding="utf-8") as event_file:
                event_file.write(event_line)
        except OSError as error:
            print(f"状态变化日志写入失败: {error}")

    # 启动后台检测循环，轮询池子状态并判断是否发生变化
    def start_monitoring(self):
        if not self.selenium_available and not REQUESTS_AVAILABLE:
            messagebox.showerror("错误", "未安装任何检测库\n请运行: pip install requests")
            self.monitor_enabled.set(False)
            return

        if not self.pools:
            messagebox.showwarning("警告", "请先添加至少一个池子")
            self.monitor_enabled.set(False)
            return

        self.monitoring = True
        self.change_count = 0
        self.start_time = datetime.now()
        self.check_count = 0
        self.initial_check_done = {}                  
        self.wx_startup_notified = False               

        for pool_id, pool_data in self.pools.items():
            pool_data["confirmed_exists"] = None
            self.wx_notified[pool_id] = False
            if pool_id in self.pool_frames:
                self.pool_frames[pool_id]["status"].set("等待监控")
                self.pool_frames[pool_id]["card"].config(bg="SystemButtonFace")

        pool_names = [p["name"] for p in self.pools.values()]
        mode_desc = "requests快速HTTP" if (self.detect_mode == "requests" and REQUESTS_AVAILABLE) else "Selenium"
        self.add_log(f"=== 开始帮看 ({mode_desc}模式) ===")
        self.add_log(f"帮看池子数量: {len(self.pools)}")
        self.add_log(f"帮看池子: {', '.join(pool_names)}")
        self.add_log(f"帮看元素: 5发不重")
        mode_value = self.monitor_interval_mode.get()
        if mode_value == "one_second":
            interval_desc = "1秒"
        elif mode_value == "one_to_three_minutes":
            interval_desc = "1~3分钟随机"
        else:
            interval_desc = "3~15秒随机"
        self.add_log(f"检查间隔: {interval_desc}")
        if self.fingerprint_profile:
            self.add_log(f"本次浏览器指纹: {self.fingerprint_profile['name']}")

        if self.detect_mode == "requests" and REQUESTS_AVAILABLE:
            self._warmup_connections()

        self.monitor_thread = threading.Thread(target=self.monitor_worker, daemon=True)
        self.monitor_thread.start()

        self.monitor_status.set("正在帮看...")
        mode_emoji = "⚡" if (self.detect_mode == "requests" and REQUESTS_AVAILABLE) else "🌐"
        self.status_var.set(f"{mode_emoji} 页面监控已启动 - 第{self.check_count}轮 - 监控{len(self.pools)}个池子")

    def stop_monitoring(self):
        self.monitoring = False
        self.monitor_enabled.set(False)

        self.add_log("=== 监控已停止 ===")

        self.monitor_status.set("监控已停止")
        self.status_var.set("页面监控已停止")

        if self.http_session:
            try:
                self.http_session.close()
            except:
                pass
            self.http_session = None
        if REQUESTS_AVAILABLE:
            self._build_http_session()

        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

    def _warmup_connections(self):
        if not self.http_session:
            return
        urls = list(set(p["url"] for p in self.pools.values()))
        for url in urls[:5]:             
            try:
                resp = self.http_session.head(url, timeout=3)
            except Exception:
                pass
        self.add_log(f"已预热 {len(urls)} 个连接")

    def speed_test(self):
        if not self.pools:
            messagebox.showinfo("提示", "请先添加池子")
            return

        self.add_log("=== 开始测速 ===")
        self.btn_speed_test.config(state="disabled", text="测速中...")

        def _run_test():
            results = []
            total_t0 = time.time()

            if REQUESTS_AVAILABLE and self.http_session:
                with ThreadPoolExecutor(max_workers=min(len(self.pools), 8)) as executor:
                    futures = {
                        executor.submit(self._check_pool_requests, pid, pdata): pid
                        for pid, pdata in self.pools.items()
                    }
                    for future in as_completed(futures):
                        pid, has_5fa, elapsed, error, method = future.result()
                        name = self.pools[pid]["name"]
                        if error:
                            results.append(f"  [{name}] 失败: {error}")
                        else:
                            results.append(f"  [{name}] {method} {elapsed:.3f}s - 5发不重:{'存在' if has_5fa else '不存在'}")

            total_elapsed = time.time() - total_t0

            self.root.after(0, self.add_log, "=== 测速结果 ===")
            for r in results:
                self.root.after(0, self.add_log, r)
            self.root.after(0, self.add_log, f"总耗时: {total_elapsed:.3f}s (并发)")
            self.root.after(0, lambda: self.btn_speed_test.config(state="normal", text="测速"))

        threading.Thread(target=_run_test, daemon=True).start()

    def _extract_items_id(self, url):
        match = re.search(r'itemsId=(\d+)', url)
        return match.group(1) if match else None

    def _check_pool_api(self, pool_id, pool_data):
        url = pool_data["url"]
        items_id = self._extract_items_id(url)
        if not items_id:
            return pool_id, None, 0, f"无法从URL提取itemsId: {url}"

        api_url = f"https://mall.bilibili.com/magic-c-search/blind_box/info?itemsId={items_id}&afterDraw=false"

        api_headers = {
            "Accept": "application/json, text/plain, */*",
            "Referer": url,
        }
        if self.fingerprint_profile and self.fingerprint_profile.get("sec_ch_ua"):
            api_headers.update({
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
            })
        t0 = time.time()
        try:
            resp = self.http_session.get(api_url, headers=api_headers, timeout=3)
            resp.raise_for_status()
            data = resp.json()

            has_5fa = False
            if data.get("code") == 0 and "data" in data:
                multi_options = data["data"].get("multiDrawOptions", [])
                for opt in multi_options:

                    if opt.get("drawNum") == 5 and opt.get("stockSufficient") is True:
                        has_5fa = True
                        break

            elapsed = time.time() - t0
            return pool_id, has_5fa, elapsed, None
        except Exception as e:
            elapsed = time.time() - t0
            return pool_id, None, elapsed, str(e)

    def _check_pool_requests(self, pool_id, pool_data):

        pid, has_5fa, elapsed, error = self._check_pool_api(pool_id, pool_data)
        if error is None:
            return pid, has_5fa, elapsed, None, "API"

        url = pool_data["url"]
        t0 = time.time()
        try:
            resp = self.http_session.get(url, timeout=3, stream=True)
            resp.raise_for_status()
            has_5fa = False
            buffer = ""
            target_keywords = ('5发不重', '5发不重复')
            for chunk in resp.iter_content(chunk_size=8192, decode_unicode=True):
                if chunk:
                    buffer += chunk
                    if target_keywords[0] in buffer or target_keywords[1] in buffer:
                        has_5fa = True
                        break
                    if len(buffer) > 524288:
                        break
            resp.close()
            elapsed = time.time() - t0
            return pool_id, has_5fa, elapsed, None, "HTTP"
        except Exception as e:
            elapsed = time.time() - t0
            return pool_id, None, elapsed, str(e), "FAIL"

    def _check_pool_selenium(self, pool_id, pool_data):
        pool_name = pool_data["name"]
        url = pool_data["url"]
        t0 = time.time()
        try:
            self.driver.get(url)
            wait = self.selenium_module['WebDriverWait'](self.driver, self.page_load_timeout, poll_frequency=0.3)
            try:
                wait.until(lambda d: ('5发不重' in d.page_source or '5发不重复' in d.page_source))
                has_5fa = True
            except Exception:
                page_source = self.driver.page_source
                has_5fa = ('5发不重' in page_source or '5发不重复' in page_source)
            elapsed = time.time() - t0
            return pool_id, has_5fa, elapsed, None
        except Exception as e:
            elapsed = time.time() - t0
            return pool_id, None, elapsed, str(e)

    # 轮询线程：优先 HTTP 请求，失败时回退到 Selenium
    def monitor_worker(self):
        retry_count = 0
        max_retries = 2
        use_requests_mode = (self.detect_mode == "requests" and REQUESTS_AVAILABLE)

        while self.monitoring:
            mode_value = self.monitor_interval_mode.get()
            if mode_value == "one_second":
                wait_time = 1
            elif mode_value == "one_to_three_minutes":
                wait_time = random.uniform(60, 180)
            else:
                wait_time = random.uniform(3, 15)
            try:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                if use_requests_mode:

                    pool_results = {}
                    errors = []
                    round_t0 = time.time()

                    with ThreadPoolExecutor(max_workers=min(len(self.pools), 8)) as executor:
                        futures = {
                            executor.submit(self._check_pool_requests, pid, pdata): pid
                            for pid, pdata in self.pools.items()
                        }
                        for future in as_completed(futures):
                            pid, has_5fa, elapsed, error, method = future.result()
                            if error:
                                errors.append((pid, error))
                            else:
                                pool_results[pid] = has_5fa
                                pool_name = self.pools[pid]["name"]
                                self.root.after(0, self.add_log,
                                    f"[{pool_name}] {method}检测完成 ({elapsed:.2f}s), 5发不重: {'存在' if has_5fa else '不存在'}")

                    round_elapsed = time.time() - round_t0

                    if errors and self.selenium_available and self.driver is None:
                        self.root.after(0, self.add_log, "部分HTTP请求失败，尝试启动Selenium降级...")

                    for pid, error in errors:
                        if pid not in pool_results:
                            pool_name = self.pools[pid]["name"]
                            self.root.after(0, self.add_log, f"[{pool_name}] HTTP检测失败: {error}")

                    if errors and self.selenium_available:

                        try:
                            if self.driver is None:
                                self.driver = self.create_driver()
                            if self.driver:
                                for pid, error in errors:
                                    if pid in self.pools:
                                        pid2, has_5fa, elapsed2, err2 = self._check_pool_selenium(pid, self.pools[pid])
                                        if err2 is None:
                                            pool_results[pid] = has_5fa
                                            pool_name = self.pools[pid]["name"]
                                            self.root.after(0, self.add_log,
                                                f"[{pool_name}] Selenium降级检测完成 ({elapsed2:.2f}s)")
                        except Exception:
                            pass

                    self.check_count += 1
                    self.root.after(0, self.update_check_info, current_time)
                    self.root.after(0, self.check_changes, pool_results, current_time)

                    if not self.wx_startup_notified:
                        self.wx_startup_notified = True
                        self.root.after(0, self._send_wx_startup_notification, pool_results, current_time)
                    self.root.after(0, self.add_log,
                        f"第{self.check_count}轮并发检测完成 (总耗时 {round_elapsed:.2f}s)，等待 {wait_time} 秒...")

                else:

                    if self.driver is None:
                        self.root.after(0, self.add_log, "正在创建 WebDriver...")
                        self.driver = self.create_driver()
                        if self.driver is None:
                            self.root.after(0, self.add_log, "无法创建WebDriver，等待重试...")
                            time.sleep(5)
                            continue
                        self.root.after(0, self.add_log, "WebDriver 创建成功")

                    pool_results = {}
                    driver_error = False

                    for pool_id, pool_data in self.pools.items():
                        pool_name = pool_data["name"]
                        self.root.after(0, self.add_log, f"[{pool_name}] 正在访问页面... ({self.check_count + 1})")

                        pid, has_5fa, elapsed, error = self._check_pool_selenium(pool_id, pool_data)
                        if error:
                            self.root.after(0, self.add_log, f"[{pool_name}] 页面访问失败: {error}")
                            driver_error = True
                            break

                        pool_results[pool_id] = has_5fa
                        self.root.after(0, self.add_log,
                            f"[{pool_name}] 检测完成 ({elapsed:.1f}s), 5发不重: {'存在' if has_5fa else '不存在'}")

                    if driver_error:
                        retry_count += 1
                        if retry_count >= max_retries:
                            self.root.after(0, self.add_log, "重试次数过多，停止帮看")
                            self.root.after(0, self.monitor_enabled.set, False)
                            break
                        try:
                            self.driver.quit()
                        except:
                            pass
                        self.driver = None
                        time.sleep(5)
                        continue

                    retry_count = 0
                    self.check_count += 1
                    self.root.after(0, self.update_check_info, current_time)
                    self.root.after(0, self.check_changes, pool_results, current_time)

                    if not self.wx_startup_notified:
                        self.wx_startup_notified = True
                        self.root.after(0, self._send_wx_startup_notification, pool_results, current_time)
                    self.root.after(0, self.add_log, f"本次检查完成，等待 {wait_time} 秒...")

            except Exception as e:
                self.root.after(0, self.add_log, f"[{datetime.now().strftime('%H:%M:%S')}] 检查失败: {str(e)}")

            remaining = wait_time
            while remaining > 0 and self.monitoring:
                time.sleep(min(0.5, remaining))
                remaining -= 0.5

        self.root.after(0, self.add_log, "帮看线程已退出")

    def _set_pool_card_state(self, pool_id, status_text, bg_color):
        frame_data = self.pool_frames.get(pool_id)
        if not frame_data:
            return
        frame_data["status"].set(status_text)
        frame_data["card"].config(bg=bg_color)

    # 对比当前检测结果和上次状态，记录首次出现/消失事件
    def check_changes(self, pool_results, check_time):
        changed_pools = []

        for pool_id, currently_exists in pool_results.items():
            if pool_id not in self.pools:
                continue

            pool_data = self.pools[pool_id]
            pool_name = pool_data["name"]
            was_exists = pool_data.get("confirmed_exists")

            if was_exists is None:
                pool_data["exists"] = currently_exists
                pool_data["confirmed_exists"] = currently_exists
                if not currently_exists:
                    self.wx_notified[pool_id] = True

                if currently_exists:
                    self._set_pool_card_state(pool_id, "存在", "#e8f5e9")
                else:
                    self._set_pool_card_state(pool_id, "不存在", "#ffcccc")

                self.add_log(f"[{pool_name}] 初始状态: {'存在' if currently_exists else '不存在'}")
                continue

            if was_exists and not currently_exists:
                pool_data["exists"] = False
                pool_data["confirmed_exists"] = False
                changed_pools.append((pool_id, pool_name, "消失", pool_data["url"]))
                self._set_pool_card_state(pool_id, "⚠ 已消失！", "#ffcccc")

            elif not was_exists and currently_exists:
                pool_data["exists"] = True
                pool_data["confirmed_exists"] = True
                self.wx_notified[pool_id] = False
                changed_pools.append((pool_id, pool_name, "出现", pool_data["url"]))
                self._set_pool_card_state(pool_id, "✓ 重新出现！", "#e8f5e9")

            elif currently_exists:
                if self.pool_frames.get(pool_id):
                    current_bg = self.pool_frames[pool_id]["card"].cget("bg")
                    if current_bg != "#e8f5e9":
                        self.pool_frames[pool_id]["card"].config(bg="#e8f5e9")
                    self.pool_frames[pool_id]["status"].set("存在")

        if changed_pools:
            self.change_count += len(changed_pools)
            for pool_id, pool_name, change_type, pool_url in changed_pools:
                if change_type == "消失":
                    if self.wx_notified.get(pool_id, False):
                        continue
                    self.wx_notified[pool_id] = True
                    self.add_log(f"[{check_time}] ★★ [{pool_name}] 5发不重 已从页面消失！★★")
                    self.status_var.set(f"⚠ [{pool_name}] 5发不重 已消失！")
                    self._show_auto_popup(
                        f"【{pool_name}】5发不重消失提醒",
                        f"重要提醒！\n\n【{pool_name}】的5发不重 已从页面消失！\n时间: {check_time}",
                        bg_color="#ffcccc"
                    )
                    self._write_pool_event_log(pool_name, pool_url, check_time, "消失")
                    self._send_wx_notification(pool_name, pool_url, check_time, "消失")
                else:
                    self.add_log(f"[{check_time}] ★★ [{pool_name}] 5发不重 已重新出现！★★")
                    self.status_var.set(f"✓ [{pool_name}] 5发不重 已重新出现！")
                    self._show_auto_popup(
                        f"【{pool_name}】5发不重出现提醒",
                        f"重要提醒！\n\n【{pool_name}】的5发不重 已重新出现在页面！\n时间: {check_time}",
                        bg_color="#e8f5e9"
                    )
                    self._write_pool_event_log(pool_name, pool_url, check_time, "出现")
                    self._send_wx_notification(pool_name, pool_url, check_time, "出现")
        else:
            self.monitor_status.set(f"未检测到变化 | 最后检查: {check_time.split(' ')[1]}")

    def update_check_info(self, check_time):
        self.monitor_status.set(f"最后检查: {check_time}")

    def add_log(self, message):
        log_line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}"
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.monitor_log.append(log_line)
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            with self.log_file_path.open("a", encoding="utf-8") as log_file:
                log_file.write(log_line + "\n")
        except OSError as error:
            print(f"日志自动写入失败: {error}")

        line_count = int(self.log_text.index('end-1c').split('.')[0])
        if line_count > 500:
            self.log_text.delete("1.0", f"{line_count - 500}.0")

    def clear_log(self):
        self.log_text.delete("1.0", "end")
        self.monitor_log.clear()
        self.add_log("日志已清空")

    def export_log(self):
        from tkinter import filedialog

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialfile=f"bilibili_monitor_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("商品监控日志\n")
                    f.write(f"商品ID: {self.url_entry.get().strip()}\n")
                    f.write(f"监控元素: 5发不重\n")
                    f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 80 + "\n\n")
                    for log in self.monitor_log:
                        f.write(log + "\n")

                messagebox.showinfo("导出成功", f"日志已保存到:\n{file_path}")
            except Exception as e:
                messagebox.showerror("导出失败", f"无法保存日志:\n{str(e)}")

    def open_in_browser(self):
        raw_value = self.url_entry.get().strip()
        if not raw_value:
            messagebox.showwarning("警告", "请输入有效的商品ID或完整链接")
            return

        try:
            url = self._normalize_pool_url(raw_value)
        except ValueError as exc:
            messagebox.showwarning("警告", str(exc))
            return
        self.status_var.set(f"正在打开: {url}")

        try:
            webbrowser.open(url)
            self.status_var.set("已在浏览器中打开链接")
            self.add_log(f"在浏览器中打开: {url}")
        except Exception as e:
            self.status_var.set(f"打开失败: {str(e)}")
            messagebox.showerror("错误", f"无法打开链接：{str(e)}")

    def copy_url(self):
        raw_value = self.url_entry.get().strip()
        if raw_value:
            try:
                url = self._normalize_pool_url(raw_value)
            except ValueError as exc:
                messagebox.showwarning("警告", str(exc))
                return
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.status_var.set("链接已复制到剪贴板")
            messagebox.showinfo("提示", "链接已复制到剪贴板")
        else:
            messagebox.showwarning("警告", "没有可复制的链接")

    def on_closing(self):
        if self.monitoring:
            self.stop_monitoring()
        self._stop_wx_consumer()
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.root.destroy()

class WeChatSenderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("微信群聊消息发送工具")
        self.root.geometry("620x580")
        self.root.resizable(True, True)
        self.root.minsize(520, 480)

        self.running = False
        self.stop_flag = False
        self.worker_thread = None

        self._build_ui()
        self._center_window()

    def _center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"+{x}+{y}")

    def _build_ui(self):

        main_frame = ttk.Frame(self.root, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

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

        list_frame = ttk.Frame(group_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.group_listbox = tk.Listbox(list_frame, height=4, selectmode=tk.EXTENDED,
                                        exportselection=False)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.group_listbox.yview)
        self.group_listbox.configure(yscrollcommand=scrollbar.set)
        self.group_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.group_listbox.bind("<Delete>", lambda e: self._remove_group())

        self.group_listbox.insert(tk.END, "幻神专属")

        msg_frame = ttk.LabelFrame(main_frame, text="消息内容", padding=8)
        msg_frame.pack(fill=tk.X, pady=(0, 8))
        self.msg_text = tk.Text(msg_frame, height=4, wrap=tk.WORD)
        self.msg_text.pack(fill=tk.X)
        self.msg_text.insert("1.0", "大家好，这是自动发送的测试消息！")

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

        param_frame = ttk.Frame(mode_frame)
        param_frame.pack(fill=tk.X, pady=(8, 0))

        self.interval_label = ttk.Label(param_frame, text="间隔(分钟):")
        self.interval_entry = ttk.Entry(param_frame, width=6)
        self.interval_entry.insert(0, "30")

        self.time_label = ttk.Label(param_frame, text="定时(HH:MM):")
        self.time_entry = ttk.Entry(param_frame, width=6)
        self.time_entry.insert(0, "09:00")

        self._on_mode_change()

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 8))

        self.send_btn = ttk.Button(btn_frame, text="▶  开始发送", command=self._start_send)
        self.send_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self.stop_btn = ttk.Button(btn_frame, text="■  停止", command=self._stop_send, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.status_var = tk.StringVar(value="就绪 - 请先添加群聊")
        ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN,
                  anchor=tk.W, padding=(6, 2)).pack(fill=tk.X, pady=(0, 6))

        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding=4)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_area = scrolledtext.ScrolledText(log_frame, height=8, state=tk.DISABLED,
                                                   wrap=tk.WORD, font=("Consolas", 9))
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def _add_group(self):
        name = self.group_entry.get().strip()
        if not name:
            return

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

    def _on_mode_change(self):
        mode = self.mode_var.get()

        for w in [self.interval_label, self.interval_entry, self.time_label, self.time_entry]:
            w.pack_forget()

        if mode == "interval":
            self.interval_label.pack(side=tk.LEFT)
            self.interval_entry.pack(side=tk.LEFT, padx=(4, 20))
        elif mode == "daily":
            self.time_label.pack(side=tk.LEFT)
            self.time_entry.pack(side=tk.LEFT, padx=(4, 20))

    def _log(self, text: str):
        def _write():
            self.log_area.configure(state=tk.NORMAL)
            timestamp = datetime.now().strftime("%H:%M:%S")
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

    def _do_send_once(self, message: str):
        groups = self._get_groups()
        if not groups:
            self._log("⚠ 没有配置群聊，请先添加")
            return

        self._log(f"开始发送，共 {len(groups)} 个群聊...")

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
                    now = datetime.now()
                    target_h, target_m = map(int, time_str.split(":"))
                    target_time = now.replace(hour=target_h, minute=target_m, second=0, microsecond=0)
                    if target_time <= now:
                        target_time += timedelta(days=1)

                    wait_sec = (target_time - now).total_seconds()
                    self._log(f"下次发送时间: {target_time.strftime('%Y-%m-%d %H:%M')} (等待 {wait_sec/60:.0f} 分钟)")

                    while wait_sec > 0 and not self.stop_flag:
                        sleep_chunk = min(60, wait_sec)
                        time.sleep(sleep_chunk)
                        wait_sec -= sleep_chunk

                    if self.stop_flag:
                        break

                    self._do_send_once(message)

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

    if len(sys.argv) >= 4 and sys.argv[1] == "--send":
        if not WX_AUTOMATION_AVAILABLE:
            sys.exit(1)
        group_name = sys.argv[2]
        message = sys.argv[3]
        try:
            focused = ensure_wechat_focused()
            if not focused:
                sys.exit(1)
            send_to_group(group_name, message)
            print("OK")
        except Exception:
            sys.exit(1)
        sys.exit(0)

    if len(sys.argv) >= 2 and sys.argv[1] == "--wx-gui":
        if not WX_AUTOMATION_AVAILABLE:
            print("未安装 pyautogui/pyperclip，请运行: pip install pyautogui pyperclip")
            sys.exit(1)
        root = tk.Tk()
        app = WeChatSenderApp(root)
        root.protocol("WM_DELETE_WINDOW", lambda: (app._stop_send(), root.destroy()))
        root.mainloop()
        return

    root = tk.Tk()
    app = PoolMonitorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
