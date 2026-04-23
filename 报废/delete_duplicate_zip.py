import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

def delete_duplicate_zips(folder_path, log_text):
    """
    删除文件夹中与文件名相同的压缩包文件。
    :param folder_path: 文件夹路径
    :param log_text: 日志显示文本框
    """
    # 获取文件夹中的所有文件
    files = os.listdir(folder_path)
    
    # 记录删除的文件数量
    deleted_count = 0
    
    # 遍历文件
    for file in files:
        file_path = os.path.join(folder_path, file)
        
        # 检查是否为文件（非文件夹）
        if os.path.isfile(file_path):
            # 获取文件名（不带扩展名）和扩展名
            file_name, file_ext = os.path.splitext(file)
            
            # 检查是否存在同名的压缩包文件（如 .zip, .rar, .7z 等）
            for ext in ['.zip', '.rar', '.7z']:
                zip_file = file_name + ext
                zip_path = os.path.join(folder_path, zip_file)
                
                # 如果压缩包文件存在且与当前文件同名，则删除压缩包
                if os.path.exists(zip_path) and os.path.isfile(zip_path):
                    try:
                        os.remove(zip_path)
                        log_text.insert(tk.END, f"已删除: {zip_path}\n")
                        log_text.see(tk.END)
                        deleted_count += 1
                    except Exception as e:
                        log_text.insert(tk.END, f"删除失败 {zip_path}: {str(e)}\n")
                        log_text.see(tk.END)
    
    log_text.insert(tk.END, f"\n处理完成！共删除 {deleted_count} 个重复压缩包。\n")
    log_text.see(tk.END)
    messagebox.showinfo("完成", f"处理完成！共删除 {deleted_count} 个重复压缩包。")

class ZipCleanerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("重复压缩包清理工具")
        self.root.geometry("600x400")
        
        # 文件夹路径变量
        self.folder_path = tk.StringVar()
        
        self.create_widgets()
    
    def create_widgets(self):
        # 标题
        title_label = tk.Label(self.root, text="重复压缩包清理工具", font=("Arial", 16))
        title_label.pack(pady=10)
        
        # 文件夹选择框架
        folder_frame = tk.Frame(self.root)
        folder_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(folder_frame, text="选择文件夹:").pack(side=tk.LEFT)
        tk.Entry(folder_frame, textvariable=self.folder_path, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        tk.Button(folder_frame, text="浏览", command=self.select_folder).pack(side=tk.RIGHT)
        
        # 执行按钮
        self.execute_button = tk.Button(self.root, text="删除重复压缩包", command=self.execute_delete, state=tk.DISABLED, bg="#4CAF50", fg="white")
        self.execute_button.pack(pady=10)
        
        # 日志显示区域
        log_frame = tk.Frame(self.root)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        tk.Label(log_frame, text="处理日志:").pack(anchor=tk.W)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 说明文本
        instruction = """
使用说明:
1. 点击"浏览"选择需要清理的文件夹
2. 点击"删除重复压缩包"开始处理
3. 程序会删除与文件同名的.zip/.rar/.7z压缩包文件
4. 处理日志会显示在下方区域
        """
        tk.Label(self.root, text=instruction, justify=tk.LEFT).pack(pady=10)
    
    def select_folder(self):
        """
        打开文件选择对话框，选择文件夹路径。
        """
        folder_selected = filedialog.askdirectory(title="请选择文件夹")
        if folder_selected:
            self.folder_path.set(folder_selected)
            self.execute_button.config(state=tk.NORMAL)
    
    def execute_delete(self):
        """
        执行删除操作
        """
        folder = self.folder_path.get()
        if not folder or not os.path.exists(folder):
            messagebox.showerror("错误", "请选择有效的文件夹路径")
            return
        
        # 确认对话框
        if messagebox.askyesno("确认", f"确定要删除文件夹 '{folder}' 中的重复压缩包吗？"):
            # 清空日志
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, f"开始处理文件夹: {folder}\n\n")
            
            # 执行删除操作
            delete_duplicate_zips(folder, self.log_text)

def main():
    root = tk.Tk()
    app = ZipCleanerApp(root)
    root.mainloop()

# 示例用法
if __name__ == "__main__":
    main()

