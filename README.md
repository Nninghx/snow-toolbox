# 宁宝工具集V3.0.0系列版本

[![Python 版本](https://img.shields.io/badge/python-3.13.13-blue.svg?logo=python&label=Python)](https://www.python.org/downloads/release/python-31313/)
[![许可证](https://img.shields.io/badge/license-Apache%202.0-red.svg?logo=apache&label=%E8%AE%B8%E5%8F%AF%E8%AF%81)](Core\LICENSE.txt)

## 项目简介

宁宝工具集是由宁幻雪开发的Python自用工具集合，具有以下特点：

- 免注册，免登录，免授权，免费用，无广告
- 功能设计无需联网,数据完全本地处理，保护隐私安全
- 本程序不收集任何用户数据，也不上传任何用户数据
- 项目新增超多各种计算器，up我经过简单测试，没有发现计算公式错误问题，如果有发现那个计算器模块公式出现错误问题，请及时反馈给我，谢谢  
- 从V3.0.0版本开始提供打包版。
- 本项目的定位自用版，所以优化上不会太好，但是能用。
- 打包版本一定要用最新的打包版，否则会出现问题


**注意：** 开发版在win11系统，VSC软件，python版本3.13.13开发的，其他系统未测试  

## 工具目录概况
PDF工具：PDF拆分、PDF合并、PDF转Word、PDF加水印、PDF转图片、图片转PDF
图片工具：九宫格分割、格式转换、ICO转换、图片合成
音频工具：音频提取
文件工具：目录树生成器、文件时间修改器、空文件夹清理
其他工具：数字小写转大写、长度单位换算、英文大小写转换、字符频率分析器、内存压缩管理工具
B站工具：封面与表情包图片批量压缩、带货链接分批处理工具
计算器工具：数学和统计、分数、代数、三角函数、二进制、体积、面积、表面积、周长、圆周率
小游戏：24点、数独、猜数字、2048
下载工具：HuggingFace模型下载、ModelScope模型下载、图片下载

## 项目更新日志

V1.0.0-V2.3.0中的版本更新日志见[项目更新日志.md](项目更新日志.md)  

|📦 版本号（Version）| 📅 发布日期（Release Date）| 🔍 更新介绍|
|--------------------|----------------------------|------------|
|V3.0.0|2026-5-16|1.本次更新正式推出了 V1.0.0 系列的首个打包版本<br>2.鉴于打包版为首次发布，相较于开发版本可能存在未知的缺陷，建议继续使用V3.0.0 系列开发版，等待后续版本更新迭代。<br>3.后续版本会逐步使用统一的项目自带的字体，不在支持自定义字体。|
|V3.1.1|2026-5-17|1.紧急修复开发版本授权bug|
|V3.2.1|2026-5-18|1.新增文件夹或文件的时间修改器功能。<br>2.新增ModelScope 模型下载器|
|V3.3.1|2026-5-22|1.小游戏系列模块完成优化|
|V3.3.2|2026-5-23|1.调整部分文件命名|
|V3.4.2|2026-5-25|1.计算器系列模块完成优化|
|V3.5.2|2026-5-26|1.图片工具模块完成优化2，新增模型下载工具(备注:Hugging Face 模型下载工具，存在网络原因导致下载失败，需要网络加速)|
|V3.6.3|2026-5-30|1.模型下载改成下载工具2.新增图片下载工具|
|V3.7.3|2026-5-27|1.其他工具系列模块完成优化|
|V3.8.4|2026-6-1|1.新增PDF系列工具模块完成优化2.调整依赖包文文件|

## 实现逻辑
1.项目图标
项目图标统一读取lmage目录下的ico图标文件

宁宝工具集  
    ├── 分类工具目录/         # N个分类工具目录  
    └── San Yuan Gong Ju.py  # 主控程序  
项目中有一个报废的文件夹，存在严重bug，请勿使用。

## 环境安装

由于本程序的项目环境多次增删，以下依赖安装可能出现遗漏情况，如有发现请反馈补充。

### 基础要求

- Python 3.10+

### 依赖安装

一次性安装所有依赖

```bash
pip install -r requirements.txt
```

### FFmpeg安装（音频工具必需）

**Windows用户**：
执行以下命令安装FFmpeg：

```bash
winget install ffmpeg
```

## 许可协议

**版本**: V3.0.0
**作者**: 宁幻雪  
**联系方式**: [Bilibili空间](https://space.bilibili.com/556216088)  
**宣传**: [Bilibili空间](https://space.bilibili.com/3546580200196227)  
**开源协议**: Apache-2.0 License  
**免责声明**  
1.作者不对软件的功能、稳定性或兼容性提供任何形式的担保。<br>
2.作者不对任何因使用本软件而导致的直接或间接损失负责。<br>
3.用户使用本软件时应自行承担风险，并确保遵守相关法律法规。<br>
4.本软件仅供学习和研究使用，非法用途。<br>
5.在使用本软件时，请务必遵守当地法律法规。<br>
6.本项目已自用为主，开发版会比打包版本更加稳定。<br>
7.项目含有授权验证，但由于本项目为开源项目，所以自带授权文件，无需破解。<br>
8.项目中存在一些子功能，没有在主程序中添加，是还没有测试过的，请勿使用。<br>

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

## 已废弃实现逻辑

![字体全局设置原理图](https://github.com/Nninghx/snow-toolbox/blob/master/Image/FontSettings.png)
主程序设置字体：主程序配置所需字体。
生成临时字体配置文件 ziti.json：将字体设置写入临时文件。
多个子程序（子程序1、子程序2、…、子程序N）读取 ziti.json：各子程序读取并应用相同的字体设置。
(已被废弃)

```
git status
git add .
git commit -m "V3.8.4版本更新"
git push origin main
```

本项目中部分功能是基于开源项目二次开发的，在此列出开源项目的链接：
```
https://github.com/microsoft/OmniParser?tab=readme-ov-file
```