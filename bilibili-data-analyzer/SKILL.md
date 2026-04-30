---
name: bilibili-data-analyzer
description: B站视频数据分析全流程工具。当用户需要分析B站视频数据、搭建数据看板、从B站创作中心自动下载数据、获取数据优化建议时使用此Skill。触发场景：(1) 用户上传了B站创作中心导出的CSV文件并要求分析 (2) 用户要求搭建B站数据看板 (3) 用户要求自动下载B站数据 (4) 用户询问B站数据指标的含义或如何优化视频数据。
---

# B站视频数据分析

## 🚀 快速启动（一键全流程）

```bash
# 安装依赖
pip install playwright
playwright install chromium

# 启动全流程服务（分析已有数据）
python main.py

# 先下载数据再启动看板
python main.py --download

# 仅运行分析
python main.py --analyze-only
```

启动后浏览器自动打开 `http://localhost:8765`，看板自动加载 `data/` 目录中的数据并展示智能分析建议。

## 工作流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  🔽 数据下载  │ ──▶ │  🧠 智能分析  │ ──▶ │  📊 可视化看板 │
│  Playwright  │     │  analyzer/  │     │  自动加载数据  │
│  模拟浏览器   │     │  健康度评分  │     │  AI建议自动渲染│
│  导出CSV     │     │  模式识别    │     │  60s自动刷新  │
└─────────────┘     └─────────────┘     └─────────────┘
      │                    │                    │
      ▼                    ▼                    ▼
   data/               data/              http://localhost:8765
   ├── 近期稿件对比.csv   analysis_result.json  浏览器看板
   └── 历史累计数据趋势.csv
```

## 模块说明

### main.py — 启动入口
串联下载 → 分析 → 看板的完整闭环。启动HTTP服务，提供API接口供前端看板调用。

| API端点 | 功能 |
|---------|------|
| `GET /` | 看板页面 |
| `GET /api/data/videos` | 近期稿件对比CSV |
| `GET /api/data/history` | 历史累计趋势CSV |
| `GET /api/analysis` | 分析结果JSON |
| `GET /api/status` | 数据状态 |
| `GET /api/refresh` | 触发重新分析 |
| `GET /api/download` | 触发数据下载 |

### analyzer/data_analyzer.py — 智能分析引擎
基于 `references/metrics-guide.md` 指标体系，自动生成分析报告。

四维度健康度评分：
- **流量获取能力**（25%）：播放量趋势 + 游客占比健康度
- **内容吸引力**（25%）：封标点击率 + 3秒跳出率
- **内容质量**（25%）：平均播放进度 + 互动率
- **粉丝转化能力**（25%）：涨粉量与播转粉率

自动识别8种数据模式（标题党、好内容缺曝光、互动高涨粉少等）。

### assets/dashboard-template.html — 可视化看板
- 9个ECharts图表（播放趋势、留存分析、互动六维、漏斗图、历史趋势等）
- 自动从API加载数据，60秒周期刷新
- AI分析建议自动渲染在底部面板
- 支持手动上传CSV作为备选方案
- 导出为PNG功能
- 深色主题 + B站粉色品牌色

### scripts/download_bilibili_data.py — 数据下载脚本 (v2.1)
使用Playwright模拟真实浏览器操作，从B站创作中心下载CSV数据。**基于文本内容定位元素**（非Vue scoped hash），页面结构变化时兼容性更好。

```bash
# 首次运行（扫码登录，自动保存cookie到项目根目录 .bili_cookies.json）
python scripts/download_bilibili_data.py --login-method qr --output-dir data/

# 后续运行（复用cookie，免扫码）
python scripts/download_bilibili_data.py --output-dir data/

# 通过主项目一键调用
python main.py --download
```

**技术特点**：
- ✅ `getByText("导出数据")` 按文本内容定位，不依赖 `data-v-xxx` 选择器
- ✅ 每个操作步骤 3-4 种备用方案
- ✅ Cookie 自动保存/加载
- ✅ 下载完成后自动搬运 CSV 到 `data/` 目录

### references/metrics-guide.md — 指标解读与优化建议框架
包含：
- 全部指标的分类解读（漏斗模型：曝光与点击 → 观看与留存 → 互动与转化）
- 数据健康度评估框架（4维度评分体系 + 权重分配）
- 优化建议生成结构（5大方向 + 具体执行方案）
- 常见数据模式识别（8种典型模式 + 对应建议）
