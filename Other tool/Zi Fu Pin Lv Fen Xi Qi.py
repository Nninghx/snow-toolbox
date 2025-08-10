import re
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font
from collections import Counter

class CharacterFrequencyAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("字符频率分析器")
        # 设置窗口图标
        try:
            self.root.iconbitmap('Image/icon.ico')
        except Exception as e:
            print(f"图标加载失败: {str(e)}")
        
        # 从ziti.json读取字体设置
        try:
            with open("Core/ziti.json", "r", encoding="utf-8") as f:
                font_data = json.load(f)
                font_family = font_data.get("family", "Microsoft YaHei")
        except Exception as e:
            font_family = "Microsoft YaHei"
        
        # 设置字体
        self.custom_font = font.Font(family=font_family, size=12)
        
        # 配置ttk样式
        self.style = ttk.Style()
        self.style.configure(".", font=(font_family, 12))
        
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
        
        self.help_button = ttk.Button(
            self.button_frame,
            text="帮助",
            command=self.show_help
        )
        self.help_button.pack(side=tk.LEFT, padx=5)
        
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
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """字符频率分析器使用说明：

1. 在文本框中输入或通过"加载文件"按钮导入文本
2. 勾选要统计的字符类型(汉字/字母/数字)
3. 点击"分析频率"按钮查看统计结果
4. 结果会按出现频率排序显示在对应标签页中
5. 可以通过滚动条查看完整结果"""
        
        messagebox.showinfo("帮助", help_text)
    
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
    root = tk.Tk()
    app = CharacterFrequencyAnalyzer(root)
    root.mainloop()