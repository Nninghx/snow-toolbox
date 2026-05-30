
from __future__ import annotations

import os
import re
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import StringVar, filedialog, messagebox, scrolledtext
from urllib.parse import unquote, urlparse

import requests
from fontTools.ttLib import TTFont


def sanitize_filename(url: str) -> str:
    """从 URL 中提取合适的文件名"""
    parsed = urlparse(url)
    path = unquote(parsed.path)
    filename = Path(path).name
    # 去掉 @ 后面的尺寸信息 (如 @800w)
    filename = re.sub(r'@[^.]+', '', filename)
    # 如果文件名为空或只有扩展名，使用默认名
    name, ext = os.path.splitext(filename)
    if not name:
        filename = f"downloaded_image{ext or '.png'}"
    # 去掉 query 参数
    if '?' in filename:
        filename = filename.split('?')[0]
    return filename


def resolve_filename(dest_dir: Path, base_filename: str) -> Path:
    """解决文件名冲突：如果文件已存在，添加序号后缀"""
    name, ext = os.path.splitext(base_filename)
    file_path = dest_dir / base_filename
    if not file_path.exists():
        return file_path
    counter = 1
    while True:
        new_name = f"{name}_{counter}{ext}"
        file_path = dest_dir / new_name
        if not file_path.exists():
            return file_path
        counter += 1


class ImageDownloaderGUI:
    def __init__(self) -> None:
        if not self.check_license():
            messagebox.showerror("错误", "缺少授权！无法使用！请先获取授权！")
            return

        self.root = tk.Tk()
        self.root.title("图片下载工具")
        self.root.geometry("760x600")

        self.set_window_icon()
        self.load_font()

        self.dest_var = StringVar(value=str(Path.home() / "Downloads"))
        self._cancel_flag = False
        self._build_ui()

    def check_license(self):
        if os.environ.get('MAIN_APP_AUTHORIZED') == '1':
            return True
        try:
            PROJECT_ROOT = Path(__file__).resolve().parent.parent
            CORE_DIR = PROJECT_ROOT / "Core"
            license_exe_path = CORE_DIR / "LICENSE.exe"
            if license_exe_path.exists():
                result = subprocess.run(
                    [str(license_exe_path), '--quiet'],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return result.returncode == 0
        except Exception as e:
            print(f"许可证验证异常: {e}")
        return False

    def set_window_icon(self):
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        IMAGE_DIR = PROJECT_ROOT / "Image"
        icon_ico_path = IMAGE_DIR / "icon.ico"
        icon_png_path = IMAGE_DIR / "icon.png"

        if os.name == 'nt':
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.ImageDownloaderGUI")
            except Exception:
                pass

        if icon_ico_path.exists():
            try:
                self.root.iconbitmap(default=str(icon_ico_path))
            except Exception:
                try:
                    self.root.iconbitmap(str(icon_ico_path))
                except Exception:
                    pass

        if hasattr(self.root, "iconphoto") and icon_png_path.exists():
            try:
                self.icon_image = tk.PhotoImage(file=str(icon_png_path))
                self.root.iconphoto(True, self.icon_image)
            except Exception:
                pass

    def load_font(self):
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        IMAGE_DIR = PROJECT_ROOT / "Image"
        font_path = IMAGE_DIR / "AlibabaPuHuiTi-3-55-RegularL3.ttf"

        if not font_path.exists():
            messagebox.showerror("错误", f"找不到字体文件：{font_path}")
            self.root.destroy()
            return

        tt = TTFont(str(font_path))
        font_name = None
        for record in tt['name'].names:
            if record.nameID == 1:
                font_name = record.toUnicode()
                break
        if not font_name:
            raise RuntimeError(f"无法从字体文件获取字体名称：{font_path}")
        tt.close()

        if os.name == 'nt':
            import ctypes
            GDI32 = ctypes.windll.gdi32
            font_path_str = str(font_path).encode('utf-16-le') + b'\x00'
            GDI32.AddFontResourceW(font_path_str)
            print(f"成功加载自定义字体: {font_path}")

        self.current_font = (font_name, 10)
        self.root.option_add("*Font", self.current_font)

    def _build_ui(self) -> None:
        frame = tk.Frame(self.root, padx=12, pady=12)
        frame.pack(fill=tk.BOTH, expand=True)

        # 图片 URL 输入区（支持多行批量）
        tk.Label(frame, text="图片 URL（每行一个，支持批量）:").grid(row=0, column=0, sticky=tk.W)
        url_frame = tk.Frame(frame)
        url_frame.grid(row=1, column=0, columnspan=4, sticky=tk.NSEW, pady=(4, 0))
        self.url_text = scrolledtext.ScrolledText(url_frame, wrap=tk.WORD, height=5, width=70)
        self.url_text.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            frame,
            text="支持直链图片地址（.png / .jpg / .webp 等），每行一个 URL",
            fg="gray",
        ).grid(row=2, column=0, columnspan=4, sticky=tk.W, pady=(2, 0))

        # 保存目录
        tk.Label(frame, text="保存目录:").grid(row=3, column=0, sticky=tk.W, pady=(8, 0))
        tk.Entry(frame, textvariable=self.dest_var, width=48).grid(row=3, column=1, sticky=tk.W, pady=(8, 0))
        tk.Button(frame, text="浏览...", command=self._browse_dest, width=10).grid(row=3, column=2, sticky=tk.W, padx=8, pady=(8, 0))
        tk.Button(frame, text="打开目录", command=self._open_dest, width=10).grid(row=3, column=3, sticky=tk.W, pady=(8, 0))

        # 按钮区
        button_frame = tk.Frame(frame)
        button_frame.grid(row=5, column=0, columnspan=4, pady=(16, 0), sticky=tk.W)
        self.start_button = tk.Button(button_frame, text="开始下载", command=self._on_start, width=12)
        self.start_button.pack(side=tk.LEFT)
        self.stop_button = tk.Button(button_frame, text="终止", command=self._on_cancel, width=10, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=8)
        tk.Button(button_frame, text="清空日志", command=self._clear_log, width=10).pack(side=tk.LEFT, padx=8)
        tk.Button(button_frame, text="退出", command=self.root.quit, width=10).pack(side=tk.LEFT)

        # 日志区域
        output_frame = tk.LabelFrame(frame, text="执行日志", padx=8, pady=8)
        output_frame.grid(row=7, column=0, columnspan=4, pady=(16, 0), sticky=tk.NSEW)
        frame.rowconfigure(7, weight=1)
        frame.columnconfigure(1, weight=1)

        self.output = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.output.pack(fill=tk.BOTH, expand=True)

    def _browse_dest(self) -> None:
        path = filedialog.askdirectory(title="选择保存目录")
        if path:
            self.dest_var.set(path)

    def _open_dest(self) -> None:
        dest = self.dest_var.get().strip()
        if not dest:
            messagebox.showwarning("警告", "请先设置保存目录。")
            return
        dest_path = Path(dest).expanduser().resolve()
        if dest_path.exists():
            os.startfile(str(dest_path))
        else:
            messagebox.showwarning("警告", f"目录不存在: {dest_path}")

    def _append_log(self, text: str) -> None:
        print(text, flush=True)
        self.output.configure(state=tk.NORMAL)
        self.output.insert(tk.END, text + "\n")
        self.output.see(tk.END)
        self.output.configure(state=tk.DISABLED)

    def _clear_log(self) -> None:
        self.output.configure(state=tk.NORMAL)
        self.output.delete("1.0", tk.END)
        self.output.configure(state=tk.DISABLED)

    def _set_controls_state(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        self.start_button.configure(state=state)
        self.stop_button.configure(state=tk.DISABLED if enabled else tk.NORMAL)

    def _on_cancel(self) -> None:
        self._cancel_flag = True
        self._append_log("⚠ 正在终止下载...")

    def _parse_urls(self) -> list[str]:
        """从文本框中解析出所有图片链接"""
        raw_text = self.url_text.get("1.0", tk.END).strip()
        if not raw_text:
            return []
        urls = []
        for line in raw_text.splitlines():
            line = line.strip()
            if line and (line.startswith("http://") or line.startswith("https://")):
                urls.append(line)
        return urls

    def _on_start(self) -> None:
        urls = self._parse_urls()
        if not urls:
            messagebox.showwarning("输入错误", "请至少输入一个有效的图片 URL（以 http:// 或 https:// 开头）。")
            return

        dest_dir = self.dest_var.get().strip()
        if not dest_dir:
            dest_dir = str(Path.home() / "Downloads")
            self.dest_var.set(dest_dir)

        self._cancel_flag = False
        self._clear_log()
        self._set_controls_state(False)
        self._append_log(f"共检测到 {len(urls)} 个图片链接，开始下载...")
        thread = threading.Thread(
            target=self._run_batch_download,
            args=(urls, dest_dir),
            daemon=True,
        )
        thread.start()

    def _download_one(self, url: str, dest_dir: Path, session: requests.Session) -> tuple[bool, str]:
        """下载单张图片，返回 (成功与否, 消息)"""
        base_name = sanitize_filename(url)
        file_path = resolve_filename(dest_dir, base_name)

        try:
            response = session.get(url, stream=True, timeout=30)
            response.raise_for_status()

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self._cancel_flag:
                        f.close()
                        try:
                            file_path.unlink()
                        except Exception:
                            pass
                        return False, "已终止"
                    if chunk:
                        f.write(chunk)

            file_size = file_path.stat().st_size
            return True, f"  → 保存至: {file_path.name} ({self._format_size(file_size)})"

        except requests.exceptions.RequestException as e:
            return False, f"  ✗ 请求失败: {e}"
        except Exception as e:
            return False, f"  ✗ 错误: {e}"

    def _run_batch_download(self, urls: list[str], dest_dir: str) -> None:
        dest_path = Path(dest_dir).expanduser().resolve()
        dest_path.mkdir(parents=True, exist_ok=True)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/",
        }
        session = requests.Session()
        session.headers.update(headers)

        success_count = 0
        fail_count = 0
        total = len(urls)

        for i, url in enumerate(urls, 1):
            if self._cancel_flag:
                self._append_log(f"\n下载被终止。")
                break

            self._append_log(f"[{i}/{total}] {url}")

            ok, msg = self._download_one(url, dest_path, session)
            self._append_log(msg)

            if ok:
                success_count += 1
            else:
                fail_count += 1

        session.close()

        # 汇总
        self._append_log("")
        self._append_log("=" * 50)
        self._append_log(f"下载完成！成功: {success_count} 张 / 失败: {fail_count} 张 / 总计: {total} 张")
        self._append_log(f"保存目录: {dest_path}")
        self._append_log("=" * 50)

        self.root.after(0, lambda: self._set_controls_state(True))
        if not self._cancel_flag:
            self.root.after(0, lambda: messagebox.showinfo(
                "完成",
                f"批量下载完成！\n成功: {success_count} / 失败: {fail_count} / 总计: {total}\n保存目录:\n{dest_path}"
            ))

    @staticmethod
    def _format_size(size: int) -> str:
        for unit in ('B', 'KB', 'MB', 'GB'):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.ImageDownloaderGUI")
        except Exception:
            pass

    app = ImageDownloaderGUI()
    if hasattr(app, 'root'):
        app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
