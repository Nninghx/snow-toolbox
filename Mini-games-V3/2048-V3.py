import tkinter as tk
import random
import math
import os
import subprocess
from pathlib import Path
from fontTools.ttLib import TTFont

# ============ 授权验证 ============

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


# ============ 窗口图标设置 ============

def set_window_icon(root):
    """设置应用程序窗口图标"""
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    IMAGE_DIR = PROJECT_ROOT / "Image"
    
    icon_ico_path = IMAGE_DIR / "icon.ico"
    icon_png_path = IMAGE_DIR / "icon.png"

    # Windows系统设置应用ID
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.2048Game")
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
            # 保持引用防止垃圾回收
            root._icon_image = icon_image
        except Exception:
            pass


# ============ 字体加载 ============

def load_font(root):
    """从配置文件加载字体设置"""
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    IMAGE_DIR = PROJECT_ROOT / "Image"
    
    font_path = IMAGE_DIR / "AlibabaPuHuiTi-3-55-RegularL3.ttf"
    
    if not font_path.exists():
        messagebox.showerror("错误", f"找不到字体文件：{font_path}")
        root.destroy()
        sys.exit(1)
    
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
        print(f"成功加载自定义字体: {font_path}")
    
    from tkinter import font as tkfont
    current_font = (font_name, 10)
    root.option_add("*Font", current_font)
    return current_font


# ============ 游戏核心逻辑 ============

class Game2048:
    def __init__(self, size=4):
        self.size = size
        self.board = [[0] * size for _ in range(size)]
        self.score = 0
        self.best = 0
        self.won = False
        self.add_random()
        self.add_random()

    def add_random(self):
        """在空白位置随机放入 2 或 4"""
        empty = [(r, c) for r in range(self.size)
                 for c in range(self.size) if self.board[r][c] == 0]
        if empty:
            r, c = random.choice(empty)
            self.board[r][c] = 2 if random.random() < 0.9 else 4

    def compress(self, row):
        """将一行向左压缩（去掉0，数字靠左）"""
        new = [v for v in row if v != 0]
        new += [0] * (self.size - len(new))
        return new

    def merge(self, row):
        """合并一行中相邻的相同数字"""
        for i in range(self.size - 1):
            if row[i] != 0 and row[i] == row[i + 1]:
                row[i] *= 2
                self.score += row[i]
                row[i + 1] = 0
        return row

    def move_row(self, row):
        """对一行执行一次完整的移动+合并"""
        row = self.compress(row)
        row = self.merge(row)
        row = self.compress(row)
        return row

    def move(self, direction):
        """
        移动方向: 'up', 'down', 'left', 'right'
        返回 True 表示移动有效，False 表示不能移动
        """
        old_board = [row[:] for row in self.board]

        if direction == 'left':
            for r in range(self.size):
                self.board[r] = self.move_row(self.board[r])

        elif direction == 'right':
            for r in range(self.size):
                rev = self.board[r][::-1]
                rev = self.move_row(rev)
                self.board[r] = rev[::-1]

        elif direction == 'up':
            for c in range(self.size):
                col = [self.board[r][c] for r in range(self.size)]
                col = self.move_row(col)
                for r in range(self.size):
                    self.board[r][c] = col[r]

        elif direction == 'down':
            for c in range(self.size):
                col = [self.board[r][c] for r in range(self.size - 1, -1, -1)]
                col = self.move_row(col)
                col = col[::-1]
                for r in range(self.size):
                    self.board[r][c] = col[r]

        if self.board != old_board:
            self.add_random()
            self.best = max(self.best, self.score)
            return True
        return False

    def can_move(self):
        """检查是否还有可用的移动"""
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] == 0:
                    return True
                if c < self.size - 1 and self.board[r][c] == self.board[r][c + 1]:
                    return True
                if r < self.size - 1 and self.board[r][c] == self.board[r + 1][c]:
                    return True
        return False

    def has_won(self):
        """检查是否达成 2048"""
        return any(2048 in row for row in self.board) and not self.won

    def check_win(self):
        if self.has_won():
            self.won = True
            return True
        return False


# ============ 视觉常量 ============

# 黑白主题
BG_COLOR = "white"
GRID_COLOR = "#cccccc"
TILE_COLORS = {
    0:    ("#e8e8e8", "#e8e8e8"),
    2:    ("#f0f0f0", "#333333"),
    4:    ("#e0e0e0", "#333333"),
    8:    ("#d0d0d0", "#222222"),
    16:   ("#cccccc", "#222222"),
    32:   ("#bbbbbb", "#111111"),
    64:   ("#aaaaaa", "#111111"),
    128:  ("#999999", "white"),
    256:  ("#888888", "white"),
    512:  ("#777777", "white"),
    1024: ("#666666", "white"),
    2048: ("#555555", "white"),
    4096: ("#444444", "white"),
    8192: ("#333333", "white"),
}
FONT_MAIN = ("Helvetica", 32, "bold")
FONT_SMALL = ("Helvetica", 18, "bold")
FONT_SCORE = ("Helvetica", 14)
FONT_TITLE = ("Helvetica", 36, "bold")


# ============ GUI ============

class GameGUI:
    def __init__(self):
        # 首先检查授权
        if not check_license():
            messagebox.showerror(
                "错误", 
                "缺少授权！无法使用！请先获取授权！\n"
            )
            sys.exit(1)
        
        self.game = Game2048()
        self.root = tk.Tk()
        self.root.title("2048")
        self.root.configure(bg=BG_COLOR)
        self.root.resizable(False, False)
        self.root.bind("<Key>", self.on_key)

        # 设置窗口图标和加载字体
        set_window_icon(self.root)
        self.current_font = load_font(self.root)
        
        # 更新字体常量以使用自定义字体
        global FONT_MAIN, FONT_SMALL, FONT_SCORE, FONT_TITLE
        FONT_MAIN = (self.current_font[0], 32, "bold")
        FONT_SMALL = (self.current_font[0], 18, "bold")
        FONT_SCORE = (self.current_font[0], 14)
        FONT_TITLE = (self.current_font[0], 36, "bold")

        # 标题栏
        self.header = tk.Frame(self.root, bg=BG_COLOR)
        self.header.pack(padx=20, pady=(20, 10), fill="x")

        self.title_label = tk.Label(
            self.header, text="2048", font=FONT_TITLE,
            bg=BG_COLOR, fg="black"
        )
        self.title_label.pack(side=tk.LEFT)

        # 得分布局
        self.score_frame = tk.Frame(self.header, bg=BG_COLOR)
        self.score_frame.pack(side=tk.RIGHT)

        self.best_box = tk.Frame(self.score_frame, bg="#cccccc", padx=2, pady=2)
        self.best_box.pack(side=tk.RIGHT, padx=(8, 0))
        self.best_title = tk.Label(
            self.best_box, text="最高分", font=FONT_SCORE,
            bg="#cccccc", fg="#333333", width=8
        )
        self.best_title.pack()
        self.best_val = tk.Label(
            self.best_box, text="0", font=FONT_SMALL,
            bg="#cccccc", fg="black", width=8
        )
        self.best_val.pack()

        self.score_box = tk.Frame(self.score_frame, bg="#cccccc", padx=2, pady=2)
        self.score_box.pack(side=tk.RIGHT, padx=(8, 0))
        self.score_title = tk.Label(
            self.score_box, text="分数", font=FONT_SCORE,
            bg="#cccccc", fg="#333333", width=8
        )
        self.score_title.pack()
        self.score_val = tk.Label(
            self.score_box, text="0", font=FONT_SMALL,
            bg="#cccccc", fg="black", width=8
        )
        self.score_val.pack()

        # 新游戏按钮
        self.btn_new = tk.Button(
            self.score_frame, text="新游戏", font=FONT_SCORE,
            bg="#888888", fg="white", activebackground="#aaaaaa",
            relief=tk.FLAT, padx=12, pady=6, cursor="hand2",
            command=self.new_game
        )
        self.btn_new.pack(side=tk.RIGHT, padx=(16, 0))

        # 提示文字
        self.hint = tk.Label(
            self.root, text="使用 方向键 或 W/A/S/D 移动方块",
            font=("Helvetica", 11), bg=BG_COLOR, fg="#888888"
        )
        self.hint.pack(pady=(0, 10))

        # 游戏画布
        self.cell_size = 120
        self.padding = 10
        self.canvas_width = self.game.size * self.cell_size + self.padding * 5
        self.canvas_height = self.game.size * self.cell_size + self.padding * 5
        self.canvas = tk.Canvas(
            self.root, width=self.canvas_width, height=self.canvas_height,
            bg=BG_COLOR, highlightthickness=0
        )
        self.canvas.pack(padx=20, pady=(0, 20))

        # 覆盖层（胜利/失败）
        self.overlay = None

        self.draw()
        self.root.mainloop()

    def new_game(self):
        self.game = Game2048()
        self.canvas.delete("overlay")
        self.overlay = None
        self.draw()

    def on_key(self, event):
        key_map = {
            'Up': 'up', 'Down': 'down', 'Left': 'left', 'Right': 'right',
            'w': 'up', 's': 'down', 'a': 'left', 'd': 'right',
            'W': 'up', 'S': 'down', 'A': 'left', 'D': 'right',
        }
        direction = key_map.get(event.keysym)
        if direction:
            if self.game.move(direction):
                self.draw()
                if not self.game.can_move():
                    self.draw_game_over()
            elif not self.game.can_move():
                self.draw_game_over()
            self.game.check_win()

    def get_font_size(self, n):
        """根据数字位数调整字体大小"""
        if n < 100:
            return ("Helvetica", 36, "bold")
        elif n < 1000:
            return ("Helvetica", 30, "bold")
        elif n < 10000:
            return ("Helvetica", 24, "bold")
        else:
            return ("Helvetica", 20, "bold")

    def draw(self):
        self.canvas.delete("all")

        # 画网格背景
        for r in range(self.game.size):
            for c in range(self.game.size):
                x1 = self.padding + c * (self.cell_size + self.padding)
                y1 = self.padding + r * (self.cell_size + self.padding)
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                radius = 8
                self.create_rounded_rect(
                    x1, y1, x2, y2, radius, fill=GRID_COLOR, outline=""
                )

        # 画数字方块
        for r in range(self.game.size):
            for c in range(self.game.size):
                val = self.game.board[r][c]
                x1 = self.padding + c * (self.cell_size + self.padding)
                y1 = self.padding + r * (self.cell_size + self.padding)
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size

                bg, fg = TILE_COLORS.get(val, TILE_COLORS[8192])
                if val > 8192:
                    bg, fg = "#222222", "white"

                radius = 8
                self.create_rounded_rect(
                    x1, y1, x2, y2, radius, fill=bg, outline=""
                )
                if val != 0:
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                    font = self.get_font_size(val)
                    self.canvas.create_text(
                        cx, cy, text=str(val), font=font, fill=fg
                    )

        # 更新分数
        self.score_val.config(text=str(self.game.score))
        self.best_val.config(text=str(self.game.best))

    def draw_game_over(self):
        self.canvas.create_rectangle(
            0, 0, self.canvas_width, self.canvas_height,
            fill="black", stipple="gray50", tags="overlay"
        )
        self.canvas.create_text(
            self.canvas_width // 2, self.canvas_height // 2 - 20,
            text="游戏结束!", font=FONT_TITLE, fill="white", tags="overlay"
        )
        self.canvas.create_text(
            self.canvas_width // 2, self.canvas_height // 2 + 30,
            text=f"最终得分: {self.game.score}",
            font=FONT_SMALL, fill="white", tags="overlay"
        )

    # 以下是创建圆角矩形的辅助函数
    def create_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        self.canvas.create_polygon(points, smooth=True, **kwargs)


if __name__ == "__main__":
    GameGUI()
