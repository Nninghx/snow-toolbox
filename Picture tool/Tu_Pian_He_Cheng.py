import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import os
import threading
import math
import json

class ImageCombinerApp:

    def __init__(self, master):
        self.master = master
        master.title("图片合成工具")
        master.geometry("400x500")
        
        # 读取字体设置
        try:
            with open("Core/ziti.json", "r", encoding="utf-8") as f:
                font_settings = json.load(f)
                self.font_family = font_settings.get("family", "微软雅黑")
        except Exception as e:
            print(f"无法加载字体设置: {str(e)}")
            self.font_family = "微软雅黑"

        # 初始化变量
        self.image_paths = []
        self.layout_mode = tk.StringVar(value="uniform")
        self.batch_mode = tk.BooleanVar(value=False)
        self.random_distribute = tk.BooleanVar(value=False)
        
        # 创建GUI组件
        self.create_widgets()
    
    def create_widgets(self):
        """创建界面组件"""
        # 主容器 - 使用grid布局
        main_frame = tk.Frame(self.master, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 设置默认字体
        default_font = (self.font_family, 10)
        self.master.option_add("*Font", default_font)
        
        # 顶部控制区域
        control_frame = tk.LabelFrame(main_frame, text="控制面板", padx=10, pady=10)
        control_frame.grid(row=0, column=0, sticky="ew", pady=(0,10))
        
        # 图片选择区域
        select_frame = tk.Frame(control_frame)
        select_frame.grid(row=0, column=0, sticky="w", pady=5)
        
        self.btn_select = tk.Button(
            select_frame,
            text="选择图片",
            command=self.select_images,
            width=15
        )
        self.btn_select.pack(side=tk.LEFT)
        
        # 布局选项区域
        options_frame = tk.LabelFrame(control_frame, text="布局选项", padx=10, pady=10)
        options_frame.grid(row=1, column=0, sticky="ew", pady=5)
        
        # 布局模式选择
        mode_frame = tk.Frame(options_frame)
        mode_frame.grid(row=0, column=0, sticky="w", pady=5)
        tk.Label(mode_frame, text="布局模式:").grid(row=0, column=0, sticky="w")
        
        for i, mode in enumerate(["uniform", "horizontal", "vertical"]):
            mode_names = {"uniform": "均匀分布", "horizontal": "水平排列", "vertical": "垂直排列"}
            tk.Radiobutton(
                mode_frame,
                text=mode_names[mode],
                variable=self.layout_mode,
                value=mode
            ).grid(row=0, column=i+1, padx=5)
        
        # 其他选项
        option_frame = tk.Frame(options_frame)
        option_frame.grid(row=1, column=0, sticky="w", pady=5)
        
        tk.Checkbutton(
            option_frame,
            text="随机分布",
            variable=self.random_distribute
        ).grid(row=0, column=0, padx=5)
        
        tk.Checkbutton(
            option_frame,
            text="批量模式",
            variable=self.batch_mode
        ).grid(row=0, column=1, padx=5)
        
        # 数量设置
        count_frame = tk.Frame(options_frame)
        count_frame.grid(row=2, column=0, sticky="w", pady=5)
        
        tk.Label(count_frame, text="导出数量:").grid(row=0, column=0, sticky="w")
        self.export_count = tk.IntVar(value=1)
        tk.Spinbox(
            count_frame,
            from_=1,
            to=100,
            width=5,
            textvariable=self.export_count
        ).grid(row=0, column=1, padx=5)
        
        tk.Label(count_frame, text="随机选择:").grid(row=0, column=2, padx=(10,0))
        self.random_select_count = tk.IntVar(value=0)
        tk.Spinbox(
            count_frame,
            from_=0,
            to=100,
            width=5,
            textvariable=self.random_select_count
        ).grid(row=0, column=3, padx=5)
        
        # 操作按钮
        action_frame = tk.Frame(control_frame)
        action_frame.grid(row=2, column=0, sticky="e", pady=5)
        
        self.btn_help = tk.Button(
            action_frame,
            text="使用帮助",
            command=self.show_help,
            width=10
        )
        self.btn_help.grid(row=0, column=0, padx=5)
        
        self.btn_preview = tk.Button(
            action_frame,
            text="预览",
            command=self.preview,
            state=tk.DISABLED,
            width=10
        )
        self.btn_preview.grid(row=0, column=1, padx=5)
        
        self.btn_save = tk.Button(
            action_frame,
            text="保存结果",
            command=self.save_result,
            state=tk.DISABLED,
            width=10
        )
        self.btn_save.grid(row=0, column=2, padx=5)
        
        # 图片预览区域
        self.preview_frame = tk.LabelFrame(main_frame, text="图片预览", padx=10, pady=10)
        self.preview_frame.grid(row=1, column=0, sticky="nsew")
        
        # 配置网格权重
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = tk.Label(
            self.master,
            textvariable=self.status_var,
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def select_images(self):
        """选择图片文件"""
        filetypes = (
            ("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif"),
            ("所有文件", "*.*")
        )
        paths = filedialog.askopenfilenames(
            title="选择图片",
            filetypes=filetypes
        )
        if paths:
            self.image_paths = list(paths)
            self.btn_preview.config(state=tk.NORMAL)
            self.btn_save.config(state=tk.NORMAL)
            self.status_var.set(f"已选择 {len(paths)} 张图片，请设置布局选项后预览")


    def preview(self):
        """预览合成效果"""
        if not self.image_paths:
            messagebox.showwarning("警告", "请先选择图片")
            return
        
        # 清空预览区域
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        
        # 创建画布用于显示图片
        canvas = tk.Canvas(self.preview_frame)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(self.preview_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 内部框架用于放置图片
        inner_frame = tk.Frame(canvas)
        canvas.create_window((0, 0), window=inner_frame, anchor=tk.NW)
        
        # 加载并显示图片
        max_width = 400
        row = 0
        for i, path in enumerate(self.image_paths):
            try:
                img = Image.open(path)
                # 等比例缩放预览
                ratio = max_width / float(img.size[0])
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                photo = ImageTk.PhotoImage(img)
                label = tk.Label(inner_frame, image=photo)
                label.image = photo  # 保持引用
                label.grid(row=row, column=0, pady=5)
                
                # 显示文件名
                filename = os.path.basename(path)
                tk.Label(inner_frame, text=filename).grid(row=row, column=1, sticky=tk.W)
                row += 1
            except Exception as e:
                messagebox.showerror("错误", f"无法加载图片 {path}: {str(e)}")
        
        # 更新滚动区域
        inner_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))
    
    def save_result(self):
        """保存合成结果"""
        if not self.image_paths:
            messagebox.showwarning("警告", "请先选择图片")
            return

        # 选择保存位置
        filetypes = [
            ("JPEG", "*.jpg"),
            ("PNG", "*.png"),
            ("BMP", "*.bmp"),
            ("所有文件", "*.*")
        ]

        save_path = filedialog.asksaveasfilename(
            title="保存合成图片",
            filetypes=filetypes,
            defaultextension=".png"
        )
        
        if save_path:
            try:
                # 获取基本文件名和扩展名
                base, ext = os.path.splitext(save_path)
                ext = ext.lower()
                
                # 保存多张图片
                count = self.export_count.get()
                for i in range(count):
                    # 合成图片(每次重新合成以确保随机分布不同)
                    combined = self.combine_images()
                    if combined is None:
                        return
                    
                    # 生成带编号的文件名
                    if count > 1:
                        current_path = f"{base}_{i+1}{ext}"
                    else:
                        current_path = save_path
                    
                    # 根据文件格式保存
                    if ext in (".jpg", ".jpeg"):
                        combined.save(current_path, "JPEG", quality=95)
                    elif ext == ".png":
                        combined.save(current_path, "PNG")
                    elif ext == ".bmp":
                        combined.save(current_path, "BMP")
                    else:
                        combined.save(current_path)  # 默认格式
                
                messagebox.showinfo("成功", f"已保存 {count} 张图片到: {os.path.dirname(save_path)}")
                
                # 在批量模式下继续处理
                if self.batch_mode.get():
                    self._batch_process(save_path)
                    
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {str(e)}")
    
    def _batch_process(self, last_save_path):
        """批量处理模式"""
        # 获取文件夹路径
        folder = os.path.dirname(last_save_path)
        
        # 创建批量处理线程
        thread = threading.Thread(
            target=self._run_batch_process,
            args=(folder,),
            daemon=True
        )
        thread.start()
        messagebox.showinfo("提示", "批量处理已在后台运行")
    
    def _run_batch_process(self, folder):
        """执行批量处理"""
        try:
            # 这里可以添加更复杂的批量处理逻辑
            # 当前简单实现只是提示功能
            print(f"批量处理模式已启动，结果将保存到: {folder}")
            self.status_var.set("批量处理进行中...")
            
            # 示例：可以在这里添加实际的批量处理逻辑
            # 比如处理多个文件夹的图片
            
        except Exception as e:
            print(f"批量处理出错: {str(e)}")
            self.status_var.set("批量处理出错")
        finally:
            self.status_var.set("批量处理完成")
    
    def combine_images(self):
        """核心图片合成方法"""
        if not self.image_paths:
            return None
            
        try:
            self.status_var.set("正在加载图片...")
            self.master.update()
            
            # 随机选择指定数量的图片
            select_count = self.random_select_count.get()
            if select_count > 0 and select_count < len(self.image_paths):
                import random
                selected_paths = random.sample(self.image_paths, select_count)
                self.status_var.set(f"已随机选择 {select_count} 张图片")
            else:
                selected_paths = self.image_paths
                
            # 加载选中的图片
            images = []
            total_size = 0
            for i, path in enumerate(selected_paths):
                self.status_var.set(f"正在加载图片 ({i+1}/{len(selected_paths)})...")
                self.master.update()
                img = Image.open(path)
                total_size += os.path.getsize(path)
                images.append(img)
                
            # 自动压缩大图片
            if total_size > 10 * 1024 * 1024:  # 10MB
                self.status_var.set("正在压缩大图片...")
                self.master.update()
                images = [self.compress_image(img) for img in images]
                
            # 根据布局模式合成图片
            mode = self.layout_mode.get()
            self.status_var.set(f"正在合成图片 ({mode}布局)...")
            self.master.update()
            
            if self.random_distribute.get():
                result = self._random_layout(images)
            elif mode == "uniform":
                result = self._uniform_layout(images)
            elif mode == "horizontal":
                result = self._horizontal_layout(images)
            elif mode == "vertical":
                result = self._vertical_layout(images)
                
            self.status_var.set("图片合成完成")
            return result
                
        except Exception as e:
            messagebox.showerror("错误", f"图片合成失败: {str(e)}")
            self.status_var.set("图片合成失败")
            return None
        finally:
            self.master.update()
    
    def _uniform_layout(self, images):
        """均匀分布布局"""
        # 计算网格行列数
        img_count = len(images)
        cols = math.ceil(math.sqrt(img_count))
        rows = math.ceil(img_count / cols)
        
        # 计算每张图片的最大尺寸
        max_width = max(img.size[0] for img in images)
        max_height = max(img.size[1] for img in images)
        
        # 创建画布
        canvas_width = cols * max_width
        canvas_height = rows * max_height
        canvas = Image.new('RGB', (canvas_width, canvas_height), (255, 255, 255))
        
        # 排列图片
        for i, img in enumerate(images):
            row = i // cols
            col = i % cols
            x = col * max_width
            y = row * max_height
            canvas.paste(img, (x, y))
            
        return canvas
    
    def _horizontal_layout(self, images):
        """水平排列布局"""
        # 计算总宽度和最大高度
        total_width = sum(img.size[0] for img in images)
        max_height = max(img.size[1] for img in images)
        
        # 创建画布
        canvas = Image.new('RGB', (total_width, max_height), (255, 255, 255))
        
        # 水平排列图片
        x_offset = 0
        for img in images:
            canvas.paste(img, (x_offset, 0))
            x_offset += img.size[0]
            
        return canvas
    
    def _vertical_layout(self, images):
        """垂直排列布局"""
        # 计算最大宽度和总高度
        max_width = max(img.size[0] for img in images)
        total_height = sum(img.size[1] for img in images)
        
        # 创建画布
        canvas = Image.new('RGB', (max_width, total_height), (255, 255, 255))
        
        # 垂直排列图片
        y_offset = 0
        for img in images:
            canvas.paste(img, (0, y_offset))
            y_offset += img.size[1]
            
        return canvas
    
    def _random_layout(self, images):
        """随机分布布局"""
        import random

        # 计算画布大小 (所有图片总面积的1.5倍)
        total_area = sum(img.size[0] * img.size[1] for img in images)
        canvas_size = int(math.sqrt(total_area) * 1.5)

        # 创建画布
        canvas = Image.new('RGB', (canvas_size, canvas_size), (255, 255, 255))
        
        # 随机放置图片
        placed = []
        for img in images:
            placed_success = False
            attempts = 0
            max_attempts = 100
            
            while not placed_success and attempts < max_attempts:
                attempts += 1
                x = random.randint(0, canvas_size - img.size[0])
                y = random.randint(0, canvas_size - img.size[1])
                
                # 检查是否与其他图片重叠
                overlap = False
                new_rect = (x, y, x + img.size[0], y + img.size[1])
                
                for existing in placed:
                    if self._check_overlap(new_rect, existing):
                        overlap = True
                        break
                
                if not overlap:
                    canvas.paste(img, (x, y))
                    placed.append(new_rect)
                    placed_success = True
        
        return canvas
    
    def _check_overlap(self, rect1, rect2):
        """检查两个矩形是否重叠"""
        return not (rect1[2] <= rect2[0] or
                   rect1[0] >= rect2[2] or
                   rect1[3] <= rect2[1] or
                   rect1[1] >= rect2[3])


    def compress_image(self, image):
        """图片压缩方法"""
        try:
            # 计算压缩比例 (目标大小: 1MB)
            original_size = image.size[0] * image.size[1]
            target_size = 1024 * 1024  # 1MB
            if original_size <= target_size:
                return image
                
            # 计算压缩比例
            ratio = math.sqrt(target_size / original_size)
            new_width = int(image.size[0] * ratio)
            new_height = int(image.size[1] * ratio)
            
            # 高质量压缩
            return image.resize(
                (new_width, new_height),
                Image.Resampling.LANCZOS
            )
            
        except Exception as e:
            messagebox.showwarning("警告", f"图片压缩失败: {str(e)}")
            return image
            
    def show_help(self):
        """显示使用帮助文档"""
        help_text = """图片合成工具Alpha1.0.0使用说明

1. 选择图片: 点击"选择图片"按钮选择要合成的图片
2. 设置布局选项:
   - 布局模式: 均匀分布/水平排列/垂直排列
   - 随机分布: 勾选后图片会随机排列
   - 批量模式: 勾选后可批量处理多组图片
3. 预览效果: 设置好选项后点击"预览"查看效果
4. 保存结果: 满意后点击"保存结果"选择保存位置

提示:
- 作者:叁垣伍瑞肆凶廿捌宿宿
- 联系方式:https://space.bilibili.com/556216088
- 版权:Apache-2.0 License
"""
        messagebox.showinfo("使用帮助", help_text)

if __name__ == "__main__":
    root = tk.Tk()
    # 设置窗口图标
    try:
        root.iconbitmap('Image/icon.ico')
    except Exception as e:
        print(f"图标加载失败: {str(e)}")
    app = ImageCombinerApp(root)
    root.mainloop()
#pyinstaller --onefile --noconsole --version-file=version_info.txt --name "图片合成工具" Tu_Pian_He_Cheng_Alpha.py