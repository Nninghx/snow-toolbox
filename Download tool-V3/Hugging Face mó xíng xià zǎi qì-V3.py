
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import BooleanVar, StringVar, filedialog, messagebox, scrolledtext
from fontTools.ttLib import TTFont

from huggingface_hub import snapshot_download


def log_message(message: str, logger=None) -> None:
    if logger:
        logger(message)
    else:
        print(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clone a Hugging Face model repository to a local directory."
    )
    parser.add_argument(
        "repo",
        help="Hugging Face model repo ID or URL, e.g. bytedance-research/Lance",
    )
    parser.add_argument(
        "--dest",
        "-d",
        default=None,
        help="Local destination directory. Defaults to the repo name.",
    )
    parser.add_argument(
        "--revision",
        "-r",
        default=None,
        help="Model revision / branch / tag. Defaults to the default branch.",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Hugging Face access token. If omitted, uses HF_TOKEN environment variable.",
    )
    parser.add_argument(
        "--snapshot",
        action="store_true",
        help="Download the model snapshot (files only) instead of cloning the git repository.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Remove existing destination directory before cloning.",
    )
    return parser.parse_args()


def normalize_repo_id(repo: str) -> str:
    repo = repo.strip()
    if repo.endswith("/"):
        repo = repo[:-1]
    match = re.search(r"huggingface\.co/(.+)", repo)
    if match:
        repo = match.group(1)
    return repo


def normalize_dest_path(dest: str | None, repo_id: str | None = None) -> Path:
    if dest:
        normalized = os.path.normpath(os.path.expandvars(dest.strip()))
        return Path(normalized).expanduser().resolve()
    if repo_id is None:
        raise ValueError("Destination directory or repo ID is required.")
    repo_name = Path(repo_id).name
    return (Path.cwd() / repo_name).resolve()


def build_dest_dir(repo_id: str, dest: str | None) -> Path:
    return normalize_dest_path(dest, repo_id=repo_id)


def ensure_clean_dest(dest_path: Path, force: bool) -> None:
    if dest_path.exists():
        if not force:
            raise FileExistsError(
                f"Destination '{dest_path}' already exists. Use --force to overwrite."
            )
        shutil.rmtree(dest_path)


def clone_repository(
    repo_id: str,
    dest_path: Path,
    revision: str | None,
    token: str | None,
    logger=None,
) -> None:
    auth_token = token or os.environ.get("HF_TOKEN")
    log_message(f"Downloading model '{repo_id}' into '{dest_path}'...", logger)
    cache_path = snapshot_download(
        repo_id=repo_id,
        revision=revision,
        token=auth_token,
        local_files_only=False,
    )
    if Path(cache_path) == dest_path:
        log_message(f"Snapshot downloaded directly into '{dest_path}'.", logger)
        return
    log_message(f"Copying from cache to '{dest_path}'...", logger)
    shutil.copytree(cache_path, dest_path)
    log_message("Download complete.", logger)


def download_snapshot(
    repo_id: str,
    dest_path: Path,
    revision: str | None,
    token: str | None,
    logger=None,
) -> None:
    auth_token = token or os.environ.get("HF_TOKEN")
    log_message(f"Downloading snapshot for '{repo_id}'...", logger)
    cache_path = snapshot_download(
        repo_id=repo_id,
        revision=revision,
        token=auth_token,
        local_files_only=False,
    )
    if Path(cache_path) == dest_path:
        log_message(f"Snapshot downloaded directly into '{dest_path}'.", logger)
        return
    log_message(f"Copying snapshot from cache to '{dest_path}'...", logger)
    shutil.copytree(cache_path, dest_path)
    log_message("Snapshot copy complete.", logger)


class HFCloneGUI:
    def __init__(self) -> None:
        # 首先检查授权
        if not self.check_license():
            messagebox.showerror(
                "错误", 
                "缺少授权！无法使用！请先获取授权！\n"
            )
            return
        
        self.root = tk.Tk()
        self.root.title("Hugging Face 模型下载工具")
        self.root.geometry("720x520")
        
        # 设置窗口图标和加载字体
        self.set_window_icon()
        self.load_font()
        
        self.repo_var = StringVar(value="https://huggingface.co/bytedance-research/Lance")
        self.dest_var = StringVar()
        self.revision_var = StringVar()
        self.token_var = StringVar()
        self.snapshot_var = BooleanVar(value=False)
        self.force_var = BooleanVar(value=False)
        self._build_ui()
    
    def check_license(self):
        """检查授权验证"""
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
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.HFCloneGUI")
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
        
        self.current_font = (font_name, 10)
        self.root.option_add("*Font", self.current_font)

    def _build_ui(self) -> None:
        frame = tk.Frame(self.root, padx=12, pady=12)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="模型仓库 ID/URL:").grid(row=0, column=0, sticky=tk.W)
        tk.Entry(frame, textvariable=self.repo_var, width=56).grid(row=0, column=1, columnspan=3, sticky=tk.W)
        tk.Label(frame, text="例如: https://huggingface.co/bytedance-research/Lance", fg="gray").grid(row=1, column=1, columnspan=3, sticky=tk.W, pady=(2, 0))

        tk.Label(frame, text="目标目录:").grid(row=2, column=0, sticky=tk.W, pady=(8, 0))
        tk.Entry(frame, textvariable=self.dest_var, width=44).grid(row=2, column=1, sticky=tk.W, pady=(8, 0))
        tk.Button(frame, text="浏览...", command=self._browse_dest, width=10).grid(row=2, column=2, sticky=tk.W, padx=8, pady=(8, 0))
        tk.Button(frame, text="打开目录", command=self._open_dest, width=10).grid(row=2, column=3, sticky=tk.W, pady=(8, 0))

        tk.Label(frame, text="Revision / Tag:").grid(row=3, column=0, sticky=tk.W, pady=(8, 0))
        tk.Entry(frame, textvariable=self.revision_var, width=56).grid(row=3, column=1, columnspan=3, sticky=tk.W, pady=(8, 0))

        tk.Label(frame, text="Access Token:").grid(row=4, column=0, sticky=tk.W, pady=(8, 0))
        tk.Entry(frame, textvariable=self.token_var, show="*", width=56).grid(row=4, column=1, columnspan=3, sticky=tk.W, pady=(8, 0))

        tk.Checkbutton(frame, text="仅下载快照 (不克隆 Git)", variable=self.snapshot_var).grid(row=5, column=1, sticky=tk.W, pady=(8, 0))
        tk.Checkbutton(frame, text="覆盖目标目录", variable=self.force_var).grid(row=5, column=2, sticky=tk.W, pady=(8, 0))

        button_frame = tk.Frame(frame)
        button_frame.grid(row=5, column=0, columnspan=4, pady=(16, 0), sticky=tk.W)
        self.start_button = tk.Button(button_frame, text="开始克隆", command=self._on_start, width=12)
        self.start_button.pack(side=tk.LEFT)
        tk.Button(button_frame, text="清空日志", command=self._clear_log, width=10).pack(side=tk.LEFT, padx=8)
        tk.Button(button_frame, text="退出", command=self.root.quit, width=10).pack(side=tk.LEFT)

        output_frame = tk.LabelFrame(frame, text="执行日志", padx=8, pady=8)
        output_frame.grid(row=7, column=0, columnspan=4, pady=(16, 0), sticky=tk.NSEW)
        frame.rowconfigure(7, weight=1)
        frame.columnconfigure(1, weight=1)

        self.output = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.output.pack(fill=tk.BOTH, expand=True)

    def _browse_dest(self) -> None:
        path = filedialog.askdirectory(title="选择目标目录")
        if path:
            self.dest_var.set(path)

    def _open_dest(self) -> None:
        dest = self.dest_var.get().strip()
        if not dest:
            messagebox.showwarning("警告", "请先设置目标目录。")
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

    def _on_start(self) -> None:
        repo = self.repo_var.get().strip()
        if not repo:
            messagebox.showwarning("输入错误", "请输入 Hugging Face 模型仓库 ID 或 URL。")
            return
        dest = self.dest_var.get().strip()
        repo_id = normalize_repo_id(repo)
        if not dest:
            dest = str(normalize_dest_path(None, repo_id=repo_id))
            self.dest_var.set(dest)
        else:
            dest = str(normalize_dest_path(dest))
            self.dest_var.set(dest)

        force = self.force_var.get()
        if Path(dest).exists() and not force:
            force = True

        self._clear_log()
        self._set_controls_state(False)
        self._append_log("开始执行，请稍候 ...")
        thread = threading.Thread(
            target=self._run_clone,
            args=(repo, dest, self.revision_var.get().strip(), self.token_var.get().strip(), self.snapshot_var.get(), force),
            daemon=True,
        )
        thread.start()

    def _run_clone(
        self,
        repo: str,
        dest: str,
        revision: str,
        token: str,
        snapshot: bool,
        force: bool,
    ) -> None:
        dest_path = Path(dest).expanduser().resolve()
        repo_id = normalize_repo_id(repo)
        try:
            ensure_clean_dest(dest_path, force)
            if snapshot:
                download_snapshot(repo_id, dest_path, revision or None, token or None, logger=self._append_log)
            else:
                clone_repository(repo_id, dest_path, revision or None, token or None, logger=self._append_log)
            self._append_log("操作完成。")
        except FileExistsError as error:
            self._append_log(f"错误: {error}")
        except Exception as error:
            self._append_log(f"发生错误: {error}")
        finally:
            self.root.after(0, lambda: self._set_controls_state(True))

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    if len(sys.argv) > 1:
        args = parse_args()
        repo_id = normalize_repo_id(args.repo)
        dest_path = build_dest_dir(repo_id, args.dest)
        ensure_clean_dest(dest_path, args.force)

        try:
            if args.snapshot:
                download_snapshot(repo_id, dest_path, args.revision, args.token)
            else:
                clone_repository(repo_id, dest_path, args.revision, args.token)
        except FileExistsError as error:
            print(error, file=sys.stderr)
            return 1
        except Exception as error:
            print("发生错误：", error, file=sys.stderr)
            return 1

        return 0

    # Windows系统设置应用ID（必须在创建窗口之前）
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.HFCloneGUI")
        except Exception:
            pass
    
    app = HFCloneGUI()
    if hasattr(app, 'root'):
        app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
