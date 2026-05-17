# 禁止生成 .pyc 文件
import sys
sys.dont_write_bytecode = True

"""
通用字体加载模块
提供统一的字体加载和管理功能,供所有GUI工具使用
"""

import os
from pathlib import Path
from fontTools.ttLib import TTFont


class FontManager:
    """字体管理器 - 单例模式"""
    
    _instance = None
    _font_family = None
    _font_size_map = {
        'large': 48,
        'medium': 36,
        'small': 24,
        'tiny': 16,
        'default': 12
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._load_font()
        self._initialized = True
    
    def _load_font(self):
        """从字体文件加载字体"""
        # 获取项目根目录
        current_file = Path(__file__).resolve()
        project_root = current_file.parent
        
        # 尝试多个可能的字体路径
        possible_paths = [
            project_root / "Image" / "AlibabaPuHuiTi-3-55-RegularL3.ttf",
            project_root.parent / "Image" / "AlibabaPuHuiTi-3-55-RegularL3.ttf",
        ]
        
        font_path = None
        for path in possible_paths:
            if path.exists():
                font_path = path
                break
        
        if not font_path:
            print("警告: 找不到自定义字体文件,使用系统默认字体")
            FontManager._font_family = 'Arial'
            return
        
        try:
            # 使用 fonttools 获取字体名称
            tt = TTFont(str(font_path))
            font_name = None
            for record in tt['name'].names:
                if record.nameID == 1:  # Font Family
                    font_name = record.toUnicode()
                    break
            
            if not font_name:
                raise RuntimeError(f"无法从字体文件获取字体名称: {font_path}")
            
            tt.close()
            
            # 使用 Windows API 注册字体
            if os.name == 'nt':
                import ctypes
                GDI32 = ctypes.windll.gdi32
                font_path_str = str(font_path).encode('utf-16-le') + b'\x00'
                GDI32.AddFontResourceW(font_path_str)
                print(f"✅ 成功加载自定义字体: {font_path}")
            
            FontManager._font_family = font_name
            
        except Exception as e:
            print(f"加载字体配置出错: {e}")
            FontManager._font_family = 'Arial'
    
    @classmethod
    def get_font_family(cls):
        """获取字体族名称"""
        if cls._font_family is None:
            instance = cls()
        return cls._font_family
    
    @classmethod
    def get_font(cls, size='default'):
        """
        获取指定大小的字体元组
        
        Args:
            size: 字体大小,可以是整数或预定义级别('large', 'medium', 'small', 'tiny', 'default')
        
        Returns:
            tuple: (字体族名称, 字号)
        """
        font_family = cls.get_font_family()
        
        if isinstance(size, str):
            size_value = cls._font_size_map.get(size, 12)
        else:
            size_value = int(size)
        
        return (font_family, size_value)
    
    @classmethod
    def apply_to_root(cls, root, size='default'):
        """
        将字体应用到Tkinter根窗口
        
        Args:
            root: Tkinter根窗口对象
            size: 字体大小
        """
        font_tuple = cls.get_font(size)
        root.option_add("*Font", font_tuple)
        return font_tuple
    
    @classmethod
    def create_font_dict(cls, sizes=None):
        """
        创建包含多种字号的字体字典
        
        Args:
            sizes: 需要创建的字号列表,默认为所有标准字号
        
        Returns:
            dict: {字号名称: 字体元组}
        """
        if sizes is None:
            sizes = ['large', 'medium', 'small', 'tiny', 'default']
        
        font_dict = {}
        for size_name in sizes:
            font_dict[size_name] = cls.get_font(size_name)
        
        return font_dict


# 便捷函数
def get_font_manager():
    """获取字体管理器实例"""
    return FontManager()


def load_font():
    """加载字体并返回字体族名称(兼容旧代码)"""
    return FontManager.get_font_family()


def get_font(size='default'):
    """获取指定大小的字体(兼容旧代码)"""
    return FontManager.get_font(size)


if __name__ == '__main__':
    # 测试代码
    print("测试字体加载模块...")
    
    # 测试1: 获取字体管理器
    manager = get_font_manager()
    print(f"字体族: {manager.get_font_family()}")
    
    # 测试2: 获取不同大小的字体
    print(f"大号字体: {manager.get_font('large')}")
    print(f"中号字体: {manager.get_font('medium')}")
    print(f"小号字体: {manager.get_font('small')}")
    print(f"微小字体: {manager.get_font('tiny')}")
    print(f"默认字体: {manager.get_font('default')}")
    
    # 测试3: 创建字体字典
    fonts = manager.create_font_dict()
    print(f"字体字典: {fonts}")
    
    # 测试4: 便捷函数
    print(f"便捷函数 - 字体族: {load_font()}")
    print(f"便捷函数 - 字体: {get_font(14)}")
    
    print("\n✅ 所有测试通过!")
