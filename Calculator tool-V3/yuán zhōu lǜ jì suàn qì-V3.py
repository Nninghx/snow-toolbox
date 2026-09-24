# 禁止生成 .pyc 文件，避免输出目录被污染
import sys
sys.dont_write_bytecode = True

import os
import time
import threading
import importlib.util
from pathlib import Path
from decimal import Decimal, getcontext

import flet as ft


def get_project_root():
    """返回项目根目录。"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def _resolve_base_class_path():
    """解析公共基类文件路径，打包后自动使用 .pyc 字节码"""
    base_py = get_project_root() / 'Core' / 'Public base class.py'
    if getattr(sys, 'frozen', False):
        return Path(importlib.util.cache_from_source(str(base_py)))
    return base_py


def run_startup_preflight():
    """执行启动前置检查：加载公共基类并验证字体可用性。"""
    base_file = _resolve_base_class_path()

    spec = importlib.util.spec_from_file_location('public_base_class', str(base_file))
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载公共基类：{base_file}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    try:
        base = module.PDFToolBase(root)
        if not root.winfo_exists():
            raise RuntimeError("授权或窗口初始化失败")

        current_font = getattr(base, 'current_font', None)
        if not current_font:
            raise RuntimeError("公共基类未成功加载字体")

        font_family = current_font[0]
        icon_path = str(base._get_project_root() / 'Image' / 'icon.ico')
        return font_family, icon_path
    finally:
        try:
            if root.winfo_exists():
                root.destroy()
        except Exception:
            pass


APP_FONT_FAMILY, APP_ICON_PATH = run_startup_preflight()

# 提高整数字符串转换限制以适应大数计算
try:
    sys.set_int_max_str_digits(100000000)
except Exception:
    pass


class PiCalculatorApp:
    """圆周率计算器 Flet 应用（Chudnovsky 算法，支持断点续算）"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.font_family = APP_FONT_FAMILY

        page.title = "圆周率计算器"
        page.window.width = 620
        page.window.height = 620
        page.window.min_width = 520
        page.window.min_height = 540
        page.padding = 0
        page.bgcolor = ft.Colors.GREY_100
        page.theme = ft.Theme(font_family=self.font_family)

        # 窗口图标由公共基类解析，直接使用
        page.window.icon = APP_ICON_PATH

        self.calculating = False
        self.cancel_flag = False

        self.digits_field = ft.TextField(
            label="计算位数",
            hint_text="请输入正整数，例如 10000",
            text_size=13,
            content_padding=ft.padding.all(10),
            border_radius=8,
        )

        self.progress = ft.ProgressBar(value=0, bar_height=8, border_radius=4,
                                          color=ft.Colors.BLUE_600)
        self.digits_label = ft.Text("当前计算位数: 0", size=12,
                                      color=ft.Colors.BLUE_GREY_700,
                                      font_family=self.font_family)
        self.result_text = ft.Text("", size=13, color=ft.Colors.BLUE_GREY_800,
                                      font_family=self.font_family, selectable=True)

        self.btn_start = ft.ElevatedButton(
            "开始计算", icon=ft.Icons.PLAY_ARROW,
            bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE,
            on_click=self.on_start, expand=1,
        )
        self.btn_resume = ft.ElevatedButton(
            "恢复计算", icon=ft.Icons.REPLAY,
            bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE,
            on_click=self.on_resume, disabled=True, expand=1,
        )
        self.btn_cancel = ft.ElevatedButton(
            "取消计算", icon=ft.Icons.STOP,
            bgcolor=ft.Colors.RED_600, color=ft.Colors.WHITE,
            on_click=self.on_cancel, disabled=True, expand=1,
        )

        self.status_text = ft.Text("就绪", size=12, color=ft.Colors.BLUE_GREY_700,
                                    font_family=self.font_family)

        self._build_ui()
        self.check_resume_file()

    def _make_card(self, title, content):
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=13, weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_GREY_700, font_family=self.font_family),
                content,
            ], spacing=8),
            padding=ft.padding.all(12),
            border_radius=10,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )

    def _build_ui(self):
        input_card = self._make_card("输入", self.digits_field)

        button_row = ft.Row([self.btn_start, self.btn_resume, self.btn_cancel], spacing=8)

        progress_card = self._make_card(
            "计算进度",
            ft.Column([self.progress, self.digits_label], spacing=8),
        )

        result_card = self._make_card(
            "结果",
            ft.Container(
                content=self.result_text,
                padding=ft.padding.all(12),
                border_radius=8,
                bgcolor=ft.Colors.BLUE_GREY_50,
                alignment=ft.alignment.center,
            ),
        )

        status_bar = ft.Container(
            content=self.status_text,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            bgcolor=ft.Colors.WHITE,
            border=ft.border.only(top=ft.BorderSide(1, ft.Colors.GREY_200)),
        )

        self.page.add(
            ft.Container(
                content=ft.Column(
                    [input_card, button_row, progress_card, result_card],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
                padding=12,
                expand=True,
            ),
        )
        self.page.add(status_bar)

    def show_status(self, message, success=True):
        self.status_text.value = message
        self.page.snack_bar = ft.SnackBar(
            ft.Text(message, font_family=self.font_family),
            bgcolor=ft.Colors.GREEN if success else ft.Colors.RED,
            open=True,
        )
        self.page.update()

    def show_info(self, title, message):
        def do_close(_e):
            self.page.dialog.open = False
            self.page.update()

        self.page.dialog = ft.AlertDialog(
            title=ft.Text(title, font_family=self.font_family),
            content=ft.Text(message, font_family=self.font_family, selectable=True),
            actions=[ft.TextButton("关闭", on_click=do_close)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog.open = True
        self.page.update()

    # ----- 临时状态文件 -----
    def get_temp_file_path(self):
        return os.path.join("Core", "pi_calc_temp.dat")

    def check_resume_file(self):
        try:
            if os.path.exists(self.get_temp_file_path()):
                self.btn_resume.disabled = False
            else:
                self.btn_resume.disabled = True
        except Exception:
            self.btn_resume.disabled = True
        self.page.update()

    def save_temp_state(self, digits, M, L, X, K, S, current_iteration):
        temp_path = self.get_temp_file_path()
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        with open(temp_path, "w") as f:
            f.write(f"{digits}\n{M}\n{L}\n{X}\n{K}\n{S}\n{current_iteration}")

    def load_temp_state(self):
        with open(self.get_temp_file_path(), "r") as f:
            digits = int(f.readline())
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

    # ----- 按钮事件 -----
    def on_start(self, e):
        if self.calculating:
            return

        digits_text = (self.digits_field.value or "").strip()
        if not digits_text:
            self.show_status("请输入计算位数", success=False)
            return
        try:
            digits = int(digits_text)
            if digits <= 0:
                raise ValueError
        except ValueError:
            self.show_status("请输入正整数", success=False)
            return

        temp_path = self.get_temp_file_path()
        if os.path.exists(temp_path):
            try:
                with open(temp_path, "r") as f:
                    saved_digits = int(f.readline().strip())
                result_file = f"pi_{saved_digits}digits.txt"
                if saved_digits >= digits and os.path.exists(result_file):
                    # 直接复用已有结果
                    with open(result_file, "r") as rf:
                        pi = rf.read()[:digits + 2]
                    filename = f"pi_{digits}digits.txt"
                    with open(filename, "w") as of:
                        of.write(pi)
                    self.show_info("结果", f"复用已有结果！\n结果已保存到 {filename}")
                    self.result_text.value = f"已复用 {saved_digits} 位结果 → {filename}"
                    self.page.update()
                    return
                elif saved_digits < digits:
                    # 询问是否续算
                    self._ask_continue_from_temp(digits, saved_digits)
                    return
            except Exception:
                pass

        self._start_new_calculation(digits)

    def _ask_continue_from_temp(self, target_digits, saved_digits):
        def do_close(_e):
            self.page.dialog.open = False
            self.page.update()

        def do_confirm(_e):
            do_close(_e)
            try:
                state = self.load_temp_state()
                self._start_thread_calculation(*state, target_override=target_digits)
            except Exception as ex:
                self.show_status(f"恢复失败：{ex}", success=False)
                self.check_resume_file()

        self.page.dialog = ft.AlertDialog(
            title=ft.Text("继续计算", font_family=self.font_family),
            content=ft.Text(
                f"发现已有 {saved_digits} 位的计算状态，是否继续计算到 {target_digits} 位？",
                font_family=self.font_family,
            ),
            actions=[
                ft.TextButton("重新开始", on_click=lambda e: (
                    do_close(e), self._start_new_calculation(target_digits)
                )),
                ft.ElevatedButton("继续计算", bgcolor=ft.Colors.BLUE_600,
                                     color=ft.Colors.WHITE, on_click=do_confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog.open = True
        self.page.update()

    def _start_new_calculation(self, digits):
        self._start_thread_calculation(digits)

    def _start_thread_calculation(self, digits, M=None, L=None, X=None,
                                     K=None, S=None, start_iteration=0,
                                     target_override=None):
        self.calculating = True
        self.cancel_flag = False
        self.btn_start.disabled = True
        self.btn_resume.disabled = True
        self.btn_cancel.disabled = False
        self.progress.value = 0
        if M is None:
            self.digits_label.value = "当前计算位数: 0"
            self.result_text.value = "计算中..."
        else:
            self.result_text.value = f"恢复计算到 {digits} 位..."
        self.page.update()

        target = target_override if target_override else digits

        threading.Thread(
            target=self.calculate_pi,
            args=(target, M, L, X, K, S, start_iteration),
            daemon=True,
        ).start()

    def on_resume(self, e):
        if self.calculating:
            return
        try:
            digits, M, L, X, K, S, current_iteration = self.load_temp_state()
            self.digits_field.value = str(digits)
            self.progress.value = min(1.0, current_iteration / (digits // 14 + 2))
            self._start_thread_calculation(
                digits, M, L, X, K, S, current_iteration
            )
        except Exception as ex:
            self.show_status(f"无法恢复计算：{ex}", success=False)
            self.check_resume_file()

    def on_cancel(self, e):
        self.cancel_flag = True
        self.result_text.value = "正在取消..."
        self.page.update()

    # ----- 计算核心 -----
    def calculate_pi(self, digits, M=None, L=None, X=None,
                       K=None, S=None, start_iteration=0):
        start_time = time.time()
        getcontext().prec = digits + 2

        CONST_L = Decimal(545140134)
        CONST_X = Decimal(-262537412640768000)
        C = 426880 * Decimal(10005).sqrt()

        if M is None:
            M = Decimal(1)
            L = Decimal(13591409)
            X = Decimal(1)
            K = 6
            S = Decimal(L)

        total_iterations = digits // 14 + 2
        batch_size = 100
        last_update_time = time.time()

        start_from = max(1, start_iteration + 1) if start_iteration else 1

        for batch_start in range(start_from, total_iterations, batch_size):
            if self.cancel_flag:
                break
            batch_end = min(batch_start + batch_size, total_iterations)
            for i in range(batch_start, batch_end):
                numerator = (K ** 3 - 16 * K) * M
                denominator = (i + 1) ** 3
                if numerator % denominator == 0:
                    M = numerator // denominator
                else:
                    M = Decimal(numerator) / Decimal(denominator)
                L += CONST_L
                X *= CONST_X
                S += Decimal(M * L) / X
                K += 12

                current_time = time.time()
                if current_time - last_update_time > 0.1:
                    progress = i / total_iterations
                    calculated_digits = min(digits, int(14 * i))
                    self._update_progress(progress, calculated_digits)
                    last_update_time = current_time

            # 批量保存状态
            try:
                self.save_temp_state(digits, M, L, X, K, S, batch_end - 1)
            except Exception:
                pass

        if not self.cancel_flag:
            pi = C / S
            pi_str = str(pi)[:digits + 2]
            elapsed = time.time() - start_time

            filename = f"pi_{digits}digits.txt"
            try:
                with open(filename, "w") as f:
                    f.write(pi_str)
            except Exception as ex:
                self.page.run_thread(
                    lambda: self.show_status(f"写入结果文件失败：{ex}", success=False)
                )

            try:
                self.save_temp_state(digits, M, L, X, K, S, total_iterations)
            except Exception:
                pass

            message = f"计算完成！耗时 {elapsed:.2f} 秒\n结果已保存到 {filename}"
            self.page.run_thread(lambda: self._on_finish(message, filename))
        else:
            self.page.run_thread(lambda: self._on_finish("计算已取消", None))

    def _update_progress(self, value, calculated_digits):
        try:
            self.progress.value = min(1.0, max(0.0, value))
            self.digits_label.value = f"当前计算位数: {calculated_digits}"
            self.page.update()
        except Exception:
            pass

    def _on_finish(self, message, filename):
        self.calculating = False
        self.cancel_flag = False
        self.btn_start.disabled = False
        self.btn_cancel.disabled = True
        if filename:
            self.result_text.value = message
            self.progress.value = 1.0
        else:
            self.result_text.value = message
            self.digits_label.value = "当前计算位数: 0"
        self.show_info("结果", message)
        self.check_resume_file()
        self.page.update()


def main(page: ft.Page):
    PiCalculatorApp(page)


if __name__ == "__main__":
    ft.app(target=main)
