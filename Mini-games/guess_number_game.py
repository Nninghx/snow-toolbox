import tkinter as tk
from tkinter import ttk, messagebox
import random
from pathlib import Path
import os  # 添加os模块导入

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
        self.game = GuessNumberLogic()
        self._load_font_config()
        
        # 设置窗口图标
        try:
            icon_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "Image", "icon.ico"))
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
            else:
                print(f"图标文件不存在: {icon_path}")
        except Exception as e:
            print(f"加载图标失败: {str(e)}")
            
        self.setup_ui()
        
    def _load_font_config(self):
        """从Core/ziti.json加载字体配置"""
        self.font_family = '微软雅黑'  # 默认值
        try:
            import json
            from pathlib import Path
            font_path = Path(__file__).parent.parent / 'Core' / 'ziti.json'
            if font_path.exists():
                with open(font_path, 'r', encoding='utf-8') as f:
                    font_config = json.load(f)
                    self.font_family = font_config.get('family', '微软雅黑')
                print(f"已加载字体: {self.font_family}")
            else:
                print(f"字体配置文件不存在于 {font_path}，使用默认字体")
        except Exception as e:
            print(f"加载字体配置失败: {e}, 使用默认字体")
        
    def setup_ui(self):
        """设置界面布局"""
        self.root.title("猜数字小游戏")
        self.root.geometry("500x400")
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 游戏设置区域
        settings_frame = ttk.LabelFrame(main_frame, text="游戏设置", padding="10")
        settings_frame.pack(fill=tk.X, pady=5)
        
        # 游戏模式选择
        ttk.Label(settings_frame, text="游戏模式:", font=(self.font_family, 10)).pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value="classic")
        ttk.Radiobutton(settings_frame, text="经典模式", variable=self.mode_var, 
                       value="classic", command=self.change_mode, style='Custom.TRadiobutton').pack(side=tk.LEFT)
        ttk.Radiobutton(settings_frame, text="1A2B模式", variable=self.mode_var,
                       value="1A2B", command=self.change_mode, style='Custom.TRadiobutton').pack(side=tk.LEFT)
        
        # 位数选择 (仅1A2B模式显示)
        self.digits_frame = ttk.Frame(settings_frame)
        ttk.Label(self.digits_frame, text="数字位数:", font=(self.font_family, 10)).pack(side=tk.LEFT)
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
        
        ttk.Label(input_frame, text="输入猜测:", font=(self.font_family, 12)).pack(side=tk.LEFT)
        
        self.guess_entry = ttk.Entry(input_frame, width=10, font=(self.font_family, 12))
        self.guess_entry.pack(side=tk.LEFT, padx=5)
        self.guess_entry.bind('<Return>', lambda e: self.make_guess())
        
        ttk.Button(input_frame, text="猜!", command=self.make_guess, style='Custom.TButton').pack(side=tk.LEFT)
        
        # 结果显示区域
        self.result_text = tk.StringVar()
        self.result_text.set("欢迎来到猜数字游戏！")
        
        result_label = ttk.Label(main_frame, textvariable=self.result_text, 
                               font=(self.font_family, 12), wraplength=350)
        result_label.pack(fill=tk.X, pady=10)
        
        # 猜测历史
        self.history_text = tk.StringVar()
        self.history_text.set("猜测历史将显示在这里")
        
        history_label = ttk.Label(main_frame, textvariable=self.history_text, 
                                font=(self.font_family, 10), wraplength=350)
        history_label.pack(fill=tk.X, pady=5)
        
        # 创建自定义样式
        style = ttk.Style()
        style.configure('Custom.TButton', font=(self.font_family, 10))
        
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