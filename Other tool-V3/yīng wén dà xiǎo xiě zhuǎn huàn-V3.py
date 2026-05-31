import os
import sys
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from fontTools.ttLib import TTFont


def to_upper(text):
    """Convert text to uppercase"""
    return text.upper()

def to_lower(text):
    """Convert text to lowercase"""
    return text.lower()

def to_title(text):
    """Convert text to title case (first letter of each word capitalized)"""
    return text.title()

def reverse_case(text):
    """Reverse the case of each character"""
    return text.swapcase()


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
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("snow_toolbox_master.EnglishCaseConverter")
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
            # 保存引用防止垃圾回收
            root._icon_image = icon_image
        except Exception:
            pass


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


def load_font():
    """从配置文件加载字体设置"""
    # 定义项目根目录和图片目录
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    IMAGE_DIR = PROJECT_ROOT / "Image"
    
    font_path = IMAGE_DIR / "AlibabaPuHuiTi-3-55-RegularL3.ttf"
    
    if not font_path.exists():
        messagebox.showerror("错误", f"找不到字体文件：{font_path}")
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
    
    # 使用 Windows API 注册字体
    if os.name == 'nt':
        import ctypes
        GDI32 = ctypes.windll.gdi32
        font_path_str = str(font_path).encode('utf-16-le') + b'\x00'
        GDI32.AddFontResourceW(font_path_str)
        print(f"成功加载自定义字体: {font_path}")
    
    from tkinter import font as tkfont
    current_font = (font_name, 10)
    return current_font


def create_gui():
    """Create and run the GUI interface"""
    # Input frame
    input_frame = ttk.Frame(root, padding="10")
    input_frame.pack(fill='x')
    
    ttk.Label(input_frame, text="输入文本:").pack(anchor='w')
    text_input = tk.Text(input_frame, height=5, width=50)
    text_input.pack(fill='x')
    
    # Options frame
    options_frame = ttk.Frame(root, padding="10")
    options_frame.pack(fill='x')
    
    case_var = tk.StringVar(value="upper")
    ttk.Radiobutton(options_frame, text="全部大写", variable=case_var, value="upper").pack(anchor='w')
    ttk.Radiobutton(options_frame, text="全部小写", variable=case_var, value="lower").pack(anchor='w')
    ttk.Radiobutton(options_frame, text="首字母大写", variable=case_var, value="title").pack(anchor='w')
    ttk.Radiobutton(options_frame, text="大小写反转", variable=case_var, value="reverse").pack(anchor='w')
    
    # Output frame
    output_frame = ttk.Frame(root, padding="10")
    output_frame.pack(fill='x')
    
    ttk.Label(output_frame, text="转换结果:").pack(anchor='w')
    text_output = tk.Text(output_frame, height=5, width=50, state='disabled')
    text_output.pack(fill='x')
    
    def convert_text():
        """Handle text conversion"""
        input_text = text_input.get("1.0", tk.END).strip()
        if not input_text:
            return
            
        if case_var.get() == "upper":
            result = to_upper(input_text)
        elif case_var.get() == "lower":
            result = to_lower(input_text)
        elif case_var.get() == "title":
            result = to_title(input_text)
        else:
            result = reverse_case(input_text)
            
        text_output.config(state='normal')
        text_output.delete("1.0", tk.END)
        text_output.insert("1.0", result)
        text_output.config(state='disabled')
    
    # Button frame
    button_frame = ttk.Frame(root, padding="10")
    button_frame.pack(fill='x')
    
    def copy_result():
        """Copy result to clipboard"""
        result = text_output.get("1.0", tk.END).strip()
        if result:
            root.clipboard_clear()
            root.clipboard_append(result)
    
    ttk.Button(button_frame, text="转换", command=convert_text).pack(side='left')
    ttk.Button(button_frame, text="清空", command=lambda: text_input.delete("1.0", tk.END)).pack(side='left')
    ttk.Button(button_frame, text="复制结果", command=copy_result).pack(side='left')
    ttk.Button(button_frame, text="退出", command=root.quit).pack(side='right')


if __name__ == '__main__':
    # 创建主窗口
    root = tk.Tk()

    # 首先检查开源协议文档是否存在并验证完整性
    if not check_license():
        messagebox.showerror(
            "错误", 
            "缺少授权！无法使用！请先获取授权！\n"
        )
        root.destroy()
        sys.exit(1)

    root.title("英文大小写转换")

    # 设置窗口图标
    set_window_icon(root)

    # 加载并注册字体
    try:
        custom_font = load_font()
        if custom_font:
            root.option_add('*Font', custom_font)
            print(f"成功设置字体: {custom_font[0]}")
    except Exception as e:
        error_msg = f"字体设置失败: {str(e)}"
        print(error_msg)
        messagebox.showwarning("字体设置", error_msg)

    create_gui()
    root.mainloop()