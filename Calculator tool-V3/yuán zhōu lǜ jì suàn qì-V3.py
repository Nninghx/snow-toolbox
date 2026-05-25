import math
import time
import json
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from decimal import Decimal, getcontext
import threading
import os
import sys
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from fontTools.ttLib import TTFont
    FONTTOOLS_AVAILABLE = True
except ImportError:
    FONTTOOLS_AVAILABLE = False

# 提高整数字符串转换限制以适应大数计算
sys.set_int_max_str_digits(100000000)  

class PiCalculatorApp:
    def __init__(self, root):
        self.root = root
        
        # 首先检查授权
        if not self.check_license():
            messagebox.showerror(
                "错误", 
                "缺少授权！无法使用！请先获取授权！"
            )
            root.destroy()
            return
        
        root.title("圆周率计算器")
        root.geometry("400x300")
        
        # 设置窗口图标
        self.set_window_icon(root)
        
        # 加载字体配置
        self.load_font()
        
        self.setup_ui()
        
        self.calculating = False
        self.cancel_flag = False

    def setup_ui(self):
        # 输入框
        ttk.Label(self.root, text="计算位数:").pack(pady=5)
        self.digits_entry = ttk.Entry(self.root)
        self.digits_entry.pack(pady=5)
        
        # 按钮
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=10)
        
        self.calc_button = ttk.Button(btn_frame, text="开始计算", command=self.start_calculation)
        self.calc_button.pack(side=tk.LEFT, padx=5)
        
        self.resume_button = ttk.Button(btn_frame, text="恢复计算", command=self.resume_calculation)
        self.resume_button.pack(side=tk.LEFT, padx=5)
        self.check_resume_file()
        
        # 取消按钮
        self.cancel_button = ttk.Button(self.root, text="取消计算", state=tk.DISABLED, command=self.cancel_calculation)
        self.cancel_button.pack(pady=5)
        
        # 进度条
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(pady=10)
        
        # 计算位数显示
        self.digits_label = ttk.Label(self.root, text="当前计算位数: 0")
        self.digits_label.pack()
        
        # 结果标签
        self.result_label = ttk.Label(self.root, text="")
        self.result_label.pack(pady=10)

    def start_calculation(self):
        if self.calculating:
            return
            
        try:
            digits = int(self.digits_entry.get())
            if digits <= 0:
                messagebox.showerror("错误", "请输入正整数")
                return
                
            # 检查是否有可复用的临时状态
            if os.path.exists(self.get_temp_file_path()):
                with open(self.get_temp_file_path(), "r") as f:
                    lines = f.readlines()
                    saved_digits = int(lines[0].strip())
                    
                    # 如果已有结果足够大，直接复用
                    if saved_digits >= digits:
                        result_file = f"pi_{saved_digits}digits.txt"
                        if os.path.exists(result_file):
                            with open(result_file, "r") as result_f:
                                pi = result_f.read()[:digits+2]
                                filename = f"pi_{digits}digits.txt"
                                with open(filename, 'w') as outfile:
                                    outfile.write(pi)
                                self.root.after(0, self.show_result, f"复用已有结果！\n结果已保存到{filename}")
                                return
                    
                    # 如果需求位数更大，从临时状态继续计算
                    elif saved_digits < digits:
                        confirm = messagebox.askyesno("继续计算", 
                            f"发现已有{saved_digits}位的计算状态，是否继续计算到{digits}位？")
                        if confirm:
                            digits, M, L, X, K, S, current_iteration = self.load_temp_state()
                            self.calculating = True
                            self.cancel_flag = False
                            self.calc_button.config(state=tk.DISABLED)
                            self.cancel_button.config(state=tk.NORMAL)
                            self.progress["value"] = (current_iteration / (digits//14 + 2)) * 100
                            self.result_label.config(text=f"继续计算到{digits}位...")
                            
                            threading.Thread(
                                target=self.calculate_pi, 
                                args=(digits, M, L, X, K, S, current_iteration),
                                daemon=True
                            ).start()
                            return
                        
        except ValueError:
            messagebox.showerror("错误", "请输入有效数字")
            return
            
        self.calculating = True
        self.cancel_flag = False
        self.calc_button.config(state=tk.DISABLED)
        self.resume_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)
        self.progress["value"] = 0
        self.result_label.config(text="计算中...")
        
        # 在新线程中执行计算
        threading.Thread(target=self.calculate_pi, args=(digits,), daemon=True).start()

    def cancel_calculation(self):
        self.cancel_flag = True
        self.result_label.config(text="正在取消...")

    def get_temp_file_path(self):
        return os.path.join("Core", "pi_calc_temp.dat")

    def check_resume_file(self):
        try:
            with open(self.get_temp_file_path(), "r") as f:
                self.resume_button.config(state=tk.NORMAL)
        except:
            self.resume_button.config(state=tk.DISABLED)

    def save_temp_state(self, digits, M, L, X, K, S, current_iteration):
        temp_path = self.get_temp_file_path()
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        with open(temp_path, "w") as f:
            f.write(f"{digits}\n")
            # 分开写入每个大数，避免字符串连接时的限制
            f.write(f"{M}\n")
            f.write(f"{L}\n")
            f.write(f"{X}\n")
            f.write(f"{K}\n")
            f.write(f"{S}\n")
            f.write(f"{current_iteration}")

    def load_temp_state(self):
        with open(self.get_temp_file_path(), "r") as f:
            digits = int(f.readline())
            # 逐行读取，避免大数处理问题
            M_line = f.readline()
            L_line = f.readline()
            X_line = f.readline()
            K_line = f.readline()
            S_line = f.readline()
            current_iteration = int(f.readline())
            
            M = Decimal(M_line.strip())
            L = Decimal(L_line.strip())
            X = Decimal(X_line.strip())
            K = int(K_line.strip())
            S = Decimal(S_line.strip())
            
            return digits, M, L, X, K, S, current_iteration

    def resume_calculation(self):
        if self.calculating:
            return
            
        try:
            digits, M, L, X, K, S, current_iteration = self.load_temp_state()
            self.digits_entry.delete(0, tk.END)
            self.digits_entry.insert(0, str(digits))
            
            self.calculating = True
            self.cancel_flag = False
            self.calc_button.config(state=tk.DISABLED)
            self.cancel_button.config(state=tk.NORMAL)
            self.resume_button.config(state=tk.DISABLED)
            self.progress["value"] = (current_iteration / (digits//14 + 2)) * 100
            self.result_label.config(text=f"恢复计算到{digits}位...")
            
            threading.Thread(
                target=self.calculate_pi, 
                args=(digits, M, L, X, K, S, current_iteration),
                daemon=True
            ).start()
        except:
            messagebox.showerror("错误", "无法恢复计算")
            self.check_resume_file()

    def calculate_pi(self, digits, M=None, L=None, X=None, K=None, S=None, start_iteration=0):
        start_time = time.time()
        getcontext().prec = digits + 2
        
        # 预计算常用常量
        CONST_L = Decimal(545140134)
        CONST_X = Decimal(-262537412640768000)
        
        if M is None:  # 全新计算
            C = 426880 * Decimal(10005).sqrt()
            M = Decimal(1)
            L = Decimal(13591409)
            X = Decimal(1)
            K = 6
            S = Decimal(L)
        else:  # 恢复计算
            C = 426880 * Decimal(10005).sqrt()
        
        total_iterations = digits // 14 + 2
        batch_size = 100  # 批量处理100次迭代
        last_update_time = time.time()
        
        for batch_start in range(1, total_iterations, batch_size):
            if self.cancel_flag:
                break
                
            batch_end = min(batch_start + batch_size, total_iterations)
            for i in range(batch_start, batch_end):
                # 优化大数除法计算
                numerator = (K**3 - 16*K) * M
                denominator = (i+1)**3
                if numerator % denominator == 0:
                    M = numerator // denominator
                else:
                    M = Decimal(numerator) / Decimal(denominator)
                    
                L += CONST_L
                X *= CONST_X
                S += Decimal(M * L) / X
                K += 12
                
                # 智能更新进度(每秒最多更新一次)
                current_time = time.time()
                if current_time - last_update_time > 0.1:  # 每0.1秒更新一次
                    progress = (i / total_iterations) * 100
                    calculated_digits = min(digits, int(14 * i))
                    self.root.after(0, self.update_progress, progress, calculated_digits)
                    last_update_time = current_time
            
            # 批量保存状态
            self.save_temp_state(digits, M, L, X, K, S, batch_end-1)
        
        if not self.cancel_flag:
            pi = C / S
            pi_str = str(pi)[:digits + 2]
            elapsed = time.time() - start_time
            
            filename = f"pi_{digits}digits.txt"
            with open(filename, 'w') as f:
                f.write(pi_str)
            
            # 保存完整结果到文件和临时状态
            self.save_temp_state(digits, M, L, X, K, S, total_iterations)
            # 确保结果文件存在
            filename = f"pi_{digits}digits.txt"
            if not os.path.exists(filename):
                with open(filename, 'w') as f:
                    f.write(pi_str)
                
            self.root.after(0, self.show_result, f"计算完成！耗时{elapsed:.2f}秒\n结果已保存到{filename}")
        else:
            self.root.after(0, self.show_result, "计算已取消")
            
        self.root.after(0, self.reset_ui)

    def update_progress(self, value, calculated_digits=0):
        self.progress["value"] = value
        self.digits_label.config(text=f"当前计算位数: {calculated_digits}")
        self.root.update()

    def show_result(self, message):
        messagebox.showinfo("结果", message)
        self.result_label.config(text=message.split('\n')[0])

    def reset_ui(self):
        self.calculating = False
        self.cancel_flag = False
        self.calc_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.DISABLED)
        self.digits_label.config(text="当前计算位数: 0")
        self.check_resume_file()

    def check_license(self):
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

    def set_window_icon(self, master):
        """设置应用程序窗口图标"""
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        IMAGE_DIR = PROJECT_ROOT / "Image"
        
        icon_ico_path = IMAGE_DIR / "icon.ico"
        icon_png_path = IMAGE_DIR / "icon.png"

        # Windows系统设置应用ID
        if os.name == 'nt':
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.pi_calculator")
            except Exception:
                pass

        # 尝试设置ICO图标
        if icon_ico_path.exists():
            try:
                master.iconbitmap(default=str(icon_ico_path))
            except Exception:
                try:
                    master.iconbitmap(str(icon_ico_path))
                except Exception:
                    pass

        # 尝试设置PNG图标
        if hasattr(master, "iconphoto") and icon_png_path.exists():
            try:
                self.icon_image = tk.PhotoImage(file=str(icon_png_path))
                master.iconphoto(True, self.icon_image)
            except Exception:
                pass

    def load_font(self):
        """从配置文件加载字体设置"""
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
            print(f"成功加载自定义字体: {font_path}")
        
        from tkinter import font as tkfont
        self.current_font = (font_name, 12)
        self.root.option_add("*Font", self.current_font)

def compute_pi(digits):
    """使用Chudnovsky算法计算圆周率到指定位数"""
    getcontext().prec = digits + 2  # 设置足够的精度
    
    C = 426880 * Decimal(10005).sqrt()
    M = 1
    L = 13591409
    X = 1
    K = 6
    S = Decimal(L)
    
    for i in range(1, digits//14 + 2):
        M = (K**3 - 16*K) * M // (i+1)**3
        L += 545140134
        X *= -262537412640768000
        S += Decimal(M * L) / X
        K += 12
    
    pi = C / S
    return str(pi)[:digits + 2]  # 去掉多余的精度

def save_pi_to_file(pi, filename):
    """将圆周率结果保存到文件"""
    with open(filename, 'w') as f:
        f.write(pi)

if __name__ == '__main__':
    root = tk.Tk()
    app = PiCalculatorApp(root)
    root.mainloop()