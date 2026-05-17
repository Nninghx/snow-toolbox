# 宁宝工具集V3.0.0

[![Python 版本](https://img.shields.io/badge/python-3.13.13-blue.svg?logo=python&label=Python)](https://www.python.org/downloads/release/python-31313/)
[![许可证](https://img.shields.io/badge/license-Apache%202.0-red.svg?logo=apache&label=%E8%AE%B8%E5%8F%AF%E8%AF%81)](Core\LICENSE.txt)

## 项目简介

三垣工具集是由宁幻雪开发的Python自用工具集合，具有以下特点：

- 免注册，免登录，免授权，免费用，无广告
- 功能设计无需联网,数据完全本地处理，保护隐私安全
- 本程序不收集任何用户数据，也不上传任何用户数据
- 项目新增超多各种计算器，up我经过简单测试，没有发现计算公式错误问题，如果有发现那个计算器模块公式出现错误问题，请及时反馈给我，谢谢  
- 从V3.0.0版本开始提供打包版。

**注意：** 开发版在win11系统，VSC软件，python版本3.13.13开发的，其他系统未测试  

## 文件说明

- 开源协议：Apache-2.0 License

**注意**：
`Learn/`：学习笔记目录（可删除）
`Core/`：核心模块目录（必须保留，删除会导致部分模块出现问题）

## 工具目录概况

具体如下：

### PDF工具

工具名称:| PDF拆分|PDF合并|PDF转Word|PDF加水印|PDF转图片|图片转PDF| 

### 图片工具

工具名称:|九宫格分割|图片格式转换|ICO转换|图片合成| 


工具名称:|音频提取|

### 文件工具

工具名称:|目录树生成|

### 其他工具

工具名称:| 
长度单位换算|数字大小写转换|空文件夹清理| 英文大小写转换| 字符频率分析器| 

### 破站工具

工具名称:|封面与表情包图片批量压缩|带货链接分批处理工具|

### 计算器工具

工具名称:
多功能分数计算器模块(包含:分数化简,小数转分数,百分比转分数,分数四则运算)|
多功能代数计算器(包含:平均值计算，指数计算，比例计算，最小公倍数计算，最大公因数计算，对数计算，自然对数计算，反对数计算)|
三角函数计算器(包含:正弦计算器，反正弦计算器，反正切计算器，正切计算器，反余弦计算器，余弦计算器)|
多功能体积计算器(包含:立方体体积计算器，长方形水箱体积计算器，管体积计算器，胶囊体积计算器，正四棱锥体积计算器，圆台体积计算器，长方体体积计算器，圆锥体积计算器，半球体积计算器，圆环体积计算器，圆柱体积计算器，金字塔体积计算器，球体体积计算器，长方体体积计算器，直圆柱体积计算器)|
多功能数学和统计计算器(包含:平方根计算器，立方根计算器，二次方程求解，组合计算器，排列计算器，重复组合计算器，重复排列计算器，四舍五入计算器，取模计算器)|
多功能面积计算器(包含:长方形面积计算器，圆形面积计算器，正方形面积计算器，八边形面积计算器，等腰三角形面积计算器)|
多功能表面积计算器(包含:球体表面积计算器，立方体表面积计算器，三角棱柱表面积计算器，圆锥表面积计算器，圆锥侧面积计算器，金字塔表面积计算器，金字塔侧面积计算器)|
多功能周长计算器(包含:长方形周长计算器，圆形周长计算器，正方形周长计算器，八边形周长计算器，等腰三角形周长计算器)|

## 项目更新日志

V1.0.0-V2.3.0中的版本更新日志见[项目更新日志.md](项目更新日志.md)  

|📦 版本号（Version）| 📅 发布日期（Release Date）| 🔍 更新介绍|
|--------------------|----------------------------|------------|
|V3.0.0|2026-5-16|1.本次更新正式推出了 V3.0.0 系列的首个打包版本<br>2.鉴于打包版为首次发布，相较于开发版本可能存在未知的缺陷，建议继续使用V3.0.0 开发版，等待后续版本更新迭代。<br>3.后续版本会逐步使用统一的项目自带的字体，不在支持自定义字体。|
|V3.0.1|2026-5-17|1.紧急修复授权bug|
## 实现逻辑

![字体全局设置原理图](https://github.com/Nninghx/snow-toolbox/blob/master/Image/FontSettings.png)
主程序设置字体：主程序配置所需字体。
生成临时字体配置文件 ziti.json：将字体设置写入临时文件。
多个子程序（子程序1、子程序2、…、子程序N）读取 ziti.json：各子程序读取并应用相同的字体设置。
![图标实现原理图]()
读取lmage目录下的ico图标文件

宁宝工具集  
    ├── Core/                # 核心模块  
    │   ├── BangZhu.py       # 统一帮助系统  
    │   └── ziti.json        # 字体配置文件 
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
7.项目含有授权验证，但由于本项目为开源项目，所以自带授权文件，无需破解。
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

更新

```
git status
git add .
git commit -m "V3.0.1版本更新"
git push origin main
```
本项目中部分功能是基于开源项目二次开发的，在此列出开源项目的链接：
```
1.https://github.com/microsoft/OmniParser?tab=readme-ov-file
```