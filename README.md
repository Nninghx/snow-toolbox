# 三垣工具集

---

## 项目简介
三垣工具集是由宁幻雪开发的Python实用工具集合，具有以下特点：
- 模块化设计，方便扩展维护
- 工具可独立运行
- 开源协议：Apache-2.0 License

**注意**：
- `Learn/`：学习笔记目录（可删除）
- `Tool module/`：核心模块目录（必须保留，删除会导致部分模块出现问题）

---

## 工具目录概况

### PDF工具
| 工具名称       | 功能描述               | 版本      | 文件路径                     |
|----------------|------------------------|-----------|------------------------------|
| PDF拆分        | 将PDF拆分为单页        | Alpha1.0.3 | `PDF tool/PDF Chai Fen`       |
| PDF合并        | 合并多个PDF文件        | Alpha1.0.3 | `PDF tool/PDF He Bing`        |
| PDF转Word      | 转换为可编辑Word文档   | Alpha1.0.2 | `PDF tool/PDF_to_Word`        |
| PDF加水印      | 添加文字水印           | Alpha1.0.1 | `PDF tool/PDF Jia Shui Yin`   |
| PDF转图片      | 将PDF转换为图片        | Alpha1.0.1 | `PDF tool/PDF Zhuan Tu Pian`  |
| 图片转PDF      | 将图片转换为PDF        | Alpha1.0.1 | `PDF tool/Tu Pian Zhuan PDF`  |

### 图片工具
| 工具名称       | 功能描述               | 版本      | 文件路径                             |
|----------------|------------------------|-----------|--------------------------------------|
| 九宫格分割     | 3×3网格分割图片        | Alpha1.0.0 | `Picture tool/Tu Pian Fen Ge Jiu Gong Ge` |
| 图片格式转换   | 支持多种格式互转       | Alpha1.0.0 | `Picture tool/Tu Pian Ge Shi Zhuan Huan`  |
| ICO转换        | 生成16-256px图标       | Alpha1.0.0 | `Picture tool/Tu Pian Zhuan ico`     |
| 图片合成       | 多图合成单图           | Alpha1.0.0 | `Picture tool/Tu_Pian_He_Chengy`      |

### 音频工具
| 工具名称       | 功能描述               | 版本      | 文件路径                     |
|----------------|------------------------|-----------|------------------------------|
| 音频提取       | 从视频提取音频         | Alpha1.0.2 | `Audio tools/Yin Pin Ti Qu`  |

### 文件工具
| 工具名称       | 功能描述               | 版本      | 文件路径                     |
|----------------|------------------------|-----------|------------------------------|
| 目录树生成     | 生成目录结构树         | Alpha1.0.0 | `File tool/Mu Lu Shu Sheng Cheng Qi` |

### 其他工具
| 工具名称       | 功能描述               | 版本      | 文件路径                     |
|----------------|------------------------|-----------|------------------------------|
| 长度单位换算   | 多种单位转换           | Alpha1.0.0 | `Other tool/Chang Du Dan Wei Huan Suan` |
| 数字大小写转换 | 数字转中文大写         | Alpha1.0.0 | `Other tool/Shu Zi Xiao Xie Zhuan Da Xie` |
| 空文件夹清理   | 清理空文件夹           | Alpha1.0.0 | `Other tool/Kong Wen Jian Jia Qing Li` |
| 英文大小写转换   | 英文首字母全量大小写互转        | Alpha1.0.0 | `Ying Wen Da Xiao Xie Zhuan Huan` |
| 字符频率分析器   | 支持字母汉字等字符出现频率分析    | Alpha1.0.0 | `Other tool/Kong Wen Jian Jia Qing Li` |




### 破站工具
| 工具名称       | 功能描述               | 版本      | 文件路径                     |
|----------------|------------------------|-----------|------------------------------|
|  封面与表情包图片批量压缩  | 透图图片批量压缩           | Alpha1.0.0 | `Feng Mian Yu Biao Qing Bao Tu Pian Pi Liang Ya Suo_Alpha1-0-0` |









## 环境安装

### 基础要求
- Python 3.6+

### 依赖安装
```bash
# 核心依赖
pip install tqdm PyPDF2 pillow pydub

# PDF工具专用
pip install pdf2docx pdfrw

# 图片工具专用
pip install opencv-python numpy

# 音频工具专用
pip install pydub
```

### FFmpeg安装（音频工具必需）
**Windows用户**：
1. 下载FFmpeg并解压
2. 将`bin/`目录添加到系统PATH



## 许可协议
**版本**: V1.5.0  
**作者**: 宁幻雪  
**联系方式**: [Bilibili空间](https://space.bilibili.com/556216088)  
**协议**: Apache-2.0 License

> 商业使用者建议联系作者告知使用情况（非强制要求），以便项目优化和版本迭代。

```text
Copyright [2025] [宁幻雪]

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```