# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

import pygame
import sys
import random
import os
import math
import tkinter as tk
from tkinter import filedialog

# ─── 常量 ───
WIDTH, HEIGHT = 1000, 700
FPS = 60
BG_COLOR = (245, 247, 250)
GRID_COLOR = (200, 208, 220)
TEXT_COLOR = (40, 44, 52)
HIGHLIGHT_COLOR = (59, 130, 246)
SHADOW_COLOR = (0, 0, 0, 40)
SUCCESS_COLOR = (34, 197, 94)
BORDER_COLOR = (170, 178, 192)
TRAY_COLOR = (238, 241, 246)
CENTER_COLOR = (232, 236, 242)

INFO_BAR_HEIGHT = 60

# 布局：左侧托盘 | 中间拼台区 | 右侧托盘
LEFT_TRAY_W = 175
RIGHT_TRAY_W = 175
CENTER_X = LEFT_TRAY_W
CENTER_Y = INFO_BAR_HEIGHT + 20
CENTER_W = WIDTH - LEFT_TRAY_W - RIGHT_TRAY_W
CENTER_H = HEIGHT - INFO_BAR_HEIGHT - 40
LEFT_TRAY = pygame.Rect(0, INFO_BAR_HEIGHT, LEFT_TRAY_W, HEIGHT - INFO_BAR_HEIGHT)
RIGHT_TRAY = pygame.Rect(WIDTH - RIGHT_TRAY_W, INFO_BAR_HEIGHT, RIGHT_TRAY_W, HEIGHT - INFO_BAR_HEIGHT)

# 难度模式
DIFFICULTIES = [
    {"name": "简单", "rows": 3, "cols": 3, "desc": "3×3 = 9 块"},
    {"name": "普通", "rows": 4, "cols": 4, "desc": "4×4 = 16 块"},
    {"name": "困难", "rows": 5, "cols": 5, "desc": "5×5 = 25 块"},
    {"name": "大师", "rows": 6, "cols": 7, "desc": "6×7 = 42 块"},
]


# ─── 凹凸边缘生成 ───

def _edge_points(p0, p1, perp, tab_type, tab_size):
    """生成一条边的凹凸路径点（不含起点，含终点）
    p0, p1: 边的两个角点 (x, y)
    perp: 朝向外的单位法向量 (dx, dy)
    tab_type: 1=凸, -1=凹, 0=平
    tab_size: 凸起/凹陷的大小
    """
    pts = []
    ex = p1[0] - p0[0]
    ey = p1[1] - p0[1]
    px, py = perp

    if tab_type == 0:
        pts.append((p1[0], p1[1]))
        return pts

    t = tab_type * tab_size
    # 关键分界点 (沿边方向的比例)
    a1 = (p0[0] + 0.35 * ex, p0[1] + 0.35 * ey)
    b1 = (p0[0] + 0.40 * ex, p0[1] + 0.40 * ey)
    c  = (p0[0] + 0.50 * ex, p0[1] + 0.50 * ey)
    d1 = (p0[0] + 0.60 * ex, p0[1] + 0.60 * ey)
    e1 = (p0[0] + 0.65 * ex, p0[1] + 0.65 * ey)

    # 从 p0 沿边到 a1 (直线)
    pts.append((a1[0], a1[1]))
    # 颈部内收
    pts.append((b1[0] + 0.04 * px * t, b1[1] + 0.04 * py * t))
    # 凸起/凹陷左侧弧 (用折线模拟圆弧)
    for frac, scale in [(0.38, 0.55), (0.42, 0.85), (0.46, 1.0), (0.50, 1.05),
                        (0.54, 1.0), (0.58, 0.85), (0.62, 0.55)]:
        px_pt = p0[0] + frac * ex + scale * px * t
        py_pt = p0[1] + frac * ey + scale * py * t
        pts.append((px_pt, py_pt))
    # 颈部内收
    pts.append((d1[0] + 0.04 * px * t, d1[1] + 0.04 * py * t))
    # 继续到 p1
    pts.append((e1[0], e1[1]))
    pts.append((p1[0], p1[1]))
    return pts


def generate_piece_outline(row, col, rows, cols, h_edges, v_edges, cell_w, cell_h, tab_size):
    """生成拼图块的轮廓点列表（顺时针）
    h_edges[r][c]: 第 r 行水平缝, 第 c 列格子的上边缘类型
    v_edges[r][c]: 第 r 行垂直缝, 第 c 列格子的左边缘类型
    """
    x0 = col * cell_w
    y0 = row * cell_h
    x1 = x0 + cell_w
    y1 = y0 + cell_h

    # 四个角
    tl = (x0, y0)
    tr = (x1, y0)
    br = (x1, y1)
    bl = (x0, y1)

    # 各边的外法向
    top_perp = (0, -1)
    right_perp = (1, 0)
    bottom_perp = (0, 1)
    left_perp = (-1, 0)

    # 四条边的凹凸类型（底边和右边取反，确保相邻块凹凸互补）
    top_type = h_edges[row][col]        # 上边缘
    right_type = -v_edges[row][col + 1] # 右边缘（取反）
    bottom_type = -h_edges[row + 1][col]# 下边缘（取反）
    left_type = v_edges[row][col]       # 左边缘

    outline = [tl]
    outline.extend(_edge_points(tl, tr, top_perp, top_type, tab_size))
    outline.extend(_edge_points(tr, br, right_perp, right_type, tab_size))
    outline.extend(_edge_points(br, bl, bottom_perp, bottom_type, tab_size))
    outline.extend(_edge_points(bl, tl, left_perp, left_type, tab_size))
    return outline


# ─── 拼图块 ───

class JigsawPiece:
    """凹凸拼图块"""

    def __init__(self, full_image, outline_pts, cell_x, cell_y, cell_w, cell_h, correct_row, correct_col):
        self.correct_row = correct_row
        self.correct_col = correct_col
        self.cell_w = cell_w
        self.cell_h = cell_h
        self.dragging = False
        self.drag_offset = (0, 0)

        # 计算轮廓包围盒（cell-local 坐标）
        min_x = min(p[0] for p in outline_pts)
        min_y = min(p[1] for p in outline_pts)
        max_x = max(p[0] for p in outline_pts)
        max_y = max(p[1] for p in outline_pts)

        surf_w = int(max_x - min_x) + 2
        surf_h = int(max_y - min_y) + 2
        self.surface = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)

        self.offset_x = cell_x + min_x
        self.offset_y = cell_y + min_y

        # 轮廓平移到表面坐标
        local_pts = [(p[0] - min_x + 1, p[1] - min_y + 1) for p in outline_pts]

        # 单元格内容在表面上的位置（用于吸附对齐）
        self.img_offset_x = int(-min_x + 1)
        self.img_offset_y = int(-min_y + 1)

        # 直接 blit 完整图片：单元格原点在图片中的位置 → 表面 img_offset
        blit_x = self.img_offset_x - correct_col * cell_w
        blit_y = self.img_offset_y - correct_row * cell_h
        self.surface.blit(full_image, (blit_x, blit_y))

        # 用多边形遮罩裁剪出凹凸形状
        mask_surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        pygame.draw.polygon(mask_surf, (255, 255, 255, 255), local_pts)
        mask_alpha = pygame.surfarray.pixels_alpha(mask_surf)
        alpha = pygame.surfarray.pixels_alpha(self.surface)
        alpha[mask_alpha < 128] = 0
        alpha[mask_alpha >= 128] = 255
        del alpha, mask_alpha

        # 创建碰撞 mask
        self.mask = pygame.mask.from_surface(self.surface)

        # 碰撞矩形（包围盒）
        self.rect = pygame.Rect(self.offset_x, self.offset_y, surf_w, surf_h)

    @property
    def center(self):
        return (self.rect.centerx, self.rect.centery)

    def start_drag(self, pos):
        self.dragging = True
        self.drag_offset = (pos[0] - self.rect.x, pos[1] - self.rect.y)

    def stop_drag(self):
        self.dragging = False

    def move_to(self, pos):
        self.rect.x = pos[0] - self.drag_offset[0]
        self.rect.y = pos[1] - self.drag_offset[1]
        # 更新 offset
        self.offset_x = self.rect.x
        self.offset_y = self.rect.y

    def snap_to_grid(self, grid_positions):
        """吸附到最近的网格位置，对齐单元格图像而非包围盒"""
        # 单元格图像中心在世界坐标的位置
        cell_cx = self.rect.x + self.img_offset_x + self.cell_w // 2
        cell_cy = self.rect.y + self.img_offset_y + self.cell_h // 2
        best_dist = float("inf")
        best_pos = None
        for (gx, gy) in grid_positions:
            dist = math.hypot(cell_cx - gx, cell_cy - gy)
            if dist < best_dist:
                best_dist = dist
                best_pos = (gx, gy)
        snap_threshold = min(self.cell_w, self.cell_h) * 0.4
        if best_pos and best_dist < snap_threshold * 3:
            # 让单元格图像对齐到网格位置
            self.rect.x = best_pos[0] - self.img_offset_x - self.cell_w // 2
            self.rect.y = best_pos[1] - self.img_offset_y - self.cell_h // 2
            self.offset_x = self.rect.x
            self.offset_y = self.rect.y

    def collide_point(self, pos):
        """像素级点击检测"""
        lx = pos[0] - self.rect.x
        ly = pos[1] - self.rect.y
        if 0 <= lx < self.rect.width and 0 <= ly < self.rect.height:
            try:
                return self.mask.get_at((int(lx), int(ly)))
            except (IndexError, TypeError):
                return 1  # 回退到矩形碰撞
        return 0


# ─── 游戏主类 ───

class PuzzleGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("凹凸拼图游戏")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("microsoftyahei", 18)
        self.big_font = pygame.font.SysFont("microsoftyahei", 28)
        self.title_font = pygame.font.SysFont("microsoftyahei", 36)
        self.small_font = pygame.font.SysFont("microsoftyahei", 14)

        self.state = "menu"  # menu / playing
        self.menu_hover = -1  # 菜单悬停索引
        self._menu_rects = []  # 菜单按钮矩形
        self.difficulty_idx = 1  # 默认普通

        self.rows = 4
        self.cols = 4
        self.pieces = []
        self.original_image = None
        self.puzzle_w = 0
        self.puzzle_h = 0
        self.cell_w = 0
        self.cell_h = 0
        self.tab_size = 0
        self.grid_positions = []
        self.grid_origins = []
        self.move_count = 0
        self.start_time = 0
        self.finish_time = 0
        self.completed = False

        # 预加载默认图片
        self._default_img_path = os.path.join(os.path.dirname(__file__), "..", "Image", "icon.png")
        if not os.path.exists(self._default_img_path):
            self._default_img_path = None

    def start_game(self, difficulty_idx):
        """根据难度开始游戏"""
        self.difficulty_idx = difficulty_idx
        diff = DIFFICULTIES[difficulty_idx]
        self.rows = diff["rows"]
        self.cols = diff["cols"]
        self.state = "playing"
        if self._default_img_path:
            self.load_image(self._default_img_path)
        else:
            self._create_default_image()

    def _create_default_image(self):
        """创建默认渐变图片"""
        surf = pygame.Surface((480, 360))
        for y in range(360):
            for x in range(480):
                r = int(50 + 180 * (x / 480))
                g = int(50 + 180 * (y / 360))
                b = int(150 + 80 * ((x + y) / (480 + 360)))
                surf.set_at((x, y), (r, g, b))
        pygame.draw.circle(surf, (255, 200, 80), (240, 180), 80)
        pygame.draw.rect(surf, (255, 100, 100), (100, 80, 120, 120), 4)
        pygame.draw.polygon(surf, (100, 255, 150), [(350, 50), (420, 200), (280, 200)])
        self.original_image = surf
        self._setup_puzzle()

    def load_image(self, path):
        """加载图片并设置拼图"""
        try:
            raw = pygame.image.load(path).convert_alpha()
        except pygame.error:
            raw = pygame.image.load(path).convert()

        # 确保图片完全不透明（合成到白色背景上）
        img = pygame.Surface(raw.get_size(), pygame.SRCALPHA)
        img.fill((255, 255, 255, 255))
        img.blit(raw, (0, 0))
        img = img.convert()  # 转为无 alpha 通道

        iw, ih = img.get_size()
        scale = min(CENTER_W / iw, CENTER_H / ih, 1.0)
        new_w = int(iw * scale)
        new_h = int(ih * scale)
        new_w = (new_w // self.cols) * self.cols
        new_h = (new_h // self.rows) * self.rows
        if new_w < self.cols or new_h < self.rows:
            return
        img = pygame.transform.smoothscale(img, (new_w, new_h))
        self.original_image = img
        self._setup_puzzle()

    def _open_file_dialog(self):
        """打开文件选择对话框，让用户选择自定义图片"""
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.askopenfilename(
            title="选择拼图图片",
            filetypes=[
                ("图片文件", "*.png *.jpg *.jpeg *.bmp *.webp"),
                ("所有文件", "*.*"),
            ]
        )
        root.destroy()
        if path and os.path.isfile(path):
            self._default_img_path = path
            if self.state == "playing":
                self.load_image(path)
            # 菜单状态下只更新路径，等用户选难度后开始

    def _generate_edges(self):
        """随机生成凹凸边缘类型"""
        # h_edges[r][c]: 水平缝（行 r 上方），r=0..rows, c=0..cols-1
        # 边界为 0（平），内部边随机 ±1
        h_edges = []
        for r in range(self.rows + 1):
            row = []
            for c in range(self.cols):
                if r == 0 or r == self.rows:
                    row.append(0)
                else:
                    row.append(random.choice([-1, 1]))
            h_edges.append(row)

        # v_edges[r][c]: 垂直缝（列 c 左方），r=0..rows-1, c=0..cols
        v_edges = []
        for r in range(self.rows):
            row = []
            for c in range(self.cols + 1):
                if c == 0 or c == self.cols:
                    row.append(0)
                else:
                    row.append(random.choice([-1, 1]))
            v_edges.append(row)

        return h_edges, v_edges

    def _setup_puzzle(self):
        """切割图片并初始化拼图块"""
        img = self.original_image
        self.puzzle_w = img.get_width()
        self.puzzle_h = img.get_height()
        self.cell_w = self.puzzle_w // self.cols
        self.cell_h = self.puzzle_h // self.rows
        self.tab_size = int(min(self.cell_w, self.cell_h) * 0.18)

        # 计算网格位置（居中于中间区域）
        area_x = CENTER_X + (CENTER_W - self.puzzle_w) // 2
        area_y = CENTER_Y + (CENTER_H - self.puzzle_h) // 2

        self.grid_positions = []
        self.grid_origins = []
        for r in range(self.rows):
            for c in range(self.cols):
                cx = area_x + c * self.cell_w + self.cell_w // 2
                cy = area_y + r * self.cell_h + self.cell_h // 2
                self.grid_positions.append((cx, cy))
                self.grid_origins.append((area_x + c * self.cell_w, area_y + r * self.cell_h))

        # 生成边缘
        h_edges, v_edges = self._generate_edges()

        # 切割并创建拼图块
        self.pieces = []
        for r in range(self.rows):
            for c in range(self.cols):
                # 生成轮廓（转为相对于 cell 左上角的坐标）
                abs_outline = generate_piece_outline(
                    r, c, self.rows, self.cols,
                    h_edges, v_edges,
                    self.cell_w, self.cell_h, self.tab_size
                )
                ox = c * self.cell_w
                oy = r * self.cell_h
                outline = [(p[0] - ox, p[1] - oy) for p in abs_outline]

                # 创建拼图块（直接传完整图片，内部计算 blit 偏移）
                cell_x = area_x + c * self.cell_w
                cell_y = area_y + r * self.cell_h
                piece = JigsawPiece(img, outline, cell_x, cell_y,
                                    self.cell_w, self.cell_h, r, c)

                # 随机位置：放在左右两侧托盘
                pw, ph = piece.rect.width, piece.rect.height
                if random.random() < 0.5:
                    rx_min = LEFT_TRAY.x + 2
                    rx_max = max(rx_min, LEFT_TRAY.x + LEFT_TRAY_W - pw - 2)
                    rx = random.randint(rx_min, rx_max)
                else:
                    rx_min = RIGHT_TRAY.x + 2
                    rx_max = max(rx_min, RIGHT_TRAY.x + RIGHT_TRAY_W - pw - 2)
                    rx = random.randint(rx_min, rx_max)
                ry_min = LEFT_TRAY.y + 5
                ry_max = max(ry_min, LEFT_TRAY.y + LEFT_TRAY.h - ph - 5)
                ry = random.randint(ry_min, ry_max)
                piece.rect.x = rx
                piece.rect.y = ry
                piece.offset_x = rx
                piece.offset_y = ry

                self.pieces.append(piece)

        self.move_count = 0
        self.start_time = pygame.time.get_ticks()
        self.completed = False

    def check_completion(self):
        """检查是否完成：单元格图像中心对齐到网格位置"""
        for piece in self.pieces:
            idx = piece.correct_row * self.cols + piece.correct_col
            target_cx, target_cy = self.grid_positions[idx]
            # 单元格图像中心
            cell_cx = piece.rect.x + piece.img_offset_x + piece.cell_w // 2
            cell_cy = piece.rect.y + piece.img_offset_y + piece.cell_h // 2
            dist = math.hypot(cell_cx - target_cx, cell_cy - target_cy)
            if dist > min(self.cell_w, self.cell_h) * 0.25:
                return False
        return True

    def draw_menu(self):
        """绘制难度选择菜单"""
        self.screen.fill(BG_COLOR)

        # 标题
        title = self.title_font.render("凹凸拼图游戏", True, TEXT_COLOR)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 80))

        subtitle = self.small_font.render("选择难度开始游戏", True, (120, 130, 145))
        self.screen.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, 130))

        # 难度按钮
        btn_w, btn_h = 320, 70
        start_y = 200
        gap = 20
        self._menu_rects = []

        colors = [
            (34, 197, 94),   # 简单 - 绿
            (59, 130, 246),  # 普通 - 蓝
            (245, 158, 11),  # 困难 - 橙
            (239, 68, 68),   # 大师 - 红
        ]

        for i, diff in enumerate(DIFFICULTIES):
            y = start_y + i * (btn_h + gap)
            rect = pygame.Rect(WIDTH // 2 - btn_w // 2, y, btn_w, btn_h)
            self._menu_rects.append(rect)

            # 悬停效果
            if self.menu_hover == i:
                pygame.draw.rect(self.screen, (255, 255, 255), rect, border_radius=12)
                pygame.draw.rect(self.screen, colors[i], rect, 3, border_radius=12)
            else:
                pygame.draw.rect(self.screen, (255, 255, 255), rect, border_radius=12)
                pygame.draw.rect(self.screen, (210, 216, 226), rect, 2, border_radius=12)

            # 难度色块标识
            dot_rect = pygame.Rect(rect.x + 20, rect.y + btn_h // 2 - 8, 16, 16)
            pygame.draw.rect(self.screen, colors[i], dot_rect, border_radius=4)

            # 难度名称
            name_surf = self.big_font.render(diff["name"], True, TEXT_COLOR)
            self.screen.blit(name_surf, (rect.x + 50, rect.y + 12))

            # 描述
            desc_surf = self.small_font.render(diff["desc"], True, (120, 130, 145))
            self.screen.blit(desc_surf, (rect.x + 50, rect.y + 44))

        # 底部：选择图片按钮
        img_btn_w, img_btn_h = 200, 44
        img_btn_y = start_y + len(DIFFICULTIES) * (btn_h + gap) + 15
        self._img_btn_rect = pygame.Rect(WIDTH // 2 - img_btn_w // 2, img_btn_y, img_btn_w, img_btn_h)
        if self._img_btn_rect.collidepoint(pygame.mouse.get_pos()):
            pygame.draw.rect(self.screen, (255, 255, 255), self._img_btn_rect, border_radius=10)
            pygame.draw.rect(self.screen, HIGHLIGHT_COLOR, self._img_btn_rect, 2, border_radius=10)
        else:
            pygame.draw.rect(self.screen, (255, 255, 255), self._img_btn_rect, border_radius=10)
            pygame.draw.rect(self.screen, (210, 216, 226), self._img_btn_rect, 2, border_radius=10)
        img_label = self.font.render("📂 选择自定义图片", True, TEXT_COLOR)
        self.screen.blit(img_label, (self._img_btn_rect.centerx - img_label.get_width() // 2,
                                     self._img_btn_rect.centery - img_label.get_height() // 2))

        # 当前图片名称
        if self._default_img_path:
            img_name = os.path.basename(self._default_img_path)
            if len(img_name) > 30:
                img_name = img_name[:27] + "..."
            name_surf = self.small_font.render(f"当前图片: {img_name}", True, (140, 148, 160))
        else:
            name_surf = self.small_font.render("当前图片: 默认渐变图", True, (140, 148, 160))
        self.screen.blit(name_surf, (WIDTH // 2 - name_surf.get_width() // 2, img_btn_y + img_btn_h + 10))

        # 底部提示
        tip = self.small_font.render("按 ESC 退出  |  支持拖入图片", True, (160, 168, 180))
        self.screen.blit(tip, (WIDTH // 2 - tip.get_width() // 2, HEIGHT - 40))

        pygame.display.flip()

    def draw(self):
        if self.state == "menu":
            self.draw_menu()
            return

        self.screen.fill(BG_COLOR)

        # ─── 顶部信息栏 ───
        elapsed = self.finish_time if self.completed else (pygame.time.get_ticks() - self.start_time) // 1000
        minutes = elapsed // 60
        seconds = elapsed % 60

        diff_name = DIFFICULTIES[self.difficulty_idx]["name"]
        info_texts = [
            f"难度: {diff_name}",
            f"步数: {self.move_count}",
            f"时间: {minutes:02d}:{seconds:02d}",
        ]
        x_offset = 20
        for txt in info_texts:
            surf = self.font.render(txt, True, TEXT_COLOR)
            self.screen.blit(surf, (x_offset, 18))
            x_offset += surf.get_width() + 30

        # 右上角“换图”按钮
        self._change_img_rect = pygame.Rect(WIDTH - 80, 14, 65, 32)
        if self._change_img_rect.collidepoint(pygame.mouse.get_pos()):
            pygame.draw.rect(self.screen, (255, 255, 255), self._change_img_rect, border_radius=6)
            pygame.draw.rect(self.screen, HIGHLIGHT_COLOR, self._change_img_rect, 2, border_radius=6)
        else:
            pygame.draw.rect(self.screen, (255, 255, 255), self._change_img_rect, border_radius=6)
            pygame.draw.rect(self.screen, (210, 216, 226), self._change_img_rect, 1, border_radius=6)
        ci_surf = self.small_font.render("换图", True, TEXT_COLOR)
        self.screen.blit(ci_surf, (self._change_img_rect.centerx - ci_surf.get_width() // 2,
                                   self._change_img_rect.centery - ci_surf.get_height() // 2))

        pygame.draw.line(self.screen, GRID_COLOR, (10, INFO_BAR_HEIGHT), (WIDTH - 10, INFO_BAR_HEIGHT), 1)

        # ─── 左右托盘背景 ───
        pygame.draw.rect(self.screen, TRAY_COLOR, LEFT_TRAY)
        pygame.draw.rect(self.screen, TRAY_COLOR, RIGHT_TRAY)
        pygame.draw.line(self.screen, GRID_COLOR, (LEFT_TRAY_W, INFO_BAR_HEIGHT), (LEFT_TRAY_W, HEIGHT), 1)
        pygame.draw.line(self.screen, GRID_COLOR, (WIDTH - RIGHT_TRAY_W, INFO_BAR_HEIGHT), (WIDTH - RIGHT_TRAY_W, HEIGHT), 1)

        # ─── 中间拼台区背景 ───
        center_rect = pygame.Rect(CENTER_X, CENTER_Y, CENTER_W, CENTER_H)
        pygame.draw.rect(self.screen, CENTER_COLOR, center_rect, border_radius=8)

        # 绘制目标网格（淡色）
        for i, (ox, oy) in enumerate(self.grid_origins):
            rect = pygame.Rect(ox, oy, self.cell_w, self.cell_h)
            pygame.draw.rect(self.screen, GRID_COLOR, rect, 1)

        # ─── 绘制拼图块 ───
        sorted_pieces = sorted(self.pieces, key=lambda p: p.dragging)
        for piece in sorted_pieces:
            if piece.dragging:
                # 拖拽阴影
                shadow_surf = pygame.Surface(
                    (piece.rect.width + 10, piece.rect.height + 10), pygame.SRCALPHA
                )
                shadow_surf.blit(piece.surface, (6, 6))
                # 给阴影加暗色
                shadow_mask = pygame.mask.from_surface(shadow_surf)
                dark_surf = pygame.Surface(shadow_surf.get_size(), pygame.SRCALPHA)
                dark_surf.fill((0, 0, 0, 35))
                shadow_surf.blit(dark_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                self.screen.blit(shadow_surf, (piece.rect.x - 3, piece.rect.y - 3))
            else:
                # 静态淡阴影
                shadow_surf = pygame.Surface(
                    (piece.rect.width + 6, piece.rect.height + 6), pygame.SRCALPHA
                )
                shadow_surf.blit(piece.surface, (3, 3))
                shadow_mask = pygame.mask.from_surface(shadow_surf)
                dark_surf = pygame.Surface(shadow_surf.get_size(), pygame.SRCALPHA)
                dark_surf.fill((0, 0, 0, 18))
                shadow_surf.blit(dark_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                self.screen.blit(shadow_surf, (piece.rect.x - 1, piece.rect.y - 1))

            self.screen.blit(piece.surface, piece.rect)

        # ─── 完成提示 ───
        if self.completed:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, 180))
            self.screen.blit(overlay, (0, 0))

            msg = self.big_font.render("拼图完成！", True, SUCCESS_COLOR)
            time_text = self.font.render(
                f"用时 {minutes:02d}:{seconds:02d}，共 {self.move_count} 步", True, TEXT_COLOR
            )
            hint_text = self.small_font.render("按 ESC 返回菜单  |  拖入新图片重新开始", True, (120, 130, 145))
            self.screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 50))
            self.screen.blit(time_text, (WIDTH // 2 - time_text.get_width() // 2, HEIGHT // 2))
            self.screen.blit(hint_text, (WIDTH // 2 - hint_text.get_width() // 2, HEIGHT // 2 + 35))

        pygame.display.flip()

    def _get_piece_at(self, pos):
        """点击检测：mask 精确检测（基于多边形遮罩）"""
        for piece in reversed(self.pieces):
            if piece.rect.collidepoint(pos):
                if piece.collide_point(pos):
                    return piece
        return None

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == "playing":
                        self.state = "menu"
                    else:
                        return False

            elif event.type == pygame.MOUSEMOTION:
                if self.state == "menu":
                    self.menu_hover = -1
                    for i, rect in enumerate(self._menu_rects):
                        if rect.collidepoint(event.pos):
                            self.menu_hover = i
                            break
                else:
                    for piece in self.pieces:
                        if piece.dragging:
                            piece.move_to(event.pos)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.state == "menu":
                    # 检查“选择图片”按钮
                    if hasattr(self, '_img_btn_rect') and self._img_btn_rect.collidepoint(event.pos):
                        self._open_file_dialog()
                        continue
                    for i, rect in enumerate(self._menu_rects):
                        if rect.collidepoint(event.pos):
                            self.start_game(i)
                            break
                else:
                    # 检查“换图”按钮
                    if hasattr(self, '_change_img_rect') and self._change_img_rect.collidepoint(event.pos):
                        self._open_file_dialog()
                        continue
                    if not self.completed:
                        piece = self._get_piece_at(event.pos)
                        if piece:
                            piece.start_drag(event.pos)
                            self.pieces.remove(piece)
                            self.pieces.append(piece)

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.state == "playing":
                    for piece in self.pieces:
                        if piece.dragging:
                            piece.stop_drag()
                            piece.snap_to_grid(self.grid_positions)
                            self.move_count += 1
                            if not self.completed and self.check_completion():
                                self.completed = True
                                self.finish_time = (pygame.time.get_ticks() - self.start_time) // 1000

            elif event.type == pygame.DROPFILE:
                path = event.file
                if os.path.isfile(path) and path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
                    self._default_img_path = path
                    if self.state == "menu":
                        self.start_game(self.difficulty_idx)
                    else:
                        self.load_image(path)

        return True

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = PuzzleGame()
    game.run()
