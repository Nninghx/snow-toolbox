# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

"""
路线换乘工具
支持输入多条线路（每行一条线路：线路名: 站1, 站2, ...），
自动识别线路间重合的换乘站，并查询两站之间最少换乘的路线。
"""

import heapq
import re
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

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


TEMP_ROUTE_FILE = Path(__file__).resolve().parent.parent / "Core" / "Route.txt"


class SubwayRouteApp(PDFToolBase):
    def __init__(self, root):
        super().__init__(root)
        if not root.winfo_exists():
            return
        self.root = root
        self.root.title("路线换乘查询")
        self.root.minsize(560, 560)

        # 路网数据
        self.lines = {}            # {线路名: [站点列表]}
        self.station_lines = {}    # {站点: [所属线路列表]}

        self._build_ui()

        # 设置权重使控件可伸缩
        main_frame = self.root.nametowidget(self.root.winfo_children()[0])
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=3)
        main_frame.rowconfigure(3, weight=2)

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 路线输入区域
        input_frame = ttk.LabelFrame(
            main_frame,
            text="路线（每行一条路线，格式：路线名: 站1, 站2, 站3 ...）",
            padding=(10, 5)
        )
        input_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        input_frame.columnconfigure(0, weight=1)
        input_frame.rowconfigure(1, weight=1)

        add_route_frame = ttk.Frame(input_frame, padding=(0, 0, 0, 6))
        add_route_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        add_route_frame.columnconfigure(1, weight=1)
        add_route_frame.columnconfigure(3, weight=2)

        ttk.Label(add_route_frame, text="路线名:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5), pady=3)
        self.route_name_entry = ttk.Entry(add_route_frame)
        self.route_name_entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 10), pady=3)

        ttk.Label(add_route_frame, text="站名:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5), pady=3)
        self.route_stations_entry = ttk.Entry(add_route_frame)
        self.route_stations_entry.grid(row=0, column=3, sticky=tk.EW, padx=(0, 10), pady=3)

        add_route_btn = ttk.Button(add_route_frame, text="新增路线", command=self.add_route)
        add_route_btn.grid(row=0, column=4, sticky=tk.EW, padx=(0, 0), pady=3)

        self.input_text = tk.Text(input_frame, height=8)
        self.input_text.grid(row=1, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(input_frame, orient=tk.VERTICAL, command=self.input_text.yview)
        scroll.grid(row=1, column=1, sticky="ns")
        self.input_text.config(yscrollcommand=scroll.set)

        cached_content = self._load_temp_route_file()
        if cached_content and cached_content.strip():
            self.input_text.insert("1.0", cached_content)

        # 解析按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        parse_btn = ttk.Button(btn_frame, text="解析路网", command=self.parse_routes)
        parse_btn.pack(side=tk.LEFT, padx=5, ipadx=20, ipady=5)
        self.parse_label = ttk.Label(btn_frame, text="请先输入路线并解析")
        self.parse_label.pack(side=tk.LEFT, padx=10)

        # 换乘查询区域
        query_frame = ttk.LabelFrame(main_frame, text="换乘查询", padding=(10, 5))
        query_frame.pack(fill=tk.X, pady=5)
        query_frame.columnconfigure(1, weight=1)
        query_frame.columnconfigure(3, weight=1)

        ttk.Label(query_frame, text="起点站:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.combo_start = ttk.Combobox(query_frame, state="normal")
        self.combo_start.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        self.combo_start.bind("<KeyRelease>", self._filter_station_list)

        ttk.Label(query_frame, text="终点站:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.combo_end = ttk.Combobox(query_frame, state="normal")
        self.combo_end.grid(row=0, column=3, sticky=tk.EW, padx=5, pady=5)
        self.combo_end.bind("<KeyRelease>", self._filter_station_list)

        query_btn = ttk.Button(query_frame, text="查询路线", command=self.query_route)
        query_btn.grid(row=0, column=4, padx=10, ipadx=15, ipady=3)

        # 结果显示区域
        result_frame = ttk.LabelFrame(main_frame, text="查询结果", padding=(10, 5))
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

        self.result_text = tk.Text(result_frame, height=10, state=tk.DISABLED)
        self.result_text.grid(row=0, column=0, sticky="nsew")
        result_scroll = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        result_scroll.grid(row=0, column=1, sticky="ns")
        self.result_text.config(yscrollcommand=result_scroll.set)

    def _load_temp_route_file(self):
        """读取 Core 下的临时路线文件，若不存在则返回空字符串"""
        try:
            if not TEMP_ROUTE_FILE.exists():
                return ""
            return TEMP_ROUTE_FILE.read_text(encoding="utf-8")
        except Exception:
            return ""

    def _save_temp_route_file(self, text):
        """把当前路线文本保存到 Core 下的临时文件（覆盖模式）"""
        try:
            TEMP_ROUTE_FILE.parent.mkdir(parents=True, exist_ok=True)
            if text is None:
                text = ""
            TEMP_ROUTE_FILE.write_text(text, encoding="utf-8")
        except Exception:
            pass

    def add_route(self):
        """从上方输入框新增一条路线，并追加到文本区与临时文件"""
        route_name = self.route_name_entry.get().strip()
        stations_text = self.route_stations_entry.get().strip()
        if not route_name:
            messagebox.showwarning("提示", "请输入路线名！")
            return
        if not stations_text:
            messagebox.showwarning("提示", "请输入站名，多个站名用逗号或空格分隔。")
            return

        stations = [s.strip() for s in re.split(r'[,，、;；\s]+', stations_text) if s.strip()]
        if len(stations) < 2:
            messagebox.showwarning("提示", "每条路线至少需要 2 个站名。")
            return

        route_line = f"{route_name}: {', '.join(stations)}"
        existing_text = self.input_text.get("1.0", tk.END)
        if existing_text and not existing_text.endswith("\n"):
            existing_text += "\n"
        self.input_text.insert(tk.END, route_line + "\n")
        self._append_temp_route_file(route_line + "\n")
        self.route_name_entry.delete(0, tk.END)
        self.route_stations_entry.delete(0, tk.END)
        self.parse_label.config(text=f"已新增路线：{route_name}（{len(stations)} 个站点）")

    def _append_temp_route_file(self, text):
        """把新路线追加到 Core 下的临时文件，避免重复写入相同路线"""
        try:
            if text is None:
                return
            incoming_lines = [ln.strip() for ln in str(text).splitlines() if ln.strip()]
            if not incoming_lines:
                return

            existing_text = self._load_temp_route_file()
            existing_lines = [ln.strip() for ln in existing_text.splitlines() if ln.strip()]
            seen = set(existing_lines)
            new_lines = [ln for ln in incoming_lines if ln not in seen]
            if not new_lines:
                return

            combined = existing_text.rstrip()
            if combined:
                combined += "\n"
            combined += "\n".join(new_lines)
            combined += "\n"
            self._save_temp_route_file(combined)
        except Exception:
            pass

    def _filter_station_list(self, event=None):
        """按输入内容过滤站名列表，保持 combobox 可搜索"""
        widget = event.widget if event else None
        if widget is None:
            return

        full_values = getattr(widget, "_full_station_values", None)
        if not full_values:
            full_values = list(widget.cget("values")) if widget.cget("values") else []
            widget._full_station_values = full_values

        query = widget.get().strip().lower()
        if not query:
            widget.configure(values=full_values)
            return

        filtered = [item for item in full_values if query in item.lower()]
        widget.configure(values=filtered if filtered else [])
        widget.set(query)

    def clear_input(self):
        """清空路线输入，但保留临时文件本身不删除"""
        self.input_text.delete("1.0", tk.END)
        self._save_temp_route_file("")

    def parse_routes(self):
        """解析输入的路线文本，构建路网并识别换乘站"""
        raw = self.input_text.get("1.0", tk.END)
        lines = {}
        station_lines = {}
        errors = []

        for lineno, line_text in enumerate(raw.splitlines(), start=1):
            text = line_text.strip()
            if not text:
                continue
            # 兼容中英文冒号
            if ':' not in text and '：' not in text:
                errors.append(f"第 {lineno} 行缺少冒号（格式：线路名: 站1, 站2 ...）")
                continue
            sep = ':' if ':' in text else '：'
            name, rest = text.split(sep, 1)
            name = name.strip()
            if not name:
                errors.append(f"第 {lineno} 行缺少线路名")
                continue
            # 站点之间兼容逗号、顿号、分号、空白分隔
            stations = [s.strip() for s in re.split(r'[,，、;；\s]+', rest.strip()) if s.strip()]
            if len(stations) < 2:
                errors.append(f"第 {lineno} 行『{name}』站点数不足 2 个")
                continue
            if name in lines:
                errors.append(f"第 {lineno} 行线路名『{name}』重复")
                continue
            lines[name] = stations
            for st in stations:
                station_lines.setdefault(st, []).append(name)

        if not lines:
            self._save_temp_route_file("")
            messagebox.showerror("解析失败", "未解析出任何线路！\n" + "\n".join(errors[:5]))
            return

        self._append_temp_route_file(raw)
        self.lines = lines
        self.station_lines = station_lines

        # 识别换乘站（被多条线路共用的站）
        transfers = {st: ls for st, ls in station_lines.items() if len(ls) > 1}

        # 更新站点下拉框
        all_stations = sorted(station_lines.keys())
        for combo in (self.combo_start, self.combo_end):
            combo.config(state="normal", values=all_stations)
            combo._full_station_values = list(all_stations)
            combo.set("")

        summary = (
            f"解析成功：{len(lines)} 条线路，{len(all_stations)} 个站点，"
            f"{len(transfers)} 个换乘站"
        )
        self.parse_label.config(text=summary)
        self._append_result(summary + "\n")
        if transfers:
            self._append_result("换乘站明细：\n")
            for st, ls in sorted(transfers.items()):
                self._append_result(f"  · {st}（{'、'.join(ls)}）\n")
        else:
            self._append_result("（各线路之间没有重合的站点）\n")
        if errors:
            self._append_result("\n以下内容已跳过：\n" + "\n".join(f"  · {e}" for e in errors) + "\n")

    def find_route(self, start, end):
        """
        最少换乘优先、其次最少站数的路线查询。
        状态为（站点, 所在线路），用 Dijkstra 求 (换乘次数, 经过站数) 最小的路径。
        """
        dist = {}       # {(站点, 线路): (换乘次数, 经过站数)}
        prev = {}       # {(站点, 线路): 上一个状态}
        heap = []
        for ln in self.station_lines[start]:
            dist[(start, ln)] = (0, 0)
            heap.append((0, 0, start, ln))
        heapq.heapify(heap)

        best_state = None
        while heap:
            tr, steps, st, ln = heapq.heappop(heap)
            state = (st, ln)
            if dist.get(state) != (tr, steps):
                continue
            if st == end:
                best_state = state
                break
            # 沿当前线路的相邻站前进（不增加换乘次数）
            idx = self.lines[ln].index(st)
            for nxt in filter(None, (self.lines[ln][idx - 1] if idx > 0 else None,
                                     self.lines[ln][idx + 1] if idx + 1 < len(self.lines[ln]) else None)):
                cand = (tr, steps + 1)
                if cand < dist.get((nxt, ln), (float('inf'), float('inf'))):
                    dist[(nxt, ln)] = cand
                    prev[(nxt, ln)] = state
                    heapq.heappush(heap, (tr, steps + 1, nxt, ln))
            # 在换乘站切换到其他线路（换乘次数 +1）
            for ln2 in self.station_lines[st]:
                if ln2 == ln:
                    continue
                cand = (tr + 1, steps)
                if cand < dist.get((st, ln2), (float('inf'), float('inf'))):
                    dist[(st, ln2)] = cand
                    prev[(st, ln2)] = state
                    heapq.heappush(heap, (tr + 1, steps, st, ln2))

        if best_state is None:
            return None

        # 回溯状态路径，再按线路切分为乘车段
        states = []
        state = best_state
        while state is not None:
            states.append(state)
            state = prev.get(state)
        states.reverse()

        segments = []  # [(线路, [站点...])]
        for st, ln in states:
            if segments and segments[-1][0] == ln:
                segments[-1][1].append(st)
            else:
                segments.append((ln, [st]))
        # 换乘点需要同时属于上一段的终点，补回每段的起点
        for i in range(1, len(segments)):
            segments[i][1].insert(0, segments[i - 1][1][-1])

        transfers, steps = dist[best_state]
        return segments, transfers, steps

    def query_route(self):
        """查询并展示两站之间的路线"""
        if not self.lines:
            messagebox.showwarning("提示", "请先输入路线并点击『解析路网』！")
            return

        start = self.combo_start.get().strip()
        end = self.combo_end.get().strip()
        if not start or not end:
            messagebox.showwarning("提示", "请选择起点站和终点站！")
            return
        if start == end:
            self._append_result(f"{start} → {end}：起点和终点是同一站，无需乘车。\n")
            return

        result = self.find_route(start, end)
        if result is None:
            self._append_result(f"{start} → {end}：两站之间不连通（路网中存在互不相连的部分）。\n")
            return

        segments, transfers, steps = result
        self._append_result(f"\n{start} → {end}：共 {steps} 站，换乘 {transfers} 次\n")
        for ln, stations in segments:
            if len(stations) > 1:
                self._append_result(f"  乘坐【{ln}】：{' → '.join(stations)}（{len(stations) - 1} 站）\n")
            else:
                self._append_result(f"  在【{stations[0]}】换乘到【{ln}】\n")

    def _append_result(self, text):
        """向结果区追加文本"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.insert(tk.END, text)
        self.result_text.see(tk.END)
        self.result_text.config(state=tk.DISABLED)


if __name__ == "__main__":
    root = tk.Tk()
    app = SubwayRouteApp(root)
    if root.winfo_exists():
        root.mainloop()
