import tkinter as tk
from tkinter import ttk, messagebox
import random
import subprocess
from pathlib import Path
import os
from fontTools.ttLib import TTFont


class GuessNumberLogic:
    """猜数字游戏逻辑部分"""
    def __init__(self):
        self.target_number = 0
        self.guesses = 0
        self.game_started = False
        self.digits = 4  # 默认4位数
        self.game_mode = "classic"  # classic或1A2B
        
    def set_digits(self, digits):
        """设置数字位数"""
        if 1 <= digits <= 9:
            self.digits = digits
            
    def set_game_mode(self, mode):
        """设置游戏模式"""
        self.game_mode = mode
        
    def start_new_game(self):
        """开始新游戏"""
        if self.game_mode == "classic":
            self.target_number = random.randint(1, 100)
        else:  # 1A2B模式
            min_num = 10 ** (self.digits - 1)
            max_num = (10 ** self.digits) - 1
            self.target_number = random.randint(min_num, max_num)
            
        self.guesses = 0
        self.game_started = True
        return self.target_number
        
    def make_guess(self, guess):
        """处理玩家猜测"""
        if not self.game_started:
            return "请先开始新游戏"
            
        try:
            guess_num = int(guess)
            self.guesses += 1
            
            if self.game_mode == "classic":
                if guess_num == self.target_number:
                    return f"正确！你用了{self.guesses}次猜中"
                elif guess_num < self.target_number:
                    return "太小了"
                else:
                    return "太大了"
            else:  # 1A2B模式
                target_str = str(self.target_number).zfill(self.digits)
                guess_str = str(guess_num).zfill(self.digits)
                
                if len(guess_str) != self.digits:
                    return f"请输入一个{self.digits}位数"
                    
                if guess_str == target_str:
                    return f"正确！你用了{self.guesses}次猜中"
                    
                # 生成每个数字的反馈符号
                feedback = []
                target_list = list(target_str)
                guess_list = list(guess_str)
                
                # 第一遍检查完全匹配(√)
                for i in range(self.digits):
                    if guess_list[i] == target_list[i]:
                        feedback.append("√")
                        target_list[i] = None  # 标记已匹配
                    else:
                        feedback.append("×")  # 默认先设为×
                
                # 第二遍检查数字存在但位置不对(乄)
                for i in range(self.digits):
                    if feedback[i] != "√" and guess_list[i] in target_list:
                        feedback[i] = "乄"
                        target_list[target_list.index(guess_list[i])] = None
                
                # 生成反馈字符串
                feedback_str = " ".join(feedback)
                
                # 计算统计
                a_count = feedback.count("√")
                b_count = feedback.count("乄")
                
                return f"{feedback_str}\n√:数字和位置正确({a_count})\n乄:数字正确但位置错误({b_count})"
                
        except ValueError:
            if self.game_mode == "classic":
                return "请输入1-100之间的整数"
            else:
                return f"请输入一个{self.digits}位数"

class GuessNumberUI:
    """猜数字游戏界面部分"""
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
        
        self.game = GuessNumberLogic()
        
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
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.guess_number_game")
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
            print(f"✅ 成功加载自定义字体: {font_path}")
        
        from tkinter import font as tkfont
        self.current_font = (font_name, 10)
        self.root.option_add("*Font", self.current_font)
        
    def _load_font_config(self):
        """从Core/ziti.json加载字体配置（已废弃，使用load_font替代）"""
        pass
        
    def setup_ui(self):
        """设置界面布局"""
        self.root.title("猜数字游戏")
        self.root.geometry("500x400")
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 游戏设置区域
        settings_frame = ttk.LabelFrame(main_frame, text="游戏设置", padding="10", style='Custom.TLabelframe')
        settings_frame.pack(fill=tk.X, pady=5)
        
        # 游戏模式选择
        ttk.Label(settings_frame, text="游戏模式:", font=(self.current_font[0], 10)).pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value="classic")
        ttk.Radiobutton(settings_frame, text="经典模式", variable=self.mode_var, 
                       value="classic", command=self.change_mode, style='Custom.TRadiobutton').pack(side=tk.LEFT)
        ttk.Radiobutton(settings_frame, text="1A2B模式", variable=self.mode_var,
                       value="1A2B", command=self.change_mode, style='Custom.TRadiobutton').pack(side=tk.LEFT)
        
        # 位数选择 (仅1A2B模式显示)
        self.digits_frame = ttk.Frame(settings_frame)
        ttk.Label(self.digits_frame, text="数字位数:", font=(self.current_font[0], 10)).pack(side=tk.LEFT)
        self.digits_var = tk.StringVar(value="4")
        digits_spin = ttk.Spinbox(self.digits_frame, from_=1, to=9, textvariable=self.digits_var, width=3)
        digits_spin.pack(side=tk.LEFT, padx=5)
        
        # 游戏控制区域
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(control_frame, text="新游戏", command=self.new_game, style='Custom.TButton').pack(side=tk.LEFT, padx=5)
        
        # 输入区域
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(input_frame, text="输入猜测:", font=(self.current_font[0], 12)).pack(side=tk.LEFT)
        
        self.guess_entry = ttk.Entry(input_frame, width=10, font=(self.current_font[0], 12))
        self.guess_entry.pack(side=tk.LEFT, padx=5)
        self.guess_entry.bind('<Return>', lambda e: self.make_guess())
        
        ttk.Button(input_frame, text="猜!", command=self.make_guess, style='Custom.TButton').pack(side=tk.LEFT)
        
        # 结果显示区域
        self.result_text = tk.StringVar()
        self.result_text.set("欢迎来到猜数字游戏！")
        
        result_label = ttk.Label(main_frame, textvariable=self.result_text, 
                               font=(self.current_font[0], 12), wraplength=350)
        result_label.pack(fill=tk.X, pady=10)
        
        # 猜测历史
        self.history_text = tk.StringVar()
        self.history_text.set("猜测历史将显示在这里")
        
        history_label = ttk.Label(main_frame, textvariable=self.history_text, 
                                font=(self.current_font[0], 10), wraplength=350)
        history_label.pack(fill=tk.X, pady=5)
        
        # 创建自定义样式
        style = ttk.Style()
        style.configure('Custom.TButton', font=(self.current_font[0], 10))
        style.configure('Custom.TRadiobutton', font=(self.current_font[0], 10))
        style.configure('Custom.TLabelframe', font=(self.current_font[0], 10))
        style.configure('Custom.TLabelframe.Label', font=(self.current_font[0], 10))
        
    def change_mode(self):
        """切换游戏模式"""
        self.game.set_game_mode(self.mode_var.get())
        if self.mode_var.get() == "1A2B":
            self.digits_frame.pack(side=tk.LEFT, padx=(10,0))
            self.game.set_digits(int(self.digits_var.get()))
        else:
            self.digits_frame.pack_forget()
        self.new_game()
        
    def new_game(self):
        """开始新游戏"""
        if self.mode_var.get() == "1A2B":
            self.game.set_digits(int(self.digits_var.get()))
            
        self.game.set_game_mode(self.mode_var.get())
        self.game.start_new_game()
        
        if self.mode_var.get() == "classic":
            self.result_text.set("新游戏已开始！猜一个1-100之间的数字")
        else:
            self.result_text.set(f"新游戏已开始！猜一个{self.game.digits}位数")
            
        self.history_text.set("")
        self.guess_entry.delete(0, tk.END)
        self.guess_entry.focus_set()
        
    def make_guess(self):
        """处理玩家猜测"""
        guess = self.guess_entry.get()
        if not guess:
            messagebox.showwarning("提示", "请输入一个数字")
            return
            
        result = self.game.make_guess(guess)
        self.result_text.set(result)
        
        # 更新历史记录
        current_history = self.history_text.get()
        if "历史将显示" in current_history:
            current_history = ""
        self.history_text.set(f"{current_history}\n第{self.game.guesses}次: {guess} -> {result}")
        
        self.guess_entry.delete(0, tk.END)
        self.guess_entry.focus_set()

if __name__ == "__main__":
    root = tk.Tk()
    try:
        app = GuessNumberUI(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("错误", f"程序运行出错: {str(e)}")