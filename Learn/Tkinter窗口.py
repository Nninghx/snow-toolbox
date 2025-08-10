import tkinter as tk

class Application:
    """
    Tkinter应用程序主类
    封装了GUI界面的主要功能和组件
    """
    def __init__(self, root):
        self.root = root  # 保存根窗口引用
        # 设置标题	title("标题")
        self.root.title("Tkinter 功能演示")  
        # 设置窗口大小	geometry("宽*高")
        self.root.geometry("400x300")  
        # 参数:设置是否可调整大小	resizable(True/False, True/False)
        self.root.resizable(False, True)  
        # 设置窗口图标(请替换为实际图标路径)
        # 参数: .ico格式图标文件路径
        self.root.iconbitmap("path/to/icon.ico")


if __name__ == "__main__":
    root = tk.Tk()
    app = Application(root)
    root.mainloop()
