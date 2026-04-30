# B站数据中心自动导出工具

自动登录B站数据中心，导出"核心数据概览"和"稿件对比"数据。

## 文件说明

| 文件 | 说明 |
|------|------|
| `playwright_version.py` | 方案A：Playwright 稳定版，用文本内容定位元素 |
| `browser_use_version.py` | 方案B：Browser-Use AI版，用自然语言驱动 |
| `requirements.txt` | Python 依赖包 |
| `README.md` | 本文件 |

## 快速开始

### 方案A：Playwright 稳定版（推荐先试这个）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 安装浏览器
playwright install chromium

# 3. 运行脚本
python playwright_version.py
```

**首次运行**会弹出B站登录二维码，用手机B站APP扫码即可。登录成功后会自动保存Cookie，后续运行无需重复登录。

### 方案B：Browser-Use AI版（元素定位困难时用这个）

```bash
# 1. 安装依赖
pip install browser-use langchain-openai

# 2. 配置 API Key
# 编辑 browser_use_version.py，填入你的 API Key

# 3. 运行
python browser_use_version.py
```

**支持的 LLM**：
- OpenAI（gpt-4o 推荐）
- DeepSeek、通义千问等兼容 OpenAI 的 API
- Ollama 本地模型（免费，但效果可能稍差）

## 两个方案对比

| | Playwright 稳定版 | Browser-Use AI版 |
|---|---|---|
| **元素定位方式** | 文本内容 + 多重备用方案 | AI 自动识别，无需指定选择器 |
| **页面变化适应性** | 中等（文本变了需要更新脚本） | 高（AI 能理解语义） |
| **运行成本** | 免费 | 需要 LLM API 费用（约几毛钱/次） |
| **运行速度** | 快（约30秒完成） | 较慢（约1-3分钟） |
| **依赖复杂度** | 低 | 较高（需要 LLM 服务） |
| **适合场景** | 页面结构相对稳定 | 页面频繁改版 |

## 配置说明

### Cookie 登录（可选）

如果不想每次扫码，可以从浏览器获取Cookie：

1. 用 Chrome 打开 bilibili.com 并登录
2. 按 F12 → Application → Cookies
3. 复制所有 cookie，填入脚本的 `BILI_COOKIE` 变量

### 下载目录

默认下载到 `~/Downloads/bilibili_data/`，可在脚本顶部修改 `DOWNLOAD_DIR`。

## 常见问题

### Q: Playwright 版提示"找不到元素"怎么办？
- 先设置 `HEADLESS = False`，观察浏览器实际操作过程
- 检查 `debug_home.png` 截图，确认页面是否正确加载
- B站可能更新了页面文案，需要对应更新脚本中的文本匹配

### Q: Browser-Use 版运行很慢？
- 换用更快的模型（如 gpt-4o-mini）
- 使用本地 Ollama 模型（免费但需要好显卡）

### Q: 下载的文件在哪里？
- 默认在 `~/Downloads/bilibili_data/`
- 脚本运行时会打印具体路径

## 技术要点：为什么 Playwright 元素定位会失败？

B站数据中心是 Vue 单页应用，元素选择器如 `data-v-f301fe52` 是 Vue 编译时自动生成的 scoped hash，**每次构建都可能变化**。

本脚本的解决方案：
- ✅ 使用 `getByText("历史累计")` 按文本内容定位
- ✅ 使用 `get_by_role()` 按语义角色定位
- ✅ 每个关键步骤都有备用方案
- ❌ 不依赖 `data-v-xxx` 等 Vue scoped 选择器
