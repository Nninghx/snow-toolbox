import random
import ast
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from math import isclose
from itertools import permutations, product
import functools

class Game24Logic:
    """游戏逻辑部分，与界面分离"""
    def __init__(self):
        self.numbers = []
        self.solution = ""
        self.mode = "with_parentheses"  # 默认含括号模式
        self.solvable_combinations = self.load_solvable_combinations()
        self.operations = ['+', '-', '*', '/']
        self.last_save_file = ""
        
    def load_solvable_combinations(self):
        """从Core文件夹加载可解组合，根据当前模式选择文件"""
        # 根据模式选择文件名
        filename = "Y24_outcome.txt" if self.mode == "with_parentheses" else "N24_outcome.txt"
        file_path = Path("Core") / filename
        print(f"尝试加载文件: {file_path}, 绝对路径: {file_path.absolute()}")
        
        if file_path.exists():
            print("文件存在，开始读取...")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    # 移除可能的头部注释
                    if '#' in content:
                        content = content[content.find('['):]
                    if content.startswith('[') and content.endswith(']'):
                        print("检测到新格式文件，解析中...")
                        try:
                            data = ast.literal_eval(content)
                            print(f"成功加载 {len(data)} 条组合")
                            return data
                        except Exception as e:
                            print(f"解析新格式文件出错: {e}")
                    print("尝试作为旧格式文件转换...")
                    combinations = []
                    for line in content.splitlines():
                        line = line.strip()
                        if line:
                            try:
                                nums = list(map(int, line.split()))
                                if len(nums) == 4:
                                    combinations.append(nums)
                            except ValueError:
                                continue
                    print(f"转换完成，共 {len(combinations)} 条组合")
                    return combinations
            except Exception as e:
                print(f"加载可解组合文件出错: {str(e)}")
                import traceback
                traceback.print_exc()
        else:
            print("错误: 文件不存在")
        return []
        
    def generate_numbers(self, must_solvable=False):
        """生成4个1-13的数字"""
        if must_solvable and self.solvable_combinations:
            self.numbers = random.choice(self.solvable_combinations)
        else:
            self.numbers = [random.randint(1, 13) for _ in range(4)]
        return self.numbers
        
    def calculate_solution(self):
        """计算一种解法"""
        if not self.numbers:
            return "请先生成数字"
            
        nums = self.numbers.copy()
        ops = self.operations
        
        # 生成所有唯一数字排列
        unique_perms = set(permutations(range(4), 4))
        
        for a, b, c, d in unique_perms:
            n1, n2, n3, n4 = nums[a], nums[b], nums[c], nums[d]
            
            # 预计算所有可能的运算符组合
            op_combinations = product(range(4), repeat=3)
            
            for op1, op2, op3 in op_combinations:
                # 无括号模式
                if self.mode == "without_parentheses":
                    try:
                        expr = f"{n1}{ops[op1]}{n2}{ops[op2]}{n3}{ops[op3]}{n4}"
                        result = eval(expr)
                        if isclose(result, 24, abs_tol=1e-6):
                            self.solution = f"{expr} = 24"
                            return self.solution
                        elif isclose(result, 0, abs_tol=1e-6):
                            continue
                    except ZeroDivisionError:
                        continue
                        
                # 含括号模式
                else:
                    patterns = [
                        f"(({n1}{ops[op1]}{n2}){ops[op2]}{n3}){ops[op3]}{n4}",
                        f"({n1}{ops[op1]}({n2}{ops[op2]}{n3})){ops[op3]}{n4}",
                        f"({n1}{ops[op1]}{n2}){ops[op2]}({n3}{ops[op3]}{n4})",
                        f"{n1}{ops[op1]}(({n2}{ops[op2]}{n3}){ops[op3]}{n4})",
                        f"{n1}{ops[op1]}({n2}{ops[op2]}({n3}{ops[op3]}{n4}))"
                    ]
                    
                    for pattern in patterns:
                        try:
                            if isclose(eval(pattern), 24, abs_tol=1e-6):
                                self.solution = f"{pattern} = 24"
                                return self.solution
                        except ZeroDivisionError:
                            continue
                        
        self.solution = "无解"
        return self.solution
        
    @staticmethod
    def process_combination(comb, mode):
        """处理单个组合，检查是否可解"""
        local_solvable = set()
        for nums in set(permutations(comb)):
            game = Game24Logic()
            game.numbers = list(nums)
            game.mode = mode
            if game.calculate_solution() != "无解":
                local_solvable.add(tuple(sorted(nums)))
        return local_solvable
        
    def generate_all_solvable(self):
        """生成所有可解组合，分别保存含括号和不含括号的结果"""
        from itertools import combinations_with_replacement, permutations
        from math import isclose
        from multiprocessing import Pool, cpu_count
        import functools
        
        print("正在计算所有可能的可解组合...")
        numbers = range(1, 14)  # 1-13的数字
        
        # 生成所有不重复的4个数字组合
        unique_combinations = list(combinations_with_replacement(numbers, 4))
        total = len(unique_combinations)
        
        # 准备多进程处理
        num_processes = min(cpu_count(), 8)  # 最多使用8个进程
        chunk_size = max(1, total // (num_processes * 10))  # 动态分块大小
        
        # 并行处理含括号模式
        with Pool(num_processes) as pool:
            results = pool.starmap(
                Game24Logic.process_combination,
                [(comb, "with_parentheses") for comb in unique_combinations],
                chunksize=chunk_size
            )
            solvable_with_parentheses = set().union(*results)
        
        # 并行处理不含括号模式
        with Pool(num_processes) as pool:
            results = pool.starmap(
                Game24Logic.process_combination,
                [(comb, "without_parentheses") for comb in unique_combinations],
                chunksize=chunk_size
            )
            solvable_without_parentheses = set().union(*results)
        
        # 保存结果
        self.solvable_combinations = [list(comb) for comb in solvable_with_parentheses]
        self.save_results("Y24_outcome.txt")
        
        self.solvable_combinations = [list(comb) for comb in solvable_without_parentheses]
        self.save_results("N24_outcome.txt")
        
        print(f"计算完成，结果已分别保存")
        print(f"含括号可解组合: {len(solvable_with_parentheses)} 个")
        print(f"不含括号可解组合: {len(solvable_without_parentheses)} 个")
        
        # 恢复默认模式
        self.mode = "with_parentheses"
        return self.solvable_combinations
        
    def save_results(self, filename):
        """保存结果到Core文件夹"""
        if not self.solvable_combinations:
            messagebox.showwarning("警告", "没有可保存的数据")
            return False
            
        try:
            # 确保Core目录存在且有写入权限
            core_dir = Path("Core")
            core_dir.mkdir(exist_ok=True)
            if not os.access(core_dir, os.W_OK):
                messagebox.showerror("错误", "Core目录没有写入权限")
                return False
                
            filepath = core_dir / filename
            # 临时文件写入
            temp_path = filepath.with_suffix('.tmp')
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                # 更健壮的保存格式
                f.write("# 24点游戏可解组合\n")
                f.write("[\n")
                for comb in self.solvable_combinations:
                    f.write(f"    {comb},\n")
                f.write("]\n")
            
            # 替换原文件
            if filepath.exists():
                filepath.unlink()
            temp_path.rename(filepath)
            
            self.last_save_file = str(filepath)
            messagebox.showinfo("成功", f"结果已保存到 {filepath}")
            return True
            
        except Exception as e:
            error_msg = f"保存失败: {str(e)}"
            print(error_msg)
            messagebox.showerror("错误", error_msg)
            return False

class Game24UI:
    """图形化界面部分"""
    def __init__(self, root):
        self.root = root
        self.game = Game24Logic()
        self.setup_ui()
        
    def setup_ui(self):
        """设置界面布局"""
        self.root.title("24点游戏")
        self.root.geometry("500x400")
        
        # 加载字体配置
        try:
            import json
            font_path = Path('Core/ziti.json')
            if font_path.exists():
                with open(font_path, 'r', encoding='utf-8') as f:
                    font_config = json.load(f)
                    font_family = font_config.get('family', '微软雅黑')  # 与主程序默认字体保持一致
            else:
                print("字体配置文件不存在，使用默认字体")
                font_family = '微软雅黑'
        except Exception as e:
            print(f"加载字体配置失败: {e}, 使用默认字体")
            font_family = '微软雅黑'
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 数字显示区域
        self.numbers_label = ttk.Label(main_frame, text="数字: ", font=(font_family, 16))
        self.numbers_label.pack(pady=10)
        
        # 模式选择
        mode_frame = ttk.LabelFrame(main_frame, text="游戏模式", padding="10", style='Custom.TLabelframe')
        mode_frame.pack(fill=tk.X, pady=5)
        
        self.mode_var = tk.StringVar(value="with_parentheses")
        ttk.Radiobutton(mode_frame, text="含括号", variable=self.mode_var, 
                       value="with_parentheses", style='Custom.TRadiobutton').pack(side=tk.LEFT)
        ttk.Radiobutton(mode_frame, text="不含括号", variable=self.mode_var,
                       value="without_parentheses", style='Custom.TRadiobutton').pack(side=tk.LEFT)
        
        # 创建自定义样式
        style = ttk.Style()
        style.configure('Custom.TButton', font=(font_family, 10))
        style.configure('Custom.TRadiobutton', font=(font_family, 10))
        style.configure('Custom.TLabelframe', font=(font_family, 10))
        style.configure('Custom.TLabelframe.Label', font=(font_family, 10))
        
        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="普通模式", command=self.normal_mode, style='Custom.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="必含解模式", command=self.solvable_mode, style='Custom.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="显示解法", command=self.show_solution, style='Custom.TButton').pack(side=tk.LEFT, padx=5)
        
        # 解法显示区域
        solution_frame = ttk.LabelFrame(main_frame, text="解法", padding="10", style='Custom.TLabelframe')
        solution_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.solution_text = tk.Text(solution_frame, height=5, state=tk.DISABLED, font=(font_family, 10))
        scrollbar = ttk.Scrollbar(solution_frame, command=self.solution_text.yview)
        self.solution_text.configure(yscrollcommand=scrollbar.set)
        
        self.solution_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 高级功能菜单
        menubar = tk.Menu(self.root, font=(font_family, 10))
        advanced_menu = tk.Menu(menubar, tearoff=0, font=(font_family, 10))
        advanced_menu.add_command(label="生成所有可解组合", command=self.generate_all_solvable, font=(font_family, 10))
        menubar.add_cascade(label="修复", menu=advanced_menu, font=(font_family, 10))
        self.root.config(menu=menubar)
    
    def normal_mode(self):
        """普通模式生成数字"""
        self.game.mode = self.mode_var.get()
        numbers = self.game.generate_numbers()
        self.numbers_label.config(text=f"数字: {numbers}")
        self.clear_solution()
    
    def solvable_mode(self):
        """必含解模式生成数字"""
        # 根据当前模式加载对应的可解组合
        self.game.mode = self.mode_var.get()
        self.game.solvable_combinations = self.game.load_solvable_combinations()
        
        if not self.game.solvable_combinations:
            messagebox.showwarning("警告", f"没有找到{self.game.mode}模式的可解组合数据\n请先生成或提供Core/{'Y' if self.game.mode == 'with_parentheses' else 'N'}24_outcome.txt文件")
            return
            
        numbers = self.game.generate_numbers(must_solvable=True)
        self.numbers_label.config(text=f"数字: {numbers}")
        self.clear_solution()
    
    def show_solution(self):
        """显示解法"""
        if not self.game.numbers:
            messagebox.showwarning("警告", "请先生成数字")
            return
            
        self.game.mode = self.mode_var.get()
        solution = self.game.calculate_solution()
        self.solution_text.config(state=tk.NORMAL)
        self.solution_text.delete(1.0, tk.END)
        self.solution_text.insert(tk.END, solution)
        self.solution_text.config(state=tk.DISABLED)
    
    def generate_all_solvable(self):
        """生成所有可解组合"""
        confirm = messagebox.askyesno("确认", "生成所有可解组合可能需要较长时间，确定继续吗?\n结果将分别保存到两个文件。")
        if confirm:
            self.game.generate_all_solvable()
            messagebox.showinfo("完成", "已生成所有可解组合\n含括号结果保存在Core/Y24_outcome.txt\n不含括号结果保存在Core/N24_outcome.txt")
    
    def clear_solution(self):
        """清空解法显示"""
        self.solution_text.config(state=tk.NORMAL)
        self.solution_text.delete(1.0, tk.END)
        self.solution_text.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    try:
        # 设置窗口图标
        try:
            icon_path = Path("Image") / "icon.ico"
            if icon_path.exists():
                root.iconbitmap(str(icon_path))
            else:
                print(f"图标文件不存在: {icon_path}")
        except Exception as e:
            print(f"加载图标失败: {e}")
            
        app = Game24UI(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("错误", f"程序运行出错: {str(e)}")