import os
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import threading


class TimeModifierApp:
    def __init__(self, root):
        self.root = root
        self.root.title("文件时间修改器 V1.0")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 设置样式
        style = ttk.Style()
        style.configure('TButton', padding=5)
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'))
        
        # 主框架
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 文件/文件夹选择区域
        selection_frame = ttk.LabelFrame(main_frame, text="选择目标", padding="10")
        selection_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(selection_frame, text="路径:", font=('Arial', 9)).grid(row=0, column=0, sticky=tk.W, padx=5)
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(selection_frame, textvariable=self.path_var, width=60)
        self.path_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        ttk.Button(selection_frame, text="浏览文件", command=self.browse_file).grid(row=0, column=2, padx=2)
        ttk.Button(selection_frame, text="浏览文件夹", command=self.browse_folder).grid(row=0, column=3, padx=2)
        
        # 时间设置区域
        time_frame = ttk.LabelFrame(main_frame, text="时间设置", padding="10")
        time_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 创建时间
        ttk.Label(time_frame, text="创建时间:", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, pady=5)
        self.create_time_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        create_time_frame = ttk.Frame(time_frame)
        create_time_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Entry(create_time_frame, textvariable=self.create_time_var, width=20).pack(side=tk.LEFT, padx=2)
        ttk.Button(create_time_frame, text="现在", command=lambda: self.set_current_time(self.create_time_var)).pack(side=tk.LEFT, padx=2)
        
        # 修改时间
        ttk.Label(time_frame, text="修改时间:", style='Header.TLabel').grid(row=1, column=0, sticky=tk.W, pady=5)
        self.modify_time_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        modify_time_frame = ttk.Frame(time_frame)
        modify_time_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Entry(modify_time_frame, textvariable=self.modify_time_var, width=20).pack(side=tk.LEFT, padx=2)
        ttk.Button(modify_time_frame, text="现在", command=lambda: self.set_current_time(self.modify_time_var)).pack(side=tk.LEFT, padx=2)
        
        # 访问时间
        ttk.Label(time_frame, text="访问时间:", style='Header.TLabel').grid(row=2, column=0, sticky=tk.W, pady=5)
        self.access_time_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        access_time_frame = ttk.Frame(time_frame)
        access_time_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Entry(access_time_frame, textvariable=self.access_time_var, width=20).pack(side=tk.LEFT, padx=2)
        ttk.Button(access_time_frame, text="现在", command=lambda: self.set_current_time(self.access_time_var)).pack(side=tk.LEFT, padx=2)
        
        # 选项区域
        options_frame = ttk.LabelFrame(main_frame, text="选项", padding="10")
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.recursive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="递归处理子文件夹（仅文件夹模式）", variable=self.recursive_var).grid(row=0, column=0, sticky=tk.W, padx=5)
        
        self.apply_create_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="应用创建时间", variable=self.apply_create_var).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        self.apply_modify_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="应用修改时间", variable=self.apply_modify_var).grid(row=0, column=2, sticky=tk.W, padx=5)
        
        self.apply_access_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="应用访问时间", variable=self.apply_access_var).grid(row=0, column=3, sticky=tk.W, padx=5)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="开始修改", command=self.start_modification, style='TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="清空日志", command=self.clear_log).pack(side=tk.LEFT, padx=5)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="操作日志", padding="5")
        log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        main_frame.rowconfigure(5, weight=1)
        
        self.log_text = tk.Text(log_frame, height=15, wrap=tk.WORD, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 当前选中项信息
        info_frame = ttk.LabelFrame(main_frame, text="当前选中项信息", padding="10")
        info_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.info_text = tk.Text(info_frame, height=6, wrap=tk.WORD, state=tk.DISABLED)
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        info_frame.columnconfigure(0, weight=1)
    
    def browse_file(self):
        """浏览选择文件"""
        file_path = filedialog.askopenfilename(title="选择文件")
        if file_path:
            self.path_var.set(file_path)
            self.show_file_info(file_path)
    
    def browse_folder(self):
        """浏览选择文件夹"""
        folder_path = filedialog.askdirectory(title="选择文件夹")
        if folder_path:
            self.path_var.set(folder_path)
            self.show_file_info(folder_path)
    
    def show_file_info(self, path):
        """显示文件或文件夹的当前时间信息"""
        try:
            stat = os.stat(path)
            create_time = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
            modify_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            access_time = datetime.fromtimestamp(stat.st_atime).strftime("%Y-%m-%d %H:%M:%S")
            
            self.info_text.config(state=tk.NORMAL)
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(tk.END, f"路径: {path}\n")
            self.info_text.insert(tk.END, f"类型: {'文件夹' if os.path.isdir(path) else '文件'}\n")
            self.info_text.insert(tk.END, f"当前创建时间: {create_time}\n")
            self.info_text.insert(tk.END, f"当前修改时间: {modify_time}\n")
            self.info_text.insert(tk.END, f"当前访问时间: {access_time}\n")
            self.info_text.config(state=tk.DISABLED)
            
            self.log(f"已加载: {path}")
        except Exception as e:
            messagebox.showerror("错误", f"获取文件信息失败: {str(e)}")
    
    def set_current_time(self, var):
        """设置为当前时间"""
        var.set(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    def validate_time_format(self, time_str):
        """验证时间格式"""
        try:
            datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            return True
        except ValueError:
            return False
    
    def parse_time(self, time_str):
        """解析时间字符串为时间戳"""
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return dt.timestamp()
    
    def modify_single_file(self, file_path, create_time, modify_time, access_time):
        """修改单个文件的时间属性"""
        try:
            # Windows系统使用os.utime修改访问和修改时间
            if self.apply_access_var.get() or self.apply_modify_var.get():
                atime = access_time if self.apply_access_var.get() else os.stat(file_path).st_atime
                mtime = modify_time if self.apply_modify_var.get() else os.stat(file_path).st_mtime
                os.utime(file_path, (atime, mtime))
            
            # Windows系统创建时间需要使用win32api或subprocess调用powershell
            if self.apply_create_var.get():
                import subprocess
                create_time_str = datetime.fromtimestamp(create_time).strftime("%Y-%m-%dT%H:%M:%S")
                cmd = f'powershell -Command "(Get-Item \'{file_path}\').CreationTime=\'{create_time_str}\'"'
                subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            return True, "成功"
        except Exception as e:
            return False, str(e)
    
    def process_files(self, path, create_time, modify_time, access_time):
        """处理文件或文件夹"""
        results = {"success": 0, "failed": 0, "total": 0}
        
        if os.path.isfile(path):
            # 处理单个文件
            results["total"] = 1
            success, msg = self.modify_single_file(path, create_time, modify_time, access_time)
            if success:
                results["success"] += 1
                self.log(f"✓ 文件修改成功: {path}")
            else:
                results["failed"] += 1
                self.log(f"✗ 文件修改失败: {path} - {msg}")
        
        elif os.path.isdir(path):
            # 处理文件夹
            if self.recursive_var.get():
                # 递归处理
                for root, dirs, files in os.walk(path):
                    for name in files:
                        file_path = os.path.join(root, name)
                        results["total"] += 1
                        success, msg = self.modify_single_file(file_path, create_time, modify_time, access_time)
                        if success:
                            results["success"] += 1
                            self.log(f"✓ 文件修改成功: {file_path}")
                        else:
                            results["failed"] += 1
                            self.log(f"✗ 文件修改失败: {file_path} - {msg}")
                    
                    # 如果需要也修改文件夹本身的时间
                    if self.apply_create_var.get() or self.apply_modify_var.get() or self.apply_access_var.get():
                        results["total"] += 1
                        success, msg = self.modify_single_file(root, create_time, modify_time, access_time)
                        if success:
                            results["success"] += 1
                            self.log(f"✓ 文件夹修改成功: {root}")
                        else:
                            results["failed"] += 1
                            self.log(f"✗ 文件夹修改失败: {root} - {msg}")
            else:
                # 仅处理顶层文件
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    if os.path.isfile(item_path):
                        results["total"] += 1
                        success, msg = self.modify_single_file(item_path, create_time, modify_time, access_time)
                        if success:
                            results["success"] += 1
                            self.log(f"✓ 文件修改成功: {item_path}")
                        else:
                            results["failed"] += 1
                            self.log(f"✗ 文件修改失败: {item_path} - {msg}")
        
        return results
    
    def start_modification(self):
        """开始修改（在新线程中执行）"""
        path = self.path_var.get().strip()
        
        if not path:
            messagebox.showwarning("警告", "请先选择文件或文件夹！")
            return
        
        if not os.path.exists(path):
            messagebox.showerror("错误", "指定的路径不存在！")
            return
        
        # 验证时间格式
        if self.apply_create_var.get() and not self.validate_time_format(self.create_time_var.get()):
            messagebox.showerror("错误", "创建时间格式不正确，请使用 YYYY-MM-DD HH:MM:SS 格式")
            return
        
        if self.apply_modify_var.get() and not self.validate_time_format(self.modify_time_var.get()):
            messagebox.showerror("错误", "修改时间格式不正确，请使用 YYYY-MM-DD HH:MM:SS 格式")
            return
        
        if self.apply_access_var.get() and not self.validate_time_format(self.access_time_var.get()):
            messagebox.showerror("错误", "访问时间格式不正确，请使用 YYYY-MM-DD HH:MM:SS 格式")
            return
        
        # 解析时间
        create_time = self.parse_time(self.create_time_var.get()) if self.apply_create_var.get() else None
        modify_time = self.parse_time(self.modify_time_var.get()) if self.apply_modify_var.get() else None
        access_time = self.parse_time(self.access_time_var.get()) if self.apply_access_var.get() else None
        
        # 在新线程中执行
        thread = threading.Thread(target=self.execute_modification, args=(path, create_time, modify_time, access_time))
        thread.daemon = True
        thread.start()
    
    def execute_modification(self, path, create_time, modify_time, access_time):
        """执行修改操作"""
        self.status_var.set("正在处理...")
        self.log("=" * 50)
        self.log(f"开始处理: {path}")
        self.log(f"创建时间: {self.create_time_var.get() if create_time else '不修改'}")
        self.log(f"修改时间: {self.modify_time_var.get() if modify_time else '不修改'}")
        self.log(f"访问时间: {self.access_time_var.get() if access_time else '不修改'}")
        self.log(f"递归处理: {'是' if self.recursive_var.get() else '否'}")
        self.log("=" * 50)
        
        try:
            results = self.process_files(path, create_time, modify_time, access_time)
            
            self.log("=" * 50)
            self.log(f"处理完成！")
            self.log(f"总计: {results['total']} 个")
            self.log(f"成功: {results['success']} 个")
            self.log(f"失败: {results['failed']} 个")
            self.log("=" * 50)
            
            self.status_var.set(f"完成 - 成功: {results['success']}, 失败: {results['failed']}")
            
            if results['failed'] == 0:
                messagebox.showinfo("完成", f"所有 {results['success']} 个项目已成功修改！")
            else:
                messagebox.showwarning("完成", f"处理完成！\n成功: {results['success']}\n失败: {results['failed']}")
        
        except Exception as e:
            self.log(f"发生错误: {str(e)}")
            self.status_var.set("处理失败")
            messagebox.showerror("错误", f"处理过程中发生错误: {str(e)}")
    
    def log(self, message):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def clear_log(self):
        """清空日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)


def main():
    root = tk.Tk()
    app = TimeModifierApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
