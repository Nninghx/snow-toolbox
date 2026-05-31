import os
import sys
import subprocess
import re
import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox, font
from fontTools.ttLib import TTFont
from collections import Counter


def set_window_icon(root):
    """设置应用程序窗口图标"""
    # 假设当前文件在 "Other tool" 目录下，项目根目录是其父目录
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    IMAGE_DIR = PROJECT_ROOT / "Image"
    
    icon_ico_path = IMAGE_DIR / "icon.ico"
    icon_png_path = IMAGE_DIR / "icon.png"

    # Windows系统设置应用ID
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.CharacterFrequencyAnalyzer")
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
            # 保存引用防止垃圾回收
            root._icon_image = icon_image
        except Exception:
            pass


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


def load_font():
    """从配置文件加载字体设置"""
    # 定义项目根目录和图片目录
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    IMAGE_DIR = PROJECT_ROOT / "Image"
    
    font_path = IMAGE_DIR / "AlibabaPuHuiTi-3-55-RegularL3.ttf"
    
    if not font_path.exists():
        # 如果找不到自定义字体，返回 None，使用默认字体
        print(f"警告: 找不到字体文件：{font_path}，将使用默认字体。")
        return None
    
    try:
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
            # AddFontResourceW 需要宽字符字符串
            added = GDI32.AddFontResourceW(str(font_path))
            if added:
                print(f"成功加载自定义字体: {font_path}")
            else:
                print(f"警告: AddFontResourceW 返回失败，可能字体已加载或路径有问题。")
        
        return (font_name, 12)
    except Exception as e:
        print(f"字体加载错误: {e}")
        return None


class CharacterFrequencyAnalyzer:
    def __init__(self, root, custom_font_tuple=None):
        self.root = root
        self.root.title("字符频率分析")
        
        # 设置窗口图标
        set_window_icon(root)
        
        # 设置字体
        if custom_font_tuple:
            self.custom_font = font.Font(family=custom_font_tuple[0], size=custom_font_tuple[1])
        else:
            # 默认字体
            self.custom_font = font.Font(family="Microsoft YaHei", size=12)
        
        # 配置ttk样式
        self.style = ttk.Style()
        self.style.configure(".", font=self.custom_font)
        
        # 创建界面组件
        self.create_widgets()
    
    def create_widgets(self):
        # 文本输入框
        self.text_label = ttk.Label(self.root, text="输入文本或选择文件:")
        self.text_label.pack(pady=5)
        
        self.text_input = tk.Text(self.root, height=10, width=50, font=self.custom_font)
        self.text_input.pack(pady=5)
        
        # 统计选项区域
        self.option_frame = ttk.Frame(self.root)
        self.option_frame.pack(pady=5)
        
        self.hanzi_var = tk.BooleanVar(value=True)
        self.hanzi_check = ttk.Checkbutton(
            self.option_frame,
            text="统计汉字",
            variable=self.hanzi_var
        )
        self.hanzi_check.pack(side=tk.LEFT, padx=5)
        
        self.letter_var = tk.BooleanVar(value=True)
        self.letter_check = ttk.Checkbutton(
            self.option_frame,
            text="统计字母",
            variable=self.letter_var
        )
        self.letter_check.pack(side=tk.LEFT, padx=5)
        
        self.digit_var = tk.BooleanVar(value=True)
        self.digit_check = ttk.Checkbutton(
            self.option_frame,
            text="统计数字",
            variable=self.digit_var
        )
        self.digit_check.pack(side=tk.LEFT, padx=5)
        
        # 按钮区域
        self.button_frame = ttk.Frame(self.root)
        self.button_frame.pack(pady=5)
        
        self.analyze_button = ttk.Button(
            self.button_frame, 
            text="分析频率", 
            command=self.analyze_frequency
        )
        self.analyze_button.pack(side=tk.LEFT, padx=5)
        
        self.load_button = ttk.Button(
            self.button_frame,
            text="加载文件",
            command=self.load_file
        )
        self.load_button.pack(side=tk.LEFT, padx=5)
        
        self.export_button = ttk.Button(
            self.button_frame,
            text="导出表格",
            command=self.export_data
        )
        self.export_button.pack(side=tk.LEFT, padx=5)
        
        # 结果显示区域
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(pady=5, fill=tk.BOTH, expand=True)
        
        # 汉字频率标签页
        self.hanzi_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.hanzi_frame, text="汉字频率")
        
        self.hanzi_tree = ttk.Treeview(
            self.hanzi_frame, 
            columns=("character", "count"), 
            show="headings",
            style="Custom.Treeview"
        )
        self.hanzi_tree.heading("character", text="汉字")
        self.hanzi_tree.heading("count", text="出现次数")
        self.hanzi_tree.pack(pady=5, fill=tk.BOTH, expand=True)
        
        # 字母频率标签页
        self.letter_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.letter_frame, text="字母频率")
        
        self.letter_tree = ttk.Treeview(
            self.letter_frame, 
            columns=("character", "count"), 
            show="headings",
            style="Custom.Treeview"
        )
        self.letter_tree.heading("character", text="字母")
        self.letter_tree.heading("count", text="出现次数")
        self.letter_tree.pack(pady=5, fill=tk.BOTH, expand=True)
        
        # 数字频率标签页
        self.digit_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.digit_frame, text="数字频率")
        
        self.digit_tree = ttk.Treeview(
            self.digit_frame, 
            columns=("character", "count"), 
            show="headings",
            style="Custom.Treeview"
        )
        self.digit_tree.heading("character", text="数字")
        self.digit_tree.heading("count", text="出现次数")
        self.digit_tree.pack(pady=5, fill=tk.BOTH, expand=True)
        
        # 为每个Treeview添加滚动条
        for tree in [self.hanzi_tree, self.letter_tree, self.digit_tree]:
            scrollbar = ttk.Scrollbar(
                tree.master,
                orient="vertical",
                command=tree.yview
            )
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            tree.configure(yscrollcommand=scrollbar.set)
    
    def analyze_frequency(self):
        """分析文本中的字符频率"""
        text = self.text_input.get("1.0", tk.END)
        
        # 清空现有结果
        for tree in [self.hanzi_tree, self.letter_tree, self.digit_tree]:
            for item in tree.get_children():
                tree.delete(item)
        
        # 根据用户选择进行统计
        if self.hanzi_var.get():
            # 分析汉字频率
            hanzi_pattern = re.compile(r'[\u4e00-\u9fff]')
            hanzi_list = hanzi_pattern.findall(text)
            hanzi_freq = Counter(hanzi_list)
            sorted_hanzi = sorted(hanzi_freq.items(), key=lambda x: x[1], reverse=True)
            
            # 显示结果
            for hanzi, count in sorted_hanzi:
                self.hanzi_tree.insert("", tk.END, values=(hanzi, count))
        
        if self.letter_var.get():
            # 分析字母频率
            letter_pattern = re.compile(r'[a-zA-Z]')
            letter_list = letter_pattern.findall(text)
            letter_freq = Counter(letter_list)
            sorted_letter = sorted(letter_freq.items(), key=lambda x: x[1], reverse=True)
            
            # 显示结果
            for letter, count in sorted_letter:
                self.letter_tree.insert("", tk.END, values=(letter, count))
        
        if self.digit_var.get():
            # 分析数字频率
            digit_pattern = re.compile(r'[0-9]')
            digit_list = digit_pattern.findall(text)
            digit_freq = Counter(digit_list)
            sorted_digit = sorted(digit_freq.items(), key=lambda x: x[1], reverse=True)
            
            # 显示结果
            for digit, count in sorted_digit:
                self.digit_tree.insert("", tk.END, values=(digit, count))
    
    def load_file(self):
        """从文件加载文本"""
        file_path = filedialog.askopenfilename(
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.text_input.delete("1.0", tk.END)
                self.text_input.insert("1.0", content)
    
    def export_data(self):
        """导出当前显示的频率数据为CSV文件"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        
        if not file_path:  # 用户取消选择
            return
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                # 获取当前选中的标签页
                current_tab = self.notebook.index(self.notebook.select())
                
                if current_tab == 0:  # 汉字标签页
                    tree = self.hanzi_tree
                    header = "汉字,出现次数\n"
                elif current_tab == 1:  # 字母标签页
                    tree = self.letter_tree
                    header = "字母,出现次数\n"
                elif current_tab == 2:  # 数字标签页
                    tree = self.digit_tree
                    header = "数字,出现次数\n"
                else:
                    return
                
                f.write(header)
                for item in tree.get_children():
                    values = tree.item(item, "values")
                    f.write(f"{values[0]},{values[1]}\n")
            
            messagebox.showinfo("导出成功", f"数据已成功导出到:\n{file_path}")
        except Exception as e:
         messagebox.showerror("导出失败", f"导出数据时出错:\n{str(e)}")

if __name__ == "__main__":
    # 创建主窗口
    root = tk.Tk()

    # 首先检查开源协议文档是否存在并验证完整性
    if not check_license():
        messagebox.showerror(
            "错误", 
            "缺少授权！无法使用！请先获取授权！\n"
        )
        root.destroy()
        sys.exit(1)

    # 加载并注册字体
    custom_font_tuple = load_font()
    if custom_font_tuple:
        try:
            # 尝试全局设置字体，作为后备
            root.option_add('*Font', custom_font_tuple)
        except Exception:
            pass

    app = CharacterFrequencyAnalyzer(root, custom_font_tuple)
    root.mainloop()