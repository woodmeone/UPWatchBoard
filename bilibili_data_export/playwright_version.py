"""
B站数据中心自动导出脚本 - Playwright 稳定版 v2
=============================================
功能：自动登录B站 → 进入数据中心 → 导出"核心数据概览"和"稿件对比"数据
特点：使用文本内容定位元素，避免 Vue scoped hash 选择器失效问题

使用方法：
  方式一（一键启动）：
    1. 双击 run.bat (Windows) 或 run.sh (Mac/Linux)
    2. 首次运行会自动安装依赖
    3. 弹出浏览器后，用B站APP扫码登录
    4. 登录成功后脚本自动执行导出

  方式二（手动运行）：
    pip install playwright
    playwright install chromium
    python playwright_version.py

作者：SOLO 自动生成
日期：2026-04-29
"""

import asyncio
import time
import os
import sys
import json
from pathlib import Path
from playwright.async_api import async_playwright, Page, BrowserContext


# ======================== 配置区 ========================

# B站登录 Cookie（可选）
# 如果为空，则弹出二维码让你扫码登录
# 获取方式：Chrome 登录B站 → F12 → Application → Cookies → 复制所有cookie
BILI_COOKIE = ""

# Cookie 文件路径（扫码登录成功后自动保存，下次免扫码）
COOKIE_FILE = str(Path(__file__).parent / ".bili_cookies.json")

# 下载保存目录（设为空则使用浏览器默认下载目录）
DOWNLOAD_DIR = ""

# 导出后等待时间（秒），确保文件下载完成
EXPORT_WAIT_TIME = 15

# 是否显示浏览器界面（必须为 False 才能看到扫码界面）
HEADLESS = False

# 操作间隔（秒），模拟人类操作节奏
ACTION_DELAY = 1.5

# ========================================================


def ensure_download_dir():
    """确保下载目录存在"""
    if DOWNLOAD_DIR:
        Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
        return DOWNLOAD_DIR
    return None


async def human_delay(min_sec=0.5, max_sec=2.0):
    """模拟人类操作延迟"""
    import random
    delay = min_sec + (max_sec - min_sec) * random.random()
    await asyncio.sleep(delay)


async def save_cookies(context: BrowserContext):
    """保存 Cookie 到文件"""
    try:
        cookies = await context.cookies()
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        print(f"✅ Cookie 已保存到 {COOKIE_FILE}，下次运行免扫码")
    except Exception as e:
        print(f"⚠️  Cookie 保存失败: {e}")


async def load_cookies(context: BrowserContext) -> bool:
    """从文件加载 Cookie"""
    if not os.path.exists(COOKIE_FILE):
        return False
    try:
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        if cookies:
            await context.add_cookies(cookies)
            return True
    except Exception:
        pass
    return False


async def login_with_cookie_str(context: BrowserContext):
    """使用字符串格式的 Cookie 登录"""
    if not BILI_COOKIE:
        return False
    cookies = []
    for item in BILI_COOKIE.split(";"):
        item = item.strip()
        if "=" in item:
            name, value = item.split("=", 1)
            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": ".bilibili.com",
                "path": "/",
            })
    await context.add_cookies(cookies)
    return True


async def check_login_status(page: Page) -> bool:
    """检查是否已登录"""
    try:
        # 访问个人主页来判断登录状态
        resp = await page.goto("https://api.bilibili.com/x/web-interface/nav", wait_until="commit")
        if resp and resp.status == 200:
            data = await resp.json()
            if data.get("data", {}).get("isLogin"):
                return True
    except Exception:
        pass
    return False


async def login_with_qrcode(page: Page):
    """使用二维码扫码登录"""
    print("\n" + "=" * 50)
    print("📱 请使用手机B站APP扫描弹出的二维码登录")
    print("   扫码后在手机上点击【确认登录】")
    print("   脚本会自动检测登录状态并继续执行")
    print("=" * 50)

    await page.goto("https://passport.bilibili.com/login")
    await page.wait_for_load_state("networkidle")

    print("\n⏳ 等待扫码登录中...（最长等待120秒）")

    # 轮询检查登录状态
    max_wait = 120
    start_time = time.time()
    logged_in = False

    while time.time() - start_time < max_wait:
        await asyncio.sleep(3)
        try:
            # 检查是否跳转到了其他页面（登录成功的标志）
            current_url = page.url
            if "passport.bilibili.com" not in current_url:
                logged_in = True
                break
            # 也通过API检查
            if await check_login_status(page):
                logged_in = True
                break
        except Exception:
            continue

    if logged_in:
        print("✅ 登录成功！")
        return True
    else:
        print("❌ 登录超时（120秒），请重试")
        return False


async def export_core_data_overview(page: Page):
    """
    导出核心数据概览
    步骤：
    1. 点击日期选择下拉箭头
    2. 选择"历史累计"
    3. 点击"导出数据"
    """
    print("\n📊 开始导出【核心数据概览】...")

    # 等待页面加载完成
    await page.wait_for_load_state("networkidle")
    await human_delay(1, 2)

    # 步骤1：点击日期范围下拉箭头
    print("  1️⃣ 点击日期范围下拉箭头...")
    clicked = False

    # 方法1：通过 SVG use 图标定位
    try:
        arrow = page.locator("use[xlink\\:href='#icon-arrow-down']").first
        if await arrow.is_visible(timeout=3000):
            await arrow.click()
            clicked = True
            print("     ✅ 通过 SVG 图标点击成功")
    except Exception:
        pass

    # 方法2：通过日期文本定位
    if not clicked:
        try:
            date_text = page.locator("text=/近\\d+天|昨日|今日/").first
            if await date_text.is_visible(timeout=3000):
                await date_text.click()
                clicked = True
                print("     ✅ 通过日期文本点击成功")
        except Exception:
            pass

    # 方法3：查找所有下拉箭头图标
    if not clicked:
        try:
            arrows = page.locator(".icon-arrow-down, [class*='arrow'], svg use[href*='arrow']")
            count = await arrows.count()
            for i in range(min(count, 5)):
                try:
                    if await arrows.nth(i).is_visible():
                        await arrows.nth(i).click()
                        clicked = True
                        print(f"     ✅ 通过第 {i+1} 个箭头图标点击成功")
                        break
                except Exception:
                    continue
        except Exception:
            pass

    if not clicked:
        print("     ❌ 无法找到日期下拉箭头，跳过此步骤")
        # 继续尝试后续步骤

    await human_delay(1, 2)

    # 步骤2：选择"历史累计"
    print("  2️⃣ 选择【历史累计】...")
    selected = False

    # 方法1：精确文本匹配
    try:
        option = page.get_by_text("历史累计", exact=True)
        if await option.is_visible(timeout=3000):
            await option.click()
            selected = True
            print("     ✅ 精确文本匹配成功")
    except Exception:
        pass

    # 方法2：包含文本匹配
    if not selected:
        try:
            option = page.locator("text=历史累计").first
            if await option.is_visible(timeout=2000):
                await option.click()
                selected = True
                print("     ✅ 包含文本匹配成功")
        except Exception:
            pass

    # 方法3：通过 value 属性
    if not selected:
        try:
            option = page.locator("[value='3']").first
            if await option.is_visible(timeout=2000):
                await option.click()
                selected = True
                print("     ✅ 通过 value 属性匹配成功")
        except Exception:
            pass

    if not selected:
        print("     ❌ 无法选择历史累计")
        return False

    await human_delay(1, 2)

    # 步骤3：点击"导出数据"
    print("  3️⃣ 点击【导出数据】...")
    exported = False

    # 方法1：精确文本匹配
    try:
        btn = page.get_by_text("导出数据", exact=True).first
        if await btn.is_visible(timeout=3000):
            await btn.click()
            exported = True
            print("     ✅ 精确文本匹配点击成功")
    except Exception:
        pass

    # 方法2：宽松文本匹配
    if not exported:
        try:
            btn = page.locator("text=导出数据").first
            if await btn.is_visible(timeout=2000):
                await btn.click()
                exported = True
                print("     ✅ 宽松文本匹配点击成功")
        except Exception:
            pass

    # 方法3：查找所有包含"导出"的元素
    if not exported:
        try:
            btns = page.locator("text=/导出.*/")
            count = await btns.count()
            for i in range(min(count, 5)):
                try:
                    if await btns.nth(i).is_visible():
                        await btns.nth(i).click()
                        exported = True
                        print(f"     ✅ 通过第 {i+1} 个导出按钮点击成功")
                        break
                except Exception:
                    continue
        except Exception:
            pass

    if not exported:
        print("     ❌ 无法点击导出数据")
        return False

    # 等待下载完成
    print(f"  ⏳ 等待下载完成（{EXPORT_WAIT_TIME}秒）...")
    await asyncio.sleep(EXPORT_WAIT_TIME)
    print("  ✅ 核心数据概览导出完成！")
    return True


async def export_video_comparison(page: Page):
    """
    导出稿件对比数据
    """
    print("\n📈 开始导出【稿件对比】...")

    await human_delay(1, 2)
    exported = False

    # 方法1：查找所有"导出数据"按钮，点击第二个
    try:
        export_btns = page.locator("text=导出数据")
        count = await export_btns.count()
        print(f"  🔍 找到 {count} 个'导出数据'元素")

        if count >= 2:
            # 尝试点击可见的第二个
            for i in range(1, count):
                try:
                    if await export_btns.nth(i).is_visible(timeout=2000):
                        await export_btns.nth(i).click()
                        exported = True
                        print(f"  ✅ 已点击第 {i+1} 个导出数据按钮")
                        break
                except Exception:
                    continue
    except Exception as e:
        print(f"  ⚠️  方法1失败: {e}")

    # 方法2：先切换到稿件对比tab
    if not exported:
        print("  ⚠️  尝试切换到稿件对比tab...")
        try:
            # 查找"稿件对比"标签
            tab = page.get_by_text("稿件对比", exact=True)
            if await tab.is_visible(timeout=3000):
                await tab.click()
                await human_delay(2, 3)
                print("  ✅ 已切换到稿件对比")

                # 再次查找导出按钮
                export_btn = page.get_by_text("导出数据", exact=True).first
                if await export_btn.is_visible(timeout=3000):
                    await export_btn.click()
                    exported = True
                    print("  ✅ 已点击导出数据")
        except Exception as e:
            print(f"  ⚠️  方法2失败: {e}")

    # 方法3：通过 popover 定位
    if not exported:
        print("  ⚠️  尝试 popover 方案...")
        try:
            popover = page.locator(".popover-content").filter(has_text="导出数据")
            if await popover.is_visible(timeout=3000):
                await popover.click()
                exported = True
                print("  ✅ 已通过 popover 点击导出")
        except Exception as e:
            print(f"  ⚠️  方法3失败: {e}")

    # 方法4：悬停触发 popover
    if not exported:
        print("  ⚠️  尝试悬停触发方案...")
        try:
            # 查找可能触发 popover 的元素
            hover_targets = page.locator("[class*='right-button'], [class*='export'], [class*='download']")
            count = await hover_targets.count()
            for i in range(min(count, 10)):
                try:
                    await hover_targets.nth(i).hover()
                    await human_delay(0.5, 1)
                    # 检查是否出现了导出按钮
                    export_btn = page.get_by_text("导出数据", exact=True)
                    if await export_btn.is_visible(timeout=1000):
                        await export_btn.click()
                        exported = True
                        print("  ✅ 悬停触发后点击成功")
                        break
                except Exception:
                    continue
        except Exception as e:
            print(f"  ⚠️  方法4失败: {e}")

    if not exported:
        print("  ❌ 所有方案均失败，无法导出稿件对比")
        return False

    # 等待下载完成
    print(f"  ⏳ 等待下载完成（{EXPORT_WAIT_TIME}秒）...")
    await asyncio.sleep(EXPORT_WAIT_TIME)
    print("  ✅ 稿件对比导出完成！")
    return True


async def main():
    """主流程"""
    download_dir = ensure_download_dir()

    print("=" * 55)
    print("  B站数据中心自动导出工具 v2.0")
    print("  功能：导出核心数据概览 + 稿件对比数据")
    print("=" * 55)
    if download_dir:
        print(f"📁 下载目录: {download_dir}")
    print()

    async with async_playwright() as p:
        # 启动浏览器（非无头模式，方便扫码和观察）
        browser = await p.chromium.launch(
            headless=HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--start-maximized",
            ]
        )

        context_kwargs = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "accept_downloads": True,
        }
        if download_dir:
            context_kwargs["downloads_path"] = download_dir

        context = await browser.new_context(**context_kwargs)

        # 隐藏 webdriver 标识
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
            window.chrome = { runtime: {} };
        """)

        page = await context.new_page()

        try:
            # ===== 登录 =====
            logged_in = False

            # 优先级1：使用配置的 Cookie 字符串
            if BILI_COOKIE:
                await login_with_cookie_str(context)
                await page.goto("https://member.bilibili.com/platform/upload-data/frame")
                await page.wait_for_load_state("networkidle")
                if await check_login_status(page):
                    logged_in = True
                    print("✅ Cookie 字符串登录成功")

            # 优先级2：使用保存的 Cookie 文件
            if not logged_in and await load_cookies(context):
                await page.goto("https://member.bilibili.com/platform/upload-data/frame")
                await page.wait_for_load_state("networkidle")
                if await check_login_status(page):
                    logged_in = True
                    print("✅ Cookie 文件登录成功（免扫码）")

            # 优先级3：扫码登录
            if not logged_in:
                if await login_with_qrcode(page):
                    logged_in = True
                    # 保存 Cookie 供下次使用
                    await save_cookies(context)

            if not logged_in:
                print("\n❌ 登录失败，脚本退出")
                return

            await human_delay(2, 3)

            # ===== 进入数据中心 =====
            print("\n🚀 正在进入数据中心...")
            data_center_url = "https://member.bilibili.com/platform/upload-data/frame"
            current_url = page.url

            if "upload-data" not in current_url:
                await page.goto(data_center_url)
                await page.wait_for_load_state("networkidle")
                await human_delay(2, 3)

            print(f"✅ 已进入数据中心")

            # ===== 截图确认当前页面 =====
            screenshot_dir = download_dir or str(Path(__file__).parent)
            screenshot_path = os.path.join(screenshot_dir, "debug_home.png")
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"📸 页面截图: {screenshot_path}")

            # ===== 导出核心数据概览 =====
            result1 = await export_core_data_overview(page)
            await human_delay(2, 4)

            # ===== 导出稿件对比 =====
            result2 = await export_video_comparison(page)

            # ===== 汇总结果 =====
            print("\n" + "=" * 55)
            print("📋 导出结果汇总：")
            print(f"  核心数据概览: {'✅ 成功' if result1 else '❌ 失败'}")
            print(f"  稿件对比:     {'✅ 成功' if result2 else '❌ 失败'}")
            if download_dir:
                print(f"  文件保存位置: {download_dir}")
            print("=" * 55)

            # 最终截图
            final_screenshot = os.path.join(screenshot_dir, "debug_final.png")
            await page.screenshot(path=final_screenshot, full_page=True)
            print(f"📸 最终截图: {final_screenshot}")

        except Exception as e:
            print(f"\n❌ 运行出错: {e}")
            import traceback
            traceback.print_exc()

            # 错误截图
            try:
                error_dir = download_dir or str(Path(__file__).parent)
                error_screenshot = os.path.join(error_dir, "debug_error.png")
                await page.screenshot(path=error_screenshot, full_page=True)
                print(f"📸 错误截图已保存，请查看: {error_screenshot}")
            except Exception:
                pass

        finally:
            print("\n⏳ 10秒后关闭浏览器（可按 Ctrl+C 立即关闭）...")
            try:
                await asyncio.sleep(10)
            except KeyboardInterrupt:
                pass
            await browser.close()
            print("👋 浏览器已关闭")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，脚本退出")
        sys.exit(0)
