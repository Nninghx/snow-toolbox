import sys
sys.dont_write_bytecode = True

"""
池子表格编辑工具
提供可视化表格界面，支持增删改池子数据，保存后输出 temp_pools.json 供辅助看池工具使用。
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def get_temp_pools_path():
    return get_base_dir() / "temp_pools.json"


class PoolTableEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("池子表格编辑 - temp_pools.json")
        self.root.geometry("700x500")
        self.root.minsize(560, 400)

        self._build_ui()
        self._load_from_file()

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 顶部按钮栏
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(btn_frame, text="新增", command=self._add_row, width=8).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_frame, text="编辑选中", command=self._edit_row, width=10).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_frame, text="删除选中", command=self._delete_row, width=10).pack(side=tk.LEFT, padx=(0, 4))

        ttk.Separator(btn_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Button(btn_frame, text="保存到文件", command=self._save_to_file, width=12).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_frame, text="另存为...", command=self._save_as, width=10).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_frame, text="导入文件", command=self._import_file, width=10).pack(side=tk.LEFT, padx=(0, 4))

        ttk.Separator(btn_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Button(btn_frame, text="清空表格", command=self._clear_all, width=10).pack(side=tk.LEFT)

        # 表格区域
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("index", "name", "items_id")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended")

        self.tree.heading("index", text="序号", anchor=tk.CENTER)
        self.tree.heading("name", text="池子名称", anchor=tk.W)
        self.tree.heading("items_id", text="商品ID", anchor=tk.W)

        self.tree.column("index", width=50, minwidth=40, anchor=tk.CENTER, stretch=False)
        self.tree.column("name", width=200, minwidth=80)
        self.tree.column("items_id", width=200, minwidth=80)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 双击编辑
        self.tree.bind("<Double-1>", lambda e: self._edit_row())

        # 底部状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=(6, 2))
        status_bar.pack(fill=tk.X, pady=(8, 0))

    def _refresh_index(self):
        """刷新序号列"""
        for i, item_id in enumerate(self.tree.get_children(), start=1):
            values = list(self.tree.item(item_id, "values"))
            values[0] = i
            self.tree.item(item_id, values=values)
        count = len(self.tree.get_children())
        self.status_var.set(f"共 {count} 条记录")

    def _load_from_file(self):
        """从 temp_pools.json 加载数据"""
        path = get_temp_pools_path()
        if not path.exists():
            self.status_var.set("未找到 temp_pools.json，表格为空")
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self._populate_table(data)
            self.status_var.set(f"已从 {path.name} 加载 {len(data)} 条记录")
        except Exception as e:
            messagebox.showerror("加载失败", f"读取 temp_pools.json 出错：\n{e}")

    def _populate_table(self, data):
        """将列表数据填充到表格"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        for i, row in enumerate(data, start=1):
            if isinstance(row, (list, tuple)) and len(row) >= 2:
                name = str(row[0]).strip()
                items_id = str(row[1]).strip()
                self.tree.insert("", tk.END, values=(i, name, items_id))
            elif isinstance(row, dict):
                name = str(row.get("name", "")).strip()
                items_id = str(row.get("items_id", row.get("id", ""))).strip()
                self.tree.insert("", tk.END, values=(i, name, items_id))

    def _get_table_data(self):
        """从表格提取数据，返回二维列表"""
        data = []
        for item_id in self.tree.get_children():
            values = self.tree.item(item_id, "values")
            name = str(values[1]).strip()
            items_id = str(values[2]).strip()
            data.append([name, items_id])
        return data

    def _add_row(self):
        """弹出对话框新增一行"""
        self._show_edit_dialog("新增池子", None)

    def _edit_row(self):
        """编辑选中的行"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选中要编辑的行")
            return
        if len(selected) > 1:
            messagebox.showwarning("提示", "只能编辑一行，请取消多选")
            return
        item_id = selected[0]
        values = self.tree.item(item_id, "values")
        self._show_edit_dialog("编辑池子", (item_id, values[1], values[2]))

    def _delete_row(self):
        """删除选中的行"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选中要删除的行")
            return
        count = len(selected)
        if not messagebox.askyesno("确认删除", f"确定要删除选中的 {count} 行吗？"):
            return
        for item_id in selected:
            self.tree.delete(item_id)
        self._refresh_index()

    def _clear_all(self):
        """清空表格"""
        if not self.tree.get_children():
            return
        if not messagebox.askyesno("确认清空", "确定要清空所有数据吗？此操作不可撤销。"):
            return
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)
        self._refresh_index()

    def _show_edit_dialog(self, title, existing):
        """
        显示编辑对话框。
        existing: None 表示新增，(item_id, name, items_id) 表示编辑。
        """
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="池子名称:").grid(row=0, column=0, sticky=tk.W, pady=(0, 6))
        name_entry = ttk.Entry(frame, width=30)
        name_entry.grid(row=0, column=1, sticky=tk.EW, pady=(0, 6), padx=(8, 0))

        ttk.Label(frame, text="商品ID:").grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        id_entry = ttk.Entry(frame, width=30)
        id_entry.grid(row=1, column=1, sticky=tk.EW, pady=(0, 10), padx=(8, 0))

        if existing:
            name_entry.insert(0, existing[1])
            id_entry.insert(0, existing[2])

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(5, 0))

        def on_confirm():
            name = name_entry.get().strip()
            items_id = id_entry.get().strip()
            if not name:
                messagebox.showwarning("提示", "请输入池子名称", parent=dialog)
                return
            if not items_id:
                messagebox.showwarning("提示", "请输入商品ID", parent=dialog)
                return

            if existing:
                self.tree.item(existing[0], values=(existing[0], name, items_id))
                self._refresh_index()
            else:
                idx = len(self.tree.get_children()) + 1
                self.tree.insert("", tk.END, values=(idx, name, items_id))
                self._refresh_index()

            dialog.destroy()

        def on_batch_add():
            """批量模式：保留对话框，继续添加下一条"""
            name = name_entry.get().strip()
            items_id = id_entry.get().strip()
            if not name or not items_id:
                messagebox.showwarning("提示", "池子名称和商品ID都不能为空", parent=dialog)
                return
            idx = len(self.tree.get_children()) + 1
            self.tree.insert("", tk.END, values=(idx, name, items_id))
            self._refresh_index()
            name_entry.delete(0, tk.END)
            id_entry.delete(0, tk.END)
            name_entry.focus_set()

        ttk.Button(btn_frame, text="确定", command=on_confirm, width=8).pack(side=tk.LEFT, padx=4)
        if not existing:
            ttk.Button(btn_frame, text="继续添加", command=on_batch_add, width=10).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy, width=8).pack(side=tk.LEFT, padx=4)

        # 居中显示
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        name_entry.focus_set()
        dialog.bind("<Return>", lambda e: on_confirm())

    def _save_to_file(self):
        """保存到 temp_pools.json"""
        data = self._get_table_data()
        path = get_temp_pools_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            self.status_var.set(f"已保存到 {path}（{len(data)} 条记录）")
            messagebox.showinfo("保存成功", f"已保存 {len(data)} 条记录到：\n{path}")
        except Exception as e:
            messagebox.showerror("保存失败", f"写入文件出错：\n{e}")

    def _save_as(self):
        """另存为指定路径"""
        data = self._get_table_data()
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
            initialfile="temp_pools.json"
        )
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            self.status_var.set(f"已另存为 {path}（{len(data)} 条记录）")
        except Exception as e:
            messagebox.showerror("保存失败", f"写入文件出错：\n{e}")

    def _import_file(self):
        """从外部文件导入数据（追加模式），支持 JSON 和 xlsx"""
        path = filedialog.askopenfilename(
            filetypes=[
                ("支持的文件", "*.json;*.xlsx"),
                ("Excel 文件", "*.xlsx"),
                ("JSON 文件", "*.json"),
                ("所有文件", "*.*"),
            ],
            title="选择要导入的文件（支持 .json / .xlsx）"
        )
        if not path:
            return

        suffix = Path(path).suffix.lower()
        if suffix == ".xlsx":
            self._import_xlsx(path)
        else:
            self._import_json(path)

    def _import_json(self, path):
        """导入 JSON 文件"""
        try:
            raw = Path(path).read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, list):
                messagebox.showerror("格式错误", "JSON 文件内容应为数组格式")
                return

            count = 0
            for row in data:
                if isinstance(row, (list, tuple)) and len(row) >= 2:
                    name = str(row[0]).strip()
                    items_id = str(row[1]).strip()
                    if name and items_id:
                        idx = len(self.tree.get_children()) + 1
                        self.tree.insert("", tk.END, values=(idx, name, items_id))
                        count += 1
                elif isinstance(row, dict):
                    name = str(row.get("name", "")).strip()
                    items_id = str(row.get("items_id", row.get("id", ""))).strip()
                    if name and items_id:
                        idx = len(self.tree.get_children()) + 1
                        self.tree.insert("", tk.END, values=(idx, name, items_id))
                        count += 1

            self._refresh_index()
            self.status_var.set(f"已从 {Path(path).name} 导入 {count} 条记录")
        except json.JSONDecodeError as e:
            messagebox.showerror("解析失败", f"JSON 格式错误：\n{e}")
        except Exception as e:
            messagebox.showerror("导入失败", f"读取文件出错：\n{e}")

    def _import_xlsx(self, path):
        """导入 Excel (.xlsx) 文件，自动识别表头行"""
        if not OPENPYXL_AVAILABLE:
            messagebox.showerror(
                "缺少依赖",
                "导入 Excel 文件需要 openpyxl 库。\n\n"
                "请运行以下命令安装：\n"
                "pip install openpyxl"
            )
            return

        try:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            ws = wb.active

            rows = list(ws.iter_rows(values_only=True))
            wb.close()

            if not rows:
                messagebox.showwarning("提示", "Excel 文件为空")
                return

            # 自动检测表头：如果第一行含有 "名称"/"name"/"池子" 等关键字则跳过
            start_idx = 0
            first_row = [str(c).strip().lower() if c else "" for c in rows[0]]
            header_keywords = ("名称", "name", "池子", "商品", "id", "items", "编号")
            if any(kw in cell for cell in first_row for kw in header_keywords):
                start_idx = 1

            count = 0
            for row in rows[start_idx:]:
                if row is None or len(row) < 2:
                    continue
                name = str(row[0]).strip() if row[0] else ""
                items_id = str(row[1]).strip() if row[1] else ""
                # 处理 Excel 中数字被读为 float 的情况（如 13665534.0）
                if items_id.endswith(".0") and items_id[:-2].isdigit():
                    items_id = items_id[:-2]
                if name and items_id:
                    idx = len(self.tree.get_children()) + 1
                    self.tree.insert("", tk.END, values=(idx, name, items_id))
                    count += 1

            self._refresh_index()
            self.status_var.set(f"已从 {Path(path).name} 导入 {count} 条记录")
            if count == 0:
                messagebox.showwarning("提示", "未从 Excel 中解析到有效数据。\n请确保前两列分别为：池子名称、商品ID")
        except Exception as e:
            messagebox.showerror("导入失败", f"读取 Excel 文件出错：\n{e}")


def main():
    root = tk.Tk()
    app = PoolTableEditorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
