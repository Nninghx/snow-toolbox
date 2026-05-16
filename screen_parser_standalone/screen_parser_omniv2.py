
import sys
import os
import json
import time
import base64
import io
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from PIL import Image, ImageTk, ImageGrab
import numpy as np
import torch
from threading import Thread
class ScreenParserGUI:
    """屏幕解析工具图形界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("OmniParser 屏幕解析工具")
        self.root.geometry("1000x720")
        
        # 配置路径 - 使用当前文件所在目录作为基础路径
        self.base_dir = Path(__file__).parent
        # 模型权重目录（与 OmniParser 目录结构保持一致）
        self.weights_dir = self.base_dir / "OmniParser"
        
        # 状态变量
        self.parser_initialized = False
        self.yolo_model = None
        self.caption_processor = None
        self.current_image = None  # 当前显示的图片（可能是原始图片或标注图片）
        self.original_image = None  # 原始未标注的图片
        self.parsed_result = None
        
        # 编辑模式相关
        self.edit_mode = False
        self.edit_boxes = []  # 存储可编辑的标注框
        self.selected_box_index = -1
        self.dragging_box = False
        self.resizing_box = False
        self.drag_start_pos = None
        self.resize_handle = None
        self.temp_box = None  # 临时绘制的新框
        self.right_click_pos = None  # 右键点击位置
        
        # 图片缩放相关
        self.zoom_scale = 1.0  # 当前缩放比例（1.0 = 100%）
        self.min_zoom = 0.1    # 最小缩放比例（10%）
        self.max_zoom = 5.0    # 最大缩放比例（500%）
        self.zoom_step = 0.1   # 每次缩放步长
        
        # 图片拖动相关
        self.pan_offset_x = 0  # 水平偏移量
        self.pan_offset_y = 0  # 垂直偏移量
        self.is_panning = False  # 是否正在拖动
        self.pan_start_x = 0  # 拖动起始X坐标
        self.pan_start_y = 0  # 拖动起始Y坐标
        
        # 默认参数
        self.box_threshold = 0.05
        self.iou_threshold = 0.1
        self.use_paddleocr = False  # 默认禁用 PaddleOCR，避免兼容性问题
        self.imgsz = 640
        
        # 创建界面
        self._create_ui()
        
        # 延迟初始化模型
        self.root.after(500, self._init_models)
    
    def _create_ui(self):
        """创建用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # === 顶部控制区 ===
        control_frame = ttk.LabelFrame(main_frame, text="控制面板", padding="10")
        control_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        # 按钮行
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill="x", pady=(0, 10))
        
        self.capture_btn = ttk.Button(btn_frame, text="📸 捕获屏幕", command=self._capture_screen, width=15)
        self.capture_btn.pack(side="left", padx=5)
        
        self.load_btn = ttk.Button(btn_frame, text="📁 加载图片", command=self._load_image, width=15)
        self.load_btn.pack(side="left", padx=5)
        
        self.parse_btn = ttk.Button(btn_frame, text="🔍 开始解析", command=self._parse_image, width=15)
        self.parse_btn.pack(side="left", padx=5)
        
        self.edit_btn = ttk.Button(btn_frame, text="✏️ 编辑标注", command=self._on_edit_button_click, width=15, state="disabled")
        self.edit_btn.pack(side="left", padx=5)
        
        self.toggle_view_btn = ttk.Button(btn_frame, text="👁️ 切换视图", command=self._toggle_image_view, width=15, state="disabled")
        self.toggle_view_btn.pack(side="left", padx=5)
        
        self.export_btn = ttk.Button(btn_frame, text="📤 导出图片", command=self._export_labeled_image, width=15, state="disabled")
        self.export_btn.pack(side="left", padx=5)
        
        self.save_btn = ttk.Button(btn_frame, text="💾 保存结果", command=self._save_result, width=15)
        self.save_btn.pack(side="left", padx=5)
        
        self.reinit_btn = ttk.Button(btn_frame, text="🔄 重新初始化", command=self._reinit_models, width=15)
        self.reinit_btn.pack(side="left", padx=5)
        
        # 参数设置
        param_frame = ttk.Frame(control_frame)
        param_frame.pack(fill="x")
        
        # Box Threshold
        ttk.Label(param_frame, text="Box阈值:").grid(row=0, column=0, sticky="w", padx=5)
        self.box_threshold_var = tk.DoubleVar(value=self.box_threshold)
        threshold_scale = ttk.Scale(param_frame, from_=0.01, to=1.0, variable=self.box_threshold_var, 
                                    orient="horizontal", length=200, command=self._on_threshold_change)
        threshold_scale.grid(row=0, column=1, padx=5)
        self.threshold_label = ttk.Label(param_frame, text=f"{self.box_threshold:.2f}", width=6)
        self.threshold_label.grid(row=0, column=2, padx=5)
        
        # IOU Threshold
        ttk.Label(param_frame, text="IOU阈值:").grid(row=0, column=3, sticky="w", padx=5)
        self.iou_threshold_var = tk.DoubleVar(value=self.iou_threshold)
        iou_scale = ttk.Scale(param_frame, from_=0.01, to=1.0, variable=self.iou_threshold_var, 
                             orient="horizontal", length=200, command=self._on_iou_change)
        iou_scale.grid(row=0, column=4, padx=5)
        self.iou_label = ttk.Label(param_frame, text=f"{self.iou_threshold:.2f}", width=6)
        self.iou_label.grid(row=0, column=5, padx=5)
        
        # 图片尺寸
        ttk.Label(param_frame, text="检测尺寸:").grid(row=0, column=6, sticky="w", padx=5)
        self.imgsz_var = tk.IntVar(value=self.imgsz)
        imgsz_spinbox = ttk.Spinbox(param_frame, from_=640, to=1920, increment=32, 
                                   textvariable=self.imgsz_var, width=8)
        imgsz_spinbox.grid(row=0, column=7, padx=5)
        
        # OCR 引擎提示（已移除 PaddleOCR 选项，统一使用 EasyOCR）
        ttk.Label(param_frame, text="OCR引擎: EasyOCR", foreground="green", font=("Arial", 9, "bold")).grid(row=0, column=8, padx=10, sticky="w")
        ttk.Label(param_frame, text="(稳定可靠)", foreground="gray", font=("Arial", 8)).grid(row=0, column=9, padx=(0, 5), sticky="w")
        
        # === 中部显示区 ===
        display_frame = ttk.Frame(main_frame)
        display_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        display_frame.columnconfigure(0, weight=1)
        display_frame.columnconfigure(1, weight=1)
        display_frame.rowconfigure(0, weight=1)
        
        # 左侧：原始/标注图片
        image_frame = ttk.LabelFrame(display_frame, text="图片显示", padding="5")
        image_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # 缩放控制工具栏
        zoom_toolbar = ttk.Frame(image_frame)
        zoom_toolbar.pack(fill="x", pady=(0, 5))
        
        ttk.Button(zoom_toolbar, text="➖", command=self._zoom_out, width=3).pack(side="left", padx=2)
        self.zoom_label = ttk.Label(zoom_toolbar, text="100%", width=6, anchor="center")
        self.zoom_label.pack(side="left", padx=2)
        ttk.Button(zoom_toolbar, text="➕", command=self._zoom_in, width=3).pack(side="left", padx=2)
        ttk.Button(zoom_toolbar, text="🔄", command=self._reset_zoom, width=3).pack(side="left", padx=2)
        ttk.Label(zoom_toolbar, text="(滚轮缩放)", foreground="gray", font=("Arial", 8)).pack(side="left", padx=5)
        
        self.image_canvas = tk.Canvas(image_frame, bg="gray90", highlightthickness=1, highlightbackground="gray")
        self.image_canvas.pack(fill="both", expand=True)
        
        # 绑定鼠标滚轮事件用于缩放
        self.image_canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.image_canvas.bind("<Button-4>", self._on_mouse_wheel)  # Linux
        self.image_canvas.bind("<Button-5>", self._on_mouse_wheel)  # Linux
        
        # 绑定鼠标拖动事件（按住中键或Shift+左键拖动）
        self.image_canvas.bind("<ButtonPress-2>", self._on_pan_start)  # 中键按下
        self.image_canvas.bind("<B2-Motion>", self._on_pan_drag)       # 中键拖动
        self.image_canvas.bind("<ButtonRelease-2>", self._on_pan_end)  # 中键释放
        self.image_canvas.bind("<Shift-ButtonPress-1>", self._on_pan_start)  # Shift+左键按下
        self.image_canvas.bind("<Shift-B1-Motion>", self._on_pan_drag)       # Shift+左键拖动
        self.image_canvas.bind("<Shift-ButtonRelease-1>", self._on_pan_end)  # Shift+左键释放
        
        # 右侧：解析结果
        result_frame = ttk.LabelFrame(display_frame, text="解析结果", padding="5")
        result_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        self.result_text = scrolledtext.ScrolledText(result_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.result_text.pack(fill="both", expand=True)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪 - 正在初始化模型...")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
    
    def _log(self, message: str):
        """输出日志到终端"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def _update_status(self, message: str):
        """更新状态栏"""
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def _zoom_in(self):
        """放大图片"""
        if self.current_image is None:
            return
        
        old_scale = self.zoom_scale
        self.zoom_scale = min(self.zoom_scale + self.zoom_step, self.max_zoom)
        
        if self.zoom_scale != old_scale:
            self._update_zoom_display()
            self._display_image(self.current_image)
            self._log(f"🔍 放大: {int(self.zoom_scale * 100)}%")
    
    def _zoom_out(self):
        """缩小图片"""
        if self.current_image is None:
            return
        
        old_scale = self.zoom_scale
        self.zoom_scale = max(self.zoom_scale - self.zoom_step, self.min_zoom)
        
        if self.zoom_scale != old_scale:
            self._update_zoom_display()
            self._display_image(self.current_image)
            self._log(f"🔍 缩小: {int(self.zoom_scale * 100)}%")
    
    def _reset_zoom(self):
        """重置缩放到100%"""
        if self.current_image is None:
            return
        
        self.zoom_scale = 1.0
        self._reset_pan()  # 同时重置拖动位置
        self._update_zoom_display()
        self._display_image(self.current_image)
        self._log("🔍 重置缩放: 100%")
    
    def _on_mouse_wheel(self, event):
        """鼠标滚轮缩放"""
        if self.current_image is None:
            return
        
        # Windows/Mac: event.delta, Linux: event.num
        if event.num == 5 or event.delta < 0:
            # 向下滚动 - 缩小
            self._zoom_out()
        elif event.num == 4 or event.delta > 0:
            # 向上滚动 - 放大
            self._zoom_in()
    
    def _on_pan_start(self, event):
        """开始拖动图片"""
        if self.current_image is None:
            return
        
        self.is_panning = True
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.image_canvas.config(cursor="fleur")  # 显示移动光标
    
    def _on_pan_drag(self, event):
        """拖动图片"""
        if not self.is_panning or self.current_image is None:
            return
        
        # 计算偏移量
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y
        
        # 更新偏移量
        self.pan_offset_x += dx
        self.pan_offset_y += dy
        
        # 更新起始位置
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        
        # 重新绘制图片
        self._display_image(self.current_image)
    
    def _on_pan_end(self, event):
        """结束拖动"""
        self.is_panning = False
        self.image_canvas.config(cursor="")  # 恢复默认光标
    
    def _reset_pan(self):
        """重置拖动偏移"""
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        if self.current_image:
            self._display_image(self.current_image)
        self._log("🔄 已重置图片位置")
    
    def _update_zoom_display(self):
        """更新缩放比例显示"""
        zoom_percent = int(self.zoom_scale * 100)
        self.zoom_label.config(text=f"{zoom_percent}%")
    
    def _toggle_image_view(self):
        """在原始图片和标注图片之间切换"""
        if not self.parsed_result:
            messagebox.showwarning("警告", "请先解析图片后再切换视图")
            return
        
        if 'labeled_image' not in self.parsed_result:
            messagebox.showwarning("警告", "没有标注后的图片")
            return
        
        labeled_image = self.parsed_result['labeled_image']
        
        # 判断当前显示的是哪种图片
        if self.current_image is labeled_image:
            # 当前是标注图片，切换到原始图片
            if self.original_image:
                self.current_image = self.original_image
                self._display_image(self.original_image)
                self._log("👁️ 切换到原始图片视图")
                self._update_status("显示原始图片（未标注）")
            else:
                messagebox.showinfo("提示", "没有保存原始图片")
        else:
            # 当前是原始图片，切换到标注图片
            self.current_image = labeled_image
            self._display_image(labeled_image)
            self._log("👁️ 切换到标注图片视图")
            self._update_status("显示标注图片")
    
    def _on_edit_button_click(self):
        """编辑标注按钮点击事件处理"""
        self._log("🔘 编辑标注按钮被点击")
        self._log(f"   - parser_initialized: {self.parser_initialized}")
        self._log(f"   - current_image: {'存在' if self.current_image else 'None'}")
        self._log(f"   - parsed_result: {'存在' if self.parsed_result else 'None'}")
        
        try:
            self._show_edit_dialog()
        except Exception as e:
            self._log(f"❌ 按钮点击异常: {str(e)}")
            import traceback
            self._log(traceback.format_exc())
            messagebox.showerror("错误", f"编辑功能出错:\n{str(e)}")
    
    def _show_edit_dialog(self):
        """显示编辑对话框，展示识别的元素结果供用户修改"""
        if not self.parsed_result:
            self._log("⚠️ 无法编辑：没有解析结果")
            messagebox.showwarning("警告", "请先解析图片后再编辑标注\n\n操作步骤：\n1. 捕获或加载图片\n2. 点击'开始解析'\n3. 等待解析完成\n4. 再点击'编辑标注'")
            return
        
        # 创建编辑窗口
        edit_window = tk.Toplevel(self.root)
        edit_window.title("✏️ 编辑识别结果")
        edit_window.geometry("800x600")
        
        # 主框架
        main_frame = ttk.Frame(edit_window, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # 说明标签
        info_label = ttk.Label(main_frame, 
                              text="📝 使用说明：直接修改下方的元素识别结果，修改完成后点击'保存并应用'按钮",
                              font=("Arial", 10),
                              foreground="blue")
        info_label.pack(fill="x", pady=(0, 10))
        
        # 文本编辑区域
        text_frame = ttk.LabelFrame(main_frame, text="识别元素列表（可直接编辑）", padding="5")
        text_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        edit_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=("Consolas", 10))
        edit_text.pack(fill="both", expand=True)
        
        # 生成可编辑的文本内容
        editable_content = self._generate_editable_content()
        edit_text.insert(tk.END, editable_content)
        
        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        
        def save_and_apply():
            """保存并应用修改"""
            try:
                modified_content = edit_text.get(1.0, tk.END).strip()
                self._apply_modified_content(modified_content)
                edit_window.destroy()
                messagebox.showinfo("成功", "✅ 修改已保存并应用！")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败:\n{str(e)}")
        
        def cancel_edit():
            """取消编辑"""
            edit_window.destroy()
        
        save_btn = ttk.Button(btn_frame, text="💾 保存并应用", command=save_and_apply, width=15)
        save_btn.pack(side="left", padx=5)
        
        cancel_btn = ttk.Button(btn_frame, text="❌ 取消", command=cancel_edit, width=15)
        cancel_btn.pack(side="left", padx=5)
        
        # 居中显示窗口
        edit_window.transient(self.root)
        edit_window.grab_set()
        self.root.wait_window(edit_window)
    
    def _generate_editable_content(self) -> str:
        """生成可编辑的文本内容"""
        if not self.parsed_result or 'parsed_content' not in self.parsed_result:
            return "无解析内容"
        
        parsed_content = self.parsed_result['parsed_content']
        
        content_lines = []
        content_lines.append("=" * 60)
        content_lines.append("屏幕解析结果 - 可编辑版本")
        content_lines.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content_lines.append(f"元素数量: {len(parsed_content)}")
        content_lines.append("=" * 60)
        content_lines.append("")
        content_lines.append("【格式说明】")
        content_lines.append("每行一个元素，格式为：序号|类型|内容|位置坐标")
        content_lines.append("示例：0|button|登录按钮|[0.1, 0.2, 0.3, 0.4]")
        content_lines.append("您可以修改：类型、内容、坐标值")
        content_lines.append("=" * 60)
        content_lines.append("")
        
        for i, item in enumerate(parsed_content):
            element_type = item.get('type', 'unknown')
            content = item.get('content', '')
            bbox = item.get('bbox', [])
            interactivity = item.get('interactivity', False)
            
            # 格式化为一行
            line = f"{i}|{element_type}|{content}|{bbox}"
            content_lines.append(line)
        
        content_lines.append("")
        content_lines.append("=" * 60)
        content_lines.append("提示：修改后请保持格式一致，然后点击'保存并应用'")
        content_lines.append("=" * 60)
        
        return "\n".join(content_lines)
    
    def _apply_modified_content(self, modified_content: str):
        """应用修改后的内容"""
        lines = modified_content.strip().split('\n')
        
        new_parsed_content = []
        
        for line in lines:
            line = line.strip()
            # 跳过空行和注释行
            if not line or line.startswith('=') or line.startswith('【') or line.startswith('提示'):
                continue
            
            # 解析每一行：序号|类型|内容|坐标
            parts = line.split('|')
            if len(parts) >= 4:
                try:
                    index = int(parts[0])
                    element_type = parts[1].strip()
                    content = parts[2].strip()
                    
                    # 解析坐标（可能是字符串形式的列表）
                    bbox_str = parts[3].strip()
                    # 移除方括号并分割
                    bbox_str = bbox_str.replace('[', '').replace(']', '')
                    bbox_values = [float(x.strip()) for x in bbox_str.split(',') if x.strip()]
                    
                    if len(bbox_values) == 4:
                        new_item = {
                            'type': element_type,
                            'content': content,
                            'bbox': bbox_values,
                            'interactivity': True if 'button' in element_type.lower() or 'link' in element_type.lower() else False
                        }
                        new_parsed_content.append(new_item)
                        self._log(f"✅ 解析元素 {index}: {element_type} - {content}")
                    else:
                        self._log(f"⚠️ 跳过无效坐标的行 {index}: {line}")
                        
                except Exception as e:
                    self._log(f"⚠️ 解析行失败: {line}, 错误: {str(e)}")
        
        if new_parsed_content:
            # 更新解析结果
            self.parsed_result['parsed_content'] = new_parsed_content
            
            # 重新生成 coordinates
            new_coordinates = {}
            for i, item in enumerate(new_parsed_content):
                bbox = item.get('bbox', [0, 0, 0, 0])
                if len(bbox) == 4:
                    # 转换 bbox [x1, y1, x2, y2] 到 [x, y, w, h] 格式
                    x, y, w, h = bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1]
                    new_coordinates[f"Element {i}"] = [x, y, w, h]
            
            self.parsed_result['coordinates'] = new_coordinates
            
            # 刷新显示
            self._display_parsed_result(self.parsed_result['image'], new_parsed_content)
            self._log(f"✅ 成功应用 {len(new_parsed_content)} 个修改后的元素")
        else:
            raise ValueError("未能解析出任何有效的元素数据，请检查格式是否正确")
    
    def _on_threshold_change(self, value):
        """Box阈值变化回调"""
        self.box_threshold = float(value)
        self.threshold_label.config(text=f"{self.box_threshold:.2f}")
    
    def _on_iou_change(self, value):
        """IOU阈值变化回调"""
        self.iou_threshold = float(value)
        self.iou_label.config(text=f"{self.iou_threshold:.2f}")
    
    def _init_models(self):
        """初始化模型（在后台线程中执行）"""
        def init_thread():
            try:
                self._update_status("正在加载 YOLO 模型...")
                self._log("开始初始化 OmniParser 模型...")
                
                from util.utils import get_yolo_model, get_caption_model_processor
                
                # 简化的 YOLO 模型路径查找（优先使用 .pt，其次 .safetensors）
                yolo_pt_path = self.weights_dir / "icon_detect" / "model.pt"
                yolo_safetensors_path = self.weights_dir / "icon_detect" / "model.safetensors"
                
                yolo_path = None
                if yolo_pt_path.exists():
                    yolo_path = yolo_pt_path
                elif yolo_safetensors_path.exists():
                    yolo_path = yolo_safetensors_path
                
                if not yolo_path:
                    raise FileNotFoundError("未找到 YOLO 模型文件，请先下载模型到 OmniParser/icon_detect 目录")
                
                self._log(f"使用 YOLO 模型: {yolo_path}")
                self.yolo_model = get_yolo_model(model_path=str(yolo_path))
                
                # 检测设备
                device = 'cuda' if torch.cuda.is_available() else ('mps' if torch.backends.mps.is_available() else 'cpu')
                self._log(f"使用设备: {device}")
                
                # 加载 caption 模型
                self._update_status("正在加载 Caption 模型...")
                
                # 简化的 Caption 模型路径查找
                caption_path = self.weights_dir / "icon_caption_florence"
                
                if not caption_path.exists():
                    raise FileNotFoundError("未找到 Caption 模型文件，请先下载模型到 OmniParser/icon_caption_florence 目录")
                
                self._log(f"使用 Caption 模型: {caption_path}")
                self.caption_processor = get_caption_model_processor(
                    model_name="florence2",
                    model_name_or_path=str(caption_path),
                    device=device
                )
                
                self.parser_initialized = True
                self._update_status("✅ 模型初始化完成")
                self._log("✅ OmniParser 模型初始化成功！")
                self._log(f"   - YOLO 模型: {yolo_path.name}")
                self._log(f"   - Caption 模型: Florence-2")
                self._log(f"   - 计算设备: {device}")
                self._log(f"   - OCR 引擎: EasyOCR（稳定可靠）")
                
            except Exception as e:
                error_msg = str(e)
                self._log(f"❌ 模型初始化失败: {error_msg}")
                self._update_status("❌ 初始化失败 - 请检查模型文件")
                messagebox.showerror("初始化错误", f"模型初始化失败:\n{str(e)}\n\n请确保已下载必要的模型文件")
        
        thread = Thread(target=init_thread, daemon=True)
        thread.start()
    
    def _reinit_models(self):
        """重新初始化模型"""
        self.parser_initialized = False
        self.yolo_model = None
        self.caption_processor = None
        self._update_status("正在重新初始化...")
        self._log("重新初始化模型...")
        self.root.after(100, self._init_models)
    
    def _capture_screen(self):
        """捕获屏幕截图"""
        if not self.parser_initialized:
            messagebox.showwarning("警告", "模型尚未初始化完成，请稍候...")
            return
        
        self._update_status("准备捕获屏幕...")
        self._log("请在3秒后选择要捕获的屏幕区域...")
        
        # 最小化窗口
        self.root.iconify()
        time.sleep(1)
        
        def capture():
            try:
                # 等待用户选择区域
                self._log("请使用鼠标拖动选择屏幕区域...")
                
                # 创建全屏透明窗口用于选择区域
                selection_window = tk.Toplevel()
                selection_window.attributes('-fullscreen', True)
                selection_window.attributes('-alpha', 0.3)
                selection_window.configure(bg='gray')
                selection_window.attributes('-topmost', True)
                
                canvas = tk.Canvas(selection_window, cursor="cross", bg='gray')
                canvas.pack(fill=tk.BOTH, expand=True)
                
                start_x = start_y = None
                rect = None
                
                def on_press(event):
                    nonlocal start_x, start_y, rect
                    start_x, start_y = event.x, event.y
                    rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='red', width=2)
                
                def on_drag(event):
                    nonlocal rect
                    if rect:
                        canvas.coords(rect, start_x, start_y, event.x, event.y)
                
                def on_release(event):
                    nonlocal start_x, start_y
                    end_x, end_y = event.x, event.y
                    
                    # 确保坐标正确
                    x1, y1 = min(start_x, end_x), min(start_y, end_y)
                    x2, y2 = max(start_x, end_x), max(start_y, end_y)
                    
                    selection_window.destroy()
                    
                    if x2 - x1 > 10 and y2 - y1 > 10:
                        # 捕获选定区域
                        screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
                        self.original_image = screenshot  # 保存原始图片
                        self.current_image = screenshot
                        self.zoom_scale = 1.0  # 重置缩放
                        self._reset_pan()  # 重置拖动位置
                        self._display_image(screenshot)
                        self._log(f"✅ 屏幕捕获成功: {screenshot.size[0]}x{screenshot.size[1]}")
                        
                        # 如果已有解析结果，启用编辑按钮
                        if self.parsed_result:
                            self.edit_btn.config(state="normal")
                            self.toggle_view_btn.config(state="normal")
                            self._update_status("屏幕捕获完成 - 可以点击'开始解析'或'编辑标注'")
                        else:
                            self._update_status("屏幕捕获完成 - 可以点击'开始解析'")
                    else:
                        self._log("❌ 选择区域太小，已取消")
                        self._update_status("已取消")
                
                canvas.bind("<ButtonPress-1>", on_press)
                canvas.bind("<B1-Motion>", on_drag)
                canvas.bind("<ButtonRelease-1>", on_release)
                selection_window.bind("<Escape>", lambda e: selection_window.destroy())
                
                self._log("提示: 拖动鼠标选择区域，按ESC取消")
                
            except Exception as e:
                self._log(f"❌ 屏幕捕获失败: {str(e)}")
                self._update_status("捕获失败")
                self.root.deiconify()
        
        Thread(target=capture, daemon=True).start()
    
    def _load_image(self):
        """加载图片文件"""
        if not self.parser_initialized:
            messagebox.showwarning("警告", "模型尚未初始化完成，请稍候...")
            return
        
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="选择图片文件",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                image = Image.open(file_path)
                if image.mode == 'RGBA':
                    image = image.convert('RGB')
                self.original_image = image  # 保存原始图片
                self.current_image = image
                self.zoom_scale = 1.0  # 重置缩放
                self._reset_pan()  # 重置拖动位置
                self._display_image(image)
                self._log(f"✅ 图片加载成功: {Path(file_path).name} ({image.size[0]}x{image.size[1]})")
                
                # 如果已有解析结果，启用编辑按钮
                if self.parsed_result:
                    self.edit_btn.config(state="normal")
                    self.toggle_view_btn.config(state="normal")
                    self._update_status("图片加载完成 - 可以点击'开始解析'或'编辑标注'")
                else:
                    self._update_status("图片加载完成 - 可以点击'开始解析'")
                    
            except Exception as e:
                self._log(f"❌ 图片加载失败: {str(e)}")
                messagebox.showerror("错误", f"无法加载图片:\n{str(e)}")
    
    def _display_image(self, image: Image.Image):
        """在画布上显示图片"""
        canvas_width = self.image_canvas.winfo_width()
        canvas_height = self.image_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = 600
            canvas_height = 400
        
        # 计算缩放比例
        img_width, img_height = image.size
        
        # 如果是首次显示或自动适应模式，计算合适的缩放比例
        if self.zoom_scale == 1.0 and hasattr(self, '_auto_fit_needed'):
            # 自动适应画布大小
            auto_scale = min(canvas_width / img_width, canvas_height / img_height, 1.0)
            scale = auto_scale
        else:
            # 使用用户设置的缩放比例
            scale = self.zoom_scale
        
        new_size = (int(img_width * scale), int(img_height * scale))
        
        resized_img = image.resize(new_size, Image.LANCZOS)
        photo = ImageTk.PhotoImage(resized_img)
        
        self.image_canvas.delete("all")
        
        # 计算显示位置（考虑拖动偏移）
        center_x = canvas_width // 2 + self.pan_offset_x
        center_y = canvas_height // 2 + self.pan_offset_y
        
        self.image_canvas.create_image(
            center_x,
            center_y,
            image=photo,
            anchor="center"
        )
        self.image_canvas.image = photo  # 保持引用
        
        # 更新缩放显示
        self._update_zoom_display()
    
    def _parse_image(self):
        """解析当前图片"""
        if not self.parser_initialized:
            messagebox.showwarning("警告", "模型尚未初始化完成")
            return
        
        if self.current_image is None:
            messagebox.showwarning("警告", "请先捕获或加载图片")
            return
        
        self._update_status("正在解析图片...")
        self._log("开始解析图片...")
        
        def parse_thread():
            try:
                from util.utils import check_ocr_box, get_som_labeled_img
                import cv2
                
                image = self.current_image.copy()
                
                # 准备参数
                box_overlay_ratio = max(image.size) / 3200
                draw_bbox_config = {
                    'text_scale': 0.8 * box_overlay_ratio,
                    'text_thickness': max(int(2 * box_overlay_ratio), 1),
                    'text_padding': max(int(3 * box_overlay_ratio), 1),
                    'thickness': max(int(3 * box_overlay_ratio), 1),
                }
                
                self._log("步骤1: 执行 OCR 文字识别...")
                # 强制使用 EasyOCR，避免 PaddleOCR 兼容性问题
                ocr_result, _ = check_ocr_box(
                    image,
                    display_img=False,
                    output_bb_format='xyxy',
                    easyocr_args={'paragraph': False, 'text_threshold': 0.9},
                    use_paddleocr=False  # 固定使用 EasyOCR
                )
                text, ocr_bbox = ocr_result
                self._log(f"   检测到 {len(text)} 个文本区域")
                
                self._log("步骤2: 执行图标检测和标注...")
                labeled_img_b64, label_coordinates, parsed_content = get_som_labeled_img(
                    image,
                    self.yolo_model,
                    BOX_TRESHOLD=self.box_threshold_var.get(),
                    output_coord_in_ratio=True,
                    ocr_bbox=ocr_bbox,
                    draw_bbox_config=draw_bbox_config,
                    caption_model_processor=self.caption_processor,
                    ocr_text=text,
                    iou_threshold=self.iou_threshold_var.get(),
                    imgsz=self.imgsz_var.get(),
                )
                
                self._log(f"   检测到 {len(parsed_content)} 个界面元素")
                
                # 转换标注后的图片
                labeled_img_bytes = base64.b64decode(labeled_img_b64)
                labeled_img = Image.open(io.BytesIO(labeled_img_bytes))
                
                # 保存结果
                self.parsed_result = {
                    'image': labeled_img,
                    'parsed_content': parsed_content,
                    'coordinates': label_coordinates,
                    'timestamp': datetime.now().isoformat()
                }
                
                # 更新UI
                self.root.after(0, lambda: self._display_parsed_result(labeled_img, parsed_content))
                
            except Exception as e:
                self._log(f"❌ 解析失败: {str(e)}")
                import traceback
                self._log(traceback.format_exc())
                self.root.after(0, lambda: self._update_status("❌ 解析失败"))
        
        Thread(target=parse_thread, daemon=True).start()
    
    def _display_parsed_result(self, labeled_image: Image.Image, parsed_content: List):
        """显示解析结果"""
        # 保存标注后的图片到 parsed_result，但不替换 current_image
        # 这样用户缩放时仍然可以看到标注
        if self.parsed_result is None:
            self.parsed_result = {}
        self.parsed_result['labeled_image'] = labeled_image
        
        # 将 current_image 切换为标注后的图片，以便缩放时显示标注
        self.current_image = labeled_image
        
        # 显示标注图片
        self._display_image(labeled_image)
        
        # 显示解析文本
        self.result_text.delete(1.0, tk.END)
        
        result_str = f"=== 屏幕解析结果 ===\n"
        result_str += f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        result_str += f"图片尺寸: {labeled_image.size[0]}x{labeled_image.size[1]}\n"
        result_str += f"检测到的元素数量: {len(parsed_content)}\n"
        result_str += "=" * 50 + "\n\n"
        
        for i, item in enumerate(parsed_content):
            result_str += f"[元素 {i}]\n"
            result_str += f"  类型: {item.get('type', 'unknown')}\n"
            result_str += f"  位置: {item.get('bbox', [])}\n"
            result_str += f"  可交互: {item.get('interactivity', False)}\n"
            if item.get('content'):
                result_str += f"  内容: {item['content']}\n"
            if item.get('source'):
                result_str += f"  来源: {item['source']}\n"
            result_str += "\n"
        
        self.result_text.insert(tk.END, result_str)
        
        self._log("✅ 解析完成！")
        self._update_status("✅ 解析完成 - 可以点击'编辑标注'进行修改")
        
        # 启用编辑按钮和切换视图按钮
        self.edit_btn.config(state="normal")
        self.toggle_view_btn.config(state="normal")
        self.export_btn.config(state="normal")  # 启用导出按钮
    
    def _export_labeled_image(self):
        """导出标注后的图片"""
        if not self.parsed_result or 'labeled_image' not in self.parsed_result:
            messagebox.showwarning("警告", "没有可导出的标注图片，请先解析图片")
            return
        
        from tkinter import filedialog
        
        # 选择保存路径
        save_path = filedialog.asksaveasfilename(
            title="保存标注图片",
            defaultextension=".png",
            filetypes=[
                ("PNG 图片", "*.png"),
                ("JPEG 图片", "*.jpg *.jpeg"),
                ("BMP 图片", "*.bmp"),
                ("所有图片格式", "*.png *.jpg *.jpeg *.bmp")
            ],
            initialfile=f"labeled_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )
        
        if not save_path:
            return
        
        try:
            labeled_image = self.parsed_result['labeled_image']
            
            # 根据文件扩展名确定保存格式
            save_path_lower = save_path.lower()
            
            if save_path_lower.endswith('.jpg') or save_path_lower.endswith('.jpeg'):
                # JPEG 格式需要转换为 RGB
                if labeled_image.mode == 'RGBA':
                    labeled_image = labeled_image.convert('RGB')
                labeled_image.save(save_path, 'JPEG', quality=95)
                self._log(f"✅ 标注图片已导出 (JPEG): {save_path}")
            elif save_path_lower.endswith('.bmp'):
                labeled_image.save(save_path, 'BMP')
                self._log(f"✅ 标注图片已导出 (BMP): {save_path}")
            else:
                # 默认 PNG 格式
                labeled_image.save(save_path, 'PNG')
                self._log(f"✅ 标注图片已导出 (PNG): {save_path}")
            
            messagebox.showinfo("成功", f"标注图片已导出到:\n{save_path}")
            
        except Exception as e:
            self._log(f"❌ 导出失败: {str(e)}")
            messagebox.showerror("错误", f"导出失败:\n{str(e)}")
    
    def _save_result(self):
        """保存解析结果"""
        if self.parsed_result is None:
            messagebox.showwarning("警告", "没有可保存的解析结果")
            return
        
        from tkinter import filedialog
        
        # 保存目录
        save_dir = filedialog.askdirectory(title="选择保存目录")
        if not save_dir:
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 保存标注图片
            img_path = Path(save_dir) / f"parsed_image_{timestamp}.png"
            self.parsed_result['image'].save(img_path)
            self._log(f"✅ 标注图片已保存: {img_path}")
            
            # 保存 JSON 结果
            json_data = {
                'timestamp': self.parsed_result['timestamp'],
                'image_size': self.parsed_result['image'].size,
                'parsed_content': self.parsed_result['parsed_content'],
                'coordinates': self.parsed_result['coordinates']
            }
            
            json_path = Path(save_dir) / f"parsed_result_{timestamp}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            self._log(f"✅ 解析结果已保存: {json_path}")
            
            messagebox.showinfo("成功", f"结果已保存到:\n{save_dir}")
            
        except Exception as e:
            self._log(f"❌ 保存失败: {str(e)}")
            messagebox.showerror("错误", f"保存失败:\n{str(e)}")
    
def main():
    """主函数"""
    root = tk.Tk()
    app = ScreenParserGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
