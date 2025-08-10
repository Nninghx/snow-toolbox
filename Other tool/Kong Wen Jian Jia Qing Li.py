import os
import json
import tkinter as tk
from tkinter import font, filedialog, messagebox

class EmptyFolderCleaner:
    def __init__(self, root):
        self.root = root
        try:
            with open('Core/ziti.json', 'r', encoding='utf-8') as f:
                font_config = json.load(f)
            self.custom_font = font.Font(family=font_config['family'], size=10)
        except (FileNotFoundError, tk.TclError):
            self.custom_font = font.Font(family="Arial", size=10)
        self.setup_ui()
        
    def setup_ui(self):
        self.root.title("空文件夹清理工具")
        self.root.geometry("400x200")
        
        tk.Label(self.root, text="选择要清理的目录:", font=self.custom_font).pack(pady=10)
        
        self.path_var = tk.StringVar()
        tk.Entry(self.root, textvariable=self.path_var, width=40, font=self.custom_font).pack()
        
        tk.Button(self.root, text="浏览", command=self.browse_directory, font=self.custom_font).pack(pady=5)
        tk.Button(self.root, text="清理空文件夹", command=self.clean_empty_folders, font=self.custom_font).pack(pady=10)
        
        # 添加帮助按钮
        tk.Button(self.root, text="帮助", command=self.show_help, font=self.custom_font).pack(pady=5)
        
    def show_help(self):
        help_text = """空文件夹清理工具使用说明:
        
1. 点击"浏览"按钮选择要清理的目录
2. 点击"清理空文件夹"按钮开始清理
3. 程序会递归删除所选目录下的所有空文件夹
4. 清理完成后会显示删除的空文件夹数量
提示:
- 作者:叁垣伍瑞肆凶廿捌宿宿
- 联系方式:https://space.bilibili.com/556216088
- 版权:Apache-2.0 License
"""
        messagebox.showinfo("帮助", help_text)
        
    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.path_var.set(directory)
            
    def clean_empty_folders(self):
        target_dir = self.path_var.get()
        if not target_dir:
            messagebox.showerror("错误", "请先选择目录")
            return
            
        try:
            count = self._remove_empty_folders(target_dir)
            messagebox.showinfo("完成", f"已删除 {count} 个空文件夹")
        except Exception as e:
            messagebox.showerror("错误", str(e))
            
    def _remove_empty_folders(self, folder):
        count = 0
        for root, dirs, files in os.walk(folder, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        count += 1
                except Exception:
                    continue
        return count

if __name__ == "__main__":
    root = tk.Tk()
    # 设置窗口图标
    try:
        root.iconbitmap('Image/icon.ico')
    except Exception as e:
        print(f"图标加载失败: {str(e)}")
    app = EmptyFolderCleaner(root)
    root.mainloop()