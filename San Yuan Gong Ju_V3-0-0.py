# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import subprocess
import flet as ft
from pathlib import Path
from fontTools.ttLib import TTFont
def get_font_name():
    """获取自定义字体名称并注册到系统"""
    base_dir = Path(__file__).resolve().parent
    font_path = base_dir / "Image" / "AlibabaPuHuiTi-3-55-RegularL3.ttf"
    
    if not font_path.exists():
        print(f"警告：找不到字体文件：{font_path}")
        return None
    
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
    
    # 在 Windows 上注册字体
    if os.name == 'nt':
        import ctypes
        GDI32 = ctypes.windll.gdi32
        font_path_str = str(font_path).encode('utf-16-le') + b'\x00'
        GDI32.AddFontResourceW(font_path_str)
        print(f"成功加载自定义字体: {font_path}")
    return font_name
# 加载自定义字体
CUSTOM_FONT_NAME = get_font_name()
class LicenseValidator:
    """授权验证类"""
    @staticmethod
    def validate_license():
        """
        验证授权文件
        返回: (bool, str) - (是否通过, 消息)
        """
        try:
            base_dir = PathUtils.get_base_dir()
            license_exe_path = os.path.join(base_dir, 'Core', 'LICENSE.exe')
            
            if not os.path.exists(license_exe_path):
                return False, "未找到授权验证程序：Core/LICENSE.exe"
            
            # 运行 LICENSE.exe 进行授权验证
            result = subprocess.run(
                [license_exe_path, '--quiet'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # 退出码为 0 表示验证通过
            if result.returncode == 0:
                return True, "授权验证通过"
            else:
                error_msg = result.stderr.strip() if result.stderr else "授权验证失败"
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            return False, "授权验证超时"
        except Exception as e:
            return False, f"授权验证出错：{str(e)}"

class PathUtils:
    """统一路径处理工具类"""

    def get_base_dir():
        """获取基础目录"""
        if getattr(sys, 'frozen', False):
            return os.path.join(os.path.dirname(sys.executable), '_internal')
        return os.path.dirname(__file__)

    def get_tool_path(category, file_name):
        """根据分类获取工具路径"""
        base_dir = PathUtils.get_base_dir()
        category_map = {
            'PDF工具': 'PDF tool-V3',
            '图片工具': 'Picture tool-V3',
            '音频工具': 'Audio tool-V3',
            '文件工具': 'File tool-V3',
            '其他工具': 'Other tool-V3',
            'B站专用工具': 'Station B tool',
            '计算器工具': 'Calculator tool-V3',
            '下载工具': 'Download tool-V3',
            '小游戏': 'Mini-games-V3',
        }
        sub_dir = category_map.get(category)
        return os.path.join(base_dir, sub_dir, file_name) if sub_dir else os.path.join(base_dir, file_name)

class ToolLauncher:
    def __init__(self):
        self.tools = {
            'PDF工具': {
                'PDF拆分': 'PDF chāi fēn-V3.py',
                'PDF合并': 'PDF hé bìng-V3.py',
                'PDF转Word': 'PDF zhuǎn Word-V3.py',
                'PDF加水印': 'PDF jiā shuǐ yìn-V3.py',
                'PDF转图片': 'PDF zhuǎn tú piàn-V3.py',
                '图片转PDF': 'tú piàn zhuǎn PDF-V3.py'
            },
            '图片工具': {
                '九宫格分割': 'tú piàn jiǔ gōng gé fēn gē-V3.py',
                '格式转换': 'tú piàn gé shì zhuǎn huàn-V3.py',
                'ICO转换': 'tú piàn zhuǎn tú biāo-V3.py',
                '图片合成': 'tú piàn hé chéng-V3.py',
            },
            '音频工具': {
                '音频提取': 'shì pín yīn pín tí qǔ-V3.py'
            },
            '文件工具': {
                '目录树生成器': 'wén jiàn mù lù shù shēng chéng qì-V3.py',
                '文件时间修改器': 'wén jiàn shí jiān xiū gǎi qì-V3.py',
                '空文件夹清理': 'kōng wén jiàn jiā qīng lǐ-V3.py',
            },
            '其他工具': {
                '数字小写转大写': 'shù zì xiǎo xiě zhuǎn dà xiě-V3.py',
                '长度单位换算': 'cháng dù dān wèi huàn suàn-V3.py',
                '英文大小写转换': 'yīng wén dà xiǎo xiě zhuǎn huàn-V3.py',
                '字符频率分析器': 'zìfú pín lǜ fēn xī-V3.py',
                '内存压缩管理工具': 'nèi cún yā suō guǎn lǐ-V3.py',
            },
            'B站专用工具': {
                '封面与表情包图片批量压缩': 'Feng Mian Yu Biao Qing Bao Tu Pian Pi Liang Ya Suo.py',
                '带货链接分批处理工具': 'Lian Jie Fen Pi Chu Li.py',
                '辅助盯池工具': 'ningB.py',
            },
            '计算器工具': {
                '数学和统计计算器': 'shù xué hé tǒng jì jì suàn qì-V3.py',
                '分数计算器': 'fēn shù jì suàn qì-V3.py',
                '代数计算器': 'dài shù jì suàn qì-V3.py',
                '三角函数计算器': 'sān jiǎo hán shù jì suàn qì-V3.py',
                '二进制计算器': 'èr jìn zhì jì suàn qì-V3.py',
                '体积计算器': 'tǐ jī jì suàn qì-V3.py',
                '面积计算器': 'miàn jī jì suàn qì-V3.py',
                '表面积计算器': 'biǎo miàn jī  jì suàn qì-V3.py',
                '周长计算器': 'zhōu cháng jì suàn qì-V3.py',
                '圆周率计算器': 'yuán zhōu lǜ jì suàn qì-V3.py',
            },
            '小游戏': {
                '24点小游戏': '24diǎn yóu xì-V3.py',
                '数独小游戏': 'cāishùzì yóuxì-V3.py',
                '猜数字小游戏': 'cāishùzì yóuxì-V3.py',
            }
            ,
            '下载工具': {
                'huggingface模型下载器': 'Hugging Face mó xíng xià zǎi qì-V3.py',
                'ModelScope 模型下载器': 'ModelScope mó xíng xià zǎi qì-V3.py',
                '图片下载': 'tú piàn xià zǎi-V3.py',
            },
        }
        self.tool_cache = {}
        self.page = None
        self.tools_tabs = None
        self.status_text = None
        self.font_family = CUSTOM_FONT_NAME

    def build(self, page: ft.Page):
        self.page = page
        page.title = "宁宝工具启动器"
        page.window_width = 860
        page.window_height = 520
        page.padding = 16
        page.theme_mode = ft.ThemeMode.LIGHT
        page.scroll = "adaptive"
        
        # 设置窗口图标
        icon_path = os.path.join(PathUtils.get_base_dir(), 'Image', 'icon.ico')
        if os.path.exists(icon_path):
            page.window.icon = icon_path

        self.status_text = ft.Text("就绪", size=14, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family)
        self.tools_tabs = ft.Tabs(expand=True)

        page.add(
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text("宁宝工具启动器", size=30, weight=ft.FontWeight.BOLD, font_family=self.font_family),
                                ], vertical_alignment=ft.CrossAxisAlignment.CENTER
                            ),
                        ], spacing=6, expand=True
                    ),
                    ft.Row(
                        [
                            ft.ElevatedButton("刷新", on_click=self.on_refresh_click, icon=ft.Icons.REFRESH),
                            ft.ElevatedButton("项目开源协议", on_click=self.on_license_click, icon=ft.Icons.DESCRIPTION),
                        ], spacing=8
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
            ft.Divider(thickness=1, opacity=0.5),
            self.tools_tabs,
            ft.Container(content=self.status_text, padding=ft.padding.symmetric(vertical=8, horizontal=12), bgcolor=ft.Colors.BLUE_GREY_50, border_radius=8, border=ft.border.all(1, ft.Colors.GREY_300)),
        )

        self.refresh_tools()
        missing_tools = self.check_tools()
        if missing_tools:
            self.show_warning("以下工具未找到：\n\n" + "\n".join(missing_tools))
        return page

    def build_tool_tabs(self):
        tabs = []
        for category, tools in self.tools.items():
            controls = []
            for tool_name, file_name in tools.items():
                exists = self.check_tool_exists(category, file_name)
                status_chip = ft.Text(
                    "可用" if exists else "缺失",
                    color=ft.Colors.GREEN if exists else ft.Colors.RED,
                    weight=ft.FontWeight.BOLD,
                    font_family=self.font_family,
                )
                tool_button = ft.ElevatedButton(
                    tool_name,
                    on_click=lambda e, c=category, f=file_name: self.run_tool(c, f),
                    disabled=not exists,
                    expand=True,
                )
                controls.append(
                    ft.Container(
                        ft.Row(
                            [tool_button, status_chip],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=ft.padding.all(10),
                        border_radius=10,
                        bgcolor=ft.Colors.WHITE,
                        border=ft.border.all(1, ft.Colors.GREY_200),
                    )
                )
            if not controls:
                controls.append(ft.Text("此分类暂时没有可用工具。", color=ft.Colors.BLUE_GREY_500, font_family=self.font_family))
            tabs.append(
                ft.Tab(
                    text=category,
                    content=ft.Column(controls, spacing=10, scroll=ft.ScrollMode.AUTO, expand=True),
                )
            )
        self.tools_tabs.tabs = tabs

    def refresh_tools(self):
        """刷新工具列表"""
        self.build_tool_tabs()
        if self.page:
            self.page.update()

    def show_status(self, message: str, success: bool = True):
        self.status_text.value = message
        self.page.snack_bar = ft.SnackBar(
            ft.Text(message), bgcolor=ft.Colors.GREEN if success else ft.Colors.RED, open=True
        )
        self.page.update()

    def on_refresh_click(self, event=None):
        self.tool_cache.clear()
        self.build_tool_tabs()
        total_tools = sum(len(tools) for tools in self.tools.values())
        available_tools = sum(
            1
            for category, tools in self.tools.items()
            for file_name in tools.values()
            if self.check_tool_exists(category, file_name)
        )
        self.show_status(f"刷新完成 - 可用工具: {available_tools}/{total_tools}")

    def on_license_click(self, event=None):
        """打开软件开源协议文件"""
        try:
            license_path = os.path.join(PathUtils.get_base_dir(), 'Core', 'LICENSE.txt')
            if not os.path.exists(license_path):
                self.show_status("未找到开源协议文件：Core/LICENSE.txt", success=False)
                return
            
            # 使用系统默认程序打开文件（只读模式）
            if sys.platform == 'win32':
                os.startfile(license_path)
            self.show_status("已打开软件开源协议")
        except Exception as e:
            self.show_status(f"打开协议失败：{e}", success=False)

    def check_tools(self):
        missing_tools = []
        for category, tools in self.tools.items():
            for tool_name, file_name in tools.items():
                if not self.check_tool_exists(category, file_name):
                    missing_tools.append(f"{category} - {tool_name} ({file_name})")
        return missing_tools

    def show_warning(self, message: str):
        self.page.dialog = ft.AlertDialog(
            title=ft.Text("工具缺失", font_family=self.font_family),
            content=ft.Text(message, font_family=self.font_family),
            actions=[ft.TextButton("关闭", on_click=lambda e: self.close_dialog())],
        )
        self.page.dialog.open = True
        self.page.update()

    def close_dialog(self, event=None):
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()

    def check_tool_exists(self, category, file_name):
        cache_key = (category, file_name)
        if cache_key in self.tool_cache:
            return self.tool_cache[cache_key]

        tool_base_name = os.path.splitext(file_name)[0]
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            exe_name = tool_base_name.replace(' ', '') + '.exe'
            exe_path = os.path.join(exe_dir, exe_name)
            py_path = PathUtils.get_tool_path(category, file_name)
            exists = os.path.exists(exe_path) or os.path.exists(py_path)
        else:
            tool_path = PathUtils.get_tool_path(category, file_name)
            exists = os.path.exists(tool_path)

        self.tool_cache[cache_key] = exists
        return exists

    def get_tool_path(self, category, file_name):
        return PathUtils.get_tool_path(category, file_name)

    def get_python_executable(self):
        """获取Python解释器路径（兼容打包和开发模式）"""
        import shutil
        # 优先使用虚拟环境中的 Python
        python_exec = getattr(sys, '_base_executable', sys.executable)
        if not getattr(sys, 'frozen', False):
            return python_exec
        
        # 打包后：尝试从 sys.prefix 找到 pythonw.exe
        python_dir = os.path.dirname(sys.prefix)
        pythonw_path = os.path.join(python_dir, 'pythonw.exe')
        if os.path.exists(pythonw_path):
            return pythonw_path
        
        # 尝试从 _MEIPASS 同级目录查找
        meipass_dir = os.path.dirname(sys._MEIPASS)
        pythonw_path = os.path.join(meipass_dir, 'pythonw.exe')
        if os.path.exists(pythonw_path):
            return pythonw_path
        
        # 尝试用 pythonw 查找
        pythonw = shutil.which('pythonw')
        if pythonw:
            return pythonw
        
        return python_exec

    def run_tool(self, category, file_name):
        try:
            tool_base_name = os.path.splitext(file_name)[0]
            tool_path = PathUtils.get_tool_path(category, file_name)
            if not os.path.exists(tool_path):
                raise FileNotFoundError(f"找不到工具文件：{file_name}")

            env = os.environ.copy()
            env['MAIN_APP_AUTHORIZED'] = '1'

            if getattr(sys, 'frozen', False):
                # 打包后：启动自身新实例来运行子工具（新实例拥有所有打包的模块）
                subprocess.Popen(
                    [sys.executable, '--run-tool', category, file_name],
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                # 开发模式：直接用 Python 解释器运行
                subprocess.Popen([sys.executable, tool_path], env=env)

            self.show_status(f"已启动：{tool_base_name}")
        except Exception as e:
            self.show_status(f"启动失败：{e}", success=False)

if __name__ == "__main__":
    # 处理 --run-tool 参数：由主程序自身新实例运行子工具
    if len(sys.argv) >= 4 and sys.argv[1] == '--run-tool':
        category = sys.argv[2]
        file_name = sys.argv[3]
        tool_path = PathUtils.get_tool_path(category, file_name)
        if os.path.exists(tool_path):
            import runpy
            # 设置环境变量以绕过子工具自身的授权验证
            os.environ['MAIN_APP_AUTHORIZED'] = '1'
            try:
                runpy.run_path(tool_path, run_name='__main__')
            except Exception as e:
                # 尝试显示错误提示
                try:
                    import tkinter as tk
                    from tkinter import messagebox
                    root = tk.Tk()
                    root.withdraw()
                    messagebox.showerror("启动失败", f"工具启动失败：{e}")
                    root.destroy()
                except:
                    print(f"工具启动失败：{e}")
        else:
            print(f"找不到工具文件：{tool_path}")
        sys.exit(0)

    # 在启动前进行授权验证
    is_valid, message = LicenseValidator.validate_license()
    
    if not is_valid:
        # 授权失败，显示错误信息并退出
        print(f"\n{'='*60}")
        print(f"授权验证失败")
        print(f"{'='*60}")
        print(f"{message}")
        print(f"\n请先获得有效授权")
        print(f"{'='*60}\n")
        
        # 尝试显示图形化错误提示（如果可能）
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口
            messagebox.showerror(
                "授权验证失败",
                f"{message}\n\n请先获得有效授权"
            )
            root.destroy()
        except:
            pass
        
        sys.exit(1)
    
    # 授权通过，正常启动软件
    launcher = ToolLauncher()
    ft.app(target=launcher.build)
