# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from collections import deque
import os
import random

class DrawProbabilityPredictor:
    """抽卡概率预测器"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("抽卡概率预测器")
        self.root.geometry("800x650")
        self.root.resizable(True, True)
        
        # 抽取历史（最多显示最近20次）
        self.history = deque(maxlen=20)
        
        # 创建界面
        self.create_widgets()
    
    def create_widgets(self):
        """创建界面组件"""
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(
            main_frame, 
            text="抽卡概率预测器", 
            font=("Arial", 20, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20), sticky=tk.W)
        
        # 参数设置区域
        settings_frame = ttk.LabelFrame(main_frame, text="参数设置", padding="15")
        settings_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # 总数量
        ttk.Label(settings_frame, text="总数量:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.total_var = tk.StringVar(value="100")
        total_entry = ttk.Entry(settings_frame, textvariable=self.total_var, width=15)
        total_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        # 红球数量
        ttk.Label(settings_frame, text="红球数量:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0), pady=5)
        self.red_var = tk.StringVar(value="1")
        red_entry = ttk.Entry(settings_frame, textvariable=self.red_var, width=15)
        red_entry.grid(row=0, column=3, sticky=tk.W, padx=(5, 0), pady=5)
        
        # 蓝球数量
        ttk.Label(settings_frame, text="蓝球数量:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.blue_var = tk.StringVar(value="0")
        blue_entry = ttk.Entry(settings_frame, textvariable=self.blue_var, width=15)
        blue_entry.grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=5)
        
        # 白球数量
        ttk.Label(settings_frame, text="白球数量:").grid(row=1, column=2, sticky=tk.W, padx=(20, 0), pady=5)
        self.white_var = tk.StringVar(value="0")
        white_entry = ttk.Entry(settings_frame, textvariable=self.white_var, width=15)
        white_entry.grid(row=1, column=3, sticky=tk.W, padx=(5, 0), pady=5)
        
        # 说明
        ttk.Label(
            settings_frame,
            text="说明: 每次抽取后，未抽中的球会移出池子 | 由您手动输入每次抽取结果 | 灰球数量 = 总数 - (红+蓝+白)",
            font=("Arial", 9),
            foreground="gray"
        ).grid(row=2, column=0, columnspan=4, sticky=tk.W, pady=(10, 0))
        
        # 概率显示区域
        prob_frame = ttk.LabelFrame(main_frame, text="当前概率", padding="15")
        prob_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))

        # 红球概率
        ttk.Label(prob_frame, text="红球概率:", font=("Arial", 11)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.red_prob_label = ttk.Label(prob_frame, text="1.00%", font=("Arial", 16, "bold"), foreground="#d32f2f")
        self.red_prob_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # 蓝球概率
        ttk.Label(prob_frame, text="蓝球概率:", font=("Arial", 11)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.blue_prob_label = ttk.Label(prob_frame, text="0.00%", font=("Arial", 16, "bold"), foreground="#1976d2")
        self.blue_prob_label.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # 白球概率
        ttk.Label(prob_frame, text="白球概率:", font=("Arial", 11)).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.white_prob_label = ttk.Label(prob_frame, text="0.00%", font=("Arial", 16, "bold"), foreground="#757575")
        self.white_prob_label.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # 剩余数量
        ttk.Label(prob_frame, text="剩余数量:", font=("Arial", 11)).grid(row=3, column=0, sticky=tk.W, pady=5)
        self.remaining_label = ttk.Label(prob_frame, text="100", font=("Arial", 14, "bold"))
        self.remaining_label.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # 红球剩余
        ttk.Label(prob_frame, text="红球剩余:", font=("Arial", 11)).grid(row=4, column=0, sticky=tk.W, pady=5)
        self.red_remaining_label = ttk.Label(prob_frame, text="1", font=("Arial", 14, "bold"), foreground="#d32f2f")
        self.red_remaining_label.grid(row=4, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # 蓝球剩余
        ttk.Label(prob_frame, text="蓝球剩余:", font=("Arial", 11)).grid(row=5, column=0, sticky=tk.W, pady=5)
        self.blue_remaining_label = ttk.Label(prob_frame, text="0", font=("Arial", 14, "bold"), foreground="#1976d2")
        self.blue_remaining_label.grid(row=5, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # 白球剩余
        ttk.Label(prob_frame, text="白球剩余:", font=("Arial", 11)).grid(row=6, column=0, sticky=tk.W, pady=5)
        self.white_remaining_label = ttk.Label(prob_frame, text="0", font=("Arial", 14, "bold"), foreground="#757575")
        self.white_remaining_label.grid(row=6, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # 抽取次数
       
       
       
       
       
       
       
       
        ttk.Label(prob_frame, text="已抽取次数:", font=("Arial", 11)).grid(row=7, column=0, sticky=tk.W, pady=5)
        self.draw_count_label = ttk.Label(prob_frame, text="0", font=("Arial", 14, "bold"))
        self.draw_count_label.grid(row=7, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # 操作按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=(0, 15))
        
        # 抽取按钮
        self.draw_button = ttk.Button(
            button_frame,
            text="抽取一次",
            command=self.draw_one,
            width=20
        )
        self.draw_button.grid(row=0, column=0, padx=5)

        # 五连抽按钮
        self.draw_five_button = ttk.Button(
            button_frame,
            text="五连抽",
            command=self.draw_five,
            width=20
        )
        self.draw_five_button.grid(row=0, column=1, padx=5)

        # 导出最极端情况按钮
        ttk.Button(
            button_frame,
            text="导出最极端情况",
            command=self.export_worst_case,
            width=20
        ).grid(row=0, column=2, padx=5)

        # 重置按钮
        ttk.Button(
            button_frame,
            text="重置",
            command=self.reset,
            width=15
        ).grid(row=0, column=3, padx=5)

        # 导出表格按钮
        ttk.Button(
            button_frame,
            text="导出为表格",
            command=self.export_as_image,
            width=15
        ).grid(row=0, column=4, padx=5)

        # 批量模拟按钮
        ttk.Button(
            button_frame,
            text="批量模拟",
            command=self.batch_simulate,
            width=15
        ).grid(row=0, column=5, padx=5)
        
        # 历史记录区域
        history_frame = ttk.LabelFrame(main_frame, text="抽取历史（最近20次）", padding="15")
        history_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.rowconfigure(4, weight=1)
        
        # 创建Treeview显示历史记录
        self.history_tree = ttk.Treeview(
            history_frame, 
            columns=("次数", "结果", "剩余", "概率"), 
            show="headings",
            height=10
        )
        self.history_tree.heading("次数", text="次数")
        self.history_tree.heading("结果", text="结果")
        self.history_tree.heading("剩余", text="剩余")
        self.history_tree.heading("概率", text="概率")
        
        self.history_tree.column("次数", width=80, anchor=tk.CENTER)
        self.history_tree.column("结果", width=150, anchor=tk.CENTER)
        self.history_tree.column("剩余", width=150, anchor=tk.CENTER)
        self.history_tree.column("概率", width=150, anchor=tk.CENTER)
        
        self.history_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(
            history_frame, 
            orient=tk.VERTICAL, 
            command=self.history_tree.yview
        )
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 统计信息
        self.stats_label = ttk.Label(
            main_frame,
            text="",
            font=("Arial", 10)
        )
        self.stats_label.grid(row=5, column=0, columnspan=3, pady=(10, 0), sticky=tk.W)
        
        # 初始化数据
        self.reset()
    
    def reset(self):
        """重置所有状态"""
        try:
            self.total = int(self.total_var.get())
            self.red = int(self.red_var.get())
            self.blue = int(self.blue_var.get())
            self.white = int(self.white_var.get())
            
            if self.total <= 0:
                raise ValueError("总数量必须大于0")
            if self.red < 0 or self.blue < 0 or self.white < 0:
                raise ValueError("各球数量不能为负数")
            if (self.red + self.blue + self.white) > self.total:
                raise ValueError("所有球数量之和不能大于总数量")
        except ValueError as e:
            messagebox.showerror("错误", f"参数设置错误: {str(e)}")
            return
        
        self.remaining = self.total
        self.red_remaining = self.red
        self.blue_remaining = self.blue
        self.white_remaining = self.white
        self.draw_count = 0
        self.history.clear()
        self.history_tree.delete(*self.history_tree.get_children())
        self.update_display()
        self.draw_button.config(state=tk.NORMAL)
        self.update_stats()
    
    def update_display(self):
        """更新显示信息"""
        if self.remaining > 0:
            red_prob = (self.red_remaining / self.remaining) * 100
            blue_prob = (self.blue_remaining / self.remaining) * 100
            white_prob = (self.white_remaining / self.remaining) * 100
        else:
            red_prob = 0
            blue_prob = 0
            white_prob = 0

        self.red_prob_label.config(text=f"{red_prob:.2f}%")
        self.blue_prob_label.config(text=f"{blue_prob:.2f}%")
        self.white_prob_label.config(text=f"{white_prob:.2f}%")
        self.remaining_label.config(text=str(self.remaining))
        self.red_remaining_label.config(text=str(self.red_remaining))
        self.blue_remaining_label.config(text=str(self.blue_remaining))
        self.white_remaining_label.config(text=str(self.white_remaining))
        self.draw_count_label.config(text=str(self.draw_count))

        # 更新按钮状态
        if self.remaining == 0 or self.red_remaining == 0:
            self.draw_button.config(state=tk.DISABLED)
        else:
            self.draw_button.config(state=tk.NORMAL)
    
    def update_stats(self):
        """更新统计信息"""
        red_count = sum(1 for _, result, _, _ in self.history if result == "红球")
        blue_count = sum(1 for _, result, _, _ in self.history if result == "蓝球")
        white_count = sum(1 for _, result, _, _ in self.history if result == "白球")
        gray_count = sum(1 for _, result, _, _ in self.history if result == "灰球")
        
        stats_text = f"历史统计: 红球 {red_count} 次, 蓝球 {blue_count} 次, 白球 {white_count} 次, 灰球 {gray_count} 次"
        self.stats_label.config(text=stats_text)
    
    def draw_one(self):
        """抽取一次 - 用户输入结果"""
        if self.remaining == 0 or self.red_remaining == 0:
            messagebox.showinfo("提示", "池子已空或红球已被抽中！")
            return

        self.draw_count += 1

        # 创建结果选择对话框
        result_window = tk.Toplevel(self.root)
        result_window.title(f"第 {self.draw_count} 次抽取")
        result_window.geometry("400x350")
        result_window.transient(self.root)
        result_window.grab_set()

        # 居中显示
        result_window.update_idletasks()
        x = (result_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (result_window.winfo_screenheight() // 2) - (350 // 2)
        result_window.geometry(f"400x350+{x}+{y}")

        # 框架
        frame = ttk.Frame(result_window, padding="30")
        frame.pack(expand=True, fill=tk.BOTH)

        # 提示
        ttk.Label(
            frame,
            text=f"第 {self.draw_count} 次抽取结果是什么？",
            font=("Arial", 14, "bold")
        ).pack(pady=(0, 20))

        # 结果变量
        result_var = tk.StringVar()

        # 红球按钮
        red_btn = ttk.Button(
            frame,
            text="红球",
            command=lambda: self.record_result(result_window, result_var, "红球"),
            width=15
        )
        red_btn.pack(pady=5)
        
        # 蓝球按钮
        blue_btn = ttk.Button(
            frame,
            text="蓝球",
            command=lambda: self.record_result(result_window, result_var, "蓝球"),
            width=15
        )
        blue_btn.pack(pady=5)
        
        # 白球按钮
        white_btn = ttk.Button(
            frame,
            text="白球",
            command=lambda: self.record_result(result_window, result_var, "白球"),
            width=15
        )
        white_btn.pack(pady=5)
        
        # 灰球按钮
        gray_btn = ttk.Button(
            frame,
            text="灰球",
            command=lambda: self.record_result(result_window, result_var, "灰球"),
            width=15
        )
        gray_btn.pack(pady=5)
    
    def record_result(self, window, result_var, result):
        """记录抽取结果"""
        result_var.set(result)
        window.destroy()
        
        if result == "红球":
            self.red_remaining -= 1
            messagebox.showinfo("恭喜", f"第 {self.draw_count} 次抽中了红球！🎉")
        elif result == "蓝球":
            self.blue_remaining -= 1
            messagebox.showinfo("恭喜", f"第 {self.draw_count} 次抽中了蓝球！💙")
        elif result == "白球":
            self.white_remaining -= 1
            messagebox.showinfo("恭喜", f"第 {self.draw_count} 次抽中了白球！⚪")
        
        self.remaining -= 1
        
        # 记录历史
        if self.remaining > 0:
            next_red_prob = (self.red_remaining / self.remaining) * 100
            next_blue_prob = (self.blue_remaining / self.remaining) * 100
            next_white_prob = (self.white_remaining / self.remaining) * 100
        else:
            next_red_prob = 0
            next_blue_prob = 0
            next_white_prob = 0

        prob_text = f"红:{next_red_prob:.2f}% 蓝:{next_blue_prob:.2f}% 白:{next_white_prob:.2f}%"

        self.history.append((
            self.draw_count,
            result,
            self.remaining,
            prob_text
        ))
        
        # 更新历史显示
        self.history_tree.insert("", 0, values=self.history[-1])
        
        # 限制历史记录显示数量
        items = self.history_tree.get_children()
        if len(items) > 20:
            self.history_tree.delete(items[-1])
        
        self.update_display()
        self.update_stats()

    def draw_five(self):
        """五连抽 - 连续抽取5次，预测概率"""
        if self.remaining == 0 or self.red_remaining == 0:
            messagebox.showinfo("提示", "池子已空或红球已被抽中！")
            return

        # 计算五连抽中各种球的概率
        temp_remaining = self.remaining
        temp_red = self.red_remaining
        temp_blue = self.blue_remaining
        temp_white = self.white_remaining

        red_probs = []
        blue_probs = []
        white_probs = []
        gray_probs = []

        # 计算五次抽取的概率
        for i in range(min(5, temp_remaining)):
            if temp_remaining > 0:
                red_prob = (temp_red / temp_remaining) * 100
                blue_prob = (temp_blue / temp_remaining) * 100
                white_prob = (temp_white / temp_remaining) * 100
                gray_prob = ((temp_remaining - temp_red - temp_blue - temp_white) / temp_remaining) * 100

                red_probs.append(red_prob)
                blue_probs.append(blue_prob)
                white_probs.append(white_prob)
                gray_probs.append(gray_prob)
            else:
                break

        # 创建五连抽概率预测窗口
        prob_window = tk.Toplevel(self.root)
        prob_window.title("五连抽概率预测")
        prob_window.geometry("800x600")
        prob_window.transient(self.root)
        prob_window.grab_set()

        # 居中显示
        prob_window.update_idletasks()
        x = (prob_window.winfo_screenwidth() // 2) - (400)
        y = (prob_window.winfo_screenheight() // 2) - (300)
        prob_window.geometry(f"800x600+{x}+{y}")

        # 主框架
        main = ttk.Frame(prob_window, padding="20")
        main.pack(expand=True, fill=tk.BOTH)

        # 标题
        ttk.Label(
            main,
            text="五连抽概率预测",
            font=("Arial", 18, "bold")
        ).pack(pady=(0, 20))

        # 说明
        ttk.Label(
            main,
            text=f"当前剩余: {self.remaining} | 红球: {self.red_remaining} | 蓝球: {self.blue_remaining} | 白球: {self.white_remaining}",
            font=("Arial", 11)
        ).pack(pady=(0, 20))

        # 创建表格
        frame = ttk.Frame(main)
        frame.pack(expand=True, fill=tk.BOTH)

        # 表头
        headers = ["次数", "红球概率", "蓝球概率", "白球概率", "灰球概率"]
        for col, header in enumerate(headers):
            label = ttk.Label(frame, text=header, font=("Arial", 11, "bold"), width=15)
            label.grid(row=0, column=col, padx=2, pady=2)

        # 数据行
        for i in range(len(red_probs)):
            ttk.Label(frame, text=f"第{i+1}次", width=15).grid(row=i+1, column=0, padx=2, pady=2)
            ttk.Label(frame, text=f"{red_probs[i]:.2f}%", width=15, foreground="#d32f2f").grid(row=i+1, column=1, padx=2, pady=2)
            ttk.Label(frame, text=f"{blue_probs[i]:.2f}%", width=15, foreground="#1976d2").grid(row=i+1, column=2, padx=2, pady=2)
            ttk.Label(frame, text=f"{white_probs[i]:.2f}%", width=15, foreground="#757575").grid(row=i+1, column=3, padx=2, pady=2)
            ttk.Label(frame, text=f"{gray_probs[i]:.2f}%", width=15, foreground="#999999").grid(row=i+1, column=4, padx=2, pady=2)

        # 说明文字
        ttk.Label(
            main,
            text="* 这是基于当前剩余球数量的理论概率预测，实际抽取结果可能不同",
            font=("Arial", 9),
            foreground="gray"
        ).pack(pady=(20, 0))

        # 开始五连抽按钮
        ttk.Button(
            main,
            text="开始五连抽",
            command=lambda: [prob_window.destroy(), self.do_draw_five()],
            width=20
        ).pack(pady=10)

    def do_draw_five(self):
        """执行五连抽"""
        for _ in range(5):
            if self.remaining == 0 or self.red_remaining == 0:
                messagebox.showinfo("提示", "池子已空或红球已被抽中，五连抽结束！")
                return
            self.draw_one()

    def auto_draw(self):
        """自动抽取（仅用于测试，不会自动结束）"""
        messagebox.showinfo("提示", "请使用「抽取一次」按钮，手动输入每次抽取结果")

    def export_worst_case(self):
        """导出最极端情况（最后一次才抽中红球）的模拟数据"""
        if self.red_remaining == 0:
            messagebox.showwarning("提示", "红球已被抽中，无法模拟！")
            return

        try:
            # 选择保存路径
            file_path = filedialog.asksaveasfilename(
                title="保存最极端情况数据",
                defaultextension=".txt",
                filetypes=[
                    ("文本文件", "*.txt"),
                    ("所有文件", "*.*")
                ],
                initialfile="最极端情况_最后一次才中.txt"
            )

            if not file_path:
                return

            # 模拟最极端情况
            lines = []
            lines.append("=" * 60)
            lines.append("最极端情况：最后一次才抽中红球")
            lines.append("=" * 60)
            lines.append("")
            lines.append("初始设置：")
            lines.append(f"  总数量: {self.total}")
            lines.append(f"  红球: {self.red_remaining}")
            lines.append(f"  蓝球: {self.blue_remaining}")
            lines.append(f"  白球: {self.white_remaining}")
            gray = self.total - self.red_remaining - self.blue_remaining - self.white_remaining
            lines.append(f"  灰球: {gray}")
            lines.append("")
            lines.append("=" * 60)
            lines.append("抽取过程模拟：")
            lines.append("=" * 60)
            lines.append("")

            # 临时变量用于模拟
            temp_remaining = self.remaining
            temp_red = self.red_remaining
            temp_blue = self.blue_remaining
            temp_white = self.white_remaining

            # 模拟抽取：前n-1次都不中红球，最后一次才中红球
            draw_count = 0

            # 先把蓝球和白球都抽完
            for _ in range(temp_blue):
                draw_count += 1
                temp_remaining -= 1
                temp_blue -= 1
                if temp_remaining > 0:
                    red_prob = (temp_red / temp_remaining) * 100
                    blue_prob = (temp_blue / temp_remaining) * 100
                    white_prob = (temp_white / temp_remaining) * 100
                else:
                    red_prob = 0
                    blue_prob = 0
                    white_prob = 0

                lines.append(f"第 {draw_count:3d} 次 | 蓝球 | 剩余: {temp_remaining:3d} | 红球概率: {red_prob:6.2f}% | 蓝球概率: {blue_prob:6.2f}% | 白球概率: {white_prob:6.2f}%")

            # 再把白球都抽完
            for _ in range(temp_white):
                draw_count += 1
                temp_remaining -= 1
                temp_white -= 1
                if temp_remaining > 0:
                    red_prob = (temp_red / temp_remaining) * 100
                    blue_prob = (temp_blue / temp_remaining) * 100
                    white_prob = (temp_white / temp_remaining) * 100
                else:
                    red_prob = 0
                    blue_prob = 0
                    white_prob = 0

                lines.append(f"第 {draw_count:3d} 次 | 白球 | 剩余: {temp_remaining:3d} | 红球概率: {red_prob:6.2f}% | 蓝球概率: {blue_prob:6.2f}% | 白球概率: {white_prob:6.2f}%")

            # 然后把灰球都抽完（假设所有灰球都抽完才中红球）
            gray_count = self.total - self.red - self.blue - self.white
            for _ in range(gray_count):
                draw_count += 1
                temp_remaining -= 1
                if temp_remaining > 0:
                    red_prob = (temp_red / temp_remaining) * 100
                    blue_prob = (temp_blue / temp_remaining) * 100
                    white_prob = (temp_white / temp_remaining) * 100
                else:
                    red_prob = 0
                    blue_prob = 0
                    white_prob = 0

                lines.append(f"第 {draw_count:3d} 次 | 灰球 | 剩余: {temp_remaining:3d} | 红球概率: {red_prob:6.2f}% | 蓝球概率: {blue_prob:6.2f}% | 白球概率: {white_prob:6.2f}%")

            # 最后一次抽中红球
            if temp_red > 0 and temp_remaining == temp_red:
                draw_count += 1
                temp_remaining -= 1
                temp_red -= 1
                lines.append(f"第 {draw_count:3d} 次 | 红球 | 剩余: {temp_remaining:3d} | 红球概率: 0.00%  | 蓝球概率: 0.00%  | 白球概率: 0.00%  | ★★★")
                lines.append("")
                lines.append("=" * 60)
                lines.append(f"第 {draw_count} 次才抽中红球（最极端情况）")
                lines.append("=" * 60)

            # 写入文本文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            # 同时生成表格文件（CSV格式）
            csv_path = file_path.rsplit('.', 1)[0] + '.csv'
            self.generate_csv_file(csv_path)

            messagebox.showinfo("成功", f"已成功导出：\n文本文件: {os.path.basename(file_path)}\n表格文件: {os.path.basename(csv_path)}")

        except Exception as e:
            messagebox.showerror("错误", f"导出失败：{str(e)}")

    def generate_csv_file(self, csv_path):
        """生成CSV表格文件"""
        try:
            # 收集数据
            data_rows = []

            # 表头
            data_rows.append(['次数', '结果', '剩余数量', '红球概率(%)', '蓝球概率(%)', '白球概率(%)'])

            # 临时变量用于模拟
            temp_remaining = self.remaining
            temp_red = self.red_remaining
            temp_blue = self.blue_remaining
            temp_white = self.white_remaining

            draw_count = 0

            # 模拟蓝球
            for _ in range(temp_blue):
                draw_count += 1
                temp_remaining -= 1
                temp_blue -= 1

                if temp_remaining > 0:
                    red_prob = (temp_red / temp_remaining) * 100
                    blue_prob = (temp_blue / temp_remaining) * 100
                    white_prob = (temp_white / temp_remaining) * 100
                else:
                    red_prob = 0
                    blue_prob = 0
                    white_prob = 0

                data_rows.append([draw_count, '蓝球', temp_remaining, red_prob, blue_prob, white_prob])

            # 模拟白球
            for _ in range(temp_white):
                draw_count += 1
                temp_remaining -= 1
                temp_white -= 1

                if temp_remaining > 0:
                    red_prob = (temp_red / temp_remaining) * 100
                    blue_prob = (temp_blue / temp_remaining) * 100
                    white_prob = (temp_white / temp_remaining) * 100
                else:
                    red_prob = 0
                    blue_prob = 0
                    white_prob = 0

                data_rows.append([draw_count, '白球', temp_remaining, red_prob, blue_prob, white_prob])

            # 模拟灰球
            gray_count = self.total - self.red - self.blue - self.white
            for _ in range(gray_count):
                draw_count += 1
                temp_remaining -= 1

                if temp_remaining > 0:
                    red_prob = (temp_red / temp_remaining) * 100
                    blue_prob = (temp_blue / temp_remaining) * 100
                    white_prob = (temp_white / temp_remaining) * 100
                else:
                    red_prob = 0
                    blue_prob = 0
                    white_prob = 0

                data_rows.append([draw_count, '灰球', temp_remaining, red_prob, blue_prob, white_prob])

            # 最后抽中红球
            if temp_red > 0 and temp_remaining == temp_red:
                draw_count += 1
                temp_remaining -= 1
                temp_red -= 1
                data_rows.append([draw_count, '红球★★★', temp_remaining, 0.0, 0.0, 0.0])

            # 写入CSV文件
            with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
                for row in data_rows:
                    line = ','.join(str(item) for item in row)
                    f.write(line + '\n')

        except Exception as e:
            print(f"生成CSV文件失败: {str(e)}")

    def export_as_image(self):
        """导出为表格文件"""
        if len(self.history) == 0:
            messagebox.showwarning("提示", "还没有抽取记录，无法导出！")
            return

        try:
            # 选择保存路径
            file_path = filedialog.asksaveasfilename(
                title="保存抽取记录表格",
                defaultextension=".csv",
                filetypes=[
                    ("CSV表格", "*.csv"),
                    ("所有文件", "*.*")
                ],
                initialfile="抽取记录.csv"
            )

            if not file_path:
                return

            # 写入CSV文件
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                # 表头
                f.write('次数,结果,剩余数量,概率\n')

                # 数据行
                for item in self.history:
                    draw_count, result, remaining, prob = item
                    f.write(f'{draw_count},{result},{remaining},{prob}\n')

            messagebox.showinfo("成功", f"已成功导出抽取记录到：\n{os.path.basename(file_path)}")

        except Exception as e:
            messagebox.showerror("错误", f"导出失败：{str(e)}")

    def batch_simulate(self):
        """批量模拟抽卡 - 记录每次抽到红球在第几次"""
        if self.red_remaining == 0:
            messagebox.showwarning("提示", "红球已被抽中，无法模拟！")
            return

        # 创建输入对话框
        input_window = tk.Toplevel(self.root)
        input_window.title("批量模拟设置")
        input_window.geometry("400x250")
        input_window.transient(self.root)
        input_window.grab_set()

        # 居中显示
        input_window.update_idletasks()
        x = (input_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (input_window.winfo_screenheight() // 2) - (250 // 2)
        input_window.geometry(f"400x250+{x}+{y}")

        # 框架
        frame = ttk.Frame(input_window, padding="30")
        frame.pack(expand=True, fill=tk.BOTH)

        # 提示
        ttk.Label(
            frame,
            text="批量模拟抽卡",
            font=("Arial", 14, "bold")
        ).pack(pady=(0, 10))

        ttk.Label(
            frame,
            text="模拟多次抽卡过程，统计每次抽到红球所需的次数",
            font=("Arial", 10)
        ).pack(pady=(0, 20))

        # 模拟次数输入
        input_frame = ttk.Frame(frame)
        input_frame.pack(pady=10)

        ttk.Label(input_frame, text="模拟次数:", font=("Arial", 11)).pack(side=tk.LEFT)
        simulate_count_var = tk.StringVar(value="100")
        simulate_entry = ttk.Entry(input_frame, textvariable=simulate_count_var, width=15)
        simulate_entry.pack(side=tk.LEFT, padx=(10, 0))

        # 开始按钮
        def start_simulate():
            try:
                count = int(simulate_count_var.get())
                if count <= 0:
                    raise ValueError("模拟次数必须大于0")
                if count > 100000000:
                    raise ValueError("模拟次数不能超过1亿")
                input_window.destroy()
                self.run_batch_simulate(count)
            except ValueError as e:
                messagebox.showerror("错误", f"输入错误: {str(e)}")

        ttk.Button(
            frame,
            text="开始模拟",
            command=start_simulate,
            width=20
        ).pack(pady=20)

    def run_batch_simulate(self, simulate_count):
        """执行批量模拟"""
        results = []  # 存储每次模拟的结果（红球在第几次被抽中）

        # 使用初始状态（每次模拟都从初始状态重新开始）
        initial_remaining = self.total
        initial_red = self.red
        initial_blue = self.blue
        initial_white = self.white

        # 创建进度窗口
        progress_window = tk.Toplevel(self.root)
        progress_window.title("批量模拟进行中")
        progress_window.geometry("400x150")
        progress_window.transient(self.root)
        progress_window.grab_set()

        # 居中显示
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (progress_window.winfo_screenheight() // 2) - (150 // 2)
        progress_window.geometry(f"400x150+{x}+{y}")

        # 进度标签
        progress_label = ttk.Label(
            progress_window,
            text=f"模拟进度: 0 / {simulate_count}",
            font=("Arial", 12)
        )
        progress_label.pack(pady=30)

        # 进度条
        progress_bar = ttk.Progressbar(
            progress_window,
            length=350,
            mode='determinate',
            maximum=simulate_count
        )
        progress_bar.pack(pady=10)

        # 强制更新UI
        progress_window.update()

        # 更新频率（每多少次更新一次进度）
        update_frequency = max(1, simulate_count // 1000)

        for i in range(simulate_count):
            # 重置到初始状态
            temp_remaining = initial_remaining
            temp_red = initial_red
            temp_blue = initial_blue
            temp_white = initial_white

            draw_count = 0

            # 模拟直到抽中红球
            while temp_red > 0 and temp_remaining > 0:
                draw_count += 1

                # 计算各球概率
                total_balls = temp_remaining

                # 创建球池
                balls = []
                balls.extend(['红球'] * temp_red)
                balls.extend(['蓝球'] * temp_blue)
                balls.extend(['白球'] * temp_white)
                gray_count = total_balls - temp_red - temp_blue - temp_white
                balls.extend(['灰球'] * gray_count)

                # 随机抽取
                result = random.choice(balls)

                # 更新状态
                if result == '红球':
                    temp_red -= 1
                elif result == '蓝球':
                    temp_blue -= 1
                elif result == '白球':
                    temp_white -= 1

                temp_remaining -= 1

                # 如果抽中红球，记录次数并开始下一次模拟
                if result == '红球':
                    results.append(draw_count)
                    break

            # 更新进度
            if (i + 1) % update_frequency == 0:
                progress_bar['value'] = i + 1
                progress_label.config(text=f"模拟进度: {i + 1} / {simulate_count}")
                progress_window.update()

        progress_window.destroy()

        # 显示结果
        self.show_batch_results(results, simulate_count)

    def show_batch_results(self, results, simulate_count):
        """显示批量模拟结果"""
        result_window = tk.Toplevel(self.root)
        result_window.title("批量模拟结果")
        result_window.geometry("700x600")
        result_window.transient(self.root)

        # 居中显示
        result_window.update_idletasks()
        x = (result_window.winfo_screenwidth() // 2) - (700 // 2)
        y = (result_window.winfo_screenheight() // 2) - (600 // 2)
        result_window.geometry(f"700x600+{x}+{y}")

        # 主框架
        main = ttk.Frame(result_window, padding="20")
        main.pack(expand=True, fill=tk.BOTH)

        # 标题
        ttk.Label(
            main,
            text=f"批量模拟结果（共 {simulate_count} 次）",
            font=("Arial", 16, "bold")
        ).pack(pady=(0, 15))

        # 统计信息
        if results:
            avg_draws = sum(results) / len(results)
            min_draws = min(results)
            max_draws = max(results)

            stats_frame = ttk.LabelFrame(main, text="统计信息", padding="15")
            stats_frame.pack(fill=tk.X, pady=(0, 15))

            stats_text = f"""
平均抽中次数: {avg_draws:.2f}
最少抽中次数: {min_draws}
最多抽中次数: {max_draws}
成功次数: {len(results)}
"""
            ttk.Label(
                stats_frame,
                text=stats_text.strip(),
                font=("Arial", 11)
            ).pack()

            # 分布统计
            dist_frame = ttk.LabelFrame(main, text="次数分布", padding="15")
            dist_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

            # 创建Treeview显示分布
            dist_tree = ttk.Treeview(
                dist_frame,
                columns=("次数", "频率", "百分比"),
                show="headings",
                height=15
            )
            dist_tree.heading("次数", text="抽中次数")
            dist_tree.heading("频率", text="出现频率")
            dist_tree.heading("百分比", text="百分比")

            dist_tree.column("次数", width=150, anchor=tk.CENTER)
            dist_tree.column("频率", width=150, anchor=tk.CENTER)
            dist_tree.column("百分比", width=150, anchor=tk.CENTER)

            # 统计分布
            from collections import Counter
            dist = Counter(results)

            # 按次数排序
            for draw_count in sorted(dist.keys()):
                freq = dist[draw_count]
                percent = (freq / len(results)) * 100
                dist_tree.insert("", tk.END, values=(draw_count, freq, f"{percent:.2f}%"))

            dist_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            # 滚动条
            scrollbar = ttk.Scrollbar(dist_frame, orient=tk.VERTICAL, command=dist_tree.yview)
            dist_tree.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # 导出按钮
            def export_results():
                try:
                    file_path = filedialog.asksaveasfilename(
                        title="保存模拟结果",
                        defaultextension=".csv",
                        filetypes=[
                            ("CSV表格", "*.csv"),
                            ("所有文件", "*.*")
                        ],
                        initialfile=f"批量模拟结果_{simulate_count}次.csv"
                    )

                    if not file_path:
                        return

                    with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                        f.write('模拟序号,抽中次数\n')
                        for i, draw_count in enumerate(results, 1):
                            f.write(f'{i},{draw_count}\n')

                    messagebox.showinfo("成功", f"已成功导出模拟结果！")
                except Exception as e:
                    messagebox.showerror("错误", f"导出失败：{str(e)}")

            ttk.Button(
                main,
                text="导出结果",
                command=export_results,
                width=20
            ).pack(pady=10)

def main():
    root = tk.Tk()
    app = DrawProbabilityPredictor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
