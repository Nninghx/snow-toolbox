from __future__ import annotations

# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import re
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import StringVar, filedialog, messagebox, scrolledtext
from urllib.parse import unquote, urlparse

# 导入公共基类
import importlib.util
_base_spec = importlib.util.spec_from_file_location(
    "public_base_class",
    Path(__file__).resolve().parent.parent / "Core" / "Public base class.py"
)
_base_module = importlib.util.module_from_spec(_base_spec)
_base_spec.loader.exec_module(_base_module)
PDFToolBase = _base_module.PDFToolBase
del _base_spec, _base_module

import requests


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


@dataclass
class UrlEntry:
    """URL 条目，可携带自定义文件名"""
    url: str
    custom_name: str = ""


class ImageDownloaderGUI(PDFToolBase):
    def __init__(self, root) -> None:
        super().__init__(root)
        if not root.winfo_exists():
            return
        self.root = root
        self.root.title("图片下载工具")
        self.root.geometry("760x600")

        self.dest_var = StringVar(value=str(Path.home() / "Downloads"))
        self._cancel_flag = False
        self._build_ui()

    def _build_ui(self) -> None:
        frame = tk.Frame(self.root, padx=12, pady=12)
        frame.pack(fill=tk.BOTH, expand=True)

        # 图片 URL 输入区（支持多行批量 + txt 导入）
        url_header = tk.Frame(frame)
        url_header.grid(row=0, column=0, columnspan=4, sticky=tk.W)
        tk.Label(url_header, text="图片 URL（每行一个，支持批量）:").pack(side=tk.LEFT)
        tk.Button(url_header, text="导入 txt", command=self._import_txt, width=8).pack(side=tk.LEFT, padx=(12, 0))
        url_frame = tk.Frame(frame)
        url_frame.grid(row=1, column=0, columnspan=4, sticky=tk.NSEW, pady=(4, 0))
        self.url_text = scrolledtext.ScrolledText(url_frame, wrap=tk.WORD, height=5, width=70)
        self.url_text.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            frame,
            text="支持直链图片地址，每行一个 URL；「导入 txt」可加载含商品信息的文本文件并自动重命名",
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

    def _import_txt(self) -> None:
        """从 txt 文件中解析商品信息（名称+图片URL）并追加到输入框"""
        file_path = filedialog.askopenfilename(
            title="选择包含商品信息的 txt 文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
        )
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="gbk") as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("读取失败", f"无法读取文件:\n{e}")
            return

        # 按 [N] 标题拆分为商品块，提取名称和图片 URL
        blocks = re.split(r'(?=^\[\d+\])', content, flags=re.MULTILINE)
        entries: list[UrlEntry] = []
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            title_match = re.match(r'\[\d+\]\s*(.+)', block)
            product_name = title_match.group(1).strip() if title_match else ""
            urls = re.findall(r'https?://[^\s<>"\']+', block)
            for url in urls:
                entries.append(UrlEntry(url=url, custom_name=product_name))

        if not entries:
            messagebox.showinfo("提示", "未在文件中找到有效的 http/https 链接。")
            return

        # 去重已有 URL
        existing_urls = set(e.url for e in self._parse_urls())
        new_entries = [e for e in entries if e.url not in existing_urls]
        if not new_entries:
            messagebox.showinfo("提示", f"文件中的 {len(entries)} 个链接已全部存在于输入框中。")
            return

        # 构建显示文本：有商品名时以注释形式标注
        lines = []
        for e in new_entries:
            if e.custom_name:
                lines.append(f"{e.url}  # {e.custom_name}")
            else:
                lines.append(e.url)
        text_to_add = "\n".join(lines)

        current = self.url_text.get("1.0", tk.END).rstrip("\n")
        if current:
            self.url_text.delete("1.0", tk.END)
            self.url_text.insert("1.0", current + "\n" + text_to_add)
        else:
            self.url_text.insert("1.0", text_to_add)

        named = sum(1 for e in new_entries if e.custom_name)
        self._append_log(
            f"已从 txt 导入 {len(new_entries)} 个新链接"
            f"（其中 {named} 个带有商品名称，将自动重命名）。"
        )

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

    def _parse_urls(self) -> list[UrlEntry]:
        """从文本框中解析出所有图片链接，支持 `URL  # 自定义名` 格式"""
        raw_text = self.url_text.get("1.0", tk.END).strip()
        if not raw_text:
            return []
        entries: list[UrlEntry] = []
        for line in raw_text.splitlines():
            line = line.strip()
            if not line:
                continue
            # 分离 URL 和注释中的自定义文件名
            comment = ""
            if "  # " in line:
                line, comment = line.split("  # ", 1)
                line = line.strip()
                comment = comment.strip()
            if line.startswith("http://") or line.startswith("https://"):
                # 排除 .html / .htm 后缀的非图片链接
                url_path = urlparse(line).path.lower()
                if url_path.endswith(('.html', '.htm')):
                    continue
                entries.append(UrlEntry(url=line, custom_name=comment))
        return entries

    def _on_start(self) -> None:
        entries = self._parse_urls()
        if not entries:
            messagebox.showwarning("输入错误", "请至少输入一个有效的图片 URL（以 http:// 或 https:// 开头）。")
            return

        dest_dir = self.dest_var.get().strip()
        if not dest_dir:
            dest_dir = str(Path.home() / "Downloads")
            self.dest_var.set(dest_dir)

        self._cancel_flag = False
        self._clear_log()
        self._set_controls_state(False)
        named_count = sum(1 for e in entries if e.custom_name)
        log_msg = f"共检测到 {len(entries)} 个图片链接，开始下载..."
        if named_count:
            log_msg += f"（其中 {named_count} 个将使用自定义文件名）"
        self._append_log(log_msg)
        thread = threading.Thread(
            target=self._run_batch_download,
            args=(entries, dest_dir),
            daemon=True,
        )
        thread.start()

    def _download_one(self, url: str, dest_dir: Path, session: requests.Session,
                       custom_name: str = "", index: int = 0) -> tuple[bool, str]:
        """下载单张图片，返回 (成功与否, 消息)；custom_name 非空时用作文件名"""
        if custom_name:
            # 清理自定义名称中的非法文件名字符
            stem = re.sub(r'[<>:"\/\\|?*\s\uff1a\uff0c]+', '_', custom_name)
            stem = re.sub(r'_+', '_', stem).strip('_')
            # 保留原始 URL 中的扩展名
            _, url_ext = os.path.splitext(sanitize_filename(url))
            prefix = f"{index:02d}_" if index else ""
            base_name = f"{prefix}{stem}{url_ext}"
        else:
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

    def _run_batch_download(self, entries: list[UrlEntry], dest_dir: str) -> None:
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
        total = len(entries)

        for i, entry in enumerate(entries, 1):
            if self._cancel_flag:
                self._append_log(f"\n下载被终止。")
                break

            name_hint = f" → {entry.custom_name}" if entry.custom_name else ""
            self._append_log(f"[{i}/{total}] {entry.url}{name_hint}")

            ok, msg = self._download_one(entry.url, dest_path, session, entry.custom_name, i)
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

    root = tk.Tk()
    app = ImageDownloaderGUI(root)
    if root.winfo_exists():
        app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
