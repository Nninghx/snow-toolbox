import tkinter as tk
from tkinter import messagebox
import re


def extract_items_id():
    """从URL中提取itemsId参数"""
    url = url_entry.get().strip()
    
    if not url:
        messagebox.showwarning("警告", "请输入URL")
        return
    
    # 尝试从URL的hash部分或查询参数中提取itemsId
    # 匹配 #itemsId=数字 或 &itemsId=数字 或 ?itemsId=数字
    match = re.search(r'[#&?]itemsId=(\d+)', url)
    
    if match:
        items_id = match.group(1)
        result_label.config(text=f"提取结果: {items_id}", fg="green")
        # 复制到剪贴板
        root.clipboard_clear()
        root.clipboard_append(items_id)
        messagebox.showinfo("成功", f"已提取 itemsId: {items_id}\n\n已自动复制到剪贴板")
    else:
        result_label.config(text="未找到 itemsId 参数", fg="red")
        messagebox.showerror("错误", "未在URL中找到 itemsId 参数")


def clear_input():
    """清空输入框"""
    url_entry.delete(0, tk.END)
    result_label.config(text="", fg="black")


def paste_from_clipboard(event=None):
    """从剪贴板粘贴内容到输入框"""
    try:
        clipboard_text = root.clipboard_get()
        if clipboard_text:
            # 如果当前有选中文本，先删除
            try:
                url_entry.delete(tk.SEL_FIRST, tk.SEL_LAST)
            except tk.TclError:
                pass
            # 在光标位置插入剪贴板内容
            url_entry.insert(tk.INSERT, clipboard_text)
    except tk.TclError:
        pass  # 剪贴板为空或不是文本格式


def show_context_menu(event):
    """显示右键菜单"""
    context_menu.post(event.x_root, event.y_root)


# 创建主窗口
root = tk.Tk()
root.title("B站商品ID提取工具")
root.geometry("600x300")
root.resizable(False, False)

# 设置窗口居中
root.update_idletasks()
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width - 600) // 2
y = (screen_height - 300) // 2
root.geometry(f"+{x}+{y}")

# 标题
title_label = tk.Label(root, text="B站商品ID提取工具", font=("Microsoft YaHei", 16, "bold"))
title_label.pack(pady=20)

# URL输入框
input_frame = tk.Frame(root)
input_frame.pack(pady=10, padx=20, fill=tk.X)

url_label = tk.Label(input_frame, text="URL:", font=("Microsoft YaHei", 10))
url_label.pack(anchor=tk.W)

url_entry = tk.Entry(input_frame, font=("Microsoft YaHei", 10), width=60)
url_entry.pack(fill=tk.X, pady=5)

# 为输入框添加右键菜单
context_menu = tk.Menu(url_entry, tearoff=0)
context_menu.add_command(label="粘贴", command=paste_from_clipboard)
url_entry.bind("<Button-3>", show_context_menu)

# 按钮区域
button_frame = tk.Frame(root)
button_frame.pack(pady=15)

extract_btn = tk.Button(button_frame, text="提取ID", command=extract_items_id, 
                        font=("Microsoft YaHei", 10), bg="#4CAF50", fg="white",
                        width=12, height=2)
extract_btn.pack(side=tk.LEFT, padx=10)

clear_btn = tk.Button(button_frame, text="清空", command=clear_input,
                      font=("Microsoft YaHei", 10), bg="#f44336", fg="white",
                      width=12, height=2)
clear_btn.pack(side=tk.LEFT, padx=10)

# 结果显示
result_label = tk.Label(root, text="", font=("Microsoft YaHei", 12))
result_label.pack(pady=10)

# 提示信息
tip_label = tk.Label(root, text="提示: 提取结果会自动复制到剪贴板", 
                     font=("Microsoft YaHei", 9), fg="gray")
tip_label.pack(pady=5)

# 绑定回车键
root.bind('<Return>', lambda event: extract_items_id())

# 启动主循环
root.mainloop()
