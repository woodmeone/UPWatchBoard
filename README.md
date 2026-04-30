# UPWatchBoard

> B站UP主数据分析看板 - 让数据驱动创作增长

一款专为B站UP主设计的智能数据分析工具。自动从B站创作中心导出数据，进行多维度健康度评分，识别数据模式，并生成可执行的优化建议。

## ✨ 核心功能

- 📊 **自动数据导出** - 一键从B站创作中心导出视频数据（播放量、互动率、涨粉量等）
- 🎯 **四维度健康度评分** - 流量获取 / 内容吸引力 / 内容质量 / 粉丝转化
- 🔍 **数据模式识别** - 自动识别8种常见数据问题模式
- 💡 **智能优化建议** - 基于数据生成可执行的改进方案
- 📈 **可视化看板** - 交互式数据图表，一目了然
- 🔄 **多账号支持** - 支持切换不同B站账号

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Playwright（用于浏览器自动化）

### 安装

```bash
# 克隆项目
git clone https://github.com/woodmeone/UPWatchBoard.git
cd UPWatchBoard

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

### 使用

```bash
# 启动看板服务
python main.py
```

首次运行会自动打开浏览器访问 `http://localhost:8765`

#### 首次使用流程

1. 点击 **「下载数据」** 按钮
2. 在弹出的浏览器窗口中用B站APP扫码登录
3. 登录成功后自动导出数据并分析
4. 刷新看板页面查看分析结果

#### 切换账号

1. 点击 **「切换账号」** 按钮，确认清除当前登录态
2. 再点击 **「下载数据」**，扫码登录新账号
3. 数据自动更新

## 📋 命令行参数

```bash
# 指定端口
python main.py --port 8080

# 启动前先下载数据
python main.py --download

# 不自动打开浏览器
python main.py --no-browser

# 仅运行分析（不启动看板）
python main.py --analyze-only
```

## 📊 数据维度说明

| 维度 | 权重 | 核心指标 |
|------|------|----------|
| 流量获取能力 | 25% | 播放量、游客占比 |
| 内容吸引力 | 25% | 封标点击率、3秒跳出率 |
| 内容质量 | 25% | 平均播放进度、互动率 |
| 粉丝转化能力 | 25% | 涨粉量、播转粉率 |

## 🔒 隐私安全

- 所有数据均在**本地处理**，不会上传至任何服务器
- B站登录Cookie仅保存在本地 `.bili_cookies.json` 文件中
- 已在 `.gitignore` 中排除敏感文件，不会意外提交

## 📁 项目结构

```
UPWatchBoard/
├── main.py                          # 主入口，HTTP看板服务
├── bilibili_export.py               # B站数据自动导出脚本
├── requirements.txt                 # Python依赖
├── bilibili-data-analyzer/          # 数据分析模块
│   ├── analyzer/
│   │   └── data_analyzer.py         # 核心分析引擎
│   ├── assets/
│   │   └── dashboard-template.html  # 可视化看板
│   ├── references/
│   │   └── metrics-guide.md         # 指标体系参考
│   └── scripts/
│       └── download_bilibili_data.py
├── data/                            # 运行时数据（已忽略）
└── skills/                          # AI Agent 编排框架
```

## 🛠️ 技术栈

- **后端**: Python 标准库 `http.server`
- **前端**: 原生 HTML/CSS/JavaScript + ECharts
- **自动化**: Playwright
- **分析引擎**: 纯Python实现，无外部依赖

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 开源协议

[MIT License](LICENSE)

---

<p align="center">Made with ❤️ for Bilibili Creators</p>
