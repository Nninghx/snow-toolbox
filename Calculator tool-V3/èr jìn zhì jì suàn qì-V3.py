import tkinter as tk
from tkinter import messagebox, simpledialog
import os
import json
import subprocess
from pathlib import Path

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

class BinaryCalculator:
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
        
        root.title("二进制计算器")
        root.geometry("500x450")
        root.resizable(False, False)
        
        # 设置窗口图标
        self.set_window_icon(root)
        
        # 加载并设置字体
        self.load_font()
        
        # 创建界面组件
        self.create_widgets()

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
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.binary_calculator")
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
    
    def create_widgets(self):
        # 输入框框架
        input_frame = tk.Frame(self.root)
        input_frame.pack(pady=(10, 5))
        
        # 二进制数1输入
        tk.Label(input_frame, text="二进制数1:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.binary1_entry = tk.Entry(input_frame, width=20)
        self.binary1_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # 二进制数2输入
        tk.Label(input_frame, text="二进制数2:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.binary2_entry = tk.Entry(input_frame, width=20)
        self.binary2_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # 运算选择
        tk.Label(input_frame, text="运算:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.operation_var = tk.StringVar(value="AND")
        operations = ["AND", "OR", "XOR", "NOT", "加法", "减法", "左移", "右移"]
        self.operation_menu = tk.OptionMenu(input_frame, self.operation_var, *operations)
        self.operation_menu.config(width=12)
        self.operation_menu.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        # 按钮框架
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        
        # 计算按钮
        self.calculate_btn = tk.Button(
            button_frame, text="计算", 
            command=self.calculate, bg="#4CAF50", fg="white"
        )
        self.calculate_btn.pack(side=tk.LEFT, padx=5)
        
        # 清除按钮
        self.clear_btn = tk.Button(
            button_frame, text="清除",
            command=self.clear, bg="#f44336", fg="white"
        )
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        # 转换按钮
        self.convert_btn = tk.Button(
            button_frame, text="十进制转二进制",
            command=self.decimal_to_binary, bg="#2196F3", fg="white"
        )
        self.convert_btn.pack(side=tk.LEFT, padx=5)
        
        # 结果显示区域
        self.result_frame = tk.Frame(self.root, bd=2, relief=tk.GROOVE)
        self.result_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        # 运算式显示
        self.equation_label = tk.Label(self.result_frame, text="运算式: ", anchor="w")
        self.equation_label.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        # 二进制结果显示
        self.binary_result_label = tk.Label(self.result_frame, text="二进制结果: ", anchor="w")
        self.binary_result_label.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # 十进制结果显示
        self.decimal_result_label = tk.Label(self.result_frame, text="十进制结果: ", anchor="w")
        self.decimal_result_label.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # 滚动条和文本框用于显示详细信息
        scrollbar = tk.Scrollbar(self.result_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.details_text = tk.Text(
            self.result_frame, 
            yscrollcommand=scrollbar.set, height=8
        )
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5)
        scrollbar.config(command=self.details_text.yview)

    def is_valid_binary(self, binary_str):
        """验证是否为有效的二进制字符串"""
        if not binary_str:
            return False
        return all(bit in ('0', '1') for bit in binary_str)

    def binary_to_decimal(self, binary_str):
        """二进制转十进制"""
        return int(binary_str, 2)

    def decimal_to_binary(self):
        """十进制转二进制"""
        decimal_str = tk.simpledialog.askstring("十进制转二进制", "请输入十进制整数:")
        if decimal_str is None:
            return
            
        try:
            decimal = int(decimal_str)
            binary = bin(decimal)[2:]  # 去掉'0b'前缀
            self.binary1_entry.delete(0, tk.END)
            self.binary1_entry.insert(0, binary)
        except ValueError:
            messagebox.showerror("错误", "请输入有效的整数!")

    def calculate(self):
        # 获取输入
        binary1 = self.binary1_entry.get().strip()
        operation = self.operation_var.get()
        
        # 根据运算类型验证输入
        if operation != "NOT":
            binary2 = self.binary2_entry.get().strip()
            if not binary2:
                messagebox.showerror("错误", "请输入二进制数2!")
                return
            if not self.is_valid_binary(binary2):
                messagebox.showerror("错误", "二进制数2包含非法字符!")
                return
        
        if not binary1:
            messagebox.showerror("错误", "请输入二进制数1!")
            return
        if not self.is_valid_binary(binary1):
            messagebox.showerror("错误", "二进制数1包含非法字符!")
            return
        
        try:
            # 转换为十进制
            decimal1 = self.binary_to_decimal(binary1)
            
            if operation != "NOT":
                decimal2 = self.binary_to_decimal(binary2)
            
            # 执行运算
            result_decimal = 0
            details = ""
            
            if operation == "AND":
                result_decimal = decimal1 & decimal2
                details = f"{binary1} AND {binary2}\n= {bin(result_decimal)[2:]}\n\n位运算:\n"
                for i in range(max(len(binary1), len(binary2))):
                    bit1 = binary1[-i-1] if i < len(binary1) else '0'
                    bit2 = binary2[-i-1] if i < len(binary2) else '0'
                    res_bit = '1' if bit1 == '1' and bit2 == '1' else '0'
                    details += f"位{i}: {bit1} & {bit2} = {res_bit}\n"
                    
            elif operation == "OR":
                result_decimal = decimal1 | decimal2
                details = f"{binary1} OR {binary2}\n= {bin(result_decimal)[2:]}\n\n位运算:\n"
                for i in range(max(len(binary1), len(binary2))):
                    bit1 = binary1[-i-1] if i < len(binary1) else '0'
                    bit2 = binary2[-i-1] if i < len(binary2) else '0'
                    res_bit = '1' if bit1 == '1' or bit2 == '1' else '0'
                    details += f"位{i}: {bit1} | {bit2} = {res_bit}\n"
                    
            elif operation == "XOR":
                result_decimal = decimal1 ^ decimal2
                details = f"{binary1} XOR {binary2}\n= {bin(result_decimal)[2:]}\n\n位运算:\n"
                for i in range(max(len(binary1), len(binary2))):
                    bit1 = binary1[-i-1] if i < len(binary1) else '0'
                    bit2 = binary2[-i-1] if i < len(binary2) else '0'
                    res_bit = '1' if bit1 != bit2 else '0'
                    details += f"位{i}: {bit1} ^ {bit2} = {res_bit}\n"
                    
            elif operation == "NOT":
                # 计算补位数
                bits = len(binary1)
                mask = (1 << bits) - 1
                result_decimal = (~decimal1) & mask
                details = f"NOT {binary1}\n= {bin(result_decimal)[2:]}\n\n按位取反:\n"
                for i in range(len(binary1)):
                    bit = binary1[-i-1]
                    res_bit = '0' if bit == '1' else '1'
                    details += f"位{i}: ~{bit} = {res_bit}\n"
                    
            elif operation == "加法":
                result_decimal = decimal1 + decimal2
                details = f"{binary1} + {binary2}\n= {bin(result_decimal)[2:]}\n\n十进制: {decimal1} + {decimal2} = {result_decimal}"
                
            elif operation == "减法":
                result_decimal = decimal1 - decimal2
                details = f"{binary1} - {binary2}\n= {bin(result_decimal)[2:]}\n\n十进制: {decimal1} - {decimal2} = {result_decimal}"
                
            elif operation == "左移":
                result_decimal = decimal1 << decimal2
                details = f"{binary1} << {binary2}\n= {bin(result_decimal)[2:]}\n\n相当于乘以2^{decimal2}: {decimal1} * {2**decimal2} = {result_decimal}"
                
            elif operation == "右移":
                result_decimal = decimal1 >> decimal2
                details = f"{binary1} >> {binary2}\n= {bin(result_decimal)[2:]}\n\n相当于除以2^{decimal2}: {decimal1} / {2**decimal2} = {result_decimal}"
            
            # 显示结果
            result_binary = bin(result_decimal)[2:]
            self.equation_label.config(text=f"运算式: {binary1} {operation} {binary2 if operation != 'NOT' else ''}")
            self.binary_result_label.config(text=f"二进制结果: {result_binary}")
            self.decimal_result_label.config(text=f"十进制结果: {result_decimal}")
            
            # 显示详细信息
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, details)
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的二进制数!")
    
    def clear(self):
        self.binary1_entry.delete(0, tk.END)
        self.binary2_entry.delete(0, tk.END)
        self.operation_var.set("AND")
        self.equation_label.config(text="运算式: ")
        self.binary_result_label.config(text="二进制结果: ")
        self.decimal_result_label.config(text="十进制结果: ")
        self.details_text.delete(1.0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = BinaryCalculator(root)
    root.mainloop()