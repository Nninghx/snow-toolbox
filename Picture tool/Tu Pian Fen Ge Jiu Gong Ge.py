# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

from PIL import Image
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from os.path import dirname, join
sys.path.insert(0, join(dirname(dirname(__file__)), "Tool module"))
from BangZhu import get_help_system

class ImageSplitterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图片九宫格分割工具")
        
        # 输入图片
        tk.Label(root, text="输入图片:").grid(row=0, column=0, padx=5, pady=5)
        self.input_entry = tk.Entry(root, width=40)
        self.input_entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Button(root, text="浏览...", command=self.browse_input).grid(row=0, column=2, padx=5, pady=5)
        
        # 输出目录
        tk.Label(root, text="输出目录:").grid(row=1, column=0, padx=5, pady=5)
        self.output_entry = tk.Entry(root, width=40)
        self.output_entry.grid(row=1, column=1, padx=5, pady=5)
        tk.Button(root, text="浏览...", command=self.browse_output).grid(row=1, column=2, padx=5, pady=5)
        
        # 进度条
        self.progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
        self.progress.grid(row=2, column=0, columnspan=3, padx=5, pady=10)
        
        # 分割按钮和帮助按钮
        tk.Button(root, text="开始分割", command=self.start_split).grid(row=3, column=1, pady=10)
        tk.Button(root, text="帮助", command=self.show_help).grid(row=3, column=0, pady=10, padx=5)
        tk.Button(root, text="更新日志", command=self.show_changelog).grid(row=3, column=2, pady=10, padx=5)
    
    def show_help(self):
        help_system = get_help_system()
        help_system.show_help("图片九宫格分割")
        
    def show_changelog(self):
        changelog = """图片九宫格分割工具 更新日志
版本 Alpha1.0.0 (2025-5-18)
- 1.初始发布版本
- 2.实现基本图片分割功能
版本 Alpha1.0.1 (2025-6-7)
- 1.新增更新日志功能
- 2.对帮助文档调用进行拆分，简化代码长度
- 3.禁止生成 .pyc 文件

"""
        messagebox.showinfo("更新日志", changelog)
    
    def browse_input(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif")]
        )
        if filepath:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, filepath)
    
    def browse_output(self):
        dirpath = filedialog.askdirectory()
        if dirpath:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, dirpath)
    
    def start_split(self):
        input_path = self.input_entry.get()
        output_dir = self.output_entry.get()
        
        if not input_path or not output_dir:
            messagebox.showerror("错误", "请选择输入图片和输出目录")
            return
        
        try:
            self.progress["value"] = 0
            self.root.update()
            
            # 获取输入文件名(不带扩展名)
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            # 创建子文件夹路径
            save_dir = os.path.join(output_dir, base_name + "_split")
            
            # 确保输出目录存在
            os.makedirs(save_dir, exist_ok=True)
            
            # 打开图片
            with Image.open(input_path) as img:
                width, height = img.size
                
                # 计算每个小块的尺寸
                tile_width = width // 3
                tile_height = height // 3
                
                # 分割图片
                total = 9
                for i in range(3):
                    for j in range(3):
                        left = j * tile_width
                        upper = i * tile_height
                        right = left + tile_width
                        lower = upper + tile_height
                        
                        # 裁剪图片
                        tile = img.crop((left, upper, right, lower))
                        
                        # 保存小块
                        tile.save(os.path.join(save_dir, f'{base_name}_tile_{i}_{j}.png'))
                        
                        # 更新进度
                        self.progress["value"] = ((i * 3) + j + 1) / total * 100
                        self.root.update()
            
            messagebox.showinfo("完成", f"图片已成功分割为9份，保存在 {save_dir}")
            self.progress["value"] = 0
        
        except Exception as e:
            messagebox.showerror("错误", f"处理图片时出错: {e}")
            self.progress["value"] = 0

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageSplitterApp(root)
    root.mainloop()
