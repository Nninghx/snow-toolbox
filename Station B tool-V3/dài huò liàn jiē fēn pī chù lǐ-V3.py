import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk, font
import json
import os
import subprocess
import sys
from pathlib import Path
from fontTools.ttLib import TTFont


# ============ 授权验证 ============

def check_license():
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


# ============ 窗口图标设置 ============

def set_window_icon(root):
    """设置应用程序窗口图标"""
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    IMAGE_DIR = PROJECT_ROOT / "Image"
    
    icon_ico_path = IMAGE_DIR / "icon.ico"
    icon_png_path = IMAGE_DIR / "icon.png"

    # Windows系统设置应用ID
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.LinkBatchProcessor")
        except Exception:
            pass

    # 尝试设置ICO图标
    if icon_ico_path.exists():
        try:
            root.iconbitmap(default=str(icon_ico_path))
        except Exception:
            try:
                root.iconbitmap(str(icon_ico_path))
            except Exception:
                pass

    # 尝试设置PNG图标
    if hasattr(root, "iconphoto") and icon_png_path.exists():
        try:
            icon_image = tk.PhotoImage(file=str(icon_png_path))
            root.iconphoto(True, icon_image)
            # 保持引用防止垃圾回收
            root._icon_image = icon_image
        except Exception:
            pass


# ============ 字体加载 ============

def load_font(root):
    """从配置文件加载字体设置"""
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    IMAGE_DIR = PROJECT_ROOT / "Image"
    
    font_path = IMAGE_DIR / "AlibabaPuHuiTi-3-55-RegularL3.ttf"
    
    if not font_path.exists():
        messagebox.showerror("错误", f"找不到字体文件：{font_path}")
        root.destroy()
        sys.exit(1)
    
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
    current_font = (font_name, 10)
    root.option_add("*Font", current_font)
    return current_font


def split_links(links, batch_size=30):
    """
    将链接列表按指定大小分批
    :param links: 链接列表
    :param batch_size: 每批链接数量，默认为30
    :return: 分批后的链接列表
    """
    return [links[i:i + batch_size] for i in range(0, len(links), batch_size)]

class LinkBatchApp:
    def __init__(self, root):
        # 首先检查授权
        if not check_license():
            messagebox.showerror(
                "错误", 
                "缺少授权！无法使用！请先获取授权！\n"
            )
            sys.exit(1)
        
        self.root = root
        self.root.title("带货链接分批处理")
        self.root.geometry("650x550")
        
        # 设置窗口图标和加载字体
        set_window_icon(self.root)
        self.current_font = load_font(self.root)
        
        # 更新字体配置以使用自定义字体
        self.font_family = self.current_font[0]
        self.font_size = 12
        
        # 创建样式对象统一设置字体
        self.style = ttk.Style()
        self.style.configure('.', font=(self.font_family, 10))
        
        self.current_batch = 0
        self.all_batches = []
        
        # 输入区域
        self.input_frame = tk.LabelFrame(
            root, 
            text="输入链接", 
            padx=5, 
            pady=5,
            font=(self.font_family, self.font_size)
        )
        
        # 添加提取链接选项
        self.extract_only = tk.BooleanVar(value=False)
        self.extract_check = tk.Checkbutton(
            self.input_frame,
            text="只提取链接部分",
            variable=self.extract_only,
            font=(self.font_family, self.font_size - 2)
        )
        self.extract_check.pack(anchor="w")
        self.input_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.text_input = scrolledtext.ScrolledText(
            self.input_frame, 
            height=10, 
            font=(self.font_family, self.font_size),
            wrap=tk.WORD
        )
        self.text_input.pack(fill="both", expand=True)
        self.add_right_click_menu(self.text_input, paste=True)
        
        # 按钮区域
        self.button_frame = tk.Frame(root)
        self.button_frame.pack(fill="x", padx=10, pady=5)
        
        button_font = (self.font_family, self.font_size - 2)  # 按钮字体稍小
        
        self.btn_load = tk.Button(
            self.button_frame, 
            text="从文件加载", 
            command=self.load_from_file,
            font=button_font
        )
        self.btn_load.pack(side="left", padx=5)
        
        self.btn_process = tk.Button(
            self.button_frame, 
            text="处理链接", 
            command=self.process_links,
            font=button_font
        )
        self.btn_process.pack(side="left", padx=5)
        
        self.btn_save = tk.Button(
            self.button_frame, 
            text="保存结果", 
            command=self.save_results,
            font=button_font
        )
        self.btn_save.pack(side="left", padx=5)
        
        self.btn_copy = tk.Button(
            self.button_frame, 
            text="复制当前组", 
            command=self.copy_current_batch,
            font=button_font
        )
        self.btn_copy.pack(side="left", padx=5)
        
        self.btn_next = tk.Button(
            self.button_frame, 
            text="下一组", 
            command=self.next_batch,
            font=button_font
        )
        self.btn_next.pack(side="left", padx=5)
        self.btn_next.config(state=tk.DISABLED)
        
        # 分组状态显示
        self.status_var = tk.StringVar()
        self.status_label = tk.Label(
            self.button_frame, 
            textvariable=self.status_var,
            font=(self.font_family, self.font_size - 2)
        )
        self.status_label.pack(side="left", padx=10)
        
        # 批量大小设置
        self.batch_frame = tk.Frame(self.button_frame)
        self.batch_frame.pack(side="left", padx=10)
        
        tk.Label(
            self.batch_frame, 
            text="每批数量:",
            font=(self.font_family, self.font_size - 2)
        ).pack(side="left")
        self.batch_size = tk.IntVar(value=30)
        self.spinbox = tk.Spinbox(
            self.batch_frame, 
            from_=1, 
            to=1000, 
            width=5,
            textvariable=self.batch_size,
            font=(self.font_family, self.font_size - 2)
        )
        self.spinbox.pack(side="left")
        
        # 输出区域
        self.output_frame = tk.LabelFrame(
            root, 
            text="处理结果", 
            padx=5, 
            pady=5,
            font=(self.font_family, self.font_size)
        )
        self.output_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.text_output = scrolledtext.ScrolledText(
            self.output_frame, 
            height=10, 
            font=(self.font_family, self.font_size),
            wrap=tk.WORD
        )
        self.text_output.pack(fill="both", expand=True)
        self.add_right_click_menu(self.text_output, paste=False)

    def add_right_click_menu(self, widget, paste=False):
        menu = tk.Menu(widget, tearoff=0)
        if paste:
            menu.add_command(label="粘贴", command=lambda: widget.event_generate('<<Paste>>'))
        else:
            menu.add_command(label="复制", command=lambda: widget.event_generate('<<Copy>>'))
        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)
        widget.bind("<Button-3>", show_menu)
        
    def load_from_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    links = f.read().splitlines()
                self.text_input.delete("1.0", tk.END)
                self.text_input.insert(tk.END, "\n".join(links))
            except Exception as e:
                messagebox.showerror("错误", f"读取文件失败: {str(e)}")
    
    def extract_url_from_line(self, line):
        """从一行文本中提取URL链接"""
        line = line.strip()
        # 查找"http"或"https"开头的部分
        url_start = line.find("http")
        if url_start == -1:
            return ""  # 如果没有找到http，返回空字符串
            
        # 提取从http开始到行尾或非URL字符前的部分
        url = line[url_start:]
        # 查找URL结束位置(遇到空格、引号、括号等符号时结束)
        for end_char in [' ', '"', "'", ')', ']', '}', '>', '\t', '\n']:
            end_pos = url.find(end_char)
            if end_pos != -1:
                url = url[:end_pos]
        
        # 移除URL末尾可能存在的标点符号
        while url and url[-1] in ['.', ',', ';', ':', '!', '?']:
            url = url[:-1]
            
        return url.strip()

    def process_links(self):
        input_text = self.text_input.get("1.0", tk.END).strip()
        if not input_text:
            messagebox.showwarning("警告", "请输入链接！")
            return
            
        # 检查是否只提取链接
        extract_only = hasattr(self, "extract_only") and self.extract_only.get()
        
        # 处理输入文本，过滤空行和无效链接
        links = []
        for line in input_text.splitlines():
            line = line.strip()
            if not line:
                continue
                
            if extract_only:
                url = self.extract_url_from_line(line)
                if url:  # 只保留非空URL
                    links.append(url)
            else:
                links.append(line)
                
        if not links:
            messagebox.showwarning("警告", "没有有效的链接可处理！")
            return
            
        self.all_batches = split_links(links, self.batch_size.get())
        self.current_batch = 0
        
        # 构建输出文本
        output_text = f"共 {len(links)} 条链接，分成 {len(self.all_batches)} 批，每批最多 {self.batch_size.get()} 条：\n"
        
        # 显示第一组并自动复制
        self.show_current_batch()
        
        # 更新按钮状态
        self.btn_next.config(state=tk.NORMAL if len(self.all_batches) > 1 else tk.DISABLED)
        self.status_var.set(f"当前组: 1/{len(self.all_batches)}")
        
        # 格式化输出
        for i, batch in enumerate(self.all_batches, 1):
            if i > 1:  # 第一组前不加空行
                output_text += "\n"
            output_text += f"第 {i} 批链接({len(batch)}条):\n"
            output_text += "\n".join(batch)
        
        self.text_output.delete("1.0", tk.END)
        self.text_output.insert(tk.END, output_text)
    
    def save_results(self):
        output_text = self.text_output.get("1.0", tk.END).strip()
        if not output_text:
            messagebox.showwarning("警告", "没有可保存的结果！")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(output_text)
                messagebox.showinfo("成功", "结果保存成功！")
            except Exception as e:
                messagebox.showerror("错误", f"保存文件失败: {str(e)}")
    
    def show_current_batch(self):
        if not self.all_batches or self.current_batch >= len(self.all_batches):
            return
            
        batch = self.all_batches[self.current_batch]
        batch_text = "\n".join(batch)
        
        # 自动复制当前组到剪贴板
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(batch_text)
        except:
            pass
            
        return batch_text
    
    def copy_current_batch(self):
        if not self.all_batches:
            messagebox.showwarning("警告", "没有可复制的链接组！")
            return
            
        batch_text = self.show_current_batch()
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(batch_text)
            messagebox.showinfo("成功", "当前组链接已复制到剪贴板！")
        except Exception as e:
            messagebox.showerror("错误", f"复制到剪贴板失败: {str(e)}")
    
    def next_batch(self):
        if self.current_batch + 1 >= len(self.all_batches):
            messagebox.showinfo("提示", "已经是最后一组链接了！")
            return
            
        self.current_batch += 1
        self.show_current_batch()
        self.status_var.set(f"当前组: {self.current_batch + 1}/{len(self.all_batches)}")
        
        # 如果是最后一组，禁用下一组按钮
        if self.current_batch + 1 >= len(self.all_batches):
            self.btn_next.config(state=tk.DISABLED)

def main():
    root = tk.Tk()
    
    # 首先检查授权
    if not check_license():
        messagebox.showerror(
            "错误", 
            "缺少授权！无法使用！请先获取授权！\n"
        )
        sys.exit(1)
    
    # 设置窗口图标和加载字体
    set_window_icon(root)
    current_font = load_font(root)
    
    app = LinkBatchApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()