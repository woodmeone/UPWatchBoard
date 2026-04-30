"""
B站数据中心自动导出脚本 - Browser-Use AI驱动版
================================================
功能：使用 AI 自动理解页面结构，导出B站数据中心的核心数据概览和稿件对比
特点：无需手动定位元素，AI 自动识别和操作页面元素，适应页面结构变化

使用前准备：
  1. pip install browser-use langchain-openai
  2. 需要配置 OpenAI API Key（或兼容的 API）
  3. 也可以使用本地模型（通过 Ollama）

作者：SOLO 自动生成
日期：2026-04-29
"""

import asyncio
import os
from pathlib import Path

# ======================== 配置区 ========================

# LLM 配置（三选一）

# 选项1：OpenAI 官方
LLM_PROVIDER = "openai"
OPENAI_API_KEY = "sk-your-api-key-here"  # 替换为你的 API Key
OPENAI_BASE_URL = None  # 如果使用代理，填写代理地址，如 "https://api.example.com/v1"
MODEL_NAME = "gpt-4o"  # 推荐使用 gpt-4o 或 gpt-4o-mini

# 选项2：使用 Ollama 本地模型（取消下方注释）
# LLM_PROVIDER = "ollama"
# MODEL_NAME = "llama3"  # 或其他已安装的模型

# 选项3：使用其他兼容 OpenAI 的 API（如 DeepSeek、通义千问等）
# LLM_PROVIDER = "openai"
# OPENAI_API_KEY = "your-key"
# OPENAI_BASE_URL = "https://api.deepseek.com/v1"
# MODEL_NAME = "deepseek-chat"

# 下载保存目录
DOWNLOAD_DIR = str(Path.home() / "Downloads" / "bilibili_data")

# 是否显示浏览器界面
HEADLESS = False

# B站登录 Cookie（如果为空，需要先手动登录一次）
BILI_COOKIE = ""

# ========================================================


async def main():
    """主流程"""
    from browser_use import Agent
    from langchain_openai import ChatOpenAI

    # 确保下载目录存在
    Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)

    # 初始化 LLM
    if LLM_PROVIDER == "ollama":
        from langchain_ollama import ChatOllama
        llm = ChatOllama(model=MODEL_NAME)
    else:
        llm_kwargs = {
            "model": MODEL_NAME,
            "api_key": OPENAI_API_KEY,
        }
        if OPENAI_BASE_URL:
            llm_kwargs["base_url"] = OPENAI_BASE_URL
        llm = ChatOpenAI(**llm_kwargs)

    # 定义任务指令（自然语言，AI会自动理解并执行）
    task = """
    你需要帮我从B站数据中心导出数据。请按以下步骤操作：

    第一步：登录
    - 如果页面显示登录页面，请等待我扫码登录（最多等待120秒）
    - 如果已经登录，直接跳到下一步

    第二步：进入数据中心
    - 导航到 https://member.bilibili.com/platform/upload-data/frame
    - 等待页面完全加载

    第三步：导出核心数据概览
    - 找到日期范围选择器（通常显示"近7天"或"近30天"），点击它
    - 在弹出的下拉菜单中，选择"历史累计"选项
    - 找到并点击"导出数据"按钮
    - 等待10秒让文件下载完成

    第四步：导出稿件对比数据
    - 在页面上找到"稿件对比"相关的区域或标签
    - 找到该区域的"导出数据"按钮并点击
    - 等待10秒让文件下载完成

    注意事项：
    - 每次操作之间等待1-2秒，模拟人类操作节奏
    - 如果某个元素找不到，尝试多种方式定位（文本、图标、位置等）
    - 如果页面结构有变化，根据当前实际页面内容灵活调整
    """

    print("🚀 启动 Browser-Use AI 浏览器自动化...")
    print(f"📁 下载目录: {DOWNLOAD_DIR}")
    print(f"🤖 使用模型: {MODEL_NAME}")
    print()

    # 创建 Agent
    agent = Agent(
        task=task,
        llm=llm,
        headless=HEADLESS,
        # 可以设置浏览器额外参数
        browser_args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ],
    )

    # 运行
    print("🤖 AI Agent 开始执行任务...")
    print("（AI 会自动操作浏览器，你可以在屏幕上看到整个过程）\n")

    try:
        result = await agent.run()
        print("\n" + "=" * 50)
        print("📋 任务执行完成！")
        print(f"📁 文件保存位置: {DOWNLOAD_DIR}")
        print("=" * 50)
    except Exception as e:
        print(f"\n❌ 执行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
