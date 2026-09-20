# -*- coding: utf-8 -*-
# 禁止生成 .pyc 文件
# PDF自动改文件名：通过 OCR 识别版权页（CIP 数据）自动提取书名、作者等信息并按模板改名
import sys
sys.dont_write_bytecode = True

import os
import re
import shutil
import threading
import subprocess
import importlib.util
from pathlib import Path

import flet as ft

import fitz  # PyMuPDF：提取文本与渲染页面为图片
import pytesseract  # Tesseract OCR 的 Python 封装
from PIL import Image


def get_project_root():
    """获取项目根目录"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def _resolve_base_class_path():
    """解析公共基类文件路径，打包后自动使用 .pyc 字节码"""
    base_py = get_project_root() / 'Core' / 'Public base class.py'
    if getattr(sys, 'frozen', False):
        import importlib.util
        return Path(importlib.util.cache_from_source(str(base_py)))
    return base_py


def run_startup_preflight():
    """复用 Core 公共基类执行启动前置流程：授权检查 -> 窗口图标 -> 字体加载；失败时直接报错"""
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
        return True, font_family
    except Exception as exc:
        if root.winfo_exists():
            root.destroy()
        raise RuntimeError(f"启动前置检查失败：无法使用项目自带字体。{exc}") from exc
    finally:
        if root.winfo_exists():
            root.destroy()


def check_tesseract():
    """检查 Tesseract OCR 引擎与语言包可用性。
    返回 (可用, 引擎路径或None, 说明文本, 已安装语言包列表)。
    引擎装了但缺中文包时 可用=True 但说明文本给出警告（中文 OCR 会失败）。
    """
    tesseract_path = shutil.which('tesseract')
    if not tesseract_path:
        # Windows 常见安装路径
        common_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            os.path.expanduser(r'~\AppData\Local\Tesseract-OCR\tesseract.exe'),
        ]
        for path in common_paths:
            if os.path.exists(path):
                tesseract_path = path
                break
    if not tesseract_path:
        return False, None, (
            "未找到 Tesseract OCR 引擎。\n\n"
            "请先安装 Tesseract：\n"
            "1. 访问 https://github.com/UB-Mannheim/tesseract/wiki\n"
            "2. 下载安装包并安装\n"
            "3. 安装时勾选需要的语言包（如 Chinese Simplified）\n"
            "4. 安装后重启本工具"
        ), []

    langs = []
    try:
        out = subprocess.check_output(
            [tesseract_path, '--list-langs'],
            text=True, errors='ignore', timeout=10,
        )
        langs = [ln.strip() for ln in out.splitlines()
                 if ln.strip() and not ln.strip().startswith('List')]
    except Exception:
        pass

    zh_packs = [l for l in langs if l.startswith('chi_')]
    if not zh_packs:
        return True, tesseract_path, (
            "Tesseract 引擎已就绪，但未安装中文语言包（chi_sim/chi_tra）。\n"
            "扫描版中文书将无法识别。请在 Tesseract 安装目录的 tessdata 中补装中文包，"
            "或重新运行安装程序勾选 Chinese Simplified / Chinese Traditional。"
        ), langs
    return True, tesseract_path, f"Tesseract 已就绪（语言包：{', '.join(sorted(zh_packs))}）", langs


STARTUP_OK, APP_FONT_FAMILY = run_startup_preflight()
if not STARTUP_OK:
    raise RuntimeError("启动前置检查失败：项目自带字体无法使用")


# OCR 语言映射
OCR_LANGUAGES = {
    '中文简体 + 英文': 'chi_sim+eng',
    '中文繁体 + 英文': 'chi_tra+eng',
    '仅英文': 'eng',
    '仅中文简体': 'chi_sim',
}

# 字段提取正则
# 匹配 ISBN 编号，允许短横线和空格
ISBN_RE = re.compile(r'ISBN\s*([\d][\d\s\-]{8,16}[\dXx])', re.IGNORECASE)
# 匹配最后位置的日期，如 "2019.8" "2019年8月"
DATE_RE = re.compile(r'(\d{4})\s*[\.\-/年]?\s*(\d{1,2})?')
# 匹配 " .—" " .-" " 。—" 形式的出版地分隔符
PUB_SEP_RE = re.compile(r'[.。]?\s*[—\-一]\s*')

# 默认文件名模板
DEFAULT_TEMPLATE = '{title}-{author}'


def clean_isbn(raw):
    """清理 ISBN：去掉多余空格（保留连字符），仅接受去除连字符后 10/13 位、末位允许 X 的合法号"""
    if not raw:
        return ''
    s = re.sub(r'\s', '', raw).strip()
    core = re.sub(r'-', '', s)
    if len(core) in (10, 13) and core[:-1].isdigit() \
            and (core[-1].isdigit() or core[-1] in 'xX'):
        # 原样保留连字符，如 978-7-5001-5962-9；OCR 无连字符时则返回纯数字
        return s.upper()
    return ''


def extract_isbn(text):
    """从全文中抽取 ISBN（保留连字符）"""
    m = ISBN_RE.search(text)
    if m:
        return clean_isbn(m.group(1))
    return ''


def trim_credit_block(s):
    """保留责任者块原样：著/编/译等后缀、国籍前缀 (美) 等一律不清除，
    仅去除首尾空白与 OCR 常见残渣标点，方便用于文件名模板与展示"""
    if not s:
        return ''
    return s.strip().strip(' :：;；,，、.。…')


def parse_cip_line(line):
    """解析 CIP 主信息行。
    典型样本: "祭语风中:英文/次仁罗布著;(美)约索·戴尔(Joshua Dyer)译.一北京:中译出版社，2019.8"
    也接受尾部粘连 "…2019.8(少数民族作家海外推广系列)ISBN 978-…" 等断行后拼回的内容。
    返回字典 {title, subtitle, author, translator, place, publisher, date}。
    """
    info = {
        'title': '', 'subtitle': '', 'author': '', 'translator': '',
        'place': '', 'publisher': '', 'date': ''
    }
    if not line:
        return info

    s = line.strip().strip(' .。')
    # 剥掉可能残留的 "图书在版编目(CIP)数据" 前缀
    s = strip_cip_marker_prefix(s)
    if not s:
        return info

    # 0) 尾部净化：截掉 ISBN、日期后紧跟的丛书名(括号内容)、分类行等粘连内容
    m_isbn = re.search(r'ISBN', s, re.IGNORECASE)
    if m_isbn:
        s = s[:m_isbn.start()].strip()
    m_paren = re.search(r'((?:19|20)\d{2}(?:[.\-年/]\d{1,2})?月?)\s*[\(（]', s)
    if m_paren:
        s = s[:m_paren.start(1) + len(m_paren.group(1))].strip()
    s = s.strip(' .（(')

    # 1) 用 ".—/-/一" 把"作者/译者"块与"出版地:出版社,日期"块分开
    head, tail = split_head_tail(s)

    # 2) 解析头部 title[:subtitle] / author[;translator]（斜杠可能是全角／）
    parts = [p for p in re.split(r'[/／]', head) if p.strip()]
    if not parts:
        return info

    # 第一个块：完整题名原样保留（含 : 副题分隔符，如 "祭语风中:英文"），
    # 冒号前后 OCR 常多出空格，规整掉以便展示与文件名一致
    title_block = re.sub(r'\s*([：:])\s*', r'\1', parts[0].strip())
    info['title'] = title_block
    _, sub = split_title_subtitle(title_block)
    info['subtitle'] = sub

    # 第二个块：作者著[;译者译]；若还有第三+块，是额外的责任者（译者、绘者等）。
    # 责任者按 CIP 原样保留：作者带 著/编 后缀、译者带国籍前缀 (美) 与 译 后缀
    credit_block = parts[1].strip() if len(parts) >= 2 else ''
    extra_blocks = parts[2:] if len(parts) > 2 else []

    # 在 author_block 内按 ; 或 ； 分隔
    if credit_block:
        for sep in [';', '；']:
            if sep in credit_block:
                ap = credit_block.split(sep, 1)
                info['author'] = trim_credit_block(ap[0])
                info['translator'] = trim_credit_block(ap[1])
                break
        else:
            # 无分号
            if '著' in credit_block or '编' in credit_block:
                info['author'] = trim_credit_block(credit_block)
            elif '译' in credit_block:
                info['translator'] = trim_credit_block(credit_block)

    # 在额外块中找译者
    if not info['translator']:
        for blk in extra_blocks:
            if '译' in blk:
                info['translator'] = trim_credit_block(blk)
                break

    # 3) 解析尾部：place:publisher,date
    if tail:
        info.update(parse_publication_tail(tail))

    return info


def strip_cip_marker_prefix(s):
    """剥掉文本开头残留的 "图书在版编目(CIP)数据" 字样（OCR 可能多字少字）"""
    m = re.search(
        r'图书在版编目\s*[\(（]?\s*CIP\s*[\)）]?\s*数据?', s, re.IGNORECASE
    )
    if m:
        return s[m.end():].lstrip(' .:：/')
    m2 = re.search(r'(?:图书)?在版编目|CIP\s*数据', s, re.IGNORECASE)
    if m2:
        return s[m2.end():].lstrip(' .:：/')
    return s


def split_head_tail(s):
    """把主行切成 头部(题名/责任者) 与 尾部(出版地:出版社,日期)。
    优先按"责任后缀(著/编/译…)+短横+出版段"锚定，避免人名里的"一"被误切。"""
    # 方式1: 责任者后缀(著/编/译)后跟 [—\-一] 起为出版段（tail 内不再含短横）
    # 注意 head 需保留责任后缀字（如"刘慈欣著"），否则作者名会丢失
    m = re.search(
        r'(?P<sep>主编|编著|编译|译者|著|编|译|撰)'
        r'\s*[。.．]?\s*[—\-－一]\s*(?P<tail>[^—\-－一]+)$',
        s,
    )
    if m:
        head = s[:m.start() + len(m.group('sep'))].strip()
        tail = m.group('tail').strip().strip(' .')
        if tail:
            return head, tail
    # 方式2: 通用"点+短横"切分
    m2 = re.search(r'[。.．]?\s*[—\-－一]\s*(?P<tail>.+)$', s)
    if m2:
        head = s[:m2.start()].strip()
        tail = m2.group('tail').strip().strip(' .')
        if tail:
            return head, tail
    return s, ''


def split_title_subtitle(block):
    """在题名块内分离主副标题"""
    block = block.strip()
    for sep in ['：', ':', '·']:
        if sep in block:
            parts = block.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    return block, ''


def parse_publication_tail(tail):
    """解析出版地/出版社/日期，例如 "北京:中译出版社，2019.8"。
    返回 dict: {place, publisher, date}。"""
    out = {'place': '', 'publisher': '', 'date': ''}
    if not tail:
        return out

    s = tail.strip().strip(' .')
    # 1) 先把日期（位于末尾的 [年.]?[月]）从尾部剥离
    m = DATE_RE.search(s)
    if m:
        date_raw = m.group(0).strip().rstrip('.')
        out['date'] = normalize_date(date_raw)
        # 只移除匹配的最后一段日期字符串
        # 找到日期起始位置，截掉
        idx = s.rfind(m.group(0))
        if idx >= 0:
            s = s[:idx] + s[idx + len(m.group(0)):]
        s = s.rstrip(' ,，。.').strip()

    # 2) 把"出版地"和"出版社"分开（按 : 或 ：）
    for sep in ['：', ':']:
        if sep in s:
            ps = s.split(sep, 1)
            out['place'] = ps[0].strip()
            out['publisher'] = ps[1].strip()
            break
    else:
        # 没有冒号时整段作为出版社
        out['publisher'] = s.strip()

    # 3) 出版社尾部清理：OCR 断行可能导致"出版社，2019.8〈丛书名)"粘连
    #    截掉从括号/书名号起的丛书名尾巴（避免污染出版社字段）
    if out['publisher']:
        out['publisher'] = re.sub(
            r'[，,、。;；]?\s*[〈《[【（(].*$', '', out['publisher']
        ).strip().strip('，,、。 .')

    return out


def normalize_date(date_raw):
    """归一化日期字符串为 YYYY.MM 形式（去除汉字单位）"""
    s = date_raw.strip()
    # "2019年8月" -> "2019.8"
    s = s.replace('年', '.').replace('月', '').replace('日', '')
    # "2019/8" -> "2019.8"
    s = s.replace('/', '.').replace('-', '.')
    # 收尾清理
    s = s.strip(' .')
    # 仅保留 "YYYY" 或 "YYYY.M" "YYYY.MM"
    m = re.match(r'(\d{4})(?:\.(\d{1,2}))?', s)
    if m:
        year = m.group(1)
        month = m.group(2) or ''
        return f"{year}.{month}" if month else year
    return date_raw


def is_cip_marker_line(line):
    """是否为 CIP 数据区标题行，如 "图书在版编目（CIP）数据"（OCR 可能有缺字）"""
    return bool(re.search(r'在版编目|CIP\s*数据', line, re.IGNORECASE))


def is_classification_line(line):
    """是否为 CIP 分类检索行(I.1祭…/Ⅳ.①I247.5…)、核字号行或出版发行信息行，
    可作为拼合终止条件"""
    if '中国版本图书馆' in line or line.startswith('出版发行'):
        return True
    # 形如 "I.1…" "Ⅱ.①…" "IV.1I247.5" 的行首
    if re.match(r'^[ⅠIIⅣⅤ１1２2３3４4]{1,3}\s*[\.．、]\s*[①②③④⑤]?', line):
        return True
    return False


def smart_join_lines(parts):
    """智能拼合被断行的 CIP 各行：
    相邻行若同为 ASCII 字母/数字(如英文人名 Joshua / Dyer 被折行)则补一个空格，
    中文字符之间直接相连，避免名字粘连"""
    joined = ''
    for ln in parts:
        if not ln:
            continue
        if (joined and joined[-1].isascii() and joined[-1].isalnum()
                and ln[0].isascii() and ln[0].isalnum()):
            joined += ' ' + ln
        else:
            joined += ln
    return joined


def find_cip_lines(text):
    """在单页文本中找出 CIP 主信息行，返回候选字符串列表。
    方式A：整行即含 '著' 与 '译' 的完整主行（文字层 PDF 常见）。
    方式B：定位 '图书在版编目(CIP)数据' 标记行，把其后被 OCR 断行的主行拼回一条。
    传入内容应尽量为单页文本，避免跨页粘连。
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    candidates = []

    # 方式 A：单行完整主行
    for line in lines:
        if is_cip_marker_line(line) or line.upper().startswith('ISBN'):
            continue
        if len(line) >= 20 and '著' in line and '译' in line:
            candidates.append(line)
            return candidates

    # 方式 B：从标记行开始拼合后续断行
    for i, line in enumerate(lines):
        if not is_cip_marker_line(line):
            continue
        joined_parts = []
        for j in range(i, len(lines)):
            cur = lines[j]
            if j > i:
                # 终止条件：ISBN 行 / 丛书名行 / 分类检索行 / 核字号行
                if cur.upper().startswith('ISBN'):
                    break
                # OCR 会把丛书名行 OCR 成各种左括号/书名号开头，统统计入终止
                if cur.startswith(('(', '（', '【', '〈', '《', '[', '〔', '「')) \
                        and not re.search(r'著|编|译|译著', cur):
                    break
                if is_classification_line(cur):
                    break
            joined_parts.append(cur)
        joined = strip_cip_marker_prefix(smart_join_lines(joined_parts))
        if joined and re.search(r'著|编|译|/', joined):
            candidates.append(joined)
            break
    return candidates


def sanitize_filename(s):
    """去除 Windows 文件系统非法字符"""
    if not s:
        return ''
    # 替换非法字符
    s = re.sub(r'[\\/:*?"<>|\r\n\t]', '', s)
    # 去除收尾不允许的字符
    s = s.strip('. ')
    return s


def unique_target_path(target_path):
    """若目标路径已存在，自动追加 (1)(2)... 后缀，返回一个不冲突的路径"""
    if not os.path.exists(target_path):
        return target_path
    stem, ext = os.path.splitext(target_path)
    n = 1
    while True:
        candidate = f"{stem} ({n}){ext}"
        if not os.path.exists(candidate):
            return candidate
        n += 1


def build_filename(template, info):
    """按模板拼接新文件名（不含扩展名）"""
    mapping = {
        'title': info.get('title', '') or '',
        'subtitle': info.get('subtitle', '') or '',
        'author': info.get('author', '') or '',
        'translator': info.get('translator', '') or '',
        'publisher': info.get('publisher', '') or '',
        'place': info.get('place', '') or '',
        'date': info.get('date', '') or '',
        'isbn': info.get('isbn', '') or '',
    }
    name = template
    for key, val in mapping.items():
        name = name.replace('{' + key + '}', val)

    # 收尾清理：合并连续分隔符、trim
    name = re.sub(r'[-_—\s]+', '-', name)
    name = name.strip('-_ .')
    return sanitize_filename(name)


def page_needs_ocr(text):
    """判断单页文字层是否需要 OCR 兜底。
    纯扫描页(无文字层)、页面文字极少、以及带乱码替换符的劣质双层 PDF 都返回 True，
    保证这类书真正走到 OCR 而不是被"总字符数够多就跳过 OCR"误伤。"""
    if not text or not text.strip():
        return True
    compact = re.sub(r'\s+', '', text)
    if not compact:
        return True
    # 替换符占比较高 -> 内嵌文字层为乱码
    if compact.count('\ufffd') / len(compact) > 0.02:
        return True
    return len(compact) < 30


def extract_metadata_from_pdf(pdf_path, lang_code='chi_sim+eng', dpi=200,
                              tesseract_cmd=None, max_pages=5):
    """从 PDF 中提取书籍元数据。
    策略：按"页"粒度判断——文字层可用直接用；文字层过少/乱码/为空
    （纯扫描页或劣质双层 PDF）的页才对该页单独 OCR（灰度渲染提精度）。
    """
    result = {
        'title': '', 'subtitle': '', 'author': '', 'translator': '',
        'place': '', 'publisher': '', 'date': '', 'isbn': '',
        'source': 'none', 'error': '', 'note': ''
    }

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    doc = None
    try:
        doc = fitz.open(pdf_path)
        total = len(doc)
        max_check = max(1, min(int(max_pages or 5), total))

        # 逐页提取文本，保持"页"边界（防止 CIP 拼合跨页粘连）
        page_texts = []
        ocr_used = False
        last_ocr_error = ''
        for i in range(max_check):
            text = ''
            try:
                page = doc[i]
                text = page.get_text('text') or ''
            except Exception:
                text = ''
            if not page_needs_ocr(text):
                page_texts.append(text.strip())
                continue
            # 该页需 OCR：渲染为灰度图再识别，降低彩色底纹/反色干扰
            ocr_used = True
            try:
                page = doc[i]
                pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)
                img = Image.frombytes('L', [pix.width, pix.height], pix.samples)
                page_texts.append(pytesseract.image_to_string(img, lang=lang_code).strip())
            except Exception as exc:
                last_ocr_error = str(exc) or type(exc).__name__
                page_texts.append('')

        result['source'] = 'ocr' if ocr_used else ('text' if any(page_texts) else 'none')
        # OCR 全程失败（如语言包缺失/引擎异常）时把原因透出，避免“识别为空却无提示”
        if ocr_used and not any(page_texts) and last_ocr_error:
            result['error'] = f"OCR 引擎调用失败：{last_ocr_error}"

        # 1) ISBN：任意一页命中即可
        for text in page_texts:
            isbn = extract_isbn(text)
            if isbn:
                result['isbn'] = isbn
                break

        # 2) CIP 主信息行：逐页尝试（先文字层页、后 OCR 页按序即先到先得）
        for text in page_texts:
            if not text:
                continue
            candidates = find_cip_lines(text)
            if not candidates:
                continue
            meta = parse_cip_line(candidates[0])
            if meta.get('title'):
                result.update(meta)
                break

        # 3) 仍未识别到书名：给出可读诊断，供用户在展开详情中自查
        if not result.get('title'):
            joined = '\n'.join(page_texts)
            if not re.search(r'在版编目|CIP\s*数据', joined, re.IGNORECASE):
                result['note'] = (
                    f"前 {max_check} 页未定位到\"图书在版编目(CIP)\"区："
                    f"若版权页超出前 {max_check} 页，请调大\"扫描前N页\"；"
                    "纯扫描件请确认 Tesseract 中文语言包可用，或调高 DPI 重试。"
                )
            else:
                result['note'] = "已找到 CIP 数据区，但未能解析出主信息行，可尝试提高 DPI 后重试。"

    except Exception as exc:
        result['error'] = str(exc)
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass

    return result


class PDFAutorenameApp:
    """PDF自动改文件名主应用类。"""

    def __init__(self):
        self.page = None
        self.font_family = APP_FONT_FAMILY
        self.processing = False
        self.tesseract_ok = False
        self.tesseract_cmd = None
        self.tesseract_langs = []
        self.tesseract_info = ''

        # 工作列表：每条为 dict {path, info, controls, enabled}
        self.rows = []
        # 当前文件列表（仅作为来源记录）
        self.input_paths = []

    # ---------------------- UI ----------------------
    def build(self, page: ft.Page):
        self.page = page
        page.title = "PDF自动改文件名"
        page.window.width = 880
        page.window.height = 760
        page.window.min_width = 760
        page.window.min_height = 620
        page.window.center()
        page.padding = 16
        page.theme_mode = ft.ThemeMode.LIGHT

        # 设置窗口图标
        icon_path = get_project_root() / 'Image' / 'icon.ico'
        if icon_path.exists():
            page.window.icon = str(icon_path)

        # Tesseract 可用性（引擎、路径、提示、已装语言包）
        (self.tesseract_ok, self.tesseract_cmd,
         self.tesseract_info, self.tesseract_langs) = check_tesseract()

        # 文件 / 文件夹选择对话框
        self.file_picker = ft.FilePicker(on_result=self.on_files_picked)
        self.folder_picker = ft.FilePicker(on_result=self.on_folder_picked)
        page.overlay.extend([self.file_picker, self.folder_picker])

        # 输入区卡片
        self.file_text = ft.Text(
            "未选择文件",
            size=13, color=ft.Colors.BLUE_GREY_500, font_family=self.font_family,
            expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.file_count_text = ft.Text(
            "", size=12, color=ft.Colors.BLUE_GREY_600, font_family=self.font_family,
        )

        input_card = self._make_card(
            "PDF 来源",
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.FOLDER_OPEN, size=18, color=ft.Colors.BLUE_GREY_400),
                            self.file_text,
                            ft.ElevatedButton(
                                "选择文件", icon=ft.Icons.UPLOAD_FILE,
                                on_click=lambda e: self.file_picker.pick_files(
                                    dialog_title="选择PDF文件",
                                    allow_multiple=True,
                                    file_type=ft.FilePickerFileType.CUSTOM,
                                    allowed_extensions=["pdf"],
                                ),
                            ),
                            ft.ElevatedButton(
                                "选择文件夹", icon=ft.Icons.FOLDER,
                                on_click=lambda e: self.folder_picker.get_directory_path(
                                    dialog_title="选择PDF文件夹",
                                ),
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    ft.Row(
                        [self.file_count_text],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    ft.Row(
                        [
                            ft.OutlinedButton(
                                "清空列表", icon=ft.Icons.CLEAR_ALL,
                                on_click=self.on_clear_list,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                ],
                spacing=6,
            ),
        )

        # OCR / 模板 设置卡片
        self.lang_dropdown = ft.Dropdown(
            label="识别语言",
            value=list(OCR_LANGUAGES.keys())[0],
            options=[ft.dropdown.Option(k) for k in OCR_LANGUAGES.keys()],
            width=240, border_radius=8,
            text_size=14,
            text_style=ft.TextStyle(font_family=self.font_family),
            content_padding=ft.padding.symmetric(vertical=4, horizontal=10),
        )
        self.dpi_field = ft.TextField(
            label="DPI", value="200", width=110, border_radius=8,
            content_padding=ft.padding.all(10), text_size=14,
            keyboard_type=ft.KeyboardType.NUMBER,
            text_style=ft.TextStyle(font_family=self.font_family),
        )
        self.pages_field = ft.TextField(
            label="扫描前 N 页", value="5", width=130, border_radius=8,
            content_padding=ft.padding.all(10), text_size=14,
            keyboard_type=ft.KeyboardType.NUMBER,
            text_style=ft.TextStyle(font_family=self.font_family),
        )
        self.template_field = ft.TextField(
            label="文件名模板",
            value=DEFAULT_TEMPLATE,
            hint_text="可用变量: {title} {subtitle} {author} {translator} {publisher} {place} {date} {isbn}（{title} 含副题名；值均为 CIP 原样）",
            border_radius=8, content_padding=ft.padding.all(10),
            text_size=14, expand=True,
            text_style=ft.TextStyle(font_family=self.font_family),
        )

        zh_installed = any(l.startswith('chi_') for l in self.tesseract_langs)
        if not self.tesseract_ok:
            engine_status_row = ft.Row(
                [
                    ft.Icon(ft.Icons.ERROR_OUTLINE, size=16, color=ft.Colors.RED),
                    ft.Text(
                        "Tesseract 未安装（仅能处理含文字层的 PDF）",
                        size=12, color=ft.Colors.RED, font_family=self.font_family,
                        tooltip=self.tesseract_info,
                    ),
                ],
                spacing=4,
            )
        elif not zh_installed:
            engine_status_row = ft.Row(
                [
                    ft.Icon(ft.Icons.WARNING_AMBER, size=16, color=ft.Colors.ORANGE),
                    ft.Text(
                        "Tesseract 缺中文语言包（扫描中文书将识别为空）",
                        size=12, color=ft.Colors.ORANGE, font_family=self.font_family,
                        tooltip=self.tesseract_info,
                    ),
                ],
                spacing=4,
            )
        else:
            engine_status_row = ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=16, color=ft.Colors.GREEN),
                    ft.Text(
                        self.tesseract_info or "Tesseract 已就绪",
                        size=12, color=ft.Colors.GREEN, font_family=self.font_family,
                    ),
                ],
                spacing=4,
            )

        settings_card = self._make_card(
            "识别与模板",
            ft.Column(
                [
                    engine_status_row,
                    ft.Row(
                        [self.lang_dropdown, self.dpi_field, self.pages_field],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    self.template_field,
                    ft.Text(
                        "默认模板 {title}-{author}。例如：祭语风中:英文-次仁罗布著"
                        "（书名内冒号在存盘时自动去除）",
                        size=12, color=ft.Colors.BLUE_GREY_500, font_family=self.font_family,
                    ),
                ],
                spacing=8,
            ),
        )

        # 预览列表卡片（动态填充）
        self.preview_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)
        self.preview_empty_text = ft.Text(
            "尚未选择 PDF 文件。请添加文件后点击「开始识别」以提取书名等元数据。",
            size=13, color=ft.Colors.BLUE_GREY_500, font_family=self.font_family,
            text_align=ft.TextAlign.CENTER,
        )
        preview_card = self._make_card(
            "预览",
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                "请在「文件名」列编辑最终名称，未勾选的行不会改名。",
                                size=12, color=ft.Colors.BLUE_GREY_500,
                                font_family=self.font_family, expand=True,
                            ),
                            ft.TextButton(
                                "全选", icon=ft.Icons.CHECK_BOX,
                                on_click=lambda e: self.toggle_all_rows(True),
                            ),
                            ft.TextButton(
                                "全不选", icon=ft.Icons.CHECK_BOX_OUTLINE_BLANK,
                                on_click=lambda e: self.toggle_all_rows(False),
                            ),
                        ],
                        spacing=6,
                    ),
                    ft.Container(
                        content=ft.Column(
                            [self.preview_empty_text, self.preview_column],
                            spacing=8,
                        ),
                        height=260,
                    ),
                ],
                spacing=6,
            ),
        )

        # 进度条
        self.progress = ft.ProgressBar(
            visible=False, color=ft.Colors.BLUE,
            bgcolor=ft.Colors.GREY_200, bar_height=6, border_radius=4, expand=True,
        )
        self.progress_text = ft.Text(
            "", size=12, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family,
        )

        # 操作按钮
        self.extract_btn = ft.ElevatedButton(
            "开始识别", icon=ft.Icons.SEARCH,
            on_click=self.on_extract_click, height=40,
        )
        self.rename_btn = ft.ElevatedButton(
            "应用改名", icon=ft.Icons.DRIVE_FILE_RENAME_OUTLINE,
            on_click=self.on_rename_click, height=40, disabled=True,
        )

        # 状态栏
        self.status_text = ft.Text(
            "就绪", size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family,
        )
        self.stats_text = ft.Text(
            size=13, color=ft.Colors.BLUE_GREY_700, font_family=self.font_family,
        )

        page.add(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.AUTO_AWESOME, size=32, color=ft.Colors.BLUE),
                            ft.Text(
                                "PDF自动改文件名", size=28, weight=ft.FontWeight.BOLD,
                                font_family=self.font_family,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=10,
                    ),
                    ft.Divider(thickness=1, opacity=0.3),
                    input_card,
                    settings_card,
                    preview_card,
                    ft.Row(
                        [self.progress, self.progress_text],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=10,
                    ),
                    ft.Row(
                        [self.extract_btn, self.rename_btn],
                        alignment=ft.MainAxisAlignment.END, spacing=10,
                    ),
                    ft.Container(
                        content=ft.Row(
                            [self.status_text, self.stats_text],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=ft.padding.symmetric(vertical=8, horizontal=12),
                        bgcolor=ft.Colors.BLUE_GREY_50,
                        border_radius=8,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                    ),
                ],
                expand=True, spacing=10, scroll=ft.ScrollMode.AUTO,
            ),
        )

    def _make_card(self, title, content):
        """白色圆角卡片"""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        title, size=13, weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_GREY_700, font_family=self.font_family,
                    ),
                    content,
                ],
                spacing=8,
            ),
            padding=ft.padding.all(12),
            border_radius=10,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
        )

    # ---------------------- 事件回调 ----------------------
    def on_files_picked(self, e):
        """单/多文件选择回调"""
        if not e.files:
            return
        paths = [f.path for f in e.files if f.path]
        if not paths:
            return
        self.add_paths(paths)

    def on_folder_picked(self, e):
        """文件夹选择回调，递归收集 PDF"""
        if not e.path or not os.path.isdir(e.path):
            return
        collected = []
        for root, _, files in os.walk(e.path):
            for name in files:
                if name.lower().endswith('.pdf'):
                    collected.append(os.path.join(root, name))
        if not collected:
            self.show_status("所选文件夹内未找到 PDF 文件", success=False)
            return
        self.add_paths(collected)

    def add_paths(self, paths):
        """添加 PDF 路径到工作列表，自动去重"""
        existing = {r['path'] for r in self.rows}
        added = 0
        for p in paths:
            if not p or not os.path.exists(p):
                continue
            if not p.lower().endswith('.pdf'):
                continue
            if p in existing:
                continue
            existing.add(p)
            self.input_paths.append(p)
            # 初始占位：未识别
            self.rows.append({
                'path': p,
                'info': {
                    'title': '', 'subtitle': '', 'author': '',
                    'translator': '', 'publisher': '', 'place': '',
                    'date': '', 'isbn': '', 'source': 'none',
                    'error': '', 'note': ''
                },
                'enabled': True,
                'new_name_text': ft.TextField(
                    value=os.path.splitext(os.path.basename(p))[0],
                    border_radius=6, content_padding=ft.padding.all(8),
                    text_size=13, expand=True,
                    text_style=ft.TextStyle(font_family=self.font_family),
                ),
                'checkbox': ft.Checkbox(value=True),
                'summary_text': ft.Text(
                    "未识别", size=12, color=ft.Colors.BLUE_GREY_500,
                    font_family=self.font_family,
                ),
            })
            added += 1
        self.refresh_input_summary()
        self.rebuild_preview()
        self.update_stats()
        self.page.update()
        if added:
            self.show_status(f"已添加 {added} 个文件，共 {len(self.rows)} 个")

    def on_clear_list(self, e):
        """清空列表"""
        self.rows.clear()
        self.input_paths.clear()
        self.refresh_input_summary()
        self.rebuild_preview()
        self.rename_btn.disabled = True
        self.update_stats()
        self.page.update()
        self.show_status("已清空")

    def refresh_input_summary(self):
        """更新输入区的小信息"""
        if not self.input_paths:
            self.file_text.value = "未选择文件"
            self.file_text.color = ft.Colors.BLUE_GREY_500
            self.file_count_text.value = ""
            return
        # 显示前若干个文件，更多用 … 省略
        sample = self.input_paths[:1]
        if len(self.input_paths) == 1:
            self.file_text.value = os.path.basename(self.input_paths[0])
        else:
            self.file_text.value = f"{os.path.basename(sample[0])} 等 {len(self.input_paths)} 个文件"
        self.file_text.color = ft.Colors.BLUE_GREY_900
        self.file_text.tooltip = "\n".join(self.input_paths)
        self.file_count_text.value = f"共 {len(self.rows)} 个 PDF 待处理"

    def rebuild_preview(self):
        """重新生成预览列表"""
        self.preview_column.controls.clear()
        if not self.rows:
            self.preview_empty_text.visible = True
            return
        self.preview_empty_text.visible = False

        for idx, row in enumerate(self.rows):
            row['checkbox'].on_change = lambda e, i=idx: self.on_row_toggle(i, e.control.value)
            row['new_name_text'].on_change = lambda e, i=idx: self.on_new_name_change(i)

            expand_btn = ft.IconButton(
                icon=ft.Icons.EXPAND_MORE,
                tooltip="查看识别详情",
                on_click=lambda e, i=idx: self.toggle_detail(i),
                icon_size=18,
            )
            row['expand_btn'] = expand_btn

            detail_text = ft.Text(
                self._format_detail(row['info']),
                size=12, color=ft.Colors.BLUE_GREY_700,
                font_family=self.font_family, visible=False,
            )
            row['detail_text'] = detail_text

            header = ft.Row(
                [
                    row['checkbox'],
                    ft.Icon(ft.Icons.PICTURE_AS_PDF, size=16, color=ft.Colors.RED),
                    ft.Column(
                        [
                            ft.Text(
                                os.path.basename(row['path']),
                                size=13, weight=ft.FontWeight.W_500,
                                font_family=self.font_family, no_wrap=True,
                                overflow=ft.TextOverflow.ELLIPSIS, expand=True,
                            ),
                            row['summary_text'],
                        ],
                        spacing=2, expand=True,
                    ),
                    row['new_name_text'],
                    expand_btn,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8,
            )

            container = ft.Container(
                content=ft.Column(
                    [header, detail_text],
                    spacing=4,
                ),
                padding=ft.padding.all(8),
                border_radius=8,
                bgcolor=ft.Colors.BLUE_GREY_50,
                border=ft.border.all(1, ft.Colors.GREY_200),
            )
            self.preview_column.controls.append(container)

    def _format_detail(self, info):
        """格式化识别详情文本（字段均为 CIP 原样值，{title} 已含副题名）"""
        parts = []
        for key, label in [
            ('title', '书名'), ('author', '作者'),
            ('translator', '翻译'), ('publisher', '出版社'),
            ('date', '时间'), ('isbn', 'ISBN'),
        ]:
            val = info.get(key) or ''
            parts.append(f"{label}：{val or '-'}")
        if info.get('source'):
            parts.append(f"来源：{'文字层' if info['source'] == 'text' else 'OCR' if info['source'] == 'ocr' else info['source']}")
        if info.get('note'):
            parts.append(f"提示：{info['note']}")
        if info.get('error'):
            parts.append(f"错误：{info['error']}")
        return "\n".join(parts)

    def toggle_detail(self, idx):
        """展开/收起识别详情"""
        row = self.rows[idx]
        row['detail_text'].visible = not row['detail_text'].visible
        row['expand_btn'].icon = ft.Icons.EXPAND_LESS if row['detail_text'].visible else ft.Icons.EXPAND_MORE
        self.page.update()

    def on_row_toggle(self, idx, value):
        self.rows[idx]['enabled'] = bool(value)

    def on_new_name_change(self, idx):
        # 文本变化无需做复杂处理，预览由 build_filename 实时显示
        pass

    def toggle_all_rows(self, enabled):
        for row in self.rows:
            row['enabled'] = bool(enabled)
            row['checkbox'].value = bool(enabled)
        self.page.update()

    # ---------------------- 识别流程 ----------------------
    def on_extract_click(self, e):
        """启动后台线程，逐个识别 PDF 元数据"""
        if self.processing:
            return
        if not self.rows:
            self.show_status("请先选择 PDF 文件", success=False)
            return

        # 校验 DPI 与页数
        try:
            dpi = int(self.dpi_field.value or "200")
            if dpi < 72 or dpi > 1200:
                raise ValueError("DPI 需在 72-1200 之间")
        except ValueError as err:
            self.show_status(f"DPI 无效: {err}", success=False)
            return
        try:
            page_count = int(self.pages_field.value or "5")
            if page_count < 1 or page_count > 20:
                raise ValueError("扫描前 N 页需在 1-20 之间")
        except ValueError as err:
            self.show_status(f"页数无效: {err}", success=False)
            return

        lang_name = self.lang_dropdown.value or list(OCR_LANGUAGES.keys())[0]
        lang_code = OCR_LANGUAGES[lang_name]

        # 检查 OCR 是否需要 Tesseract（如果原 PDF 无文字层）
        # 真实判断留到线程内
        self.processing = True
        self.extract_btn.disabled = True
        self.rename_btn.disabled = True
        self.progress.value = 0
        self.progress.visible = True
        self.progress_text.value = "准备中..."
        self.show_status("正在识别 PDF 元数据...")

        threading.Thread(
            target=self._do_extract,
            args=(lang_code, dpi, page_count),
            daemon=True,
        ).start()

    def _do_extract(self, lang_code, dpi, page_count):
        """后台线程：逐个提取元数据并刷新界面"""
        total = len(self.rows)
        ok_count = 0
        # 设置 Tesseract 路径
        tesseract_cmd = self.tesseract_cmd if self.tesseract_ok else None

        for i, row in enumerate(self.rows):
            try:
                info = extract_metadata_from_pdf(
                    row['path'], lang_code=lang_code,
                    dpi=dpi,
                    tesseract_cmd=tesseract_cmd,
                    max_pages=page_count,
                )
            except Exception as exc:
                info = {
                    'title': '', 'subtitle': '', 'author': '', 'translator': '',
                    'place': '', 'publisher': '', 'date': '', 'isbn': '',
                    'source': 'error', 'error': str(exc), 'note': '',
                }

            row['info'] = info
            row['summary_text'].value = self._row_summary(info)
            row['summary_text'].color = (
                ft.Colors.GREEN if info.get('title') or info.get('isbn')
                else ft.Colors.ORANGE if info.get('error')
                else ft.Colors.BLUE_GREY_500
            )
            if row.get('detail_text'):
                row['detail_text'].value = self._format_detail(info)
                row['detail_text'].update()
            row['summary_text'].update()

            # 实时按当前模板刷新 new_name
            template = self.template_field.value or DEFAULT_TEMPLATE
            new_name = build_filename(template, info)
            row['new_name_text'].value = new_name
            row['new_name_text'].update()

            if info.get('title') or info.get('isbn'):
                ok_count += 1

            self._update_progress((i + 1) / total, f"{i + 1}/{total}")

        # 完成
        self.progress.value = 1
        self.progress.update()
        self.progress_text.value = "完成"
        self.progress_text.update()
        self.processing = False
        self.extract_btn.disabled = False
        self.rename_btn.disabled = (ok_count == 0)
        self.extract_btn.update()
        self.rename_btn.update()
        self.show_status(
            f"识别完成：成功 {ok_count} / 共 {total}",
            success=ok_count > 0,
        )
        self.update_stats()

    def _row_summary(self, info):
        """识别完成后的简要摘要文本"""
        if info.get('error'):
            return f"错误：{info['error'][:30]}"
        title = info.get('title') or ''
        author = info.get('author') or ''
        if title and author:
            return f"{title} — {author}"
        if title:
            return title
        if info.get('isbn'):
            return f"ISBN: {info['isbn']}"
        return "未提取到有效信息"

    def _update_progress(self, value, text):
        self.progress.value = max(0.0, min(1.0, value))
        self.progress_text.value = text
        try:
            self.progress.update()
            self.progress_text.update()
        except Exception:
            pass

    # ---------------------- 改名 ----------------------
    def on_rename_click(self, e):
        """启动改名流程"""
        if self.processing:
            return
        if not self.rows:
            self.show_status("请先选择 PDF 文件", success=False)
            return

        # 仅处理用户勾选且 new_name 不为空的项
        targets = []
        for row in self.rows:
            if not row['enabled']:
                continue
            new_base = (row['new_name_text'].value or '').strip()
            if not new_base:
                continue
            targets.append(row)

        if not targets:
            self.show_status("请勾选至少一个文件并填写新文件名", success=False)
            return

        # 预览目标：检查冲突
        msg_lines = [f"即将改名 {len(targets)} 个文件:", ""]
        for row in targets[:10]:
            base = (row['new_name_text'].value or '').strip()
            old = os.path.basename(row['path'])
            msg_lines.append(f"{old} → {base}.pdf")
        if len(targets) > 10:
            msg_lines.append(f"…还有 {len(targets) - 10} 个")
        msg_lines.append("")
        msg_lines.append("确定要执行改名吗？目标文件夹内若有同名文件将自动追加 (1) (2) … 后缀。")

        def do_confirm(ev):
            self.close_dialog(ev)
            self._start_rename(targets)

        self.page.dialog = ft.AlertDialog(
            title=ft.Text("确认改名", font_family=self.font_family),
            content=ft.Text("\n".join(msg_lines), font_family=self.font_family),
            actions=[
                ft.TextButton("取消", on_click=self.close_dialog),
                ft.TextButton("确定", on_click=do_confirm),
            ],
        )
        self.page.dialog.open = True
        self.page.update()

    def _start_rename(self, targets):
        """启动后台改名流程"""
        self.processing = True
        self.rename_btn.disabled = True
        self.extract_btn.disabled = True
        self.progress.value = 0
        self.progress.visible = True
        self.progress_text.value = "准备改名..."
        self.show_status("正在改名...")

        threading.Thread(
            target=self._do_rename,
            args=(targets,),
            daemon=True,
        ).start()

    def _do_rename(self, targets):
        """后台线程：依次改名"""
        ok_count = 0
        fail = []
        total = len(targets)
        for i, row in enumerate(targets):
            old_path = row['path']
            old_dir = os.path.dirname(old_path)
            new_base = sanitize_filename((row['new_name_text'].value or '').strip())
            if not new_base:
                fail.append(f"{os.path.basename(old_path)}: 新文件名为空")
                continue
            new_path = os.path.join(old_dir, new_base + '.pdf')
            new_path = unique_target_path(new_path)
            try:
                os.rename(old_path, new_path)
                row['path'] = new_path
                ok_count += 1
            except Exception as exc:
                fail.append(f"{os.path.basename(old_path)}: {exc}")
            self._update_progress((i + 1) / total, f"{i + 1}/{total}")

        self.progress.value = 1
        self.progress.update()
        self.progress_text.value = "完成"
        self.progress_text.update()
        self.processing = False
        self.extract_btn.disabled = False
        self.rename_btn.disabled = (ok_count == 0)
        self.extract_btn.update()
        self.rename_btn.update()

        # 更新 input_paths、summary
        self.input_paths = [r['path'] for r in self.rows]
        self.refresh_input_summary()

        if fail:
            self.show_status(f"完成：成功 {ok_count}，失败 {len(fail)}", success=False)
            self.show_info("部分失败", "\n".join(fail[:20]))
        else:
            self.show_status(f"成功改名 {ok_count} 个文件", success=True)
            self.show_info("完成", f"已成功改名 {ok_count} 个 PDF 文件。")

    # ---------------------- 工具方法 ----------------------
    def update_stats(self):
        self.stats_text.value = f"待处理: {len(self.rows)}"

    def show_status(self, message: str, success: bool = True):
        self.status_text.value = message
        self.page.snack_bar = ft.SnackBar(
            ft.Text(message, font_family=self.font_family),
            bgcolor=ft.Colors.GREEN if success else ft.Colors.RED,
            open=True,
        )
        self.page.update()

    def show_info(self, title: str, message: str):
        self.page.dialog = ft.AlertDialog(
            title=ft.Text(title, font_family=self.font_family),
            content=ft.Text(message, font_family=self.font_family),
            actions=[ft.TextButton("关闭", on_click=self.close_dialog)],
        )
        self.page.dialog.open = True
        self.page.update()

    def close_dialog(self, e=None):
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()


if __name__ == '__main__':
    app = PDFAutorenameApp()
    ft.app(target=app.build)
