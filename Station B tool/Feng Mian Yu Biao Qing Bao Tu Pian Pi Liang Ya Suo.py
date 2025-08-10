import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image
import threading
from pathlib import Path
from typing import Tuple, Optional
import io

class ImageProcessor:
    """图片处理核心类"""
    
    def __init__(self):
        # 定义图片类型的尺寸和大小限制
        self.IMAGE_SPECS = {
            'cover': {
                'size': (360, 360),
                'max_size': 300 * 1024,  # 300KB
                'min_quality': 60,        # 最低质量限制
                'allow_webp': False       # 不允许转换为WebP
            },
            'emoji': {
                'size': (162, 162),
                'max_size': 16 * 1024,    # 16KB
                'min_quality': 30,        # 允许更低的质量
                'allow_webp': True        # 允许转换为WebP
            }
        }
        
    def resize_image(self, image: Image.Image, target_size: Tuple[int, int]) -> Image.Image:
        """调整图片尺寸，保持宽高比并优化图片质量"""
        # 计算目标尺寸
        target_ratio = target_size[0] / target_size[1]
        img_ratio = image.width / image.height
        
        if img_ratio > target_ratio:
            # 图片更宽，以高度为准
            new_height = target_size[1]
            new_width = int(new_height * img_ratio)
        else:
            # 图片更高，以宽度为准
            new_width = target_size[0]
            new_height = int(new_width / img_ratio)
            
        print(f"调整尺寸: {image.size} -> ({new_width}, {new_height})")
        
        # 使用高质量的重采样方法
        resized = image.resize((new_width, new_height), 
                             Image.Resampling.LANCZOS,
                             reducing_gap=2.0)
        
        # 创建目标尺寸的新图片（居中放置）
        new_img = Image.new('RGBA', target_size, (0, 0, 0, 0))
        paste_x = (target_size[0] - new_width) // 2
        paste_y = (target_size[1] - new_height) // 2
        
        # 如果是RGBA模式，使用alpha通道作为mask
        if resized.mode == 'RGBA':
            new_img.paste(resized, (paste_x, paste_y), resized)
        else:
            new_img.paste(resized, (paste_x, paste_y))
        
        print(f"最终尺寸: {new_img.size}")
        return new_img
    
    def compress_image(self, image: Image.Image, max_size: int, min_quality: int = 30) -> Optional[bytes]:
        """压缩图片到指定大小以下"""
        
        def try_save_image(img: Image.Image, format: str, **save_args) -> Optional[bytes]:
            """尝试保存图片并返回字节数据"""
            buffer = io.BytesIO()
            img.save(buffer, format, **save_args)
            size = buffer.tell()
            print(f"尝试 {format} 格式，参数：{save_args}，大小：{size/1024:.1f}KB")
            if size <= max_size:
                buffer.seek(0)
                return buffer.getvalue()
            return None
            
        # 如果是RGBA模式（带透明通道）
        if image.mode == 'RGBA':
            # 1. 首先尝试直接优化PNG
            result = try_save_image(image, 'PNG', optimize=True)
            if result:
                return result
                
            # 2. 尝试减少颜色数量
            for colors in [256, 128, 64, 32]:
                quantized = image.quantize(colors=colors, method=2)  # method=2 使用中位切分法
                converted = quantized.convert('RGBA')  # 转回RGBA模式
                result = try_save_image(converted, 'PNG', optimize=True)
                if result:
                    return result
            
            # 3. 尝试更激进的压缩方法
            for colors in [256, 128, 64, 32]:
                # 分离透明通道
                rgb = image.convert('RGB')
                alpha = image.split()[3]
                
                # 对RGB部分进行量化
                quantized_rgb = rgb.quantize(colors=colors, method=2)
                
                # 重新组合透明通道
                quantized_rgba = Image.new('RGBA', image.size)
                quantized_rgba.paste(quantized_rgb, mask=alpha)
                
                result = try_save_image(quantized_rgba, 'PNG', optimize=True)
                if result:
                    return result
                    
            print("警告：无法将PNG压缩到目标大小，尝试转换为带透明度的WebP格式")
            # 4. 最后尝试WebP格式（支持透明度的有损压缩）
            quality = 90
            while quality >= min_quality:
                result = try_save_image(image, 'WEBP', quality=quality, lossless=False)
                if result:
                    return result
                quality -= 5
                
        else:  # 非透明图片使用JPEG
            quality = 95
            while quality >= min_quality:
                result = try_save_image(image, 'JPEG', quality=quality, optimize=True)
                if result:
                    return result
                quality -= 5
        
        return None
    
    def process_image(self, input_path: str, output_path: str, image_type: str) -> bool:
        """处理单个图片"""
        try:
            # 获取目标规格
            if image_type not in self.IMAGE_SPECS:
                print(f"错误: 未知的图片类型: {image_type}")
                return False
                
            specs = self.IMAGE_SPECS[image_type]
            print(f"\n{'='*50}")
            print(f"开始处理图片:")
            print(f"输入文件: {input_path}")
            print(f"输出路径: {output_path}")
            print(f"处理类型: {image_type}")
            print(f"目标参数: 尺寸={specs['size']}, 最大大小={specs['max_size']/1024:.1f}KB")
            print(f"压缩选项: 最低质量={specs['min_quality']}, 允许WebP={specs['allow_webp']}")
            
            # 检查输入文件
            if not os.path.exists(input_path):
                print(f"错误: 输入文件不存在: {input_path}")
                return False
            
            # 检查文件大小
            input_size = os.path.getsize(input_path)
            print(f"原始文件大小: {input_size/1024:.1f}KB")
            
            # 如果原始文件已经小于目标大小，检查是否需要调整尺寸
            if input_size <= specs['max_size']:
                print("文件大小已符合要求，检查是否需要调整尺寸...")
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 打开并验证图片
            try:
                with Image.open(input_path) as img:
                    print(f"图片信息: 尺寸={img.size}, 模式={img.mode}, 格式={img.format}")
                    
                    # 检查是否是支持的格式
                    if img.format not in ['PNG', 'JPEG', 'JPG']:
                        print(f"警告: 不支持的图片格式: {img.format}")
                    
                    # 转换颜色模式
                    if img.mode not in ['RGB', 'RGBA']:
                        print(f"转换颜色模式: {img.mode} -> RGBA")
                        img = img.convert('RGBA')
                    
                    # 调整尺寸
                    resized_img = self.resize_image(img, specs['size'])
                    
                    # 压缩图片
                    print("\n开始压缩图片...")
                    compressed_data = self.compress_image(
                        resized_img, 
                        specs['max_size'],
                        specs['min_quality']
                    )
                    
                    if compressed_data is None:
                        print("错误: 无法将图片压缩到目标大小")
                        print("建议: 尝试手动优化图片或调整压缩参数")
                        return False
                    
                    compressed_size = len(compressed_data)
                    print(f"压缩后大小: {compressed_size/1024:.1f}KB")
                    print(f"压缩率: {(1 - compressed_size/input_size) * 100:.1f}%")
                    
                    # 保存压缩后的图片
                    try:
                        with open(output_path, 'wb') as f:
                            f.write(compressed_data)
                        
                        # 验证输出文件
                        if os.path.exists(output_path):
                            output_size = os.path.getsize(output_path)
                            print(f"\n处理完成:")
                            print(f"输出文件: {output_path}")
                            print(f"最终大小: {output_size/1024:.1f}KB")
                            
                            # 验证输出文件可以被正常打开
                            try:
                                with Image.open(output_path) as verify_img:
                                    print(f"输出格式: {verify_img.format}")
                                    print(f"输出尺寸: {verify_img.size}")
                                return True
                            except Exception as e:
                                print(f"警告: 输出文件完整性检查失败: {str(e)}")
                                return False
                        else:
                            print("错误: 文件保存失败，无法找到输出文件")
                            return False
                            
                    except Exception as e:
                        print(f"保存文件时出错: {str(e)}")
                        return False
                    
            except Exception as e:
                print(f"处理图片时出错: {str(e)}")
                return False
                
        except Exception as e:
            print(f"发生未预期的错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

class CompressorGUI:
    """图形界面类"""
    
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("B站专用封面与表情包图片批量压缩工具")
        self.window.geometry("600x400")
        # 设置窗口图标
        try:
            self.window.iconbitmap('Image/icon.ico')
        except Exception as e:
            print(f"图标加载失败: {str(e)}")
        
        # 动态加载字体设置
        try:
            import json
            with open('Core/ziti.json', 'r', encoding='utf-8') as f:
                font_settings = json.load(f)
            font_family = font_settings.get('family', 'Microsoft YaHei')
            self.window.option_add('*Font', (font_family, 10))
        except Exception as e:
            print(f"加载字体设置失败: {str(e)}")
            self.window.option_add('*Font', ('Microsoft YaHei', 10))
        
        self.processor = ImageProcessor()
        self.setup_gui()
        
    def setup_gui(self):
        """设置GUI界面"""
        # 配置主窗口网格
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        
        # 创建主框架
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(1, weight=1)
        
        # 输入目录选择
        ttk.Label(main_frame, text="输入目录:").grid(row=0, column=0, sticky=tk.W)
        self.input_path = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.input_path, width=50).grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E))
        ttk.Button(main_frame, text="浏览", command=self.select_input_dir).grid(row=0, column=2)
        
        # 输出目录选择
        ttk.Label(main_frame, text="输出目录:").grid(row=1, column=0, sticky=tk.W)
        self.output_path = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.output_path, width=50).grid(row=1, column=1, padx=5, sticky=(tk.W, tk.E))
        ttk.Button(main_frame, text="浏览", command=self.select_output_dir).grid(row=1, column=2)
        
        # 图片类型选择
        type_frame = ttk.LabelFrame(main_frame, text="图片类型", padding="5")
        type_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        self.image_type = tk.StringVar(value="cover")
        ttk.Radiobutton(type_frame, text="B站专用封面图 (360x360, 300KB)", value="cover", 
                       variable=self.image_type).grid(row=0, column=0, padx=20)
        ttk.Radiobutton(type_frame, text="B站专用表情图 (162x162, 16KB)", value="emoji", 
                       variable=self.image_type).grid(row=0, column=1, padx=20)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # 状态显示
        self.status_text = tk.StringVar(value="就绪")
        status_label = ttk.Label(main_frame, textvariable=self.status_text)
        status_label.grid(row=4, column=0, columnspan=3)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=10)
        
        # 帮助按钮
        ttk.Button(button_frame, text="帮助", command=self.show_help).pack(side=tk.LEFT, padx=5)
        
        # 开始按钮
        self.start_button = ttk.Button(button_frame, text="开始压缩", command=self.start_processing)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # 创建日志区域
        self.create_log_area(main_frame)
        
    def create_log_area(self, main_frame):
        """创建日志显示区域"""
        # 创建日志框架
        log_frame = ttk.LabelFrame(main_frame, text="处理日志", padding="5")
        log_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        main_frame.rowconfigure(6, weight=1)
        
        # 创建文本框和滚动条
        self.log_text = tk.Text(log_frame, height=10, width=60, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # 放置文本框和滚动条
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 配置日志框架的网格
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 设置文本框只读
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, "准备就绪，等待开始处理...\n")
        self.log_text.see(tk.END)
        
    def select_input_dir(self):
        """选择输入目录"""
        directory = filedialog.askdirectory()
        if directory:
            self.input_path.set(directory)
            
    def select_output_dir(self):
        """选择输出目录"""
        directory = filedialog.askdirectory()
        if directory:
            self.output_path.set(directory)
            
    def process_images(self):
        """处理所有图片"""
        try:
            input_dir = self.input_path.get()
            output_dir = self.output_path.get()
            image_type = self.image_type.get()
            
            # 检查输入目录是否存在
            if not os.path.exists(input_dir):
                messagebox.showerror("错误", f"输入目录不存在：{input_dir}")
                self.status_text.set("错误：输入目录不存在")
                self.start_button['state'] = 'normal'
                return
            
            # 检查输入目录是否可读
            if not os.access(input_dir, os.R_OK):
                messagebox.showerror("错误", f"无法读取输入目录：{input_dir}")
                self.status_text.set("错误：无法读取输入目录")
                self.start_button['state'] = 'normal'
                return
            
            # 尝试创建输出目录
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("错误", f"无法创建输出目录：{str(e)}")
                self.status_text.set("错误：无法创建输出目录")
                self.start_button['state'] = 'normal'
                return
            
            # 检查输出目录是否可写
            if not os.access(output_dir, os.W_OK):
                messagebox.showerror("错误", f"无法写入输出目录：{output_dir}")
                self.status_text.set("错误：无法写入输出目录")
                self.start_button['state'] = 'normal'
                return
            
            # 获取所有图片文件
            image_files = []
            for ext in ('.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG'):
                image_files.extend(Path(input_dir).glob(f'*{ext}'))
            
            if not image_files:
                messagebox.showwarning("警告", "未找到支持的图片文件！\n支持的格式：PNG、JPG、JPEG")
                self.status_text.set("就绪")
                self.start_button['state'] = 'normal'
                return
            
            # 创建日志区域
            if not hasattr(self, 'log_text'):
                self.create_log_area()
            
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, f"找到 {len(image_files)} 个图片文件\n")
            self.log_text.insert(tk.END, f"开始处理...\n\n")
            self.log_text.see(tk.END)
            
            # 处理每个图片
            total = len(image_files)
            success_count = 0
            failed_files = []
            
            for i, img_path in enumerate(image_files):
                self.log_text.insert(tk.END, f"处理: {img_path.name}\n")
                self.log_text.see(tk.END)
                
                output_path = Path(output_dir) / img_path.name
                
                if self.processor.process_image(str(img_path), str(output_path), image_type):
                    success_count += 1
                    self.log_text.insert(tk.END, f"成功: {img_path.name}\n")
                else:
                    failed_files.append(img_path.name)
                    self.log_text.insert(tk.END, f"失败: {img_path.name}\n")
                
                self.log_text.insert(tk.END, "-" * 50 + "\n")
                self.log_text.see(tk.END)
                
                # 更新进度
                progress = (i + 1) / total * 100
                self.progress_var.set(progress)
                self.status_text.set(f"处理中... {i+1}/{total}")
                self.window.update_idletasks()
            
            # 完成处理
            self.status_text.set(f"完成！成功处理 {success_count}/{total} 个文件")
            self.start_button['state'] = 'normal'
            
            # 显示详细结果
            result_message = f"处理完成！\n\n成功: {success_count}\n失败: {total-success_count}"
            if failed_files:
                result_message += "\n\n失败的文件:\n" + "\n".join(failed_files)
            
            messagebox.showinfo("完成", result_message)
            
        except Exception as e:
            import traceback
            error_msg = f"处理过程中出错：\n{str(e)}\n\n{traceback.format_exc()}"
            self.log_text.insert(tk.END, f"\n错误：\n{error_msg}\n")
            self.log_text.see(tk.END)
            messagebox.showerror("错误", f"处理过程中出错：\n{str(e)}")
            self.status_text.set("处理出错")
            self.start_button['state'] = 'normal'
        
    def show_help(self):
        """显示帮助信息"""
        help_text = """B站专用封面与表情包图片批量压缩工具 使用说明

1. 选择输入目录：包含需要压缩的图片文件
2. 选择输出目录：压缩后的图片将保存到这里
3. 选择图片类型：
   - 封面图：360x360像素，最大300KB
   - 表情图：162x162像素，最大16KB
4. 点击"开始压缩"按钮开始处理

支持的图片格式：PNG、JPG、JPEG
代码层面无需联网，无需登录，无需注册，无需授权
功能设计无需联网,数据完全本地处理
无网络漏洞风险：由于不涉及网络通信，不存在因网络请求导致的数据泄露风险
提示:
- 项目测试人员:软软酱Aruan
- 作者:宁幻雪(叁垣伍瑞肆凶廿捌宿宿)
- 联系方式:https://space.bilibili.com/556216088
- 

"""
        messagebox.showinfo("帮助", help_text)
        
    def start_processing(self):
        """开始处理图片"""
        # 检查输入
        if not self.input_path.get() or not self.output_path.get():
            messagebox.showerror("错误", "请选择输入和输出目录！")
            return
            
        # 禁用开始按钮
        self.start_button['state'] = 'disabled'
        self.status_text.set("准备处理...")
        self.progress_var.set(0)
        
        # 在新线程中处理图片
        thread = threading.Thread(target=self.process_images)
        thread.daemon = True
        thread.start()
        
    def run(self):
        """运行GUI程序"""
        self.window.mainloop()

def main():
    """主程序入口"""
    app = CompressorGUI()
    app.run()

if __name__ == "__main__":
    main()