# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os

class PathUtils:
    """统一路径处理工具类"""
    @staticmethod
    def get_tool_path(category, file_name):
        """根据分类获取工具路径"""
        base_dir = os.path.dirname(__file__)
        category_map = {
            'PDF工具': 'PDF tool',
            '图片工具': 'Picture tool',
            '音频工具': 'Audio tools',
            '文件工具': 'File tool',
            '其他工具': 'Other tool',
            'B站专用工具': 'Station B tool',
            '计算器工具': 'Calculator tool'
        }
        sub_dir = category_map.get(category)
        return os.path.join(base_dir, sub_dir, file_name) if sub_dir else os.path.join(base_dir, file_name)

    @staticmethod
    def get_icon_path():
        """获取图标路径"""
        return os.path.join(os.path.dirname(__file__), 'icon.ico')

class ToolLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("工具启动器-V2.0.1")
        self.root.geometry("440x500")
        self.root.minsize(440, 500)
        # 分类折叠状态，折叠状态(True)，展开状态(False)
        self.category_states = {
            'PDF工具': True,
            '图片工具': True,
            '音频工具': True,
            '文件工具': True,
            '其他工具': True,
            'B站专用工具': True,
            '计算器工具': True
        }
        
        # 创建顶部按钮框架
        self.top_frame = ttk.Frame(self.root)
        self.top_frame.pack(fill="x", padx=10, pady=5)
        
        # 添加刷新按钮
        refresh_button = ttk.Button(self.top_frame, text="刷新", command=self.refresh_tools)
        refresh_button.pack(side="left", padx=5)
        
        # 添加帮助、关于和更新日志按钮
        help_button = ttk.Button(self.top_frame, text="帮助", command=self.show_help)
        help_button.pack(side="right", padx=5)
        
        about_button = ttk.Button(self.top_frame, text="关于", command=self.show_about)
        about_button.pack(side="right", padx=5)
        
        changelog_button = ttk.Button(self.top_frame, text="更新日志", command=self.show_changelog)
        changelog_button.pack(side="right", padx=5)
        
        # 工具列表
        self.tools = {
            'PDF工具': {
                'PDF拆分': 'PDF Chai Fen.py',
                'PDF合并': 'PDF He Bing.py',
                'PDF转Word': 'PDF_to_Word.py',
                'PDF加水印': 'PDF Jia Shui Yin.py',
                'PDF转图片': 'PDF Zhuan Tu Pian.py',
                '图片转PDF': 'Tu Pian Zhuan PDF.py'
            },
            '图片工具': {
                '九宫格分割': 'Tu Pian Fen Ge Jiu Gong Ge.py',
                '格式转换': 'Tu Pian Ge Shi Zhuan Huan.py',
                'ICO转换': 'Tu Pian Zhuan ico.py',
                '图片合成': 'Tu_Pian_He_Cheng.py'
            },
            '音频工具': {
                '音频提取': 'Yin Pin Ti Qu.py'
            },
            '文件工具': {
                '目录树生成器': 'Mu Lu Shu Sheng Cheng Qi.py',
            },
            '其他工具': {
                '数字小写转大写': 'Shu Zi Xiao Xie Zhuan Da Xie.py',
                '长度单位换算': 'Chang Du Dan Wei Huan Suan.py',
                '空文件夹清理': 'Kong Wen Jian Jia Qing Li.py',
                '英文大小写转换': 'Ying Wen Da Xiao Xie Zhuan Huan.py',
                '字符频率分析器': 'Zi Fu Pin Lv Fen Xi Qi.py',
            },
            'B站专用工具': {
                '封面与表情包图片批量压缩': 'Feng Mian Yu Biao Qing Bao Tu Pian Pi Liang Ya Suo.py',

            },
            '计算器工具': {
                '最小公倍数计算器': 'Zui Xiao Gong Bei Shu Ji Suan Qi.py',
                '平方根计算器': 'Ping Fang Gen Ji Suan Qi.py',
                '重复组合计算器': 'Chong Fu Zu He Ji Suan Qi.py',
                '立方根计算器': 'Li Fang Gen Ji Suan Qi.py',
                '排列计算器': 'Pai Lie Ji Suan Qi.py',
                '因数计算器': 'Yin Shu Ji Suan Qi.py',


            }
        }
        
        # 设置窗口图标
        try:
            icon_path = PathUtils.get_icon_path()
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except:
            pass
        
        # 检查工具完整性
        self.check_tools()
        self.setup_ui()
        
    def check_tools(self):
        """检查工具完整性"""
        missing_tools = []
        for category, tools in self.tools.items():
            for tool_name, file_name in tools.items():
                tool_path = PathUtils.get_tool_path(category, file_name)
                if not os.path.exists(tool_path):
                    missing_tools.append(f"{category} - {tool_name} ({file_name})")
        
        if missing_tools:
            warning_message = "以下工具未找到：\n\n" + "\n".join(missing_tools)
            messagebox.showwarning("工具缺失", warning_message)
        
    def setup_ui(self):
        # 创建工具列表框架
        frame = ttk.LabelFrame(self.root, text="可用工具", padding="10")
        frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 创建Canvas和滚动条
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # 配置Canvas
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # 布局Canvas和滚动条
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y", padx=(0,1))
        
        # 动态创建工具按钮
        for category, tools in self.tools.items():
            # 创建分类标题框架
            category_frame = ttk.Frame(scrollable_frame)
            category_frame.pack(fill="x", pady=(10,0))
            
            # 添加折叠/展开按钮
            toggle_text = "▼" if self.category_states[category] else "▲"
            toggle_btn = ttk.Button(category_frame, text=toggle_text, width=2,
                                 command=lambda c=category: self.toggle_category(c))
            toggle_btn.pack(side="left")
            toggle_btn.category = category  # 标记按钮所属分类
            
            # 添加分类标签
            ttk.Label(category_frame, text=f"{category}：", font=("", 10, "bold")).pack(side="left", anchor="w")
            
            # 添加工具按钮容器
            tools_container = ttk.Frame(scrollable_frame)
            if not self.category_states[category]:
                tools_container.pack(fill="x")
            for tool_name, file_name in tools.items():
                # 检查工具是否存在
                tool_path = PathUtils.get_tool_path(category, file_name)
                button = ttk.Button(tools_container, text=tool_name, width=50,
                                  command=lambda f=file_name, c=category: self.run_tool(f, c))
                
                # 如果工具不存在，禁用按钮
                if not os.path.exists(tool_path):
                    button.state(['disabled'])
                    self.create_tooltip(button, f"工具文件不存在: {file_name}")
                else:
                    self.create_tooltip(button, f"启动{tool_name}")
                button.pack(pady=2)
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken")
        self.status_bar.pack(side="bottom", fill="x", padx=10, pady=5)
        
    def check_tool_exists(self, category, file_name):
        """检查工具文件是否存在"""
        tool_path = PathUtils.get_tool_path(category, file_name)
        return os.path.exists(tool_path)

    def get_tool_path(self, category, file_name):
        """获取工具文件的完整路径"""
        return PathUtils.get_tool_path(category, file_name)

    def refresh_tools(self):
        """刷新工具状态并更新界面"""
        # 更新状态
        self.status_var.set("正在刷新工具列表...")
        self.root.update()
        
        # 清除现有的工具列表框架
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.LabelFrame):
                widget.destroy()
        
        # 创建新的工具列表框架
        frame = ttk.LabelFrame(self.root, text="可用工具", padding="10")
        frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 创建Canvas和滚动条
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # 配置Canvas
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # 布局Canvas和滚动条
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y", padx=(0,5))
        
        # 动态创建工具按钮
        available_tools = 0
        total_tools = 0
        
        for category, tools in self.tools.items():
            # 创建分类标题框架
            category_frame = ttk.Frame(scrollable_frame)
            category_frame.pack(fill="x", pady=(10,0))
            
            # 添加折叠/展开按钮
            toggle_text = "▼" if self.category_states[category] else "▲"
            toggle_btn = ttk.Button(category_frame, text=toggle_text, width=2,
                                 command=lambda c=category: self.toggle_category(c))
            toggle_btn.pack(side="left")
            toggle_btn.category = category  # 标记按钮所属分类
            
            # 添加分类标签
            ttk.Label(category_frame, text=f"{category}：", font=("", 10, "bold")).pack(side="left", anchor="w")
            
            # 添加工具按钮容器
            tools_container = ttk.Frame(scrollable_frame)
            if not self.category_states[category]:
                tools_container.pack(fill="x")
            
            for tool_name, file_name in tools.items():
                total_tools += 1
                button = ttk.Button(tools_container, text=tool_name, width=50,
                                  command=lambda f=file_name, c=category: self.run_tool(f, c))
                
                # 检查工具是否存在
                if not self.check_tool_exists(category, file_name):
                    button.state(['disabled'])
                    self.create_tooltip(button, f"工具文件不存在: {file_name}")
                else:
                    available_tools += 1
                    self.create_tooltip(button, f"启动{tool_name}")
                
                button.pack(pady=2)
        
        # 更新状态栏
        self.status_var.set(f"刷新完成 - 可用工具: {available_tools}/{total_tools}")
        
    def create_tooltip(self, widget, text):
        """为控件创建工具提示"""
        def enter(event):
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            
            # 创建工具提示窗口
            self.tooltip = tk.Toplevel()
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            
            label = ttk.Label(self.tooltip, text=text, background="#ffffe0", 
                            relief="solid", borderwidth=1)
            label.pack()
            
        def leave(event):
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
                self.tooltip = None
                
        widget.bind('<Enter>', enter)
        widget.bind('<Leave>', leave)
        
    def run_tool(self, tool_name, category=None):
        """运行指定的工具"""
        try:
            # 获取工具的完整路径
            tool_path = self.get_tool_path(category, tool_name)
            # 检查文件是否存在
            if not os.path.exists(tool_path):
                raise FileNotFoundError(f"找不到工具文件：{tool_name}")
            
            # 更新状态
            self.status_var.set(f"正在启动：{tool_name}")
            self.root.update()
            
            # 使用Python解释器运行工具
            subprocess.Popen([sys.executable, tool_path])
            
            # 更新状态
            self.status_var.set(f"已启动：{tool_name}")
            
        except Exception as e:
            self.status_var.set("启动失败！")
            messagebox.showerror("错误", f"工具启动失败：{str(e)}")
    
    def show_about(self):
        """显示关于信息"""
        about_text = """
这是一个用于启动各种三垣开发的小工具模块的程序，提供了统一的启动界面。
版本说明，本启动器为正式发布版本
本项目在部署完整的开发环境后，可以离线本地运行。
- 作者:叁垣伍瑞肆凶廿捌宿宿
- 联系方式:https://space.bilibili.com/556216088
- 版权:Apache-2.0 License
- 代码层面无需联网，无需登录，无需注册，无需授权
- 功能设计无需联网,数据完全本地处理
- 本程序不收集任何用户数据，不上传任何用户数据
        """
        
        # 创建关于窗口
        about_window = tk.Toplevel(self.root)
        about_window.title("关于")
        about_window.geometry("400x200")
        about_window.resizable(False, False)
        
        # 添加图标标签（如果有的话）
        icon_path = PathUtils.get_icon_path()
        try:
            if os.path.exists(icon_path):
                icon = Image.open(icon_path)
                icon = icon.resize((64, 64), Image.Resampling.LANCZOS)
                icon_photo = ImageTk.PhotoImage(icon)
                icon_label = ttk.Label(about_window, image=icon_photo)
                icon_label.image = icon_photo  # 保持引用
                icon_label.pack(pady=10)
        except:
            pass
        
        # 添加关于文本
        text_widget = tk.Text(about_window, wrap="word", padx=20, pady=10, height=10)
        text_widget.pack(fill="both", expand=True)
        text_widget.insert("1.0", about_text)
        text_widget.config(state="disabled")  # 设置为只读
        
        # 添加关闭按钮
        close_button = ttk.Button(about_window, text="关闭", command=about_window.destroy)
        close_button.pack(pady=10)
        
    def show_changelog(self):
        """显示更新日志"""
        changelog_text = """
三垣工具启动器 更新日志
V2.0.1 (2025-7-15)
1.统一处理主程序的路径逻辑，减少重复代码
        """
        
        # 创建更新日志窗口
        changelog_window = tk.Toplevel(self.root)
        changelog_window.title("更新日志")
        changelog_window.geometry("350x300")
        changelog_window.resizable(True, True)
        
        # 添加更新日志文本
        text_widget = tk.Text(changelog_window, wrap="word", padx=10, pady=10)
        text_widget.pack(fill="both", expand=True)
        text_widget.insert("1.0", changelog_text)
        text_widget.config(state="disabled")  # 设置为只读
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(text_widget, command=text_widget.yview)
        scrollbar.pack(side="right", fill="y")
        text_widget.config(yscrollcommand=scrollbar.set)
        
        # 添加关闭按钮
        close_button = ttk.Button(changelog_window, text="关闭", command=changelog_window.destroy)
        close_button.pack(pady=10)
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """
工具启动器使用帮助

1. 功能说明
   本程序用于启动各种工具模块，包括PDF处理、图片处理和音频处理等工具。

2. 使用方法
   - 在界面上选择需要使用的工具，点击对应按钮
   - 工具将在独立窗口中启动
   - 可以同时运行多个工具
   - 状态栏会显示工具的启动状态
        """
        
        # 创建帮助窗口
        help_window = tk.Toplevel(self.root)
        help_window.title("帮助")
        help_window.geometry("500x600")
        help_window.resizable(True, True)
        
        # 添加帮助文本
        text_widget = tk.Text(help_window, wrap="word", padx=10, pady=10)
        text_widget.pack(fill="both", expand=True)
        text_widget.insert("1.0", help_text)
        text_widget.config(state="disabled")  # 设置为只读
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(text_widget, command=text_widget.yview)
        scrollbar.pack(side="right", fill="y")
        text_widget.config(yscrollcommand=scrollbar.set)
        
        # 添加关闭按钮
        close_button = ttk.Button(help_window, text="关闭", command=help_window.destroy)
        close_button.pack(pady=10)
        
    def toggle_category(self, category):
        """切换分类的折叠状态"""
        self.category_states[category] = not self.category_states[category]
        
        # 更新按钮文本
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.LabelFrame):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Canvas):
                        for grandchild in child.winfo_children():
                            if isinstance(grandchild, ttk.Frame):  # scrollable_frame
                                for greatgrandchild in grandchild.winfo_children():
                                    if hasattr(greatgrandchild, 'category') and greatgrandchild.category == category:
                                        # 更新按钮文本
                                        for btn in greatgrandchild.winfo_children():
                                            if hasattr(btn, 'category') and btn.category == category:
                                                btn.config(text="▼" if self.category_states[category] else "▲")
                                        
                                        # 切换工具按钮的显示状态
                                        for tool in greatgrandchild.winfo_children()[2:]:  # 跳过前两个控件(按钮和标签)
                                            if self.category_states[category]:
                                                tool.pack_forget()
                                            else:
                                                tool.pack(fill="x")
                                        return
        self.refresh_tools()  # 如果没找到，回退到完整刷新
        
    def run(self):
        """运行启动器"""
        self.root.mainloop()

if __name__ == "__main__":
    app = ToolLauncher()
    app.run()