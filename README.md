# 宁宝工具集 V4

[![Python](https://img.shields.io/badge/Python-3.13.13-blue?logo=python)](https://www.python.org/downloads/release/python-31313/)
[![License](https://img.shields.io/badge/License-Apache%202.0-red?logo=apache)](Core/LICENSE.txt)
[![Platform](https://img.shields.io/badge/Platform-Windows%2011-0078D4?logo=windows)]()

> 宁幻雪 个人自用 Python 工具集合 —— 本地运行 · 免联网 · 零数据收集 · 隐私安全

## 项目简介

宁宝工具集是一款桌面工具箱应用，采用**主程序 + 分类子工具**的模块化架构。主启动器统一管理 9 大工具分类、40+ 子工具，所有功能均在本地完成，不收集、不上传任何用户数据。

**核心特性：**

- 免注册、免登录、免授权、无广告
- 全部功能离线可用，数据完全本地处理
- 不收集、不上传任何用户数据
- 模块化设计，按需启动子工具，互不干扰
- 支持开发模式（Python 脚本）与打包模式（EXE）双运行方式
- 内置授权验证机制（开源项目自带授权文件，无需破解）
- 注意本项目能用，但不好用

## 工具一览

| 分类 | 工具 |进度 |
|------|------|------|
| **PDF 工具** | PDF 拆分 · PDF 合并 · PDF 转 Word · PDF 加水印 · PDF 转图片 · 图片转 PDF |已更新|
| **图片工具** | 九宫格分割 · 格式转换 · ICO 转换 · 图片合成 |
| **音频工具** | 视频音频提取 |
| **文件工具** | 目录树生成器 · 文件时间修改器 · 空文件夹清理 |
| **其他工具** | 数字小写转大写 · 长度单位换算 · 英文大小写转换 · 字符频率分析器 · 内存压缩管理 · VX 群聊消息发送 |
| **B 站工具** | 封面与表情包图片批量压缩 · 带货链接分批处理 · 商品链接 ID 提取 |
| **计算器工具** | 数学和统计 · 分数 · 代数 · 三角函数 · 二进制 · 体积 · 表面积 · 圆周率· 多边形周长计算器 · 多边形面积计算器 |
| **小游戏** | 24 点 · 数独 · 猜数字 · 2048 · 凹凸拼图 |
| **下载工具** | HuggingFace 模型下载 · ModelScope 模型下载 · 图片下载 |

## 项目结构

```
snow-toolbox/
├── San yuan Gong Ju_V4.py   # 主启动器（Flet GUI）
├── Core/                     # 核心资源（授权、字体许可等）
├── Image/                    # 图标与字体资源
│   ├── icon.ico              # 应用图标
│   ├── icon.png              # 应用图标（PNG）
│   └── AlibabaPuHuiTi-3-55-RegularL3.ttf  # 内置字体
├── PDF tool-V3/              # PDF 工具集
├── Picture tool-V3/          # 图片工具集
├── Audio tool-V3/            # 音频工具集
├── File tool-V3/             # 文件工具集
├── Other tool-V3/            # 其他工具集
├── Station B tool-V3/        # B 站专用工具集
├── Calculator tool-V3/       # 计算器工具集
├── Mini-games-V3/            # 小游戏集
├── Download tool-V3/         # 下载工具集
└── scrap-V0/                 # 报废淘汰工具集(不在维护更新，有更好的替换)
```

**运行架构：**

主启动器启动后，通过 Tab 页分类展示所有工具。点击工具按钮时，以独立子进程方式启动对应的 Python 脚本，实现工具间的隔离运行。

## 环境要求

- **Python** 3.10+（开发环境 3.13.13）
- **操作系统** Windows 11（开发测试平台）
- **FFmpeg** 音频工具必需，Windows 下安装：`winget install ffmpeg`

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动程序

```bash
python "San yuan Gong Ju_V4.py"
```

## 更新日志(概况)

| 版本 | 日期 | 内容 |详细|
|------|------|------|------|
| V4.2.3 | 2026-08-25 | 新增新版的多边形周长计算器和多边形面积计算器，新增报废淘汰分组，主程序重构优化|
| V4.1.2 | 2026-08-19 | 整体PDF tool-V3下的架构优化，本架构优化会同步更新其他工具上， 修复已知Bug，删除无用代码 |
| V4.0.2 | 2026-08-09 | 新增 VX 群聊消息发送 |
| V4.0.1 | 2026-07-25 | 新增凹凸拼图游戏 |
| V4.0.0 | 2026-07-23 | 开发版与打包版功能对齐；新增商品链接 ID 提取 |

> V1 ~ V3 的历史日志见 [项目更新日志.md](项目更新日志.md)

### 更新日志(详细)

V4.1.2
子程序架构优化
1.新增 Core/Public base class.py，共用的窗口图标、授权验证及字体加载等方法至 PDFToolBase 基类。
2. Bug 修复:PDF 合并功能中，添加文件后默认未选中页面导致合并结果为空的问题。

V4.2.3
 主程序重构优化：
 1.消除重复字体加载逻辑，统一使用 Core.FontManager 加载字体<br>
 2.新增全局搜索功能，支持按工具名/分类名实时跨分类过滤<br>
 3.各分类标签页新增语义化图标，提升视觉辨识度<br>
 4.底部状态栏新增工具可用数量实时统计<br>
 5.改进 UI 布局：卡片式设计、窗口居中、可点击清除按钮
 子程序新增功能
1.新版的多边形周长计算器和多边形面积计算器，新增报废淘汰分组

## 许可协议

**作者**：宁幻雪  
**协议**：Apache License 2.0  
**联系**：[Bilibili 主页](https://space.bilibili.com/556216088)

```
Copyright [2025-2026] [宁幻雪]

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

## 免责声明

1. 隐私与数据收集声明（不包含相关依赖）
本项目在运行、安装或使用过程中，不会向项目作者、维护者或任何第三方服务器发送、上传或收集您的任何个人信息、设备数据或使用记录。所有数据的存储与处理均仅在您的本地环境中进行，请用户自行做好本地数据的安全备份与防护。
2. 使用风险承担
用户在使用、修改、分发本项目时，需自行承担全部风险。因使用或无法使用本项目导致的任何直接、间接、附带、特殊、惩戒性或后果性损害（包括但不限于数据丢失、业务中断、利润损失或计算机系统故障），项目维护者及贡献者概不负责，即使已被告知发生此类损害的可能性。
3. 代码与内容准确性
尽管我们尽力确保代码质量与文档准确性，但本项目不保证：
代码完全无错误、无漏洞或无安全缺陷；
文档内容绝对准确、完整或及时更新；
项目功能满足用户的所有特定需求。
4. 第三方依赖与链接
本项目可能包含第三方库、插件或外部链接。这些资源由各自所有者维护，其可用性、安全性及合规性不在本项目的控制范围内。用户需自行评估并遵守第三方资源的相关条款。
5. 技术支持与更新
本项目为开源项目，不提供任何形式的官方技术支持、保修服务或强制性更新承诺。维护者有权根据社区反馈、个人意愿或资源情况，随时暂停、修改或终止项目的开发与维护。
6. 法律合规与责任限制
用户在使用本项目时，需遵守所在国家/地区的法律法规。若因用户违反法律法规或滥用本项目导致的任何法律责任，由用户自行承担
7. 条款修改与解释权
本免责声明可能随项目发展进行更新，修改后的条款将在项目仓库中公布，自公布之日起生效。用户继续使用本项目即视为接受更新后的条款。本条款的最终解释权归项目维护团队所有

```
git status
git add .
git commit -m "V4版本更新"
git push origin main
```