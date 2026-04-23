# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import webbrowser
import threading
import time
from pathlib import Path
from datetime import datetime


class BilibiliMallReader:
    def __init__(self, root):
        self.root = root
        self.root.title("辅助盯池工具")
        self.root.geometry("900x800")
        
        # 加载字体配置
        self.load_font_config()
        
        # 默认URL
        self.default_url = "https://mall.bilibili.com/neul-next/index.html?page=magic-detail_detail&noTitleBar=1&itemsId=13645965"
        
        # 监控相关变量
        self.monitoring = False
        self.monitor_thread = None
        self.monitor_interval = 30
        self.monitor_log = []
        
        # Selenium相关
        self.driver = None
        self.selenium_available = False
        
        # 池子列表
        self.pools = {}  # {pool_id: {"name": str, "url": str, "exists": bool, "confirmed_exists": bool}}
        self.pool_counter = 0
        self.pool_frames = {}  # {pool_id: {"card": frame, "status": StringVar, "name_label": Label}}
        
        # 创建UI
        self.create_ui()
        
        # 尝试初始化Selenium
        self.init_selenium()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def load_font_config(self):
        """加载字体配置"""
        try:
            font_path = Path(__file__).parent.parent / "Core" / "ziti.json"
            if font_path.exists():
                with open(font_path, "r", encoding="utf-8") as f:
                    font_config = json.load(f)
                    self.font_family = font_config.get("family", "Microsoft YaHei")
            else:
                self.font_family = "Microsoft YaHei"
        except Exception as e:
            print(f"字体加载错误: {str(e)}")
            self.font_family = "Microsoft YaHei"
        
        self.font_size = 10
        self.style = ttk.Style()
        self.style.configure('.', font=(self.font_family, self.font_size))
    
    def create_ui(self):
        """创建UI界面"""
        # 顶部URL输入区域
        url_frame = tk.LabelFrame(
            self.root,
            text="商品链接",
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
        self.url_entry.insert(0, self.default_url)
        
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
        
        # 提示标签
        tip_label = tk.Label(
            url_frame,
            text="提示: 商城页面需要登录后才能查看完整商品信息",
            font=(self.font_family, self.font_size - 2),
            fg="gray"
        )
        tip_label.pack(side="bottom", anchor="w", padx=5, pady=(5, 0))
        
        # 池子管理区域
        pool_manager_frame = tk.LabelFrame(
            self.root,
            text="池子管理",
            padx=10,
            pady=5,
            font=(self.font_family, self.font_size)
        )
        pool_manager_frame.pack(fill="x", padx=10, pady=5)
        
        # 池子列表容器
        self.pool_list_frame = tk.Frame(pool_manager_frame)
        self.pool_list_frame.pack(fill="x", pady=5)
        
        # 添池子按钮区域
        add_pool_frame = tk.Frame(pool_manager_frame)
        add_pool_frame.pack(fill="x", pady=5)
        
        tk.Label(
            add_pool_frame,
            text="池子名称:",
            font=(self.font_family, self.font_size)
        ).pack(side="left", padx=(0, 5))
        
        self.pool_name_entry = tk.Entry(
            add_pool_frame,
            font=(self.font_family, self.font_size),
            width=15
        )
        self.pool_name_entry.pack(side="left", padx=5)
        self.pool_name_entry.insert(0, "池子1")
        
        tk.Label(
            add_pool_frame,
            text="URL:",
            font=(self.font_family, self.font_size)
        ).pack(side="left", padx=(10, 5))
        
        self.pool_url_entry = tk.Entry(
            add_pool_frame,
            font=(self.font_family, self.font_size),
            width=40
        )
        self.pool_url_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.pool_url_entry.insert(0, self.default_url)
        
        btn_add_pool = tk.Button(
            add_pool_frame,
            text="添加池子",
            command=self.add_pool,
            font=(self.font_family, self.font_size - 2),
            bg="#4CAF50",
            fg="white",
            width=10
        )
        btn_add_pool.pack(side="left", padx=5)
        
        # 监控设置区域
        monitor_frame = tk.LabelFrame(
            self.root,
            text="页面监控设置",
            padx=10,
            pady=5,
            font=(self.font_family, self.font_size)
        )
        monitor_frame.pack(fill="x", padx=10, pady=5)
        
        # 监控开关
        self.monitor_enabled = tk.BooleanVar(value=False)
        self.monitor_check = tk.Checkbutton(
            monitor_frame,
            text="启用页面监控",
            variable=self.monitor_enabled,
            command=self.toggle_monitoring,
            font=(self.font_family, self.font_size)
        )
        self.monitor_check.pack(anchor="w")
        
        # 监控间隔设置
        interval_frame = tk.Frame(monitor_frame)
        interval_frame.pack(fill="x", pady=5)
        
        tk.Label(
            interval_frame,
            text="检查间隔:",
            font=(self.font_family, self.font_size)
        ).pack(side="left", padx=(0, 5))
        
        self.interval_combo = ttk.Combobox(
            interval_frame,
            values=["10秒", "30秒", "1分钟", "5分钟", "10分钟"],
            font=(self.font_family, self.font_size),
            width=10,
            state="readonly"
        )
        self.interval_combo.current(1)
        self.interval_combo.pack(side="left", padx=5)
        self.interval_combo.bind("<<ComboboxSelected>>", self.on_interval_change)
        
        # 监控状态标签
        self.monitor_status = tk.StringVar(value="监控未启动")
        self.monitor_status_label = tk.Label(
            monitor_frame,
            textvariable=self.monitor_status,
            font=(self.font_family, self.font_size - 2),
            fg="gray"
        )
        self.monitor_status_label.pack(anchor="w", pady=5)
        
        # 监控元素显示区域（滚动式）
        elements_frame = tk.LabelFrame(
            self.root,
            text="池子监控状态",
            padx=10,
            pady=5,
            font=(self.font_family, self.font_size)
        )
        elements_frame.pack(fill="x", padx=10, pady=5)
        
        # 创建池子卡片容器（带滚动条）
        self.pools_container = tk.Frame(elements_frame)
        self.pools_container.pack(fill="x", pady=5)
        
        # 主内容区域 - 使用Notebook实现多标签页
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 页面1: 监控日志
        self.create_log_tab()
        
        # 添加一个默认池子（需要在日志创建之后）
        self.add_pool("池子1", self.default_url)
        
        # 底部状态栏
        self.status_var = tk.StringVar(value="就绪")
        self.status_bar = tk.Label(
            self.root,
            textvariable=self.status_var,
            relief="sunken",
            font=(self.font_family, self.font_size - 2)
        )
        self.status_bar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        
        # 右键菜单
        self.url_entry.bind("<Button-3>", lambda e: self.show_context_menu(e, self.url_entry))
    
    def create_log_tab(self):
        """创建监控日志标签页"""
        frame = tk.Frame(self.notebook)
        self.notebook.add(frame, text="监控日志")
        
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
        
        self.add_log("系统启动，等待开始监控...")
    

    def show_context_menu(self, event, widget):
        """显示右键菜单"""
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="剪切", command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="复制", command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="粘贴", command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_command(label="全选", command=lambda: widget.event_generate("<<SelectAll>>"))
        menu.tk_popup(event.x_root, event.y_root)
    
    def add_pool(self, name=None, url=None):
        """添加一个新池子"""
        if name is None:
            name = self.pool_name_entry.get().strip()
        if url is None:
            url = self.pool_url_entry.get().strip()
        
        if not name:
            messagebox.showwarning("警告", "请输入池子名称")
            return
        
        if not url:
            messagebox.showwarning("警告", "请输入池子URL")
            return
        
        self.pool_counter += 1
        pool_id = self.pool_counter
        
        # 保存池子数据
        self.pools[pool_id] = {
            "name": name,
            "url": url,
            "exists": True,
            "confirmed_exists": None
        }
        
        # 创建池子卡片
        card = tk.Frame(self.pools_container, relief="groove", borderwidth=2)
        card.pack(fill="x", pady=3, padx=3)
        
        # 池子名称
        name_label = tk.Label(
            card,
            text=name,
            font=(self.font_family, self.font_size, "bold"),
            width=12,
            anchor="w"
        )
        name_label.pack(side="left", padx=5)
        
        # URL显示（截断）
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
        
        # 状态指示
        status_text = tk.StringVar(value="等待监控")
        status_label = tk.Label(
            card,
            textvariable=status_text,
            font=(self.font_family, self.font_size + 2, "bold"),
            fg="gray",
            width=18
        )
        status_label.pack(side="right", padx=10)
        
        # 删除按钮
        def delete_this_pool():
            self.delete_pool(pool_id)
        
        btn_delete = tk.Button(
            card,
            text="X",
            command=delete_this_pool,
            font=(self.font_family, self.font_size - 2, "bold"),
            width=3,
            bg="#f44336",
            fg="white",
            relief="flat"
        )
        btn_delete.pack(side="right", padx=(5, 2))
        
        # 保存卡片引用
        self.pool_frames[pool_id] = {
            "card": card,
            "status": status_text,
            "name_label": name_label
        }
        
        self.add_log(f"已添加池子: {name}")
        
        # 清空输入框
        self.pool_name_entry.delete(0, "end")
        self.pool_name_entry.insert(0, f"池子{self.pool_counter + 1}")
        self.pool_url_entry.delete(0, "end")
        self.pool_url_entry.insert(0, self.default_url)
    
    def delete_pool(self, pool_id):
        """删除指定池子"""
        if pool_id not in self.pools:
            return
        
        pool_name = self.pools[pool_id]["name"]
        
        # 从数据结构中删除
        del self.pools[pool_id]
        
        # 销毁卡片
        if pool_id in self.pool_frames:
            self.pool_frames[pool_id]["card"].destroy()
            del self.pool_frames[pool_id]
        
        self.add_log(f"已删除池子: {pool_name}")
    
    def init_selenium(self):
        """初始化Selenium WebDriver"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # 尝试导入 webdriver-manager
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                self.chrome_driver_manager = ChromeDriverManager
                self.add_log("webdriver-manager 已加载，自动匹配驱动版本")
            except ImportError:
                self.chrome_driver_manager = None
                self.add_log("提示: 可安装 webdriver-manager 自动管理驱动版本")
                self.add_log("   运行: pip install webdriver-manager")
            
            # 保存Selenium模块引用
            self.selenium_module = {
                'webdriver': webdriver,
                'Options': Options,
                'Service': Service,
                'By': By,
                'WebDriverWait': WebDriverWait,
                'EC': EC
            }
            
            self.selenium_available = True
            self.status_var.set("Selenium可用 - 支持动态页面")
            self.add_log("Selenium WebDriver 初始化成功")
            
        except ImportError:
            self.selenium_available = False
            self.status_var.set("Selenium未安装 - 无法检测动态页面")
            self.add_log("警告: Selenium未安装，无法检测动态页面内容")
            self.add_log("请运行: pip install selenium")
    
    def create_driver(self):
        """创建WebDriver实例"""
        try:
            self.root.after(0, self.add_log, "正在创建 WebDriver...")
            
            chrome_options = self.selenium_module['Options']()
            chrome_options.add_argument('--headless')  # 无头模式
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            # 设置User-Agent
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # 方法1：尝试使用 webdriver-manager (如果已安装)
            if self.chrome_driver_manager:
                try:
                    self.root.after(0, self.add_log, "尝试使用 webdriver-manager...")
                    # 清除缓存强制重新下载
                    chromedriver_path = self.chrome_driver_manager().install()
                    self.root.after(0, self.add_log, f"驱动路径: {chromedriver_path}")
                    service = self.selenium_module['Service'](chromedriver_path)
                    driver = self.selenium_module['webdriver'].Chrome(service=service, options=chrome_options)
                    self.root.after(0, self.add_log, "ChromeDriver 启动成功")
                    driver.set_page_load_timeout(30)
                    return driver
                except Exception as e:
                    self.root.after(0, self.add_log, f"webdriver-manager 失败: {str(e)}")
            
            # 方法2：使用 Selenium 内置的驱动管理器 (Selenium 4.6+)
            try:
                self.root.after(0, self.add_log, "尝试使用 Selenium 内置驱动管理器...")
                # Selenium 4.6+ 会自动下载正确版本的 chromedriver
                driver = self.selenium_module['webdriver'].Chrome(options=chrome_options)
                self.root.after(0, self.add_log, "Selenium 驱动管理器 启动成功")
                driver.set_page_load_timeout(30)
                return driver
            except Exception as e:
                self.root.after(0, self.add_log, f"Selenium 内置驱动管理器失败: {str(e)}")
            
            # 方法3：使用本地 chromedriver
            chromedriver_path = Path(__file__).parent / "chromedriver.exe"
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
        """切换监控状态"""
        if self.monitor_enabled.get():
            self.start_monitoring()
        else:
            self.stop_monitoring()
    
    def on_interval_change(self, _event=None):
        """检查间隔改变事件"""
        interval_text = self.interval_combo.get()
        interval_map = {
            "10秒": 10,
            "30秒": 30,
            "1分钟": 60,
            "5分钟": 300,
            "10分钟": 600
        }
        self.monitor_interval = interval_map.get(interval_text, 30)
        
        if self.monitor_enabled.get():
            self.stop_monitoring()
            self.start_monitoring()
    
    def start_monitoring(self):
        """开始页面监控"""
        if not self.selenium_available:
            messagebox.showerror("错误", "Selenium未安装，无法进行动态页面监控")
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
        self.initial_check_done = {}  # 标记每个池子是否完成首次检查
        
        # 重置所有池子状态
        for pool_id, pool_data in self.pools.items():
            pool_data["confirmed_exists"] = None
            if pool_id in self.pool_frames:
                self.pool_frames[pool_id]["status"].set("等待监控")
                self.pool_frames[pool_id]["card"].config(bg="SystemButtonFace")
        
        pool_names = [p["name"] for p in self.pools.values()]
        self.add_log(f"=== 开始监控 (Selenium模式) ===")
        self.add_log(f"监控池子数量: {len(self.pools)}")
        self.add_log(f"监控池子: {', '.join(pool_names)}")
        self.add_log(f"监控元素: 5发不重")
        self.add_log(f"检查间隔: {self.monitor_interval}秒")
        
        self.monitor_thread = threading.Thread(target=self.monitor_worker, daemon=True)
        self.monitor_thread.start()
        
        self.monitor_status.set("正在监控...")
        self.status_var.set(f"页面监控已启动 - 监控{len(self.pools)}个池子")
    
    def stop_monitoring(self):
        """停止页面监控"""
        self.monitoring = False
        self.monitor_enabled.set(False)
        
        self.add_log("=== 监控已停止 ===")
        
        self.monitor_status.set("监控已停止")
        self.status_var.set("页面监控已停止")
        
        # 关闭WebDriver
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def monitor_worker(self):
        """监控工作线程 - 使用Selenium"""
        retry_count = 0
        max_retries = 2
        
        while self.monitoring:
            try:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 检查是否需要重新创建driver
                if self.driver is None:
                    self.root.after(0, self.add_log, "正在创建 WebDriver...")
                    self.driver = self.create_driver()
                    if self.driver is None:
                        self.root.after(0, self.add_log, "无法创建WebDriver，等待重试...")
                        time.sleep(5)
                        continue
                    self.root.after(0, self.add_log, "WebDriver 创建成功")
                
                # 遍历所有池子进行检查
                pool_results = {}
                driver_error = False
                
                for pool_id, pool_data in self.pools.items():
                    pool_name = pool_data["name"]
                    url = pool_data["url"]
                    
                    self.root.after(0, self.add_log, f"[{pool_name}] 正在访问页面... ({self.check_count + 1})")
                    
                    try:
                        self.driver.get(url)
                        time.sleep(3)  # 等待JavaScript执行
                        page_source = self.driver.page_source
                        
                        # 检查"5发不重"是否存在
                        has_5fa = ('5发不重' in page_source or '5发不重复' in page_source)
                        pool_results[pool_id] = has_5fa
                        
                        self.root.after(0, self.add_log, f"[{pool_name}] 页面已加载，5发不重: {'存在' if has_5fa else '不存在'}")
                        
                    except Exception as e:
                        self.root.after(0, self.add_log, f"[{pool_name}] 页面访问失败: {str(e)}")
                        driver_error = True
                        break
                
                if driver_error:
                    retry_count += 1
                    if retry_count >= max_retries:
                        self.root.after(0, self.add_log, "重试次数过多，停止监控")
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
                
                # 在主线程更新UI
                self.root.after(0, self.update_check_info, current_time)
                
                # 检查所有池子的变化
                self.root.after(0, self.check_changes, pool_results, current_time)
                
                self.root.after(0, self.add_log, f"本次检查完成，等待 {self.monitor_interval} 秒...")
                
            except Exception as e:
                self.root.after(0, self.add_log, f"[{datetime.now().strftime('%H:%M:%S')}] 检查失败: {str(e)}")
            
            # 等待下一个检查周期
            for _ in range(self.monitor_interval):
                if not self.monitoring:
                    break
                time.sleep(1)
        
        self.root.after(0, self.add_log, "监控线程已退出")
    
    def check_changes(self, pool_results, check_time):
        """检查所有池子的元素存在变化"""
        changed_pools = []
        
        for pool_id, currently_exists in pool_results.items():
            if pool_id not in self.pools:
                continue
            
            pool_data = self.pools[pool_id]
            pool_name = pool_data["name"]
            was_exists = pool_data.get("confirmed_exists")
            
            # 首次检查：记录初始状态
            if was_exists is None:
                pool_data["exists"] = currently_exists
                pool_data["confirmed_exists"] = currently_exists
                
                if pool_id in self.pool_frames:
                    frame_data = self.pool_frames[pool_id]
                    if currently_exists:
                        frame_data["status"].set("存在")
                        frame_data["card"].config(bg="#e8f5e9")
                    else:
                        frame_data["status"].set("不存在")
                        frame_data["card"].config(bg="#ffcccc")
                
                self.add_log(f"[{pool_name}] 初始状态: {'存在' if currently_exists else '不存在'}")
                continue
            
            # 检查存在性变化
            if was_exists and not currently_exists:
                # 元素消失了
                pool_data["exists"] = False
                pool_data["confirmed_exists"] = False
                changed_pools.append((pool_name, "消失", True))
                
                if pool_id in self.pool_frames:
                    self.pool_frames[pool_id]["status"].set("⚠ 已消失！")
                    self.pool_frames[pool_id]["card"].config(bg="#ffcccc")
                
            elif not was_exists and currently_exists:
                # 元素出现了
                pool_data["exists"] = True
                pool_data["confirmed_exists"] = True
                changed_pools.append((pool_name, "出现", True))
                
                if pool_id in self.pool_frames:
                    self.pool_frames[pool_id]["status"].set("✓ 重新出现！")
                    self.pool_frames[pool_id]["card"].config(bg="#e8f5e9")
                
            elif currently_exists:
                # 元素存在
                if pool_id in self.pool_frames:
                    current_bg = self.pool_frames[pool_id]["card"].cget("bg")
                    if current_bg != "#e8f5e9":
                        self.pool_frames[pool_id]["card"].config(bg="#e8f5e9")
                    self.pool_frames[pool_id]["status"].set("存在")
        
        # 处理变化的池子
        if changed_pools:
            self.change_count += len(changed_pools)
            for pool_name, change_type, _ in changed_pools:
                if change_type == "消失":
                    self.add_log(f"[{check_time}] ★★ [{pool_name}] 5发不重 已从页面消失！★★")
                    self.status_var.set(f"⚠ [{pool_name}] 5发不重 已消失！")
                    messagebox.showwarning(f"【{pool_name}】5发不重消失提醒", 
                        f"重要提醒！\n\n【{pool_name}】的5发不重 已从页面消失！\n\n时间: {check_time}")
                else:
                    self.add_log(f"[{check_time}] ★★ [{pool_name}] 5发不重 已重新出现！★★")
                    self.status_var.set(f"✓ [{pool_name}] 5发不重 已重新出现！")
                    messagebox.showwarning(f"【{pool_name}】5发不重出现提醒", 
                        f"重要提醒！\n\n【{pool_name}】的5发不重 已重新出现在页面！\n\n时间: {check_time}")
        else:
            # 没有变化
            status_parts = []
            for pool_id, pool_data in self.pools.items():
                status_parts.append(f"{pool_data['name']}:{'✓' if pool_data['confirmed_exists'] else '✗'}")
            self.monitor_status.set(f"未检测到变化 | 最后检查: {check_time.split(' ')[1]}")
    
    def update_check_info(self, check_time):
        """更新检查信息"""
        self.monitor_status.set(f"最后检查: {check_time}")
    
    def add_log(self, message):
        """添加日志消息"""
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.monitor_log.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")
    
    def clear_log(self):
        """清空日志"""
        self.log_text.delete("1.0", "end")
        self.monitor_log.clear()
        self.add_log("日志已清空")
    
    def export_log(self):
        """导出日志"""
        from tkinter import filedialog
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialfile=f"bilibili_monitor_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("B站商城商品监控日志\n")
                    f.write(f"监控URL: {self.url_entry.get().strip()}\n")
                    f.write(f"监控元素: 5发不重\n")
                    f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 80 + "\n\n")
                    for log in self.monitor_log:
                        f.write(log + "\n")
                
                messagebox.showinfo("导出成功", f"日志已保存到:\n{file_path}")
            except Exception as e:
                messagebox.showerror("导出失败", f"无法保存日志:\n{str(e)}")
    
    def open_in_browser(self):
        """使用系统默认浏览器打开链接"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("警告", "请输入有效的URL")
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
        """复制当前URL到剪贴板"""
        url = self.url_entry.get().strip()
        if url:
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.status_var.set("链接已复制到剪贴板")
            messagebox.showinfo("提示", "链接已复制到剪贴板")
        else:
            messagebox.showwarning("警告", "没有可复制的链接")
    
    def on_closing(self):
        """窗口关闭事件"""
        if self.monitoring:
            self.stop_monitoring()
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = BilibiliMallReader(root)
    root.mainloop()


if __name__ == "__main__":
    main()
