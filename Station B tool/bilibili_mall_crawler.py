import os
import sys
import time
import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog


class BilibiliMallCrawler:
    """B站会员购爬虫类"""
    
    def __init__(self, driver_path=None, headless=False):
        """
        初始化爬虫
        
        Args:
            driver_path: ChromeDriver路径，如果为None则使用webdriver-manager
            headless: 是否使用无头模式
        """
        self.driver = None
        self.driver_path = driver_path
        self.headless = headless
        
    def setup_driver(self):
        """设置ChromeDriver"""
        options = webdriver.ChromeOptions()
        
        if self.headless:
            options.add_argument('--headless')
        
        # 添加常用的浏览器选项
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            if self.driver_path and os.path.exists(self.driver_path):
                # 使用指定的ChromeDriver路径
                service = Service(executable_path=self.driver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
                print(f"✓ 使用指定的ChromeDriver: {self.driver_path}")
            else:
                # 使用webdriver-manager自动管理
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
                print("✓ 使用webdriver-manager自动管理的ChromeDriver")
        except ImportError:
            print("✗ 未安装webdriver-manager，尝试使用默认ChromeDriver")
            self.driver = webdriver.Chrome(options=options)
        except Exception as e:
            print(f"✗ ChromeDriver初始化失败: {e}")
            raise
    
    def get_product_info(self, url):
        """
        获取商品信息
        
        Args:
            url: 商品页面URL
            
        Returns:
            dict: 商品信息字典
        """
        if not self.driver:
            self.setup_driver()
        
        product_info = {
            'name': '',
            'price': '',
            'original_price': '',
            'deposit_price': '',
            'description': '',
            'images': [],
            'specifications': {},  # 商品规格信息
            'status': '',           # 商品状态(预售开始/制作完成等)
            'status_time': '',      # 状态时间
            'url': url
        }
        
        try:
            print(f"\n正在访问: {url}")
            self.driver.get(url)
            
            # 等待页面加载
            wait = WebDriverWait(self.driver, 15)
            
            # 等待商品名称元素出现
            try:
                name_element = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".clamp-real-text"))
                )
                product_info['name'] = name_element.text.strip()
                print(f"✓ 商品名称: {product_info['name']}")
            except TimeoutException:
                print("⚠ 未找到商品名称元素")
            
            # 尝试获取价格信息
            try:
                price_elements = self.driver.find_elements(By.CSS_SELECTOR, ".price-current, .sale-price, .current-price")
                if price_elements:
                    product_info['price'] = price_elements[0].text.strip()
                    print(f"✓ 商品价格: {product_info['price']}")
            except Exception as e:
                print(f"⚠ 获取价格失败: {e}")
            
            # 尝试获取原价
            try:
                original_price_elements = self.driver.find_elements(By.CSS_SELECTOR, ".price-original, .original-price")
                if original_price_elements:
                    product_info['original_price'] = original_price_elements[0].text.strip()
                    print(f"✓ 商品原价: {product_info['original_price']}")
            except Exception as e:
                print(f"⚠ 获取原价失败: {e}")
            
            # 尝试获取定金价格
            try:
                deposit_element = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".deposit-price"))
                )
                if deposit_element:
                    product_info['deposit_price'] = deposit_element.text.strip()
                    print(f"✓ 商品定金: {product_info['deposit_price']}")
            except TimeoutException:
                print("⚠ 未找到定金价格元素")
            except Exception as e:
                print(f"⚠ 获取定金价格失败: {e}")
            
            # 尝试获取商品描述
            try:
                desc_elements = self.driver.find_elements(By.CSS_SELECTOR, ".description, .product-desc, .detail-desc")
                if desc_elements:
                    product_info['description'] = desc_elements[0].text.strip()
                    print(f"✓ 商品描述: {product_info['description'][:100]}...")
            except Exception as e:
                print(f"⚠ 获取描述失败: {e}")
            
            # 尝试获取商品图片
            try:
                img_elements = self.driver.find_elements(By.CSS_SELECTOR, "img.product-img, img.detail-img, .gallery img")
                for img in img_elements[:5]:  # 最多获取5张图片
                    src = img.get_attribute('src') or img.get_attribute('data-src')
                    if src:
                        product_info['images'].append(src)
                if product_info['images']:
                    print(f"✓ 获取到 {len(product_info['images'])} 张商品图片")
            except Exception as e:
                print(f"⚠ 获取图片失败: {e}")
            
            # 尝试获取商品规格信息（尺寸、比例、官方价、发售日、材质、特典等）
            try:
                spec_items = self.driver.find_elements(By.CSS_SELECTOR, ".item-complex")
                if spec_items:
                    print(f"✓ 找到 {len(spec_items)} 个商品规格项")
                    for item in spec_items:
                        try:
                            key_element = item.find_element(By.CSS_SELECTOR, ".item-complex-key")
                            value_element = item.find_element(By.CSS_SELECTOR, ".item-complex-value")
                            if key_element and value_element:
                                key = key_element.text.strip()
                                value = value_element.text.strip()
                                if key and value:
                                    product_info['specifications'][key] = value
                                    print(f"  - {key}: {value}")
                        except Exception as e:
                            continue
            except Exception as e:
                print(f"⚠ 获取商品规格失败: {e}")
            
            # 尝试获取商品状态信息(预售开始/制作完成等)
            try:
                status_element = self.driver.find_element(By.CSS_SELECTOR, ".pro-item-bottom")
                if status_element:
                    product_info['status'] = status_element.text.strip()
                    print(f"✓ 商品状态: {product_info['status']}")
            except Exception as e:
                print(f"⚠ 获取商品状态失败: {e}")
            
            try:
                status_time_element = self.driver.find_element(By.CSS_SELECTOR, ".top-time")
                if status_time_element:
                    product_info['status_time'] = status_time_element.text.strip()
                    print(f"✓ 状态时间: {product_info['status_time']}")
            except Exception as e:
                print(f"⚠ 获取状态时间失败: {e}")
            
            # 获取页面中所有可能的文本信息（备用方案）
            if not product_info['name']:
                try:
                    # 尝试其他常见的商品名称选择器
                    selectors = [
                        "h1.product-title",
                        ".title",
                        "[class*='title']",
                        "[class*='name']"
                    ]
                    for selector in selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            if elements:
                                product_info['name'] = elements[0].text.strip()
                                if product_info['name']:
                                    print(f"✓ 商品名称(备用): {product_info['name']}")
                                    break
                        except:
                            continue
                except Exception as e:
                    print(f"⚠ 备用方案获取名称失败: {e}")
            
            return product_info
            
        except Exception as e:
            print(f"✗ 获取商品信息失败: {e}")
            return product_info
    
    def save_to_file(self, product_info, filename="product_info.txt"):
        """
        保存商品信息到文件
        
        Args:
            product_info: 商品信息字典
            filename: 输出文件名
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("商品信息\n")
                f.write(f"商品名称: {product_info['name']}\n")
                
                # 整合价格信息
                price_parts = []
                
                # 处理全款价格
                if product_info['price']:
                    price_text = product_info['price'].strip()
                    # 如果价格文本中包含"定金",提取全款部分
                    if '定金' in price_text:
                        # 尝试提取全款金额
                        import re
                        full_price_match = re.search(r'全款[¥￥]?\d+\.?\d*', price_text)
                        if full_price_match:
                            price_parts.append(full_price_match.group())
                    else:
                        price_parts.append(price_text)
                
                # 添加原价信息
                if product_info.get('original_price'):
                    original_price_text = product_info['original_price'].strip()
                    if original_price_text and original_price_text not in price_parts:
                        price_parts.append(original_price_text)
                
                # 添加定金信息
                if product_info.get('deposit_price'):
                    deposit_text = product_info['deposit_price'].strip()
                    # 确保定金格式统一
                    if not deposit_text.startswith('定金'):
                        deposit_text = f"定金{deposit_text}"
                    price_parts.append(deposit_text)
                
                if price_parts:
                    f.write(f"商品价格: {'，'.join(price_parts)}\n")
                
                f.write(f"商品链接: {product_info['url']}\n")
                
                # 保存商品规格信息
                if product_info.get('specifications'):
                    f.write("商品规格:\n")
                    for key, value in product_info['specifications'].items():
                        f.write(f"  {key}: {value}\n")
                
                f.write(f"\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            print(f"\n✓ 商品信息已保存到: {filename}")
            
        except Exception as e:
            print(f"✗ 保存文件失败: {e}")
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            print("✓ 浏览器已关闭")
    
    def __enter__(self):
        """上下文管理器入口"""
        self.setup_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


class BilibiliCrawlerGUI:
    """B站会员购爬虫图形界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("B站会员购商品爬虫")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # 默认配置
        self.base_url = "https://mall.bilibili.com/neul-next/detailuniversal/detail.html?page=detailuniversal_detail&itemsId="
        self.default_item_id = "13650409"
        self.driver_path = r"Station B tool\chromedriver.exe"
        self.crawler = None
        self.is_crawling = False
        self.product_info = None
        self.crawl_thread = None
        
        # 创建界面
        self.create_widgets()
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="B站会员购商品爬虫", font=("Microsoft YaHei", 16, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 10), sticky=tk.W)
        
        # URL输入区域
        url_frame = ttk.LabelFrame(main_frame, text="商品ID", padding="10")
        url_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        url_frame.columnconfigure(0, weight=1)
        
        self.item_id_var = tk.StringVar(value=self.default_item_id)
        item_id_entry = ttk.Entry(url_frame, textvariable=self.item_id_var, font=("Microsoft YaHei", 10))
        item_id_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # 添加提示标签
        tip_label = ttk.Label(url_frame, text="支持输入商品ID(如: 13650409)或完整链接", font=("Microsoft YaHei", 8), foreground="gray")
        tip_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # 选项区域
        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.headless_var = tk.BooleanVar(value=False)
        headless_check = ttk.Checkbutton(options_frame, text="无头模式（不显示浏览器窗口）", variable=self.headless_var)
        headless_check.grid(row=0, column=0, sticky=tk.W, padx=5)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.start_btn = ttk.Button(button_frame, text="开始爬取", command=self.start_crawling, width=15)
        self.start_btn.grid(row=0, column=0, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="停止", command=self.stop_crawling, width=15, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=1, padx=5)
        
        save_btn = ttk.Button(button_frame, text="保存结果", command=self.save_result, width=15)
        save_btn.grid(row=0, column=2, padx=5)
        
        clear_btn = ttk.Button(button_frame, text="清空日志", command=self.clear_log, width=15)
        clear_btn.grid(row=0, column=3, padx=5)
        
        # 日志显示区域
        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding="10")
        log_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, font=("Consolas", 9), wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 结果显示区域
        result_frame = ttk.LabelFrame(main_frame, text="商品信息", padding="10")
        result_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        
        self.result_text = scrolledtext.ScrolledText(result_frame, height=10, font=("Microsoft YaHei", 10), wrap=tk.WORD)
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 绑定右键菜单用于复制
        self.result_text.bind("<Button-3>", self.show_copy_menu)
        
        # 创建右键菜单
        self.copy_menu = tk.Menu(self.root, tearoff=0)
        self.copy_menu.add_command(label="复制选中内容", command=self.copy_selected_text)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=(5, 0))

    def log(self, message):
        """添加日志消息"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def start_crawling(self):
        """开始爬取"""
        if self.is_crawling:
            messagebox.showwarning("警告", "爬取任务正在进行中！")
            return
        
        input_text = self.item_id_var.get().strip()
        if not input_text:
            messagebox.showerror("错误", "请输入商品ID或商品链接！")
            return
        
        # 判断输入的是否是完整URL
        if input_text.startswith('http'):
            # 如果是完整URL,直接使用
            url = input_text
        else:
            # 否则当作商品ID处理,构建完整URL
            url = f"{self.base_url}{input_text}"
        
        self.is_crawling = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set("正在爬取...")
        self.result_text.delete(1.0, tk.END)
        
        # 在新线程中执行爬取
        thread = threading.Thread(target=self.crawl_product, args=(url,), daemon=True)
        thread.start()
    
    def crawl_product(self, url):
        """执行商品爬取（在后台线程中运行）"""
        try:
            self.log("=" * 60)
            self.log("开始爬取商品信息...")
            self.log(f"URL: {url}")
            
            headless = self.headless_var.get()
            self.crawler = BilibiliMallCrawler(driver_path=self.driver_path, headless=headless)
            self.crawler.setup_driver()
            
            self.log("ChromeDriver初始化成功")
            
            # 获取商品信息
            product_info = self.crawler.get_product_info(url)
            
            # 显示结果
            self.display_result(product_info)
            
            # 保存最后一次的爬取结果
            self.last_product_info = product_info
            
            self.log("=" * 60)
            self.log("爬取完成！")
            self.status_var.set("爬取完成")
            
        except Exception as e:
            self.log(f"✗ 发生错误: {str(e)}")
            self.status_var.set("爬取失败")
            import traceback
            self.log(traceback.format_exc())
        finally:
            if self.crawler:
                self.crawler.close()
            self.is_crawling = False
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

    def display_result(self, product_info):
        """显示爬取结果"""
        self.result_text.delete(1.0, tk.END)
        
        result = "商品信息\n"
        result += f"商品名称: {product_info['name']}\n"
        
        # 整合价格信息
        price_parts = []
        
        # 处理全款价格
        if product_info['price']:
            price_text = product_info['price'].strip()
            # 如果价格文本中包含"定金",提取全款部分
            if '定金' in price_text:
                # 尝试提取全款金额
                import re
                full_price_match = re.search(r'全款[¥￥]?\d+\.?\d*', price_text)
                if full_price_match:
                    price_parts.append(full_price_match.group())
            else:
                price_parts.append(price_text)
        
        # 添加原价信息
        if product_info.get('original_price'):
            original_price_text = product_info['original_price'].strip()
            if original_price_text and original_price_text not in price_parts:
                price_parts.append(original_price_text)
        
        # 添加定金信息
        if product_info.get('deposit_price'):
            deposit_text = product_info['deposit_price'].strip()
            # 确保定金格式统一
            if not deposit_text.startswith('定金'):
                deposit_text = f"定金{deposit_text}"
            price_parts.append(deposit_text)
        
        if price_parts:
            result += f"商品价格: {'，'.join(price_parts)}\n"
        
        result += f"商品链接: {product_info['url']}\n"
        
        # 显示商品规格信息
        if product_info.get('specifications'):
            result += "商品规格:\n"
            for key, value in product_info['specifications'].items():
                result += f"  {key}: {value}\n"
        
        result += f"\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        self.result_text.insert(tk.END, result)
        self.log("商品信息已显示")
    
    def stop_crawling(self):
        """停止爬取"""
        if self.crawler and self.crawler.driver:
            try:
                self.crawler.close()
                self.log("已停止爬取")
                self.status_var.set("已停止")
            except:
                pass
        self.is_crawling = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
    
    def save_result(self):
        """保存结果到文件"""
        if not hasattr(self, 'last_product_info') or not self.last_product_info:
            messagebox.showwarning("警告", "没有可保存的爬取结果！")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialfilename="product_info.txt"
        )
        
        if filename:
            try:
                self.crawler.save_to_file(self.last_product_info, filename)
                self.log(f"结果已保存到: {filename}")
                messagebox.showinfo("成功", f"结果已保存到:\n{filename}")
            except Exception as e:
                self.log(f"✗ 保存失败: {str(e)}")
                messagebox.showerror("错误", f"保存失败:\n{str(e)}")
    
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        self.result_text.delete(1.0, tk.END)
        self.log("日志已清空")
    
    def show_copy_menu(self, event):
        """显示复制菜单"""
        # 如果有选中的文本，显示复制菜单
        try:
            selected_text = self.result_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected_text:
                self.copy_menu.post(event.x_root, event.y_root)
        except tk.TclError:
            # 没有选中任何文本
            pass
    
    def copy_selected_text(self):
        """复制选中的文本到剪贴板"""
        try:
            selected_text = self.result_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected_text:
                self.root.clipboard_clear()
                self.root.clipboard_append(selected_text)
                self.log("✓ 已复制到剪贴板")
        except tk.TclError:
            messagebox.showinfo("提示", "请先选中要复制的文本")


def main():
    """主函数 - 启动图形界面"""
    root = tk.Tk()
    app = BilibiliCrawlerGUI(root)
    
    # 设置窗口图标（如果有的话）
    try:
        root.iconbitmap(default='icon.ico')
    except:
        pass
    
    # 居中显示窗口
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'+{x}+{y}')
    
    root.mainloop()


if __name__ == "__main__":
    main()
