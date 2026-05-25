import tkinter as tk
from tkinter import ttk, messagebox
import random
import subprocess
import os
from pathlib import Path
from fontTools.ttLib import TTFont


class SudokuLogic:
    """数独游戏逻辑部分"""
    def __init__(self):
        self.board = [[0]*9 for _ in range(9)]  # 9x9数独板
        self.solution = [[0]*9 for _ in range(9)]  # 完整解
        self.difficulty = "medium"  # 默认难度
        
    def generate_board(self):
        """生成一个新的数独板"""
        # 生成一个完整的解
        self._generate_solution()
        self.solution = [row[:] for row in self.board]
        
        # 根据难度移除数字
        if self.difficulty == "easy":
            to_remove = 30
        elif self.difficulty == "hard":
            to_remove = 55
        else:  # medium
            to_remove = 45
            
        removed = 0
        while removed < to_remove:
            row, col = random.randint(0, 8), random.randint(0, 8)
            if self.board[row][col] != 0:
                self.board[row][col] = 0
                removed += 1
                
        return self.board
        
    def _generate_solution(self):
        """生成一个有效的数独解"""
        # 清空板
        self.board = [[0]*9 for _ in range(9)]
        
        # 填充对角线上的3x3方块
        for box in range(0, 9, 3):
            self._fill_box(box, box)
            
        # 解剩余部分
        self._solve_partial(0, 0)
        
    def _fill_box(self, row, col):
        """填充一个3x3方块"""
        nums = list(range(1, 10))
        random.shuffle(nums)
        
        for i in range(3):
            for j in range(3):
                self.board[row+i][col+j] = nums.pop()
                
    def _solve_partial(self, row, col):
        """递归解决数独"""
        if row == 9:
            return True
            
        next_row, next_col = (row, col+1) if col < 8 else (row+1, 0)
        
        if self.board[row][col] != 0:
            return self._solve_partial(next_row, next_col)
            
        for num in random.sample(range(1, 10), 9):
            if self._is_valid(row, col, num):
                self.board[row][col] = num
                if self._solve_partial(next_row, next_col):
                    return True
                self.board[row][col] = 0
                
        return False
        
    def _is_valid(self, row, col, num):
        """检查数字在当前位置是否有效"""
        # 检查行
        if num in self.board[row]:
            return False
            
        # 检查列
        if num in [self.board[i][col] for i in range(9)]:
            return False
            
        # 检查3x3方块
        box_row, box_col = row//3*3, col//3*3
        for i in range(3):
            for j in range(3):
                if self.board[box_row+i][box_col+j] == num:
                    return False
                    
        return True
        
    def check_solution(self, user_board):
        """检查用户解是否正确"""
        for i in range(9):
            for j in range(9):
                if user_board[i][j] != self.solution[i][j]:
                    return False
        return True
        
    def set_difficulty(self, difficulty):
        """设置难度级别"""
        self.difficulty = difficulty

class SudokuUI:
    """数独游戏界面部分"""
    def __init__(self, root):
        self.root = root
        
        # 首先检查授权
        if not self.check_license():
            messagebox.showerror(
                "错误", 
                "缺少授权！无法使用！请先获取授权！\n"
            )
            root.destroy()
            return
        
        self.game = SudokuLogic()
        
        # 设置窗口图标、加载字体并构建UI
        self.set_window_icon()
        self.load_font()
        self.setup_ui()
    
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
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.sudoku_game")
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
                self.icon_image = tk.PhotoImage(file=str(icon_png_path))
                self.root.iconphoto(True, self.icon_image)
            except Exception:
                pass
    
    def check_license(self):
        """检查授权"""
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
    
    def load_font(self):
        """从字体文件加载并注册字体"""
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
            print(f"[成功加载自定义字体: {font_path}")
        
        from tkinter import font as tkfont
        self.current_font = (font_name, 10)
        self.root.option_add("*Font", self.current_font)
        
    def _load_font_config(self):
        """从Core/ziti.json加载字体配置（已废弃，使用load_font替代）"""
        pass
        
    def setup_ui(self):
        """设置界面布局"""
        self.root.title("数独游戏")
        self.root.geometry("500x600")
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 难度选择
        difficulty_frame = ttk.LabelFrame(main_frame, text="难度", padding="10", style='Custom.TLabelframe')
        difficulty_frame.pack(fill=tk.X, pady=5)
        
        self.difficulty_var = tk.StringVar(value="medium")
        ttk.Radiobutton(difficulty_frame, text="简单", variable=self.difficulty_var, 
                       value="easy", command=self.change_difficulty, style='Custom.TRadiobutton').pack(side=tk.LEFT)
        ttk.Radiobutton(difficulty_frame, text="中等", variable=self.difficulty_var,
                       value="medium", command=self.change_difficulty, style='Custom.TRadiobutton').pack(side=tk.LEFT)
        ttk.Radiobutton(difficulty_frame, text="困难", variable=self.difficulty_var,
                       value="hard", command=self.change_difficulty, style='Custom.TRadiobutton').pack(side=tk.LEFT)
        
        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="新游戏", command=self.new_game, style='Custom.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="检查答案", command=self.check_answer, style='Custom.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="显示答案", command=self.show_solution, style='Custom.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="自定义模式", command=self.custom_mode, style='Custom.TButton').pack(side=tk.LEFT, padx=5)
        
        # 数独板
        self.board_frame = ttk.Frame(main_frame)
        self.board_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建数独单元格
        self.cells = []
        for i in range(9):
            row = []
            for j in range(9):
                cell = tk.Entry(self.board_frame, width=3, font=(self.current_font[0], 16), 
                               justify='center', validate='key')
                cell.grid(row=i, column=j, padx=1, pady=1, ipady=5)
                cell['validatecommand'] = (cell.register(self._validate_input), '%P')
                row.append(cell)
            self.cells.append(row)
            
        # 添加3x3方块的分隔线
        for i in range(9):
            for j in range(9):
                if i % 3 == 0 and j % 3 == 0:
                    self.cells[i][j].grid(padx=(0, 3), pady=(0, 3))
                elif i % 3 == 0:
                    self.cells[i][j].grid(pady=(0, 3))
                elif j % 3 == 0:
                    self.cells[i][j].grid(padx=(0, 3))
        
        # 创建自定义样式
        style = ttk.Style()
        style.configure('Custom.TButton', font=(self.current_font[0], 10))
        style.configure('Custom.TRadiobutton', font=(self.current_font[0], 10))
        style.configure('Custom.TLabelframe', font=(self.current_font[0], 10))
        style.configure('Custom.TLabelframe.Label', font=(self.current_font[0], 10))
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(main_frame, textvariable=self.status_var, font=(self.current_font[0], 10))
        self.status_bar.pack(fill=tk.X, pady=5)
        
        # 初始化游戏
        self.new_game()
        
    def _validate_input(self, new_value):
        """验证用户输入是否为1-9的数字或空"""
        return new_value == '' or (new_value.isdigit() and 1 <= int(new_value) <= 9)
        
    def change_difficulty(self):
        """改变游戏难度"""
        self.game.set_difficulty(self.difficulty_var.get())
        self.new_game()
        
    def new_game(self):
        """开始新游戏"""
        board = self.game.generate_board()
        
        # 更新UI
        for i in range(9):
            for j in range(9):
                self.cells[i][j].config(state='normal', background='white')
                self.cells[i][j].delete(0, tk.END)
                if board[i][j] != 0:
                    self.cells[i][j].insert(0, str(board[i][j]))
                    self.cells[i][j].config(state='readonly', readonlybackground='#f0f0f0')
                    
        self.status_var.set("游戏已开始！")
        # 强制刷新界面
        self.root.update()
        
    def check_answer(self):
        """检查用户答案"""
        if not hasattr(self.game, 'solution') or not self.game.solution:
            messagebox.showwarning("提示", "请先生成或输入一个有效的数独题目")
            return
            
        user_board = []
        for i in range(9):
            row = []
            for j in range(9):
                value = self.cells[i][j].get()
                row.append(int(value) if value else 0)
            user_board.append(row)
            
        if self.game.check_solution(user_board):
            messagebox.showinfo("恭喜", "答案正确！")
            self.status_var.set("答案正确！")
        else:
            messagebox.showerror("错误", "答案不正确，请继续尝试！")
            self.status_var.set("答案不正确！")
            
    def custom_mode(self):
        """进入自定义数独输入模式"""
        # 清空当前游戏
        for i in range(9):
            for j in range(9):
                self.cells[i][j].config(state='normal', background='white')
                self.cells[i][j].delete(0, tk.END)
        
        # 初始化解决方案为一个有效的数独板
        self.game.solution = [[0]*9 for _ in range(9)]
        self.game.board = [[0]*9 for _ in range(9)]
        self.status_var.set("自定义模式：请输入您的数独题目（留空表示空格）")
        
    def show_solution(self):
        """显示完整解"""
        # 在自定义模式下，先保存用户输入作为题目
        if not hasattr(self.game, 'solution'):
            self.game.solution = [[0]*9 for _ in range(9)]
            
        # 保存用户当前输入
        user_board = []
        for i in range(9):
            row = []
            for j in range(9):
                value = self.cells[i][j].get()
                row.append(int(value) if value else 0)
            user_board.append(row)
            
        # 如果是自定义模式且没有解决方案，尝试解数独
        if all(cell == 0 for row in self.game.solution for cell in row):
            # 复制用户输入到游戏板
            self.game.board = [row[:] for row in user_board]
            # 尝试解数独
            if not self.game._solve_partial(0, 0):
                messagebox.showerror("错误", "无法解决此数独题目，请检查输入是否正确")
                return
            self.game.solution = [row[:] for row in self.game.board]
            
        # 显示完整解
        for i in range(9):
            for j in range(9):
                self.cells[i][j].config(state='normal')
                self.cells[i][j].delete(0, tk.END)
                self.cells[i][j].insert(0, str(self.game.solution[i][j]))
                # 标记用户已填正确的数字
                if user_board[i][j] == self.game.solution[i][j] and user_board[i][j] != 0:
                    self.cells[i][j].config(state='readonly', readonlybackground='#e6ffe6')  # 绿色背景表示正确
                else:
                    self.cells[i][j].config(state='readonly', readonlybackground='#ffe6e6')  # 红色背景表示错误或未填
                
        self.status_var.set("已显示完整解 - 绿色表示您已填正确的数字")

if __name__ == "__main__":
    root = tk.Tk()
    try:
        app = SudokuUI(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("错误", f"程序运行出错: {str(e)}")