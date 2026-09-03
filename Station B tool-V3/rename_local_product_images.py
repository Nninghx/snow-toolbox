from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shutil
import sys
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Callable, List, Sequence
from urllib.parse import urlparse

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

try:
    from PIL import Image as PILImage, ImageTk as PILImageTk
except ImportError:  # pragma: no cover
    PILImage = None
    PILImageTk = None

SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
SIMILARITY_THRESHOLD = 0.85

def _load_download_module():
    """动态加载 tú piàn xià zǎi-V3.py 的下载辅助函数"""
    dl_path = (
        Path(__file__).resolve().parent.parent
        / "Download tool-V3"
        / "tú piàn xià zǎi-V3.py"
    )
    if not dl_path.exists():
        return None
    try:
        spec = importlib.util.spec_from_file_location("image_downloader", dl_path)
        mod = importlib.util.module_from_spec(spec)
        # 必须在 exec_module 前注册到 sys.modules，否则 @dataclass 装饰器
        # 在 Python 3.13 中会因 sys.modules.get(cls.__module__) 返回 None 而崩溃
        sys.modules["image_downloader"] = mod
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        sys.modules.pop("image_downloader", None)
        return None


_DOWNLOAD_MOD = _load_download_module()


def natural_sort_key(value: str):
    parts = re.split(r"(\d+)", value)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def clean_title(title: str) -> str:
    """清理商品标题使其符合文件名规范，与 tú piàn xià zǎi-V3.py 的命名规则保持一致"""
    title = title.strip()
    # 替换所有非法文件名字符（含中文标点 \uff1a \uff0c）为下划线
    title = re.sub(r'[<>:"/\\|?*\s\uff1a\uff0c\uff1b;]+', '_', title)
    # 折叠连续下划线，去除首尾下划线
    title = re.sub(r'_+', '_', title).strip('_')
    if not title:
        title = "商品"
    return title


def url_to_basename(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    url = url.split("?", 1)[0]
    if "/" in url:
        url = url.rsplit("/", 1)[1]
    url = url.split("@", 1)[0]
    name = Path(url).stem
    return name.lower()


# 比对时统一缩小到此尺寸，避免大图逐像素循环导致卡死
_COMPARE_SIZE = 128


def image_similarity_score(a: PILImage.Image | Path | str, b: PILImage.Image | Path | str) -> float:
    """计算两张图片的相似度（0~1），先缩小到 _COMPARE_SIZE 再比对"""
    if PILImage is None:
        return 0.0

    def to_small(source) -> PILImage.Image:
        if isinstance(source, (str, Path)):
            img = PILImage.open(source).convert("RGB")
        else:
            img = source.convert("RGB")
        img.thumbnail((_COMPARE_SIZE, _COMPARE_SIZE), PILImage.Resampling.BILINEAR)
        return img

    left = to_small(a)
    right = to_small(b)

    # 统一尺寸
    w = min(left.width, right.width)
    h = min(left.height, right.height)
    if w <= 0 or h <= 0:
        return 0.0
    left = left.resize((w, h), PILImage.Resampling.BILINEAR)
    right = right.resize((w, h), PILImage.Resampling.BILINEAR)

    # 批量读取像素（比 getpixel 快 50~100 倍）
    # Pillow 14+ 使用 get_flattened_data，旧版回退到 getdata
    _get_data = getattr(PILImage.Image, "get_flattened_data", None) or PILImage.Image.getdata
    lpixels = list(_get_data(left))
    rpixels = list(_get_data(right))

    diff = sum(
        abs(lp[0] - rp[0]) + abs(lp[1] - rp[1]) + abs(lp[2] - rp[2])
        for lp, rp in zip(lpixels, rpixels)
    )
    avg_diff = diff / (w * h * 255 * 3)
    return max(0.0, 1.0 - avg_diff)


def parse_detail_entries(detail_text: str) -> List[dict]:
    entries: List[dict] = []
    current = None

    for raw in detail_text.splitlines():
        line = raw.strip()
        if not line:
            continue

        match = re.match(r"^\[(\d+)\]\s*(.+)$", line)
        if match:
            if current:
                entries.append(current)
            current = {
                "index": int(match.group(1)),
                "title": match.group(2).strip(),
                "image_url": "",
            }
            continue

        if current and line.startswith("图片:"):
            current["image_url"] = line.split(":", 1)[1].strip()

    if current:
        entries.append(current)

    return entries


def iter_local_assets(directory: Path) -> List[Path]:
    assets = []
    for file_path in directory.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.name == "主图-1.png":
            continue
        if file_path.suffix.lower() not in SUPPORTED_EXTS:
            continue
        assets.append(file_path)
    assets.sort(key=lambda p: natural_sort_key(p.name))
    return assets


def build_rename_plan(
    detail_path: Path,
    image_dir: Path,
    temp_dir: Path | None = None,
    log: Callable[[str], None] | None = None,
) -> tuple[List[tuple[Path, Path, str]], dict]:
    """
    从商品详情文件解析条目，调用 tú piàn xià zǎi-V3 的下载能力将商品图片下载到临时目录，
    再与本地高清图做像素级比较，生成重命名计划。

    返回: (plan, ref_map)
      plan   — [(src_path, dst_path, title), ...]
      ref_map — {title: dl_path}  商品标题→下载参考图路径的映射

    temp_dir：临时下载目录（调用方负责在重命名完成后删除）；
              为 None 时自动创建系统临时目录。
    """
    if requests is None:
        raise RuntimeError("缺少 requests 库，请先安装：pip install requests")
    if _DOWNLOAD_MOD is None:
        raise RuntimeError("找不到 Download tool-V3/tú piàn xià zǎi-V3.py，请确认文件路径正确")
    if PILImage is None:
        raise RuntimeError("缺少 Pillow 库，请先安装：pip install Pillow")

    _log = log or (lambda m: None)

    text = detail_path.read_text(encoding="utf-8", errors="ignore")
    entries = parse_detail_entries(text)
    assets = iter_local_assets(image_dir)
    if not entries:
        raise ValueError(f"未在详情文件中找到商品条目：{detail_path}")
    if not assets:
        raise ValueError(f"未在目录中找到图片文件：{image_dir}")

    # ── 第一步：批量下载商品图片到临时目录 ──────────────────────────────
    if temp_dir is None:
        temp_dir = Path(tempfile.mkdtemp(prefix="product_imgs_"))
    temp_dir.mkdir(parents=True, exist_ok=True)
    _log(f"临时下载目录：{temp_dir}")

    sanitize_filename = _DOWNLOAD_MOD.sanitize_filename
    resolve_filename  = _DOWNLOAD_MOD.resolve_filename

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
    })

    downloaded: List[tuple[Path, dict]] = []
    for entry in entries:
        url = entry.get("image_url", "")
        if not url:
            _log(f"  [{entry['index']}] {entry['title']} — 无图片链接，跳过")
            continue
        base_name = sanitize_filename(url)
        file_path = resolve_filename(temp_dir, base_name)
        try:
            resp = session.get(url, stream=True, timeout=30)
            resp.raise_for_status()
            with open(file_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            downloaded.append((file_path, entry))
            _log(f"  [{entry['index']}] 下载成功: {file_path.name}")
        except Exception as exc:
            _log(f"  [{entry['index']}] 下载失败: {exc}")
    session.close()

    if not downloaded:
        raise ValueError("所有商品图片下载均失败，无法进行比对")

    # ── 第二步：像素级比对，收集所有候选 ─────────────────────────────
    _log("开始像素级比对...")
    candidates_list: List[tuple] = []   # [(entry, dl_path, scored), ...]
    ref_map: dict = {}                  # title → dl_path

    for dl_idx, (dl_path, entry) in enumerate(downloaded, 1):
        _log(f"  [{dl_idx}/{len(downloaded)}] 比对: {entry['title']}")
        try:
            remote_img = PILImage.open(dl_path).convert("RGB")
        except Exception as exc:
            _log(f"  无法读取下载文件 {dl_path.name}: {exc}")
            continue

        scored = []
        for asset in assets:
            try:
                with PILImage.open(asset) as local_img:
                    score = image_similarity_score(remote_img, local_img.convert("RGB"))
                scored.append((score, asset))
            except Exception:
                continue

        if not scored:
            _log(f"  [{entry['index']}] {entry['title']} — 无可比对图片")
            continue

        ordered_scored = list(scored)
        above = [(s, a) for s, a in ordered_scored if s >= SIMILARITY_THRESHOLD]
        candidate_pool = ordered_scored
        if candidate_pool:
            candidates_list.append((entry, dl_path, candidate_pool))
            ref_map[entry["title"]] = dl_path
            if above:
                _log(f"  [{entry['index']}] 找到 {len(above)} 个高相似候选，按本地图片顺序逐张确认")
            else:
                _log(f"  [{entry['index']}] {entry['title']} — 最高相似度 {ordered_scored[0][0]:.1%} "
                     f"低于阈值 {SIMILARITY_THRESHOLD:.0%}，按本地顺序继续逐张比对（{len(candidate_pool)} 张）")
        else:
            _log(f"  [{entry['index']}] {entry['title']} — 无可比对图片")

    return candidates_list, ref_map


def rename_assets(plan: Sequence[tuple[Path, Path, str]], dry_run: bool = False) -> list[str]:
    summary: List[str] = []
    for src, dst, title in plan:
        if src == dst:
            summary.append(f"Skip: {src.name} -> already named correctly")
            continue
        if dst.exists():
            summary.append(f"Skip: {src.name} -> target exists: {dst.name}")
            continue

        if dry_run:
            summary.append(f"Would rename: {src.name} -> {dst.name}  [{title}]")
        else:
            src.rename(dst)
            summary.append(f"Renamed: {src.name} -> {dst.name}  [{title}]")
    return summary


class ImageRenameApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("商品高清图重命名工具")
        self.root.geometry("980x700")
        self.root.minsize(900, 600)

        self.detail_var = tk.StringVar(value="")
        self.image_dir_var = tk.StringVar(value="")
        self._last_plan: List[tuple[Path, Path, str]] = []
        self._temp_dir: Path | None = None
        self._ref_map: dict = {}   # title → dl_path

        self._build_ui()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="商品详情文件", font=("Microsoft YaHei", 10, "bold")).pack(anchor="w")
        detail_row = ttk.Frame(main)
        detail_row.pack(fill=tk.X, pady=(4, 10))
        ttk.Entry(detail_row, textvariable=self.detail_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(detail_row, text="选择文件", command=self.choose_detail_file).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(main, text="本地高清图片目录", font=("Microsoft YaHei", 10, "bold")).pack(anchor="w")
        dir_row = ttk.Frame(main)
        dir_row.pack(fill=tk.X, pady=(4, 10))
        ttk.Entry(dir_row, textvariable=self.image_dir_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(dir_row, text="选择目录", command=self.choose_image_dir).pack(side=tk.LEFT, padx=(8, 0))

        button_row = ttk.Frame(main)
        button_row.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(button_row, text="预览重命名", command=self.preview_rename).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_row, text="执行重命名", command=self.execute_rename).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_row, text="清空日志", command=self.clear_log).pack(side=tk.LEFT)

        ttk.Label(main, text="日志", font=("Microsoft YaHei", 10, "bold")).pack(anchor="w")
        self.log_area = scrolledtext.ScrolledText(main, font=("Consolas", 9), wrap=tk.WORD)
        self.log_area.pack(fill=tk.BOTH, expand=True)
        self.log_area.insert(tk.END, "请选择商品详情文件和本地图片目录，然后点击“预览重命名”。\n")
        self.log_area.configure(state=tk.DISABLED)

    def log(self, message: str):
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.configure(state=tk.DISABLED)

    def choose_detail_file(self):
        path = filedialog.askopenfilename(
            title="选择商品详细信息文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
        )
        if path:
            self.detail_var.set(path)

    def choose_image_dir(self):
        path = filedialog.askdirectory(title="选择本地高清图片目录")
        if path:
            self.image_dir_var.set(path)

    def _prepare_plan(self):
        """下载+比对，返回 (candidates_list, ref_map)"""
        detail_path = Path(self.detail_var.get()).expanduser().resolve()
        image_dir = Path(self.image_dir_var.get()).expanduser().resolve()
        if not detail_path.exists():
            raise FileNotFoundError(f"未找到商品详情文件：{detail_path}")
        if not image_dir.exists():
            raise FileNotFoundError(f"未找到图片目录：{image_dir}")
        self._cleanup_temp()
        self._temp_dir = Path(tempfile.mkdtemp(prefix="product_imgs_"))

        def thread_safe_log(msg: str) -> None:
            self.root.after(0, lambda m=msg: self.log(m))

        candidates, ref_map = build_rename_plan(
            detail_path, image_dir,
            temp_dir=self._temp_dir,
            log=thread_safe_log,
        )
        self._ref_map = ref_map
        return candidates

    def _cleanup_temp(self) -> int:
        """清理临时下载目录，返回删除文件数"""
        temp = self._temp_dir
        self._temp_dir = None
        if temp and temp.exists():
            count = sum(1 for _ in temp.rglob("*") if _.is_file())
            shutil.rmtree(temp, ignore_errors=True)
            return count
        return 0

    def _run_background_task(self, task_label: str, worker, on_done):
        if getattr(self, "_busy", False):
            return
        self._busy = True
        self.log(f"{task_label}处理中...")

        def runner():
            try:
                result = worker()
            except Exception as exc:
                self.root.after(0, lambda e=exc: self._handle_task_error(task_label, e))
                return
            self.root.after(0, lambda: on_done(result))

        threading.Thread(target=runner, daemon=True).start()

    def _handle_task_error(self, task_label: str, exc: Exception):
        self._busy = False
        messagebox.showerror("错误", str(exc))
        self.log(f"{task_label}错误: {exc}")

    def preview_rename(self):
        def worker():
            return self._prepare_plan()

        def on_done(candidates):
            self._busy = False
            if not candidates:
                self.log("\n未找到匹配候选。")
                cleaned = self._cleanup_temp()
                if cleaned:
                    self.log(f"已清理 {cleaned} 个临时图片。")
                return
            self.log(f"\n自动比对完成，找到 {len(candidates)} 个商品有候选匹配。开始逐张确认...")
            self._confirm_matches(candidates)

        self.log_area.configure(state=tk.NORMAL)
        self.log_area.delete(1.0, tk.END)
        self.log_area.configure(state=tk.DISABLED)
        self._run_background_task("预览重命名", worker, on_done)

    def _confirm_matches(self, candidates_list: List[tuple]) -> None:
        """
        逐张弹窗确认匹配结果。
        「确认」→ 保留该匹配；「跳过」→ 取下一个候选重新展示。
        """
        if PILImage is None or PILImageTk is None:
            # 无 Pillow 时自动确认所有最佳候选
            confirmed = []
            used: set = set()
            for entry, dl_path, scored in candidates_list:
                for score, asset in scored:
                    if asset not in used:
                        used.add(asset)
                        new_name = f"{entry['index']:02d}_{clean_title(entry['title'])}{asset.suffix}"
                        confirmed.append((asset, asset.with_name(new_name), entry["title"]))
                        break
            self._on_confirm_done(confirmed)
            return

        confirmed: List[tuple[Path, Path, str]] = []
        used_assets: set = set()
        total = len(candidates_list)

        for prod_idx, (entry, dl_path, scored) in enumerate(candidates_list):
            title = entry["title"]
            # 保持本地高清图的原始顺序，不在没有确认的情况下“跳到下一张”
            available = [(s, a) for s, a in scored if a not in used_assets]
            if not available:
                self.log(f"  [{prod_idx+1}/{total}] {title} — 候选已被占用，跳过")
                continue

            found = False
            cursor = 0
            while cursor < len(available):
                score, asset = available[cursor]
                cand_idx = cursor + 1
                new_name = f"{entry['index']:02d}_{clean_title(title)}{asset.suffix}"
                dst_path = asset.with_name(new_name)

                action = self._show_confirm_dialog(
                    prod_idx + 1, total, cand_idx, len(available),
                    asset, dst_path, title, dl_path, score,
                    allow_back=(cursor > 0),
                )
                if action == "confirm":
                    used_assets.add(asset)
                    confirmed.append((asset, dst_path, title))
                    self.log(f"  ✓ [{prod_idx+1}/{total}] 确认: {asset.name} → {new_name}  (相似度 {score:.1%})")
                    found = True
                    break
                if action == "back":
                    cursor = max(0, cursor - 1)
                    self.log(f"  ↩ [{prod_idx+1}/{total}] 返回上一张候选: {available[cursor][1].name}")
                    continue
                # 这里遵循“本地图片不动，直到匹配上才下一张”的规则：
                # 仅当用户确认当前图片不是目标时，才继续前进。
                self.log(f"  ✗ [{prod_idx+1}/{total}] 不是目标: {asset.name}  (相似度 {score:.1%})")
                cursor += 1

            if not found:
                self.log(f"  ⊘ [{prod_idx+1}/{total}] {title} — 未在本地图片中找到匹配项")

        self._on_confirm_done(confirmed)
        if confirmed:
            self._show_summary_preview(confirmed)

    def _show_confirm_dialog(
        self,
        prod_idx: int, prod_total: int,
        cand_idx: int, cand_total: int,
        local_path: Path, dst_path: Path, title: str,
        ref_path: Path | None, score: float,
        allow_back: bool = False,
    ) -> str:
        """显示单张匹配确认对话框，返回 confirm / skip / back"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"确认匹配 [{prod_idx}/{prod_total}]  候选 {cand_idx}/{cand_total}")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        result = ["skip"]

        # ── 标题 ──
        ttk.Label(
            dialog, text=f"商品：{title}",
            font=("Microsoft YaHei", 10, "bold"), wraplength=540,
        ).pack(padx=16, pady=(12, 2))
        ttk.Label(
            dialog,
            text=f"{local_path.name}  →  {dst_path.name}",
            font=("Consolas", 9), foreground="#555",
        ).pack(padx=16, pady=(0, 2))
        ttk.Label(
            dialog,
            text=f"相似度：{score:.1%}    候选 {cand_idx}/{cand_total}",
            font=("Microsoft YaHei", 9), foreground="#1a73e8",
        ).pack(padx=16, pady=(0, 8))

        # ── 图片对比区 ──
        img_frame = ttk.Frame(dialog)
        img_frame.pack(padx=16, pady=(0, 8))
        thumb_size = (220, 220)

        # 左：本地高清图
        left_box = ttk.LabelFrame(img_frame, text="本地高清图（待重命名）", padding=4)
        left_box.grid(row=0, column=0, padx=(0, 8))
        try:
            _limg = PILImage.open(local_path)
            _limg.thumbnail(thumb_size, PILImage.Resampling.BILINEAR)
            _lphoto = PILImageTk.PhotoImage(_limg)
            ttk.Label(left_box, image=_lphoto).pack()
            left_box._photo_ref = _lphoto
        except Exception as exc:
            ttk.Label(left_box, text=f"无法加载\n{exc}", foreground="red").pack()

        # 右：下载的参考图
        right_box = ttk.LabelFrame(img_frame, text="下载参考图", padding=4)
        right_box.grid(row=0, column=1, padx=(8, 0))
        if ref_path and ref_path.exists():
            try:
                _rimg = PILImage.open(ref_path)
                _rimg.thumbnail(thumb_size, PILImage.Resampling.BILINEAR)
                _rphoto = PILImageTk.PhotoImage(_rimg)
                ttk.Label(right_box, image=_rphoto).pack()
                right_box._photo_ref = _rphoto
            except Exception as exc:
                ttk.Label(right_box, text=f"无法加载\n{exc}", foreground="red").pack()
        else:
            ttk.Label(right_box, text="无参考图", foreground="gray").pack()

        # ── 按钮 ──
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(padx=16, pady=(4, 14))

        def on_confirm():
            result[0] = "confirm"
            dialog.destroy()

        def on_skip():
            result[0] = "skip"
            dialog.destroy()

        def on_back():
            result[0] = "back"
            dialog.destroy()

        skip_label = "✗ 跳过（下一候选）" if cand_idx < cand_total else "✗ 跳过（无更多候选）"
        ttk.Button(btn_frame, text="✓ 确认匹配", command=on_confirm, width=14).pack(side=tk.LEFT, padx=6)
        if allow_back:
            ttk.Button(btn_frame, text="↩ 上一张", command=on_back, width=12).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text=skip_label, command=on_skip, width=18).pack(side=tk.LEFT, padx=6)

        dialog.protocol("WM_DELETE_WINDOW", on_skip)

        dialog.update_idletasks()
        w, h = dialog.winfo_width(), dialog.winfo_height()
        x = (dialog.winfo_screenwidth() - w) // 2
        y = (dialog.winfo_screenheight() - h) // 3
        dialog.geometry(f"+{x}+{y}")

        self.root.wait_window(dialog)
        return result[0]

    def _on_confirm_done(self, confirmed_plan: List[tuple[Path, Path, str]]) -> None:
        """确认流程结束后显示预览"""
        self._last_plan = confirmed_plan
        if not confirmed_plan:
            self.log("\n无确认的匹配项，未生成重命名计划。")
            cleaned = self._cleanup_temp()
            if cleaned:
                self.log(f"已清理 {cleaned} 个临时图片。")
            return

        preview_lines = [f"\n确认完成，共 {len(confirmed_plan)} 个匹配："]
        preview_lines.extend(rename_assets(confirmed_plan, dry_run=True))
        preview_lines.append("")
        preview_lines.append("预览完成，未实际改名。点击「执行重命名」后将自动清理下载的临时图片。")

        self.log_area.configure(state=tk.NORMAL)
        for line in preview_lines:
            self.log_area.insert(tk.END, line + "\n")
        self.log_area.see(tk.END)
        self.log_area.configure(state=tk.DISABLED)

    def _show_summary_preview(self, confirmed_plan: List[tuple[Path, Path, str]]) -> None:
        """显示最终总预览：全部已确认的重命名结果"""
        plan = list(confirmed_plan)

        dialog = tk.Toplevel(self.root)
        dialog.title("总预览：全部已确认重命名")
        dialog.geometry("760x520")
        dialog.transient(self.root)
        dialog.grab_set()

        tree = ttk.Treeview(
            dialog,
            columns=("index", "source", "new_name", "title"),
            show="headings",
            height=16,
        )
        tree.heading("index", text="序号")
        tree.heading("source", text="本地文件")
        tree.heading("new_name", text="目标文件名")
        tree.heading("title", text="商品")
        tree.column("index", width=60, anchor="center")
        tree.column("source", width=220, anchor="w")
        tree.column("new_name", width=220, anchor="w")
        tree.column("title", width=220, anchor="w")
        tree.pack(fill=tk.BOTH, expand=True, padx=12, pady=(12, 8))

        def refresh_tree():
            for child in tree.get_children():
                tree.delete(child)
            for i, (src, dst, title) in enumerate(plan, start=1):
                tree.insert(
                    "",
                    tk.END,
                    values=(i, src.name, dst.name, title),
                )

        def remove_selected():
            if not tree.selection():
                messagebox.showinfo("提示", "请先选中一条需要修改的记录。")
                return
            selected = tree.selection()[0]
            index = int(tree.item(selected, "values")[0]) - 1
            if 0 <= index < len(plan):
                del plan[index]
                self._last_plan = list(plan)
                refresh_tree()

        def edit_selected():
            if not tree.selection():
                messagebox.showinfo("提示", "请先选中一条需要修改的记录。")
                return
            selected = tree.selection()[0]
            index = int(tree.item(selected, "values")[0]) - 1
            if not 0 <= index < len(plan):
                return

            src, dst, title = plan[index]
            edit_win = tk.Toplevel(dialog)
            edit_win.title("修改目标文件名")
            edit_win.transient(dialog)
            edit_win.grab_set()

            ttk.Label(edit_win, text=f"当前文件：{src.name}", anchor="w").pack(fill=tk.X, padx=12, pady=(12, 4))
            ttk.Label(edit_win, text=f"商品：{title}", anchor="w").pack(fill=tk.X, padx=12, pady=4)

            var = tk.StringVar(value=dst.name)
            ttk.Entry(edit_win, textvariable=var, width=40).pack(fill=tk.X, padx=12, pady=(4, 10))

            def apply_edit():
                new_name = var.get().strip()
                if not new_name:
                    messagebox.showwarning("提示", "目标文件名不能为空。")
                    return
                new_dst = src.with_name(new_name)
                plan[index] = (src, new_dst, title)
                self._last_plan = list(plan)
                refresh_tree()
                edit_win.destroy()

            ttk.Button(edit_win, text="保存修改", command=apply_edit).pack(pady=(0, 12))

        refresh_tree()

        button_row = ttk.Frame(dialog)
        button_row.pack(fill=tk.X, padx=12, pady=(0, 12))
        ttk.Button(button_row, text="修改选中项", command=edit_selected).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_row, text="删除选中项", command=remove_selected).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_row, text="关闭", command=dialog.destroy).pack(side=tk.RIGHT)

        if not plan:
            ttk.Label(dialog, text="当前没有可执行的重命名项。", foreground="gray").pack(pady=(0, 8))

    def execute_rename(self):
        if not self._last_plan:
            messagebox.showinfo("提示", "请先点击「预览重命名」并完成确认。")
            return

        def worker():
            return rename_assets(self._last_plan, dry_run=False)

        def on_done(summary):
            self._busy = False
            cleaned = self._cleanup_temp()
            self.log_area.configure(state=tk.NORMAL)
            self.log_area.delete(1.0, tk.END)
            self.log_area.insert(tk.END, f"已执行重命名，共 {len(summary)} 条记录\n")
            for row in summary:
                self.log_area.insert(tk.END, row + "\n")
            self.log_area.insert(tk.END, "\n重命名完成。\n")
            if cleaned:
                self.log_area.insert(tk.END, f"已清理 {cleaned} 个临时下载图片。\n")
            self.log_area.configure(state=tk.DISABLED)
            messagebox.showinfo("完成", f"已重命名 {len(summary)} 个文件"
                                + (f"\n已清理 {cleaned} 个临时图片" if cleaned else ""))

        self._run_background_task("执行重命名", worker, on_done)

    def clear_log(self):
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.delete(1.0, tk.END)
        self.log_area.insert(tk.END, "日志已清空。\n")
        self.log_area.configure(state=tk.DISABLED)


def cli_main() -> None:
    parser = argparse.ArgumentParser(description="Rename local product images based on Bilibili product detail info.")
    parser.add_argument("--detail", type=Path, help="Path to 商品详细信息.txt")
    parser.add_argument("--image-dir", type=Path, help="Folder containing the local high-resolution images")
    parser.add_argument("--dry-run", action="store_true", help="Preview the rename plan without changing files")
    args = parser.parse_args()

    if not args.detail or not args.image_dir:
        raise SystemExit("Please provide both --detail and --image-dir when using CLI mode.")

    detail_path = args.detail.resolve()
    image_dir = args.image_dir.resolve()

    if not detail_path.exists():
        raise FileNotFoundError(f"Detail file not found: {detail_path}")
    if not image_dir.exists():
        raise FileNotFoundError(f"Image directory not found: {image_dir}")

    temp_dir = Path(tempfile.mkdtemp(prefix="product_imgs_"))
    try:
        candidates, _ref_map = build_rename_plan(detail_path, image_dir, temp_dir=temp_dir, log=print)
        # CLI 模式：自动确认所有最佳候选
        used: set = set()
        plan: List[tuple[Path, Path, str]] = []
        for entry, dl_path, scored in candidates:
            for score, asset in scored:
                if asset not in used:
                    used.add(asset)
                    new_name = f"{entry['index']:02d}_{clean_title(entry['title'])}{asset.suffix}"
                    plan.append((asset, asset.with_name(new_name), entry["title"]))
                    break
        print(f"\nDetected {len(plan)} rename candidates in {image_dir}")
        for row in rename_assets(plan, dry_run=args.dry_run):
            print(row)

        if args.dry_run:
            print("\nDry run enabled. No files were changed.")
        else:
            print("\nDone. Files renamed successfully.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"临时下载目录已清理：{temp_dir}")


def main() -> None:
    if len(sys.argv) > 1:
        cli_main()
        return

    root = tk.Tk()
    app = ImageRenameApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
