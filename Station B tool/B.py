import os
import re
import time
import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog


class BilibiliMarqueeExtractor:
    """B站会员购页面跑马灯文字 & 商品详情提取器"""

    def __init__(self, driver_path=None, headless=False, log_callback=None):
        self.driver = None
        self.driver_path = driver_path
        self.headless = headless
        self.log = log_callback if log_callback else print

    def setup_driver(self):
        """设置ChromeDriver"""
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument(
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        try:
            if self.driver_path and os.path.exists(self.driver_path):
                service = Service(executable_path=self.driver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
                self.log(f"使用指定的ChromeDriver: {self.driver_path}")
            else:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
                self.log("使用webdriver-manager自动管理的ChromeDriver")
        except ImportError:
            self.log("未安装webdriver-manager，尝试使用默认ChromeDriver")
            self.driver = webdriver.Chrome(options=options)
        except Exception as e:
            self.log(f"ChromeDriver初始化失败: {e}")
            raise

    def extract_marquee(self, url, wait_time=15):
        """提取页面中的跑马灯文字"""
        if not self.driver:
            self.setup_driver()

        marquee_texts = []

        try:
            self.log(f"正在访问: {url}")
            self.driver.get(url)

            # 等待用户手动点击"展开全部"
            self.log("等待5秒，请在浏览器中点击【展开全部】按钮...")
            time.sleep(5)
            self.log("等待结束，开始提取商品详情")

            wait = WebDriverWait(self.driver, wait_time)

            try:
                marquee_container = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, ".franky-marquee_container")
                    )
                )
                self.log("找到 .franky-marquee_container 元素")

                content_elements = marquee_container.find_elements(
                    By.CSS_SELECTOR, ".franky-marquee_content"
                )

                if content_elements:
                    self.log(f"找到 {len(content_elements)} 个 .franky-marquee_content 元素")
                    for content_el in content_elements:
                        inner_div = content_el.find_element(By.CSS_SELECTOR, "div")
                        text = inner_div.text.strip().rstrip()
                        if text:
                            marquee_texts.append(text)
                else:
                    all_divs = marquee_container.find_elements(By.CSS_SELECTOR, "div")
                    for div in all_divs:
                        text = div.text.strip()
                        if text:
                            marquee_texts.append(text)

            except TimeoutException:
                self.log("未找到 .franky-marquee_container，尝试备用方案...")
                time.sleep(3)
                all_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, "[class*='marquee'], [class*='franky']"
                )
                for el in all_elements:
                    text = el.text.strip()
                    if text and text not in marquee_texts:
                        marquee_texts.append(text)

            return marquee_texts

        except Exception as e:
            self.log(f"提取失败: {e}")
            import traceback
            self.log(traceback.format_exc())
            return marquee_texts

    def save_to_file(self, marquee_texts, url, filename="marquee_text.txt"):
        """保存跑马灯文字到文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("B站会员购页面跑马灯文字\n")
                f.write(f"来源: {url}\n")
                f.write(f"提取时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                if marquee_texts:
                    unique_texts = list(dict.fromkeys(marquee_texts))
                    for i, text in enumerate(unique_texts, 1):
                        f.write(f"[{i}] {text}\n")
                else:
                    f.write("未提取到任何跑马灯文字\n")
            self.log(f"已保存到: {filename}")
        except Exception as e:
            self.log(f"保存失败: {e}")

    def extract_product_details(self, url, wait_time=15):
        """提取 .img-detail.ql-editor 中的商品详情"""
        if not self.driver:
            self.setup_driver()

        products = []

        try:
            self.log(f"正在访问: {url}")
            self.driver.get(url)

            # 等待用户手动点击"展开全部"
            self.log("等待5秒，请在浏览器中点击【展开全部】按钮...")
            time.sleep(5)
            self.log("等待结束，开始提取商品详情")

            wait = WebDriverWait(self.driver, wait_time)

            try:
                detail_container = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, ".img-detail.ql-editor")
                    )
                )
                self.log("找到 .img-detail.ql-editor 容器")

                # 获取所有 <p> 子元素（直接子元素和嵌套的 p）
                p_elements = detail_container.find_elements(By.CSS_SELECTOR, "p")
                self.log(f"找到 {len(p_elements)} 个 <p> 段落")

                # 解析段落，按商品分块
                product = None
                for p_el in p_elements:
                    text = p_el.text.strip()
                    if not text:
                        continue

                    # 检测是否为新商品条目开头（"超神款"、"欧皇款"、"普通款"）
                    if re.match(r'^(超神款|欧皇款|普通款)：', text):
                        if product:
                            products.append(product)
                        product = {"name": text, "spec": "", "size": "",
                                   "material": "", "official_price": "",
                                   "reference_price": "", "extra": []}
                    elif product is not None:
                        if text.startswith('规格') or text.startswith('规格:'):
                            product["spec"] = text.split(':', 1)[-1].strip() if ':' in text else text.split('：', 1)[-1].strip()
                        elif text.startswith('尺寸') or text.startswith('尺寸:'):
                            product["size"] = text.split(':', 1)[-1].strip() if ':' in text else text.split('：', 1)[-1].strip()
                        elif text.startswith('材质') or text.startswith('材质:'):
                            product["material"] = text.split(':', 1)[-1].strip() if ':' in text else text.split('：', 1)[-1].strip()
                        elif text.startswith('官方价') or text.startswith('官方价:'):
                            product["official_price"] = text.split(':', 1)[-1].strip() if ':' in text else text.split('：', 1)[-1].strip()
                        elif text.startswith('参考价格') or text.startswith('参考价格:'):
                            product["reference_price"] = text.split(':', 1)[-1].strip() if ':' in text else text.split('：', 1)[-1].strip()
                        else:
                            product["extra"].append(text)

                # 最后一个商品入列
                if product:
                    products.append(product)

                # 提取图片
                try:
                    img_elements = detail_container.find_elements(
                        By.CSS_SELECTOR, ".desc-wrapper img"
                    )
                    self.log(f"找到 {len(img_elements)} 张图片")
                    for i, img in enumerate(img_elements):
                        src = img.get_attribute("src") or img.get_attribute("data-src") or ""
                        if src and i < len(products):
                            products[i]["image"] = src
                except Exception:
                    self.log("图片提取失败")

                self.log(f"成功解析 {len(products)} 条商品详情")

            except TimeoutException:
                self.log("未找到 .img-detail.ql-editor 容器")
                # 备用方案：直接获取 body 文本
                body = self.driver.find_element(By.TAG_NAME, "body")
                self.log(f"页面主体文本预览: {body.text[:500]}...")

            return products

        except Exception as e:
            self.log(f"提取商品详情失败: {e}")
            import traceback
            self.log(traceback.format_exc())
            return products

    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.log("浏览器已关闭")


class MarqueeExtractorGUI:
    """B站会员购跑马灯提取器 - 图形界面（支持跑马灯 & 商品详情）"""

    BASE_URL = (
        "https://mall.bilibili.com/neul-next/index.html"
        "?activeType=1&page=magic-detail_detail&noTitleBar=1&itemsId="
    )

    def __init__(self, root):
        self.root = root
        self.root.title("B站会员购提取器（跑马灯 & 商品详情）")
        self.root.geometry("1000x800")
        self.root.resizable(True, True)

        self.driver_path = r"Station B tool\chromedriver.exe"
        self.extractor = None
        self.is_running = False
        self.last_result = None
        self.last_detail_result = None

        self.create_widgets()

    def create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)

        # ---- 标题 ----
        title_label = ttk.Label(
            main_frame, text="B站会员购提取器（跑马灯 & 商品详情）",
            font=("Microsoft YaHei", 16, "bold")
        )
        title_label.grid(row=0, column=0, pady=(0, 10), sticky=tk.W)

        # ---- 商品ID输入 ----
        input_frame = ttk.LabelFrame(main_frame, text="商品ID", padding="10")
        input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        input_frame.columnconfigure(0, weight=1)

        self.item_id_var = tk.StringVar(value="13654224")
        item_id_entry = ttk.Entry(
            input_frame, textvariable=self.item_id_var, font=("Microsoft YaHei", 10)
        )
        item_id_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))

        tip_label = ttk.Label(
            input_frame, text="支持输入商品ID(如: 13654224)或完整链接",
            font=("Microsoft YaHei", 8), foreground="gray"
        )
        tip_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))

        # ---- 选项 + 按钮 ----
        ctrl_frame = ttk.Frame(main_frame)
        ctrl_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # 无头模式
        self.headless_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            ctrl_frame, text="无头模式（不显示浏览器窗口）",
            variable=self.headless_var
        ).grid(row=0, column=0, sticky=tk.W, padx=5)

        # 提取模式选择
        ttk.Label(ctrl_frame, text="提取模式:").grid(row=0, column=1, padx=(20, 5))
        self.mode_var = tk.StringVar(value="both")
        ttk.Radiobutton(ctrl_frame, text="跑马灯", variable=self.mode_var,
                        value="marquee").grid(row=0, column=2, padx=5)
        ttk.Radiobutton(ctrl_frame, text="商品详情", variable=self.mode_var,
                        value="detail").grid(row=0, column=3, padx=5)
        ttk.Radiobutton(ctrl_frame, text="全部", variable=self.mode_var,
                        value="both").grid(row=0, column=4, padx=5)

        # 按钮
        self.start_btn = ttk.Button(ctrl_frame, text="开始提取", command=self.start, width=12)
        self.start_btn.grid(row=0, column=5, padx=5)

        self.stop_btn = ttk.Button(ctrl_frame, text="停止", command=self.stop, width=12, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=6, padx=5)

        ttk.Button(ctrl_frame, text="保存结果", command=self.save_result, width=12).grid(row=0, column=7, padx=5)

        ttk.Button(ctrl_frame, text="清空日志", command=self.clear_log, width=12).grid(row=0, column=8, padx=5)

        # ---- Notebook 双标签页 ----
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # --- 跑马灯标签页 ---
        marquee_tab = ttk.Frame(self.notebook)
        self.notebook.add(marquee_tab, text="跑马灯结果")
        marquee_tab.columnconfigure(0, weight=1)
        marquee_tab.rowconfigure(0, weight=1)

        self.marquee_result = scrolledtext.ScrolledText(
            marquee_tab, font=("Microsoft YaHei", 10), wrap=tk.WORD
        )
        self.marquee_result.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 跑马灯右键复制菜单
        self.marquee_result.bind("<Button-3>", self.show_copy_menu)
        self.copy_menu = tk.Menu(self.root, tearoff=0)
        self.copy_menu.add_command(label="复制选中内容", command=self.copy_selected)

        # --- 商品详情标签页 ---
        detail_tab = ttk.Frame(self.notebook)
        self.notebook.add(detail_tab, text="商品详情")
        detail_tab.columnconfigure(0, weight=1)
        detail_tab.rowconfigure(0, weight=1)

        self.detail_tree = ttk.Treeview(
            detail_tab,
            columns=("index", "name", "spec", "size", "material",
                     "official_price", "reference_price"),
            show="headings",
            selectmode="extended"
        )

        # 定义列
        self.detail_tree.heading("index", text="序号", anchor=tk.CENTER)
        self.detail_tree.heading("name", text="商品名称")
        self.detail_tree.heading("spec", text="规格")
        self.detail_tree.heading("size", text="尺寸")
        self.detail_tree.heading("material", text="材质")
        self.detail_tree.heading("official_price", text="官方价")
        self.detail_tree.heading("reference_price", text="参考价格")

        self.detail_tree.column("index", width=50, anchor=tk.CENTER)
        self.detail_tree.column("name", width=280)
        self.detail_tree.column("spec", width=140)
        self.detail_tree.column("size", width=160)
        self.detail_tree.column("material", width=120)
        self.detail_tree.column("official_price", width=120)
        self.detail_tree.column("reference_price", width=100)

        # 滚动条
        tree_scroll_y = ttk.Scrollbar(detail_tab, orient=tk.VERTICAL,
                                       command=self.detail_tree.yview)
        tree_scroll_x = ttk.Scrollbar(detail_tab, orient=tk.HORIZONTAL,
                                       command=self.detail_tree.xview)
        self.detail_tree.configure(yscrollcommand=tree_scroll_y.set,
                                    xscrollcommand=tree_scroll_x.set)
        self.detail_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        tree_scroll_x.grid(row=0, column=2, sticky=(tk.W, tk.E),
                           pady=(0, 16))

        # Treeview 右键菜单
        self.detail_tree.bind("<Button-3>", self.show_tree_copy_menu)
        self.tree_menu = tk.Menu(self.root, tearoff=0)
        self.tree_menu.add_command(label="复制选中行", command=self.copy_tree_selection)

        # --- 日志标签页 ---
        log_tab = ttk.Frame(self.notebook)
        self.notebook.add(log_tab, text="运行日志")
        log_tab.columnconfigure(0, weight=1)
        log_tab.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(
            log_tab, font=("Consolas", 9), wrap=tk.WORD
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # ---- 状态栏 ----
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(
            main_frame, textvariable=self.status_var,
            relief=tk.SUNKEN, anchor=tk.W
        ).grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(5, 0))

    # ==================== 辅助方法 ====================

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def show_copy_menu(self, event):
        try:
            if self.marquee_result.get(tk.SEL_FIRST, tk.SEL_LAST):
                self.copy_menu.post(event.x_root, event.y_root)
        except tk.TclError:
            pass

    def copy_selected(self):
        try:
            text = self.marquee_result.get(tk.SEL_FIRST, tk.SEL_LAST)
            if text:
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                self.log("已复制到剪贴板")
        except tk.TclError:
            messagebox.showinfo("提示", "请先选中要复制的文本")

    def show_tree_copy_menu(self, event):
        if self.detail_tree.selection():
            self.tree_menu.post(event.x_root, event.y_root)

    def copy_tree_selection(self):
        selected = self.detail_tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选中要复制的行")
            return

        lines = []
        for item_id in selected:
            values = self.detail_tree.item(item_id, "values")
            # 格式化: [序号] 名称 | 规格 | 尺寸 | 材质 | 官方价 | 参考价格
            line = f"[{values[0]}] {values[1]}"
            if values[2]:
                line += f" | 规格:{values[2]}"
            if values[3]:
                line += f" | 尺寸:{values[3]}"
            if values[4]:
                line += f" | 材质:{values[4]}"
            if values[5]:
                line += f" | 官方价:{values[5]}"
            if values[6]:
                line += f" | 参考价格:{values[6]}"
            lines.append(line)

        text = "\n".join(lines)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.log(f"已复制 {len(selected)} 行到剪贴板")

    # ==================== 核心操作 ====================

    def start(self):
        if self.is_running:
            messagebox.showwarning("警告", "任务正在进行中！")
            return

        input_text = self.item_id_var.get().strip()
        if not input_text:
            messagebox.showerror("错误", "请输入商品ID或商品链接！")
            return

        if input_text.startswith('http'):
            url = input_text
        else:
            url = f"{self.BASE_URL}{input_text}"

        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set("正在提取...")

        # 清空上次结果
        self.marquee_result.delete(1.0, tk.END)
        for item in self.detail_tree.get_children():
            self.detail_tree.delete(item)

        mode = self.mode_var.get()
        thread = threading.Thread(target=self._do_extract, args=(url, mode), daemon=True)
        thread.start()

    def _do_extract(self, url, mode):
        marquee_texts = []
        product_details = []

        try:
            self.log("=" * 60)
            if mode == "marquee":
                self.log("模式: 跑马灯提取")
            elif mode == "detail":
                self.log("模式: 商品详情提取")
            else:
                self.log("模式: 全部提取（跑马灯 + 商品详情）")

            headless = self.headless_var.get()
            self.extractor = BilibiliMarqueeExtractor(
                driver_path=self.driver_path,
                headless=headless,
                log_callback=self.log
            )
            self.extractor.setup_driver()
            self.log("ChromeDriver初始化成功")

            # 提取跑马灯
            if mode in ("marquee", "both"):
                marquee_texts = self.extractor.extract_marquee(url)
                self.last_result = (marquee_texts, url)

            # 提取商品详情
            if mode in ("detail", "both"):
                product_details = self.extractor.extract_product_details(url)
                self.last_detail_result = (product_details, url)

            # 显示结果
            self.display_result(marquee_texts, product_details, url, mode)

            self.log("=" * 60)
            if mode in ("marquee", "both"):
                if marquee_texts:
                    unique = list(dict.fromkeys(marquee_texts))
                    self.log(f"[跑马灯] 提取完成！共 {len(unique)} 条（去重后）")
                else:
                    self.log("[跑马灯] 未获取到文字")
            if mode in ("detail", "both"):
                self.log(f"[商品详情] 提取完成！共 {len(product_details)} 条")
            self.status_var.set("提取完成")

            # 自动切换到详情页
            if mode in ("detail", "both") and product_details:
                self.notebook.select(1)  # 商品详情标签页
            elif mode == "marquee":
                self.notebook.select(0)  # 跑马灯标签页

        except Exception as e:
            self.log(f"发生错误: {e}")
            import traceback
            self.log(traceback.format_exc())
            self.status_var.set("提取失败")
        finally:
            if self.extractor:
                self.extractor.close()
            self.is_running = False
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

    def display_result(self, marquee_texts, product_details, url, mode):
        # --- 跑马灯结果 ---
        if mode in ("marquee", "both"):
            self.marquee_result.delete(1.0, tk.END)
            lines = [
                "B站会员购页面跑马灯文字",
                f"来源: {url}",
                f"提取时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                "=" * 60,
                ""
            ]
            if marquee_texts:
                unique_texts = list(dict.fromkeys(marquee_texts))
                for i, text in enumerate(unique_texts, 1):
                    lines.append(f"[{i}] {text}")
            else:
                lines.append("未提取到任何跑马灯文字")
            self.marquee_result.insert(tk.END, "\n".join(lines))

        # --- 商品详情结果 ---
        if mode in ("detail", "both"):
            for item in self.detail_tree.get_children():
                self.detail_tree.delete(item)
            if product_details:
                for i, p in enumerate(product_details, 1):
                    self.detail_tree.insert("", tk.END, values=(
                        str(i),
                        p.get("name", ""),
                        p.get("spec", ""),
                        p.get("size", ""),
                        p.get("material", ""),
                        p.get("official_price", ""),
                        p.get("reference_price", "")
                    ))

        self.log("结果已显示")

    def stop(self):
        if self.extractor and self.extractor.driver:
            try:
                self.extractor.close()
                self.log("已停止提取")
                self.status_var.set("已停止")
            except Exception:
                pass
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def save_result(self):
        mode = self.mode_var.get()

        has_marquee = self.last_result and mode in ("marquee", "both")
        has_detail = self.last_detail_result and mode in ("detail", "both")

        if not has_marquee and not has_detail:
            messagebox.showwarning("警告", "没有可保存的提取结果！")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialfile="extract_result.txt"
        )
        if not filename:
            return

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("B站会员购页面提取结果\n")
                f.write(f"提取时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")

                # 跑马灯
                if has_marquee:
                    marquee_texts, url = self.last_result
                    f.write("【跑马灯文字】\n")
                    f.write(f"来源: {url}\n")
                    f.write("-" * 40 + "\n")
                    if marquee_texts:
                        unique = list(dict.fromkeys(marquee_texts))
                        for i, text in enumerate(unique, 1):
                            f.write(f"[{i}] {text}\n")
                    else:
                        f.write("未提取到任何跑马灯文字\n")
                    f.write("\n")

                # 商品详情
                if has_detail:
                    product_details, url = self.last_detail_result
                    f.write("【商品详情】\n")
                    f.write(f"来源: {url}\n")
                    f.write("-" * 40 + "\n")
                    if product_details:
                        for i, p in enumerate(product_details, 1):
                            f.write(f"[{i}] {p.get('name', '')}\n")
                            if p.get('spec'):
                                f.write(f"    规格: {p['spec']}\n")
                            if p.get('size'):
                                f.write(f"    尺寸: {p['size']}\n")
                            if p.get('material'):
                                f.write(f"    材质: {p['material']}\n")
                            if p.get('official_price'):
                                f.write(f"    官方价: {p['official_price']}\n")
                            if p.get('reference_price'):
                                f.write(f"    参考价格: {p['reference_price']}\n")
                            if p.get('image'):
                                f.write(f"    图片: {p['image']}\n")
                            f.write("\n")
                    else:
                        f.write("未提取到任何商品详情\n")

            self.log(f"结果已保存到: {filename}")
            messagebox.showinfo("成功", f"结果已保存到:\n{filename}")
        except Exception as e:
            self.log(f"保存失败: {e}")
            messagebox.showerror("错误", f"保存失败:\n{e}")

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
        self.marquee_result.delete(1.0, tk.END)
        for item in self.detail_tree.get_children():
            self.detail_tree.delete(item)
        self.log("日志已清空")


def main():
    root = tk.Tk()
    app = MarqueeExtractorGUI(root)

    # 居中显示
    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f'+{x}+{y}')

    root.mainloop()


if __name__ == "__main__":
    main()
