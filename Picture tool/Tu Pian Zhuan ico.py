# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import os
import json

from os.path import dirname, join
sys.path.insert(0, join(dirname(__file__), "..", "Core"))
from BangZhu import get_help_system

class IconConverterApp:
    def __init__(self, master):
        self.master = master
        master.title("图片转图标")
        
        # 读取字体设置
        try:
            with open(join(dirname(__file__), "..", "Core", "ziti.json"), "r", encoding="utf-8") as f:
                font_data = json.load(f)
                font_family = font_data.get("family", "Microsoft YaHei")
                # 应用字体设置
                self.default_font = (font_family, 10)
        except Exception as e:
            print(f"读取字体设置失败: {e}")
            self.default_font = ("Microsoft YaHei", 10)
        
        # 默认尺寸
        self.default_sizes = [16, 32, 48, 64, 128]
        
        # 创建界面组件
        self.create_widgets()
    
    def create_widgets(self):
        # 文件选择部分
        tk.Label(self.master, text="选择源图片:", font=self.default_font).grid(row=0, column=0, sticky="w")
        self.file_entry = tk.Entry(self.master, width=40, font=self.default_font)
        self.file_entry.grid(row=0, column=1)
        tk.Button(self.master, text="浏览...", command=self.browse_file, font=self.default_font).grid(row=0, column=2)
        
        # 图标尺寸选择
        tk.Label(self.master, text="选择图标尺寸:", font=self.default_font).grid(row=1, column=0, sticky="w")
        self.size_frame = tk.Frame(self.master)
        self.size_frame.grid(row=1, column=1, columnspan=2, sticky="w")
        
        # 默认尺寸单选按钮
        self.size_var = tk.IntVar(value=self.default_sizes[0])  # 默认选中第一个尺寸
        for i, size in enumerate(self.default_sizes):
            rb = tk.Radiobutton(self.size_frame, text=f"{size}x{size}", 
                              variable=self.size_var, value=size, font=self.default_font)
            rb.grid(row=0, column=i, sticky="w")
        
        # 自定义尺寸
        custom_frame = tk.Frame(self.master)
        custom_frame.grid(row=2, column=0, columnspan=3, sticky="we", padx=5, pady=5)
        
        tk.Label(custom_frame, text="自定义尺寸:", font=self.default_font).pack(side="left")
        self.custom_entry = tk.Entry(custom_frame, width=15, font=self.default_font)
        self.custom_entry.pack(side="left", padx=5)
        self.custom_entry.insert(0, "宽x高")
        self.custom_entry.bind("<FocusIn>", lambda e: self.clear_placeholder())
        
        tk.Label(custom_frame, text="(16-256像素)", font=self.default_font).pack(side="left")
        tk.Label(custom_frame, text="示例: 256x256", fg="gray", font=self.default_font).pack(side="left", padx=5)
        
        # 按钮区域
        button_frame = tk.Frame(self.master)
        button_frame.grid(row=3, column=0, columnspan=3, pady=10, sticky="e")
        
        # 帮助按钮
        tk.Button(button_frame, text="使用帮助", command=self.show_help, width=8, font=self.default_font).pack(side="right", padx=5)
        
        # 转换按钮
        tk.Button(button_frame, text="转换为ICO", command=self.convert_to_ico, width=12, font=self.default_font).pack(side="right")
    
    def clear_placeholder(self):
        if self.custom_entry.get() == "宽x高":
            self.custom_entry.delete(0, tk.END)
    
    def browse_file(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("图片文件", "*.png;*.jpg;*.jpeg;*.bmp")]
        )
        if filepath:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, filepath)
    
    def show_help(self):
        help_system = get_help_system()
        help_system.show_help("图片转图标")
    
    def convert_to_ico(self):
        input_path = self.file_entry.get()
        if not input_path:
            messagebox.showerror("错误", "请选择源图片文件")
            return
        
        try:
            # 获取选中的尺寸
            size = self.size_var.get()
            
            # 检查自定义尺寸
            custom_size = self.custom_entry.get()
            if custom_size and custom_size != "宽x高":
                try:
                    width, height = map(int, custom_size.lower().split("x"))
                    if not (16 <= width <= 256 and 16 <= height <= 256):
                        messagebox.showerror("错误", "尺寸必须在16x16到256x256之间")
                        return
                    size = (width, height)
                except:
                    messagebox.showerror("错误", "请输入有效的尺寸格式，如: 64x64")
                    return
            else:
                size = (size, size)  # 使用单选按钮选择的尺寸
            
            # 选择输出路径
            output_path = filedialog.asksaveasfilename(
                defaultextension=".ico",
                filetypes=[("ICO文件", "*.ico")]
            )
            if not output_path:
                return
            
            # 转换图片
            image = Image.open(input_path)
            resized_img = image.resize(size, Image.LANCZOS)
            
            # 保存ICO文件
            resized_img.save(output_path)
            messagebox.showinfo("成功", f"ICO文件已保存到:\n{output_path}")
            
        except Exception as e:
            messagebox.showerror("错误", f"转换失败: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    # 设置窗口图标
    try:
        root.iconbitmap('Image/icon.ico')
    except Exception as e:
        print(f"图标加载失败: {str(e)}")
    app = IconConverterApp(root)
    root.mainloop()
