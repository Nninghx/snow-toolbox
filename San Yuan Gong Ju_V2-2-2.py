# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

class PathUtils:
    """统一路径处理工具类"""

    def get_base_dir():
        """获取基础目录"""
        if getattr(sys, 'frozen', False):
            # 打包模式：使用 _internal 目录（PyInstaller 目录模式）
            return os.path.join(os.path.dirname(sys.executable), '_internal')
        else:
            # 开发模式：使用脚本所在目录
            return os.path.dirname(__file__)
    

    def get_temp_dir():
        """获取临时解压目录（仅打包模式有效）"""
        if getattr(sys, 'frozen', False):
            # PyInstaller 单文件模式下的临时解压目录
            return getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        else:
            # 开发模式：使用脚本所在目录
            return os.path.dirname(__file__)
    

    def get_tool_path(category, file_name):
        """根据分类获取工具路径"""
        base_dir = PathUtils.get_base_dir()
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
    

    def get_tool_temp_path(category, file_name):
        """获取工具在临时目录中的路径（用于单文件打包模式）"""
        temp_dir = PathUtils.get_temp_dir()
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
        return os.path.join(temp_dir, sub_dir, file_name) if sub_dir else os.path.join(temp_dir, file_name)

    @staticmethod
    def get_icon_path():
        """获取图标路径"""
        return os.path.join(PathUtils.get_base_dir(), 'Image', 'icon.ico')

class ToolLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("工具启动器-V2.1.3-32")
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
        
        # 工具存在性缓存
        self.tool_cache = {}
        
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
                '音频提取': 'Yin Pin Ti Qu V2-2-1.py'
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
                '辅助盯池工具': 'Bi Zhan Shang Cheng Du Qu Gong Ju.py',
            },
            '计算器工具': {
                '数学和统计计算器': 'Shu Xue Tong Ji Ji Suan Qi.py',
                '多功能分数计算器': 'Fen Shu Ji Suan Qi.py',
                '多功能代数计算器': 'Dai Shu Ji Suan Qi.py',
                '多功能三角函数计算器': 'San Jiao Han Shu Ji Suan Qi.py',
                '二进制计算器': 'Er Jin Zhi Ji Suan Qi.py',
                '多功能体积计算器': 'Ti Ji Ji Suan Qi.py',
                '多功能面积计算器': 'Mian Ji Ji Suan Qi.py',
                '多功能表面积计算器': 'Biao Mian Ji Ji Suan Qi V2-2-1.py',
                '多功能周长计算器': 'Zhou Chang Ji Suan Qi.py',
                '圆周率计算器': 'Yuan Zhou Lv Ji Suan Qi.py',
            },
            '小游戏': {
                '24点小游戏': '24dian_game.py',
                '数独小游戏': 'sudoku_game.py',
                '猜数字小游戏': 'guess_number_game.py',
            }
        }
        # 设置窗口和任务栏图标
        self.set_window_icon()
        
        # 检查工具完整性
        self.check_tools()
        self.setup_ui()
        
    def set_window_icon(self):
        """设置窗口图标，并尝试让 Windows 任务栏显示指定图标。"""
        icon_path = os.path.abspath(PathUtils.get_icon_path())
        if not os.path.exists(icon_path):
            return

        try:
            if os.name == 'nt':
                try:
                    import ctypes
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.launcher")
                except Exception as e:
                    print(f"设置 AppUserModelID 失败: {e}")

                try:
                    self.root.iconbitmap(default=icon_path)
                except Exception as e:
                    print(f"Windows iconbitmap 设置失败: {e}")

            if PIL_AVAILABLE:
                try:
                    icon = Image.open(icon_path)
                    icon_photo = ImageTk.PhotoImage(icon)
                    self.root.iconphoto(True, icon_photo)
                    self.root._icon_photo = icon_photo
                except Exception as e:
                    print(f"PIL iconphoto 设置失败: {e}")
            else:
                try:
                    icon_photo = tk.PhotoImage(file=icon_path)
                    self.root.iconphoto(True, icon_photo)
                    self.root._icon_photo = icon_photo
                except Exception as e:
                    print(f"tk.PhotoImage iconphoto 设置失败: {e}")
        except Exception as e:
            print(f"加载图标失败: {e}")

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
        # 创建工具树视图
        frame = ttk.LabelFrame(self.root, text="可用工具", padding="10")
        frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 创建 Treeview
        self.tree = ttk.Treeview(frame, columns=("status",), show="tree headings", height=20)
        self.tree.heading("#0", text="工具名称")
        self.tree.heading("status", text="状态")
        self.tree.column("status", width=60, anchor="center")
        
        # 设置字体
        style = ttk.Style()
        style.configure("Treeview", font=self.current_font)
        style.configure("Treeview.Heading", font=self.current_font)
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定事件
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self.tree.bind("<Return>", self.on_tree_double_click)
        
        # 填充工具列表
        self.populate_tree()
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        self.status_bar = tk.Label(self.root, textvariable=self.status_var, relief="sunken")
        self.status_bar.pack(side="bottom", fill="x", padx=10, pady=5)
        self.status_bar.configure(font=self.current_font)
    
    def populate_tree(self):
        """填充工具树"""
        # 清空现有项目
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for category, tools in self.tools.items():
            # 添加分类节点
            category_item = self.tree.insert("", "end", text=f"{category}：", values=("文件夹",))
            self.tree.item(category_item, open=not self.category_states[category])
            
            for tool_name, file_name in tools.items():
                exists = self.check_tool_exists(category, file_name)
                status = "可用" if exists else "缺失"
                tool_item = self.tree.insert(category_item, "end", text=tool_name, values=(status,))
                
                # 设置标签以便后续识别
                self.tree.item(tool_item, tags=(category, file_name))
                
                # 如果工具缺失，设置不同颜色
                if not exists:
                    self.tree.item(tool_item, tags=("missing",))
    
    def on_tree_double_click(self, event):
        """处理树视图双击事件"""
        item = self.tree.selection()
        if not item:
            return
        
        item = item[0]
        tags = self.tree.item(item, "tags")
        
        if len(tags) >= 2:
            category, file_name = tags[0], tags[1]
            self.run_tool(file_name, category)
        else:
            # 点击分类，切换展开状态
            current_open = self.tree.item(item, "open")
            self.tree.item(item, open=not current_open)
            # 更新 category_states
            category_text = self.tree.item(item, "text").rstrip("：")
            self.category_states[category_text] = not current_open
        
    def check_tool_exists(self, category, file_name):
        """检查工具文件是否存在（带缓存）"""
        cache_key = (category, file_name)
        if cache_key in self.tool_cache:
            return self.tool_cache[cache_key]
        
        # 获取工具名称（不含扩展名）
        tool_base_name = os.path.splitext(file_name)[0]
        
        # 检查是否在打包模式下运行
        if getattr(sys, 'frozen', False):
            # 打包模式：检查 exe 或 py 文件是否存在
            exe_dir = os.path.dirname(sys.executable)
            # exe 文件名去空格，如 "PDF Chai Fen.exe" -> "PDFChaiFen.exe"
            exe_name = tool_base_name.replace(' ', '') + '.exe'
            exe_path = os.path.join(exe_dir, exe_name)
            py_path = PathUtils.get_tool_path(category, file_name)
            exists = os.path.exists(exe_path) or os.path.exists(py_path)
        else:
            # 开发模式：检查 .py 文件
            tool_path = PathUtils.get_tool_path(category, file_name)
            exists = os.path.exists(tool_path)
        
        self.tool_cache[cache_key] = exists
        return exists

    def get_tool_path(self, category, file_name):
        """获取工具文件的完整路径"""
        return PathUtils.get_tool_path(category, file_name)

    def refresh_tools(self):
        """刷新工具状态并更新界面"""
        self.status_var.set("正在刷新工具列表...")
        self.root.update()
        
        # 清空缓存
        self.tool_cache.clear()
        
        # 统计工具数量
        total_tools = sum(len(tools) for tools in self.tools.values())
        available_tools = sum(
            1 for category, tools in self.tools.items()
            for file_name in tools.values()
            if self.check_tool_exists(category, file_name)
        )
        
        # 重新填充树
        self.populate_tree()
        
        self.status_var.set(f"刷新完成 - 可用工具: {available_tools}/{total_tools}")
        
    def run_tool(self, tool_name, category=None):
        """运行指定的工具"""
        if not category:
            # 从当前选择获取
            item = self.tree.selection()
            if item:
                tags = self.tree.item(item[0], "tags")
                if len(tags) >= 2:
                    category, tool_name = tags[0], tags[1]
                else:
                    return
        
        try:
            # 获取工具名称（不含扩展名）
            tool_base_name = os.path.splitext(tool_name)[0]
            
            # 检查是否在打包模式下运行
            if getattr(sys, 'frozen', False):
                # 打包模式：优先运行同目录下的 exe，如果没有则运行 py 文件
                exe_dir = os.path.dirname(sys.executable)
                # exe 文件名去空格，如 "PDF Chai Fen.exe" -> "PDFChaiFen.exe"
                exe_name = tool_base_name.replace(' ', '') + '.exe'
                exe_path = os.path.join(exe_dir, exe_name)
                py_path = PathUtils.get_tool_path(category, tool_name)
                
                if os.path.exists(exe_path):
                    # 运行打包后的 exe
                    subprocess.Popen([exe_path])
                    self.status_var.set(f"已启动：{tool_name}")
                    return
                elif os.path.exists(py_path):
                    # 运行 py 文件
                    subprocess.Popen([sys.executable, py_path])
                    self.status_var.set(f"已启动：{tool_name}")
                    return
                else:
                    raise FileNotFoundError(f"找不到工具文件：{tool_base_name}")
            else:
                # 开发模式：使用 Python 运行 .py 文件
                tool_path = self.get_tool_path(category, tool_name)
                if not os.path.exists(tool_path):
                    raise FileNotFoundError(f"找不到工具文件：{tool_name}")
                
                # 使用Python解释器运行工具
                subprocess.Popen([sys.executable, tool_path])
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
            if os.path.exists(icon_path) and PIL_AVAILABLE:
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
V2.1.1 (2026-4-14)
1.主程序UI 控件优化，提升界面美观度
2.任务栏中的图标，改为项目图标

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
            core_dir = os.path.join(PathUtils.get_base_dir(), "Core")
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
            font_path = os.path.join(PathUtils.get_base_dir(), "Core", "ziti.json")
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
        
        # 更新 Treeview 字体
        style = ttk.Style()
        style.configure("Treeview", font=self.current_font)
        style.configure("Treeview.Heading", font=self.current_font)
        
        # 更新状态栏字体
        self.status_bar.configure(font=self.current_font)
        
        # 强制刷新界面
        self.root.update()
        
    def run(self):
        """运行启动器"""
        self.root.mainloop()

if __name__ == "__main__":
    app = ToolLauncher()
    app.run()