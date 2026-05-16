import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk, font
import json
import os
from pathlib import Path

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
        self.root = root
        self.root.title("带货链接分批处理工具")
        self.root.geometry("650x550")
        
        # 加载字体配置
        try:
            from pathlib import Path
            font_path = Path(__file__).parent.parent / "Core" / "ziti.json"
            if not font_path.exists():
                raise FileNotFoundError(f"字体配置文件 {font_path} 不存在")
                
            with open(font_path, "r", encoding="utf-8") as f:
                font_config = json.load(f)
                self.font_family = font_config.get("family", "Microsoft YaHei")
                
            # 创建样式对象统一设置字体
            self.style = ttk.Style()
            self.style.configure('.', font=(self.font_family, 10))
            
            # 测试字体是否可用
            test_font = font.Font(family=self.font_family, size=10)
            if test_font.actual()["family"] != self.font_family:
                raise ValueError(f"字体 '{self.font_family}' 不可用")
                
            self.font_size = 12  # 设置合适的默认字号
            print(f"成功加载字体: {self.font_family}")
            
        except Exception as e:
            print(f"字体加载错误: {str(e)}")
            self.font_family = "Microsoft YaHei"
            self.font_size = 12
            self.style = ttk.Style()
            self.style.configure('.', font=(self.font_family, 10))
            messagebox.showwarning("字体警告", 
                f"无法加载配置字体: {str(e)}\n将使用默认字体: {self.font_family}")
            
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
    # 设置窗口图标
    try:
        root.iconbitmap('Image/icon.ico')
    except Exception as e:
        print(f"图标加载失败: {str(e)}")
    app = LinkBatchApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()