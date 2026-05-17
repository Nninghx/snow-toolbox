# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import subprocess
from pathlib import Path
from tkinter import *
from tkinter import filedialog, messagebox
from fontTools.ttLib import TTFont

from os.path import dirname, join
sys.path.insert(0, join(dirname(__file__), "..", "Core"))


def generate_dir_tree(path='.', ignore=None, prefix=''):
    if ignore is None:
        ignore = ['.git', '__pycache__', '.DS_Store']
    try:
        items = sorted(os.listdir(path))
    except PermissionError:
        return f"无法访问 {path}：权限不足\n"
    result = ""
    for i, item in enumerate(items):
        if item in ignore:
            continue
        full_path = os.path.join(path, item)
        is_last = i == len(items) - 1
        # 添加当前项到结果
        result += prefix + ('└── ' if is_last else '├── ') + item + '\n'
        # 如果是目录，递归处理
        if os.path.isdir(full_path):
            new_prefix = prefix + ('    ' if is_last else '│   ')
            result += generate_dir_tree(full_path, ignore, new_prefix)
    return result
class DirTreeGUI:
    def __init__(self, root):
        """初始化应用界面和配置"""
        # 首先检查开源协议文档是否存在并验证完整性
        if not self.check_license():
            messagebox.showerror(
                "错误", 
                "缺少授权！无法使用！请先获取授权！\n"
            )
            root.destroy()
            return
        
        self.root = root
        self.root.title("目录树生成器")
        
        # 定义项目根目录和核心模块目录
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        CORE_DIR = PROJECT_ROOT / "Core"
        IMAGE_DIR = PROJECT_ROOT / "Image"
        
        # 设置窗口图标、加载字体并构建UI
        self.set_window_icon()
        self.load_font()
        
        # 设置窗口大小并居中显示
        window_width = 800
        window_height = 600
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 定义字体设置
        self.button_font = (self.font_family, 12)
        self.mono_font = ('Courier New', 10)  # 输出框保持等宽字体
        
        self.create_widgets()

    def check_license(self):
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

    def set_window_icon(self):
        """设置应用程序窗口图标"""
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        IMAGE_DIR = PROJECT_ROOT / "Image"
        
        icon_ico_path = IMAGE_DIR / "icon.ico"
        icon_png_path = IMAGE_DIR / "icon.png"

        # Windows系统设置应用ID
        if os.name == 'nt':
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.DirTreeGenerator")
            except Exception:
                pass

        # 尝试设置ICO图标
        if icon_ico_path.exists():
            try:
                self.root.iconbitmap(default=str(icon_ico_path))
            except Exception:
                try:
                    self.root.iconbitmap(str(icon_ico_path))
                except Exception:
                    pass

        # 尝试设置PNG图标
        if hasattr(self.root, "iconphoto") and icon_png_path.exists():
            try:
                self.icon_image = PhotoImage(file=str(icon_png_path))
                self.root.iconphoto(True, self.icon_image)
            except Exception:
                pass

    def load_font(self):
        """从配置文件加载字体设置"""
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        IMAGE_DIR = PROJECT_ROOT / "Image"
        
        font_path = IMAGE_DIR / "AlibabaPuHuiTi-3-55-RegularL3.ttf"
        
        if not font_path.exists():
            messagebox.showerror("错误", f"找不到字体文件：{font_path}")
            self.root.destroy()
            return
        
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
            print(f"✅ 成功加载自定义字体: {font_path}")
        
        self.font_family = font_name
        self.current_font = (self.font_family, 12)
        self.root.option_add("*Font", self.current_font)
    def create_widgets(self):
        # 目录选择框架
        dir_frame = Frame(self.root)
        dir_frame.pack(pady=10, padx=10, fill=X)
        self.dir_entry = Entry(dir_frame, font=self.current_font)
        self.dir_entry.pack(side=LEFT, expand=True, fill=X)
        browse_btn = Button(dir_frame, text="浏览", command=self.browse_directory, width=8, font=self.button_font)
        browse_btn.pack(side=LEFT, padx=5)
        # 按钮框架
        btn_frame = Frame(self.root)
        btn_frame.pack(pady=10)
        generate_btn = Button(btn_frame, text="生成目录树", command=self.generate_tree, width=15, font=self.button_font)
        generate_btn.pack(side=LEFT, padx=5)
        save_btn = Button(btn_frame, text="保存文本", command=self.save_result, width=10, font=self.button_font)
        save_btn.pack(side=LEFT, padx=5)
        save_mindmap_btn = Button(btn_frame, text="导出思维导图", command=self.save_mindmap, width=12, font=self.button_font)
        save_mindmap_btn.pack(side=LEFT, padx=5)
        clear_btn = Button(btn_frame, text="清空", command=self.clear_output, width=10, font=self.button_font)
        clear_btn.pack(side=LEFT, padx=5)
        license_btn = Button(btn_frame, text="项目开源协议", command=self.show_license, width=10, font=self.button_font)
        license_btn.pack(side=LEFT, padx=5)
        # 输出框架
        output_frame = Frame(self.root)
        output_frame.pack(pady=10, padx=10, fill=BOTH, expand=True)
        # 创建带滚动条的文本框
        output_scrollbar = Scrollbar(output_frame)
        output_scrollbar.pack(side=RIGHT, fill=Y)
        self.output_text = Text(output_frame, wrap=NONE, yscrollcommand=output_scrollbar.set, font=self.mono_font)
        self.output_text.pack(side=LEFT, fill=BOTH, expand=True)
        output_scrollbar.config(command=self.output_text.yview)
    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_entry.delete(0, END)
            self.dir_entry.insert(0, directory)
    def generate_tree(self):
        directory = self.dir_entry.get()
        if not os.path.isdir(directory):
            self.output_text.delete('1.0', END)
            self.output_text.insert(END, "请输入有效的目录路径")
            return
        self.output_text.delete('1.0', END)
        ignore_list = ['.git', '__pycache__', '.DS_Store']
        result = generate_dir_tree(directory, ignore=ignore_list)
        self.output_text.insert(END, f"目录结构（忽略: {', '.join(ignore_list)}）:\n\n")
        self.output_text.insert(END, result)
    def save_result(self):
        result = self.output_text.get('1.0', END)
        if not result.strip():
            messagebox.showwarning("警告", "没有可保存的内容")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", ".txt"), ("所有文件", ".*")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(result)
                messagebox.showinfo("成功", "结果已保存")
            except Exception as e:
                messagebox.showerror("错误", f"保存文件时出错: {str(e)}")

    def save_mindmap(self):
        directory = self.dir_entry.get()
        if not os.path.isdir(directory):
            messagebox.showwarning("警告", "请先选择有效目录并生成目录树")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown文件", ".md"), ("所有文件", ".*")]
        )
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("# 目录结构思维导图\n\n")
                f.write("``markmap\n")
                f.write("{\n")
                f.write('  "text": "' + os.path.basename(directory) + '",\n')
                f.write('  "children": [\n')
                self._write_mindmap_items(directory, f, 1)
                f.write("  ]\n")
                f.write("}\n")
                f.write("```\n")
            messagebox.showinfo("成功", "思维导图文件已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存思维导图时出错: {str(e)}")

    def _write_mindmap_items(self, path, file, depth):
        items = sorted(os.listdir(path))
        for i, item in enumerate(items):
            full_path = os.path.join(path, item)
            is_last = i == len(items) - 1
            
            indent = "    " * depth
            file.write(indent + '{\n')
            file.write(indent + '  "text": "' + item + '",\n')
            
            if os.path.isdir(full_path):
                file.write(indent + '  "children": [\n')
                self._write_mindmap_items(full_path, file, depth + 1)
                file.write(indent + '  ]\n')
            
            file.write(indent + '}' + ('' if is_last else ',') + '\n')
    def clear_output(self):
        self.output_text.delete('1.0', END)
        self.dir_entry.delete(0, END)

    def show_license(self):
        """显示开源协议文档"""
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        CORE_DIR = PROJECT_ROOT / "Core"
        license_path = CORE_DIR / "LICENSE.txt"
        
        if not license_path.exists():
            messagebox.showerror("错误", f"找不到开源协议文件：{license_path}")
            return
        
        try:
            with open(license_path, 'r', encoding='utf-8') as f:
                license_content = f.read()
            
            # 创建只读窗口显示协议内容
            license_window = Toplevel(self.root)
            license_window.title("Apache-2.0 License")
            
            # 设置窗口大小
            window_width = 700
            window_height = 500
            screen_width = license_window.winfo_screenwidth()
            screen_height = license_window.winfo_screenheight()
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            license_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
            
            # 创建文本框和滚动条
            text_frame = Frame(license_window)
            text_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
            
            scrollbar = Scrollbar(text_frame)
            scrollbar.pack(side=RIGHT, fill=Y)
            
            text_widget = Text(text_frame, wrap=WORD, yscrollcommand=scrollbar.set, 
                             font=self.current_font, state=NORMAL)
            text_widget.pack(side=LEFT, fill=BOTH, expand=True)
            scrollbar.config(command=text_widget.yview)
            
            # 插入协议内容并设置为只读
            text_widget.insert('1.0', license_content)
            text_widget.config(state=DISABLED)
            
        except Exception as e:
            messagebox.showerror("错误", f"读取开源协议时出错: {str(e)}")

if __name__ == '__main__':
    root = Tk()
    app = DirTreeGUI(root)
    root.mainloop()