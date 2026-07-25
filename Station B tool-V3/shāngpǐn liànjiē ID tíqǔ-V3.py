import os
import sys
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
from fontTools.ttLib import TTFont
import re
import urllib.request
import urllib.error


class BStationItemIDExtractor:
    """B站商品链接ID提取工具"""

    def __init__(self, root):
        """初始化应用界面和配置"""
        # 首先检查开源协议文档是否存在并验证完整性
        if not self.check_license():
            messagebox.showerror(
                "错误",
                "缺少授权！无法使用！请先获取授权！\n"
            )
            root.destroy()
            return

        self.root = root
        self.root.title("B站商品链接ID提取")
        self.root.geometry("600x300")
        self.root.resizable(False, False)

        # 设置窗口图标、加载字体并构建UI
        self.set_window_icon()
        self.load_font()
        self.build_ui()

    # ==================== 许可认证 ====================

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

    # ==================== 图标设置 ====================

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
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.BStationItemIDExtractor")
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

    # ==================== 字体加载 ====================

    def load_font(self):
        """从配置文件加载字体设置"""
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

        from tkinter import font as tkfont
        self.current_font = (font_name, 10)
        self.root.option_add("*Font", self.current_font)

    # ==================== 业务逻辑 ====================

    def resolve_url(self, url):
        """跟踪短链接重定向，获取最终URL"""
        try:
            req = urllib.request.Request(url, method='GET')
            # 使用自定义 User-Agent 避免被拒绝
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            with urllib.request.urlopen(req, timeout=10) as response:
                final_url = response.geturl()
            # 如果重定向后的URL与原始URL不同，说明发生了重定向
            if final_url != url:
                return final_url
            return url
        except Exception:
            return url  # 失败时返回原始URL

    def extract_items_id(self):
        """从URL中提取itemsId参数，支持短链接跟踪"""
        url = self.url_entry.get().strip()

        if not url:
            messagebox.showwarning("警告", "请输入URL")
            return

        # 检测是否是短链接，如果是则先跟踪重定向
        if 'b23.tv' in url or 't.cn' in url or 'dwz.cn' in url or 'bit.ly' in url:
            self.result_label.config(text="正在解析短链接...")
            self.root.update()  # 刷新UI显示状态
            url = self.resolve_url(url)

        # 匹配 #itemsId=数字 或 &itemsId=数字 或 ?itemsId=数字
        match = re.search(r'[#&?]itemsId=(\d+)', url)

        if match:
            items_id = match.group(1)
            self.result_label.config(text=f"提取结果: {items_id}")
            # 复制到剪贴板
            self.root.clipboard_clear()
            self.root.clipboard_append(items_id)
            messagebox.showinfo("成功", f"已提取 itemsId: {items_id}\n\n已自动复制到剪贴板")
        else:
            self.result_label.config(text="未找到 itemsId 参数")
            messagebox.showerror("错误", "未在URL中找到 itemsId 参数")

    def clear_input(self):
        """清空输入框"""
        self.url_entry.delete(0, tk.END)
        self.result_label.config(text="")

    def paste_from_clipboard(self, event=None):
        """从剪贴板粘贴内容到输入框"""
        try:
            clipboard_text = self.root.clipboard_get()
            if clipboard_text:
                # 如果当前有选中文本，先删除
                try:
                    self.url_entry.delete(tk.SEL_FIRST, tk.SEL_LAST)
                except tk.TclError:
                    pass
                # 在光标位置插入剪贴板内容
                self.url_entry.insert(tk.INSERT, clipboard_text)
        except tk.TclError:
            pass  # 剪贴板为空或不是文本格式

    def show_context_menu(self, event):
        """显示右键菜单"""
        self.context_menu.post(event.x_root, event.y_root)

    # ==================== UI构建 ====================

    def build_ui(self):
        """构建用户界面"""
        # 设置窗口居中
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 600) // 2
        y = (screen_height - 300) // 2
        self.root.geometry(f"+{x}+{y}")

        # 标题
        title_label = tk.Label(
            self.root,
            text="B站商品链接ID提取",
            font=(self.current_font[0], 16, "bold")
        )
        title_label.pack(pady=20)

        # URL输入框
        input_frame = tk.Frame(self.root)
        input_frame.pack(pady=10, padx=20, fill=tk.X)

        url_label = tk.Label(input_frame, text="URL:", font=self.current_font)
        url_label.pack(anchor=tk.W)

        self.url_entry = tk.Entry(input_frame, font=self.current_font, width=60)
        self.url_entry.pack(fill=tk.X, pady=5)

        # 为输入框添加右键菜单
        self.context_menu = tk.Menu(self.url_entry, tearoff=0)
        self.context_menu.add_command(label="粘贴", command=self.paste_from_clipboard)
        self.url_entry.bind("<Button-3>", self.show_context_menu)

        # 按钮区域
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=15)

        extract_btn = tk.Button(
            button_frame, text="提取ID", command=self.extract_items_id,
            font=(self.current_font[0], 10),
            width=12, height=2
        )
        extract_btn.pack(side=tk.LEFT, padx=10)

        clear_btn = tk.Button(
            button_frame, text="清空", command=self.clear_input,
            font=(self.current_font[0], 10),
            width=12, height=2
        )
        clear_btn.pack(side=tk.LEFT, padx=10)

        # 结果显示
        self.result_label = tk.Label(self.root, text="", font=(self.current_font[0], 12))
        self.result_label.pack(pady=10)

        # 提示信息
        tip_label = tk.Label(
            self.root,
            text="提示: 提取结果会自动复制到剪贴板",
            font=(self.current_font[0], 9)
        )
        tip_label.pack(pady=5)

        # 绑定回车键
        self.root.bind('<Return>', lambda event: self.extract_items_id())


if __name__ == "__main__":
    print("=" * 60)
    print("B站商品链接ID提取")
    print("=" * 60)
    print()

    try:
        root = tk.Tk()
        app = BStationItemIDExtractor(root)
        print("\u2705 Tkinter 应用启动成功")
        root.mainloop()

        print("\n" + "=" * 60)
        print("程序运行完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n\u274c 程序运行失败：{e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
