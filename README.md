# 三垣工具集

## 项目简介
三垣工具集是由宁幻雪开发的Python自用工具集合，具有以下特点：
- 整体采用模块化设计，方便扩展维护
- 代码层面无需联网，无需登录，无需注册，无需授权
- 功能设计无需联网,数据完全本地处理，保护隐私
- 本程序不收集任何用户数据，也不上传任何用户数据
- 开源协议：Apache-2.0 License

**注意**：
- `Learn/`：学习笔记目录（可删除）
- `Tool module/`：核心模块目录（必须保留，删除会导致部分模块出现问题）

## 工具目录概况
经过近2个月的开发与测试，正式从Alpha版本调整为Beta版本,目前工具数量为24个未来还会继续增加，具体如下：
### PDF工具
工具名称:| PDF拆分|PDF合并|PDF转Word|PDF加水印|PDF转图片|图片转PDF| 

### 图片工具
工具名称:|九宫格分割|图片格式转换|ICO转换|图片合成| 

### 音频工具
工具名称:|音频提取|

### 文件工具
工具名称:|目录树生成|

### 其他工具
工具名称:| 
长度单位换算|数字大小写转换|空文件夹清理| 英文大小写转换| 字符频率分析器| 

### 破站工具
工具名称:|封面与表情包图片批量压缩| 

### 计算器工具
工具名称:|最小公倍数计算器|平方根计算器|重复组合计算器|立方根计算器|排列计算器|因数计算器|

## 项目更新日志
|📦 版本号（Version）| 📅 发布日期（Release Date）| 🧩 更新类型分类| 🔍 更新介绍|
|--------------------|----------------------------|----------------|------------|
|V1.0.0|2025-5-24|初始版本|无|
|V1.0.1|2025-5-25|问题修复（Bug Fixes）|修复音频工具刷新后无法使用的问题|
|V1.0.2|2025-5-26|文档更新（Documentation）|添加更新日志|
|V1.1.0|2025-5-27|新功能（New Features）<br>问题修复（Bug Fixes）|1.新增目录树生成器工具<br>2.修复V1.0.2版，调用工具名称错误的问题|
|V1.1.1|2025-5-28|新功能（New Features）<br>界面优化（UI/UX Improvements）|1.新增折叠/展开功能<br>2.工具列表添加了垂直滚动条<br>3.优化UI工具列表布局
|V1.2.0|2025-5-31|新功能（New Features）|新增PDF转图片工具|
|V1.3.0|2025-6-6|新功能（New Features）界面优化（UI/UX Improvements）|1.新增图片转PDF工具<br>2.新增数字小写转大写工具<br>4.新增长度单位换算工具<br>5.新增空文件夹清理工具<br>6.优化工具列表布局|
|V1.3.1|2025-6-7|性能优化（Performance Improvements）|1.对PDF工具列表中，帮助的代码片段进行优化<br>2.对PDF列表模块添加禁止生成 .pyc 文件|
|V1.3.2|2025-6-8|性能优化（Performance Improvements）|1.对图形工具列表中，部分模块的帮助的代码片段进行优化，添加禁止生成 .pyc 文件<br>2.对音频工具和文件工具列表中，帮助的代码片段进行优化，并添加禁止生成 .pyc 文件
|V1.4.0|2025-6-10|新功能（New Features）|1.新增字符频率分析器<br>2.新增英文大小写转换|
|V1.4.1|2025-6-11|问题修复（Bug Fixes）|修复已知BUG|
|V1.5.0|2025-6-24|新功能（New Features）<br>文档更新（Documentation）|1.新增B站专用封面与表情包图片批量压缩工具<br>2.对于帮助界面用词进行了修改，于完善
|V2.0.0|2025-7-14|新功能（New Features）<br>文档更新（Documentation）<br>重大变更（Breaking Changes）|1.新增最小公倍数计算器<br>2.新增平方根计算器<br>3.新增重复组合计算器<br>4.新增立方根计算器<br>5.新增排列计算器<br>6.新增因数计算器<br>7.对文档进行调整<br>备注:V2.0.0版本后功能模块的更新日志不在单独更新，并逐步删除，集合进本工具更新模块中，功能模块的Alpha调整为Beta版本


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
**版本**: V1.6.0  
**作者**: 宁幻雪  
**联系方式**: [Bilibili空间](https://space.bilibili.com/556216088)  
**开源协议**: Apache-2.0 License  
**免责声明**  
1.作者不对软件的功能、稳定性或兼容性提供任何形式的担保。
2.作者不对任何因使用本软件而导致的直接或间接损失负责。
3.作者保留对本软件进行修改、更新和维护的权利。


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