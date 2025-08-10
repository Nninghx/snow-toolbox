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
            '音频工具': 'Audio tool',
            '文件工具': 'File tool',
            '其他工具': 'Other tool',
            'B站专用工具': 'Station B tool',
            '计算器工具': 'Calculator tool',
            '小游戏': 'Mini-games',
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
        self.root.title("工具启动器-V2.1.2-32")
        self.root.geometry("400x500")  # 调整窗口大小以适应菜单栏
        self.root.minsize(400, 500)
        
        # 默认字体设置
        self.current_font = ("微软雅黑", 10)
        
        # 尝试加载保存的字体设置
        self.load_font_settings()
        
        # 分类折叠状态，折叠状态(True)，展开状态(False)
        self.category_states = {
            'PDF工具': True,
            '图片工具': True,
            '音频工具': True,
            '文件工具': True,
            '其他工具': True,
            'B站专用工具': True,
            '计算器工具': True,
            '小游戏': True,
        }
        
        # 创建菜单栏
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        
        # 文件菜单
        file_menu = tk.Menu(self.menubar, tearoff=0)
        file_menu.add_command(label="刷新", command=self.refresh_tools)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        self.menubar.add_cascade(label="文件", menu=file_menu)
        
        # 设置菜单
        settings_menu = tk.Menu(self.menubar, tearoff=0)
        settings_menu.add_command(label="字体设置", command=self.show_font_settings)
        self.menubar.add_cascade(label="设置", menu=settings_menu)
        
        # 帮助菜单
        help_menu = tk.Menu(self.menubar, tearoff=0)
        help_menu.add_command(label="介绍", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)
        help_menu.add_command(label="更新日志", command=self.show_changelog)
        self.menubar.add_cascade(label="帮助", menu=help_menu)
        
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
                '带货链接分批处理工具': 'Lian Jie Fen Pi Chu Li.py',
            },
            '计算器工具': {
                '数学和统计计算器': 'Shu Xue Tong Ji Ji Suan Qi.py',
                '多功能分数计算器': 'Fen Shu Ji Suan Qi.py',
                '多功能代数计算器': 'Dai Shu Ji Suan Qi.py',
                '多功能三角函数计算器': 'San Jiao Han Shu Ji Suan Qi.py',
                '二进制计算器': 'Er Jin Zhi Ji Suan Qi.py',
                '多功能体积计算器': 'Ti Ji Ji Suan Qi.py',
                '多功能面积计算器': 'Mian Ji Ji Suan Qi.py',
                '多功能表面积计算器': 'Biao Mian Ji Ji Suan Qi.py',
                '多功能周长计算器': 'Zhou Chang Ji Suan Qi.py',
                '圆周率计算器': 'Yuan Zhou Lv Ji Suan Qi.py',
            },
            '小游戏': {
                '24点小游戏': '24dian_game.py',
                '数独小游戏': 'sudoku_game.py',
                '猜数字小游戏': 'guess_number_game.py',
            }
        }
        # 设置窗口图标
        try:
            icon_path = os.path.join(os.path.dirname(__file__), 'Image', 'icon.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"加载图标失败: {e}")
        
        # 检查工具完整性
        self.check_tools()
        self.setup_ui()
        
    def _create_scrollable_frame(self, parent):
        """创建可滚动框架的公共方法"""
        frame = ttk.LabelFrame(parent, text="可用工具", padding="10")
        frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y", padx=(0,1))
        
        return scrollable_frame

    def _create_tool_buttons(self, scrollable_frame, check_exists=True):
        """创建工具按钮的公共方法"""
        # 清空之前的引用
        self.tool_buttons = []
        self.category_labels = []
        
        for category, tools in self.tools.items():
            category_frame = ttk.Frame(scrollable_frame)
            category_frame.pack(fill="x", pady=(10,0))
            
            toggle_text = "▼" if self.category_states[category] else "▲"
            toggle_btn = tk.Button(category_frame, text=toggle_text, width=2,
                                 command=lambda c=category: self.toggle_category(c))
            toggle_btn.pack(side="left")
            toggle_btn.category = category
            toggle_btn.configure(font=self.current_font)
            
            label = tk.Label(category_frame, text=f"{category}：", font=("", 10, "bold"))
            label.pack(side="left", anchor="w")
            label.configure(font=self.current_font)
            self.category_labels.append(label)  # 保存分类标签引用
            
            tools_container = ttk.Frame(scrollable_frame)
            if not self.category_states[category]:
                tools_container.pack(fill="x")
                
            for tool_name, file_name in tools.items():
                button = tk.Button(tools_container, text=tool_name, width=50,
                                  command=lambda f=file_name, c=category: self.run_tool(f, c))
                button.configure(font=self.current_font)
                self.tool_buttons.append(button)  # 保存工具按钮引用
                
                if check_exists and not self.check_tool_exists(category, file_name):
                    button.state(['disabled'])
                    self.create_tooltip(button, f"工具文件不存在: {file_name}")
                else:
                    self.create_tooltip(button, f"启动{tool_name}")
                button.pack(pady=2)

    def check_tools(self):
        """检查工具完整性"""
        missing_tools = []
        for category, tools in self.tools.items():
            for tool_name, file_name in tools.items():
                if not self.check_tool_exists(category, file_name):
                    missing_tools.append(f"{category} - {tool_name} ({file_name})")
        
        if missing_tools:
            warning_message = "以下工具未找到：\n\n" + "\n".join(missing_tools)
            messagebox.showwarning("工具缺失", warning_message)
        
    def setup_ui(self):
        scrollable_frame = self._create_scrollable_frame(self.root)
        self._create_tool_buttons(scrollable_frame)
        self.status_var = tk.StringVar(value="就绪")
        self.status_bar = tk.Label(self.root, textvariable=self.status_var, relief="sunken")
        self.status_bar.pack(side="bottom", fill="x", padx=10, pady=5)
        self.status_bar.configure(font=self.current_font)
        
    def check_tool_exists(self, category, file_name):
        """检查工具文件是否存在"""
        tool_path = PathUtils.get_tool_path(category, file_name)
        return os.path.exists(tool_path)

    def get_tool_path(self, category, file_name):
        """获取工具文件的完整路径"""
        return PathUtils.get_tool_path(category, file_name)

    def refresh_tools(self):
        """刷新工具状态并更新界面"""
        self.status_var.set("正在刷新工具列表...")
        self.root.update()
        
        # 清除现有的工具列表框架
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.LabelFrame):
                widget.destroy()
        
        # 创建新的UI
        scrollable_frame = self._create_scrollable_frame(self.root)
        
        # 统计工具数量
        total_tools = sum(len(tools) for tools in self.tools.values())
        available_tools = sum(
            1 for category, tools in self.tools.items()
            for file_name in tools.values()
            if self.check_tool_exists(category, file_name)
        )
        
        # 创建工具按钮
        self._create_tool_buttons(scrollable_frame, check_exists=False)
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
- 作者:宁幻雪
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
V2.1.2 (2025-8-10)
1.对带货链接分批处理工具，添加只提取链接部分的功能，提高工作效率
2.对目录树生成器工具，新增的导出思维导图功能
3.添加项目图标

历史版本查看README.md文档
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
    
    def show_font_settings(self):
        """显示字体设置窗口"""
        font_window = tk.Toplevel(self.root)
        font_window.title("字体设置")
        font_window.geometry("300x150")
        
        # 添加字体选择控件，如果你需要自定义字体，请在以下代码修改或添加新字体族
        ttk.Label(font_window, text="选择字体:").pack(pady=10)
        font_family = ttk.Combobox(font_window, values=["阿里巴巴普惠体 3 115 Black", "阿里巴巴普惠体 3 55 Regular L3", "阿里巴巴普惠体 3.0 35 Thin"])
        font_family.pack(pady=5)
        font_family.set("阿里巴巴普惠体 3 115 Black")
        
        # 添加应用按钮
        apply_button = ttk.Button(font_window, text="应用", 
                                command=lambda: self.apply_font_settings(font_family.get(), 10))  # 固定字体大小为10
        apply_button.pack(pady=10)

    def apply_font_settings(self, family, size):
        """应用字体设置"""
        self.current_font = (family, size)
        
        # 更新所有控件的字体
        self.update_fonts()
        messagebox.showinfo("提示", f"已应用字体设置: {family} {size}px")
        
        # 保存字体设置到文件
        self.save_font_settings()
        
        # 自动执行刷新操作
        self.refresh_tools()
        
    def save_font_settings(self):
        """保存字体设置到Core/ziti.json文件"""
        import json
        try:
            # 确保Core文件夹存在
            core_dir = os.path.join(os.path.dirname(__file__), "Core")
            if not os.path.exists(core_dir):
                os.makedirs(core_dir)
            
            font_data = {
                "family": self.current_font[0]  # 只保存字体类型
            }
            font_path = os.path.join(core_dir, "ziti.json")
            with open(font_path, "w", encoding="utf-8") as f:
                json.dump(font_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存字体设置失败: {e}")
            
    def load_font_settings(self):
        """从Core/ziti.json文件加载字体设置"""
        import json
        try:
            font_path = os.path.join(os.path.dirname(__file__), "Core", "ziti.json")
            if os.path.exists(font_path):
                with open(font_path, "r", encoding="utf-8") as f:
                    font_data = json.load(f)
                    self.current_font = (font_data["family"], 10)  # 固定字体大小为10
        except Exception as e:
            print(f"加载字体设置失败: {e}")
        
    def update_fonts(self):
        """更新所有控件的字体"""
        # 更新菜单栏字体
        for menu in [self.menubar]:
            try:
                menu.configure(font=self.current_font)
            except:
                pass
            for item in menu.winfo_children():
                try:
                    item.configure(font=self.current_font)
                except:
                    pass
        
        # 更新工具按钮字体
        for button in self.tool_buttons:
            button.configure(font=self.current_font)
        
        # 更新分类标签字体
        for label in self.category_labels:
            label.configure(font=self.current_font)
        
        # 更新状态栏字体
        self.status_bar.configure(font=self.current_font)
        
        # 强制刷新界面
        self.root.update()
        
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