# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import os
import subprocess
import flet as ft

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

class ToolLauncher:
    def __init__(self):
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
                '多功能代数计算器': 'Dai Shu Ji Suan Qi V2-2-1.py',
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
        self.tool_cache = {}
        self.page = None
        self.tools_tabs = None
        self.status_text = None

    def build(self, page: ft.Page):
        self.page = page
        page.title = "三垣工具启动器"
        page.window_width = 960
        page.window_height = 720
        page.padding = 16
        page.theme_mode = ft.ThemeMode.LIGHT
        page.scroll = "adaptive"
        
        # 设置窗口图标
        icon_path = os.path.join(PathUtils.get_base_dir(), 'Image', 'icon.ico')
        if os.path.exists(icon_path):
            page.window.icon = icon_path

        self.status_text = ft.Text("就绪", size=14, color=ft.Colors.BLUE_GREY_700)
        self.tools_tabs = ft.Tabs(expand=True)

        page.add(
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text("三垣工具启动器", size=30, weight=ft.FontWeight.BOLD),
                                ], vertical_alignment=ft.CrossAxisAlignment.CENTER
                            ),
                        ], spacing=6, expand=True
                    ),
                    ft.Row(
                        [
                            ft.ElevatedButton("刷新", on_click=self.on_refresh_click, icon=ft.Icons.REFRESH),
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
                controls.append(ft.Text("此分类暂时没有可用工具。", color=ft.Colors.BLUE_GREY_500))
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

    def check_tools(self):
        missing_tools = []
        for category, tools in self.tools.items():
            for tool_name, file_name in tools.items():
                if not self.check_tool_exists(category, file_name):
                    missing_tools.append(f"{category} - {tool_name} ({file_name})")
        return missing_tools

    def show_warning(self, message: str):
        self.page.dialog = ft.AlertDialog(
            title=ft.Text("工具缺失"),
            content=ft.Text(message),
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

    def run_tool(self, category, file_name):
        try:
            tool_base_name = os.path.splitext(file_name)[0]
            if getattr(sys, 'frozen', False):
                exe_dir = os.path.dirname(sys.executable)
                exe_name = tool_base_name.replace(' ', '') + '.exe'
                exe_path = os.path.join(exe_dir, exe_name)
                py_path = PathUtils.get_tool_path(category, file_name)

                if os.path.exists(exe_path):
                    subprocess.Popen([exe_path])
                    self.show_status(f"已启动：{tool_base_name}")
                    return
                if os.path.exists(py_path):
                    subprocess.Popen([sys.executable, py_path])
                    self.show_status(f"已启动：{tool_base_name}")
                    return
                raise FileNotFoundError(f"找不到工具文件：{tool_base_name}")
            else:
                tool_path = self.get_tool_path(category, file_name)
                if not os.path.exists(tool_path):
                    raise FileNotFoundError(f"找不到工具文件：{file_name}")
                subprocess.Popen([sys.executable, tool_path])
                self.show_status(f"已启动：{tool_base_name}")
        except Exception as e:
            self.show_status(f"启动失败：{e}", success=False)

if __name__ == "__main__":
    launcher = ToolLauncher()
    ft.app(target=launcher.build)
