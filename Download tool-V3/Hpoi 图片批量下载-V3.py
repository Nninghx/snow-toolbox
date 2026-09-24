import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
from bs4 import BeautifulSoup
import os
import re
import threading
from datetime import datetime
import urllib.parse
from PIL import Image
from io import BytesIO


class HpoiImageDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Hpoi 图片批量下载工具")
        self.root.geometry("900x700")
        
        # 设置 Windows 应用 ID
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('hpoi.image.downloader.v1')
        except:
            pass
        
        # 下载状态
        self.is_downloading = False
        self.download_count = 0
        self.total_count = 0
        self.filtered_count = 0  # 被过滤的图片数量
        
        self.create_widgets()
    
    def create_widgets(self):
        """创建界面组件"""
        # 标题
        title_frame = tk.Frame(self.root)
        title_frame.pack(fill=tk.X, padx=10, pady=5)
        
        title_label = tk.Label(
            title_frame, 
            text="🖼️ Hpoi 图片批量下载工具", 
            font=("Microsoft YaHei", 16, "bold"),
            fg="#2c3e50"
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            title_frame,
            text="输入商品页面 URL 自动提取并下载图片",
            font=("Microsoft YaHei", 10),
            fg="#7f8c8d"
        )
        subtitle_label.pack()
        
        # URL 输入区域
        url_frame = tk.LabelFrame(self.root, text="🔗 商品页面 URL", font=("Microsoft YaHei", 11, "bold"), padx=10, pady=10)
        url_frame.pack(fill=tk.X, padx=10, pady=5)
        
        url_input_frame = tk.Frame(url_frame)
        url_input_frame.pack(fill=tk.X)
        
        tk.Label(url_input_frame, text="URL:", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)
        
        self.url_var = tk.StringVar(value="https://www.hpoi.net/hobby/64155")
        url_entry = tk.Entry(url_input_frame, textvariable=self.url_var, font=("Microsoft YaHei", 10), width=60)
        url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 添加示例按钮
        example_btn = tk.Button(
            url_input_frame,
            text="📝 加载示例",
            command=self.load_example_url,
            bg="#3498db",
            fg="white",
            font=("Microsoft YaHei", 9),
            relief=tk.FLAT,
            cursor="hand2"
        )
        example_btn.pack(side=tk.LEFT, padx=5)
        
        # 配置区域
        config_frame = tk.LabelFrame(self.root, text="⚙️ 下载配置", font=("Microsoft YaHei", 11, "bold"), padx=10, pady=10)
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 保存目录
        dir_frame = tk.Frame(config_frame)
        dir_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(dir_frame, text="保存目录:", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)
        
        self.save_dir_var = tk.StringVar(value=os.path.join(os.getcwd(), "hpoi_images"))
        dir_entry = tk.Entry(dir_frame, textvariable=self.save_dir_var, font=("Microsoft YaHei", 9), width=50)
        dir_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        browse_btn = tk.Button(
            dir_frame,
            text="📁 浏览",
            command=self.browse_directory,
            bg="#95a5a6",
            fg="white",
            font=("Microsoft YaHei", 9),
            relief=tk.FLAT,
            cursor="hand2"
        )
        browse_btn.pack(side=tk.LEFT, padx=5)
        
        # 文件名前缀
        prefix_frame = tk.Frame(config_frame)
        prefix_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(prefix_frame, text="文件名前缀:", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)
        
        self.filename_prefix_var = tk.StringVar(value="hpoi_")
        prefix_entry = tk.Entry(prefix_frame, textvariable=self.filename_prefix_var, font=("Microsoft YaHei", 9), width=30)
        prefix_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Label(prefix_frame, text="(可选，为空则使用时间戳)", font=("Microsoft YaHei", 8), fg="#95a5a6").pack(side=tk.LEFT, padx=5)
        
        # 最小尺寸过滤
        size_filter_frame = tk.Frame(config_frame)
        size_filter_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(size_filter_frame, text="最小尺寸:", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)
        
        self.min_size_var = tk.StringVar(value="300")
        size_entry = tk.Entry(size_filter_frame, textvariable=self.min_size_var, font=("Microsoft YaHei", 9), width=10)
        size_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Label(size_filter_frame, text="×", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=2)
        
        size_entry2 = tk.Entry(size_filter_frame, textvariable=self.min_size_var, font=("Microsoft YaHei", 9), width=10)
        size_entry2.pack(side=tk.LEFT, padx=5)
        
        tk.Label(size_filter_frame, text="像素（小于此尺寸的图片将被自动过滤）", font=("Microsoft YaHei", 8), fg="#95a5a6").pack(side=tk.LEFT, padx=5)
        
        # 按钮区域
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.start_btn = tk.Button(
            btn_frame,
            text="🚀 开始提取并下载",
            command=self.start_download,
            bg="#27ae60",
            fg="white",
            font=("Microsoft YaHei", 12, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            height=2
        )
        self.start_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.stop_btn = tk.Button(
            btn_frame,
            text="⏹️ 停止下载",
            command=self.stop_download,
            bg="#e74c3c",
            fg="white",
            font=("Microsoft YaHei", 12, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            height=2,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        clear_btn = tk.Button(
            btn_frame,
            text="🗑️ 清空",
            command=self.clear_all,
            bg="#95a5a6",
            fg="white",
            font=("Microsoft YaHei", 12, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            height=2
        )
        clear_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 日志区域
        log_frame = tk.LabelFrame(self.root, text="📊 下载日志", font=("Microsoft YaHei", 11, "bold"), padx=10, pady=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建带滚动条的文本框
        log_scroll = tk.Scrollbar(log_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(log_frame, height=10, font=("Consolas", 9), wrap=tk.WORD, yscrollcommand=log_scroll.set)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        log_scroll.config(command=self.log_text.yview)
        
        # 状态栏
        self.status_var = tk.StringVar(value="✅ 就绪 - 请输入 Hpoi 商品页面 URL")
        status_bar = tk.Label(
            self.root,
            textvariable=self.status_var,
            font=("Microsoft YaHei", 9),
            fg="#2c3e50",
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padx=10,
            pady=5
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def load_example_url(self):
        """加载示例 URL"""
        self.url_var.set("https://www.hpoi.net/hobby/64155")
        self.log_message("已加载示例 URL")
    
    def browse_directory(self):
        """选择保存目录"""
        directory = filedialog.askdirectory(title="选择图片保存目录")
        if directory:
            self.save_dir_var.set(directory)
    
    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def fetch_page_html(self, url):
        """获取网页 HTML 内容"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://www.hpoi.net/'
            }
            
            self.log_message(f"🌐 正在访问: {url}")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            self.log_message(f"✅ 成功获取网页内容 (状态码: {response.status_code})")
            return response.text
            
        except requests.exceptions.Timeout:
            self.log_message("❌ 请求超时，请检查网络连接")
            return None
        except requests.exceptions.ConnectionError:
            self.log_message("❌ 连接失败，请检查网络或 URL")
            return None
        except Exception as e:
            self.log_message(f"❌ 获取网页失败: {str(e)}")
            return None
    
    def extract_image_urls(self, html_content):
        """从 HTML 中提取图片 URL"""
        image_urls = []
        
        try:
            # 使用 BeautifulSoup 解析 HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找所有 img 标签
            img_tags = soup.find_all('img')
            
            for img in img_tags:
                src = img.get('src', '')
                if src:
                    # 清理 URL（移除查询参数）
                    clean_url = src.split('?')[0]
                    # 只保留 http/https 开头的完整 URL
                    if clean_url.startswith(('http://', 'https://')):
                        image_urls.append(clean_url)
            
            # 如果没有找到 img 标签，尝试用正则表达式
            if not image_urls:
                pattern = r'src=["\'](https?://[^"\']+?\.(?:jpg|jpeg|png|gif|webp|bmp))["\']'
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                image_urls = [url.split('?')[0] for url in matches]
            
            # 去重
            image_urls = list(dict.fromkeys(image_urls))
            
        except Exception as e:
            self.log_message(f"❌ 解析 HTML 失败: {str(e)}")
            return []
        
        return image_urls
    
    def get_image_size(self, url):
        """获取图片尺寸（宽度和高度）"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.hpoi.net/'
            }
            
            # 先尝试通过 HEAD 请求获取 Content-Length（快速判断）
            head_response = requests.head(url, headers=headers, timeout=10)
            content_length = head_response.headers.get('Content-Length')
            
            # 如果文件大小太小（小于 1KB），可能是缩略图
            if content_length and int(content_length) < 1024:
                return 0, 0
            
            # 发送 GET 请求获取图片
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # 使用 Pillow 打开图片获取尺寸
            img = Image.open(BytesIO(response.content))
            width, height = img.size
            
            return width, height
            
        except Exception as e:
            self.log_message(f"⚠️ 无法获取图片尺寸: {os.path.basename(url)} - {str(e)}")
            return -1, -1  # 返回 -1 表示无法获取，默认保留
    
    def filter_images_by_size(self, image_urls, min_size):
        """根据尺寸过滤图片"""
        filtered_urls = []
        self.filtered_count = 0
        
        self.log_message(f"🔍 开始检查图片尺寸（最小尺寸: {min_size}x{min_size}）...")
        
        for idx, url in enumerate(image_urls, 1):
            try:
                self.log_message(f"📏 [{idx}/{len(image_urls)}] 检查: {os.path.basename(url)}")
                
                width, height = self.get_image_size(url)
                
                if width == -1 or height == -1:
                    # 无法获取尺寸，保留该图片
                    self.log_message(f"⚠️ 无法获取尺寸，保留: {os.path.basename(url)}")
                    filtered_urls.append(url)
                elif width >= min_size and height >= min_size:
                    # 符合尺寸要求
                    self.log_message(f"✅ [{width}x{height}] 符合要求，保留")
                    filtered_urls.append(url)
                else:
                    # 不符合尺寸要求，过滤掉
                    self.filtered_count += 1
                    self.log_message(f"❌ [{width}x{height}] 小于 {min_size}x{min_size}，已过滤")
                    
            except Exception as e:
                self.log_message(f"⚠️ 检查图片 {idx} 时出错: {str(e)}")
                filtered_urls.append(url)  # 出错时保留图片
        
        self.log_message(f"📊 尺寸过滤完成: 原始 {len(image_urls)} 张，保留 {len(filtered_urls)} 张，过滤 {self.filtered_count} 张")
        
        return filtered_urls
    
    def download_image(self, url, save_path):
        """下载单张图片"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.hpoi.net/'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            return True
        except Exception as e:
            self.log_message(f"❌ 下载失败: {os.path.basename(save_path)} - {str(e)}")
            return False
    
    def start_download(self):
        """开始下载"""
        if self.is_downloading:
            messagebox.showwarning("警告", "下载正在进行中，请稍候...")
            return
        
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("错误", "请输入 Hpoi 商品页面 URL！")
            return
        
        # 验证 URL 格式
        if not url.startswith(('http://', 'https://')):
            messagebox.showerror("错误", "URL 必须以 http:// 或 https:// 开头！")
            return
        
        if 'hpoi.net' not in url:
            messagebox.showwarning("警告", "URL 似乎不是 Hpoi 网站的链接，是否继续？")
            # 不阻止用户，继续执行
        
        # 获取最小尺寸设置
        try:
            min_size = int(self.min_size_var.get().strip())
            if min_size <= 0:
                raise ValueError()
        except:
            messagebox.showerror("错误", "最小尺寸必须是正整数！")
            return
        
        # 获取网页 HTML
        self.log_message("=" * 50)
        html_content = self.fetch_page_html(url)
        
        if not html_content:
            messagebox.showerror("错误", "无法获取网页内容，请检查 URL 和网络连接！")
            return
        
        # 提取图片 URL
        self.log_message("🔍 开始提取图片链接...")
        image_urls = self.extract_image_urls(html_content)
        
        if not image_urls:
            messagebox.showwarning("警告", "未找到任何图片链接！")
            self.log_message("❌ 未找到任何图片链接")
            return
        
        self.log_message(f"✅ 成功提取 {len(image_urls)} 张图片")
        
        # 根据尺寸过滤图片
        if min_size > 0:
            image_urls = self.filter_images_by_size(image_urls, min_size)
        
        if not image_urls:
            messagebox.showwarning("警告", "所有图片都被过滤掉了！")
            self.log_message("❌ 所有图片都不符合尺寸要求")
            return
        
        self.total_count = len(image_urls)
        self.log_message(f"✅ 最终确定下载 {self.total_count} 张图片")
        
        # 创建保存目录
        save_dir = self.save_dir_var.get()
        if not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir)
                self.log_message(f"📁 创建目录: {save_dir}")
            except Exception as e:
                messagebox.showerror("错误", f"无法创建目录: {str(e)}")
                return
        
        # 启动下载线程
        self.is_downloading = True
        self.download_count = 0
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set(f"⏳ 正在下载 0/{self.total_count} 张图片...")
        
        thread = threading.Thread(target=self.download_thread, args=(image_urls, save_dir))
        thread.daemon = True
        thread.start()
    
    def is_valid_filename(self, filename):
        """判断文件名是否符合要求：长数字+字母的哈希组合"""
        # 去除扩展名
        name_without_ext = os.path.splitext(filename)[0]
        
        # 检查是否为纯十六进制字符（数字0-9和字母a-f）
        # Hpoi 的图片文件名通常是32位或更长的十六进制字符串
        if len(name_without_ext) >= 16 and all(c in '0123456789abcdef' for c in name_without_ext.lower()):
            return True
        
        return False
    
    def download_thread(self, image_urls, save_dir):
        """下载线程"""
        prefix = self.filename_prefix_var.get().strip()
        
        for idx, url in enumerate(image_urls, 1):
            if not self.is_downloading:
                self.log_message("⏹️ 下载已停止")
                break
            
            try:
                # 从 URL 中提取文件名（长数字+字母组合）
                # 例如: https://rfx.hpoi.net/gk/pic/s/2026/06/9836ec14216a4100b0edddc0a79ac671.jpg?date=xxx
                # 提取: 9836ec14216a4100b0edddc0a79ac671.jpg
                url_path = urllib.parse.urlparse(url).path
                filename = os.path.basename(url_path)
                
                # 验证文件名是否符合要求（长数字+字母的哈希组合）
                if not self.is_valid_filename(filename):
                    self.log_message(f"❌ [{idx}/{self.total_count}] 跳过: {filename} (不符合命名规则)")
                    continue
                
                save_path = os.path.join(save_dir, filename)
                
                self.log_message(f"⬇️ [{idx}/{self.total_count}] 下载: {filename}")
                
                success = self.download_image(url, save_path)
                
                if success:
                    self.download_count += 1
                    self.log_message(f"✅ [{idx}/{self.total_count}] 保存成功: {filename}")
                else:
                    self.log_message(f"❌ [{idx}/{self.total_count}] 下载失败")
                
                # 更新状态栏
                self.status_var.set(f"⏳ 正在下载 {self.download_count}/{self.total_count} 张图片...")
                
            except Exception as e:
                self.log_message(f"❌ 处理图片 {idx} 时出错: {str(e)}")
        
        # 下载完成
        self.is_downloading = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        self.log_message("=" * 50)
        self.log_message(f"🎉 下载完成！成功: {self.download_count}/{self.total_count}")
        if self.filtered_count > 0:
            self.log_message(f"🗑️ 已过滤 {self.filtered_count} 张不符合尺寸要求的图片")
        self.status_var.set(f"✅ 下载完成！成功: {self.download_count}/{self.total_count}")
        
        if self.download_count > 0:
            messagebox.showinfo("完成", f"成功下载 {self.download_count}/{self.total_count} 张图片！\n保存位置: {save_dir}")
    
    def stop_download(self):
        """停止下载"""
        if self.is_downloading:
            self.is_downloading = False
            self.log_message("⏹️ 正在停止下载...")
            self.status_var.set("⏹️ 正在停止...")
    
    def clear_all(self):
        """清空所有内容"""
        self.url_var.set("")
        self.log_text.delete(1.0, tk.END)
        self.status_var.set("✅ 已清空 - 请输入 Hpoi 商品页面 URL")
        self.log_message("🗑️ 已清空所有内容")


def main():
    root = tk.Tk()
    app = HpoiImageDownloader(root)
    root.mainloop()


if __name__ == "__main__":
    main()
