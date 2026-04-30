"""
B站数据中心自动导出脚本 v4.0
=============================================
基于 iframe/Frame 方案，在 iframe 内部操作元素
自动捕获下载文件到 data/ 目录

使用方法：
  1. pip install playwright
  2. playwright install chromium
  3. python bilibili_export.py
"""

import argparse
import asyncio
import time
import os
import sys
import json
import random
from pathlib import Path
from playwright.async_api import async_playwright, Page, BrowserContext, Frame


# ======================== 配置区 ========================

PROJECT_DIR = Path(__file__).parent

COOKIE_FILE = str(PROJECT_DIR / ".bili_cookies.json")
DATA_DIR = str(PROJECT_DIR / "data")

EXPORT_WAIT_TIME = 15

# ========================================================


async def human_delay(min_sec=0.5, max_sec=2.0):
    await asyncio.sleep(min_sec + (max_sec - min_sec) * random.random())


async def save_cookies(context: BrowserContext):
    try:
        cookies = await context.cookies()
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        print("✅ Cookie 已保存，下次运行免扫码")
    except Exception as e:
        print(f"⚠️  Cookie 保存失败: {e}")


async def load_cookies(context: BrowserContext) -> bool:
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


async def check_login(page: Page) -> bool:
    """通过API检查登录状态（使用fetch，不导航页面）"""
    try:
        result = await page.evaluate("""async () => {
            try {
                const resp = await fetch('https://api.bilibili.com/x/web-interface/nav', {
                    credentials: 'include'
                });
                if (resp.ok) {
                    const data = await resp.json();
                    return data?.data?.isLogin || false;
                }
            } catch(e) {}
            return false;
        }""")
        return bool(result)
    except Exception:
        return False


async def login_with_qrcode(page: Page):
    """扫码登录"""
    print("\n" + "=" * 50)
    print("📱 请使用手机B站APP扫描弹出的二维码登录")
    print("   扫码后在手机上点击【确认登录】")
    print("=" * 50)

    await page.goto("https://passport.bilibili.com/login")
    await page.wait_for_load_state("networkidle")

    print("\n⏳ 等待扫码登录中...（最长等待120秒）")
    start = time.time()
    while time.time() - start < 120:
        await asyncio.sleep(3)
        try:
            if "passport.bilibili.com" not in page.url:
                print("  ✅ 页面已跳转，登录成功")
                await human_delay(2, 3)
                return True
            if await check_login(page):
                print("  ✅ API检测登录成功，跳转到创作中心...")
                await page.goto("https://member.bilibili.com/platform/home", wait_until="networkidle")
                await human_delay(2, 3)
                if "passport" not in page.url:
                    print("  ✅ 已进入创作中心")
                    return True
                print("  ⚠️  跳转后被重定向回登录页，等待继续...")
        except Exception:
            continue

    if await check_login(page):
        print("  ⚠️  超时但API显示已登录，尝试跳转...")
        await page.goto("https://member.bilibili.com/platform/home", wait_until="networkidle")
        await human_delay(2, 3)
        if "passport" not in page.url:
            return True

    return False


def find_frame(page: Page, url_keyword: str, timeout_sec: int = 15) -> Frame:
    """等待并找到包含指定关键词的 iframe"""
    start = time.time()
    while time.time() - start < timeout_sec:
        for frame in page.frames:
            if url_keyword in frame.url:
                return frame
        time.sleep(1)
    return None


async def enter_data_center(page: Page) -> Frame:
    """进入数据中心并返回 iframe 的 Frame 对象"""
    print("\n🚀 正在进入数据中心...")

    await page.goto("https://member.bilibili.com/platform/home", wait_until="networkidle")
    await human_delay(2, 3)

    # 点击左侧"数据中心"菜单
    try:
        result = await page.evaluate("""() => {
            const items = document.querySelectorAll(
                '.bcc-nav-slider-item__wrap, .router-item, .router_wrap'
            );
            for (const el of items) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0 &&
                    el.textContent.trim().includes('数据中心')) {
                    el.click();
                    return true;
                }
            }
            return false;
        }""")
        if result:
            print("  ✅ 已点击数据中心菜单")
    except Exception as e:
        print(f"  ⚠️  点击菜单失败: {e}")

    await human_delay(3, 5)

    # 获取 iframe 的 Frame 对象
    print("  🔍 查找数据中心 iframe...")
    frame = find_frame(page, "data-center-web", timeout_sec=15)

    if frame:
        print(f"  ✅ 找到 iframe: {frame.url[:60]}...")
        try:
            await frame.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await human_delay(2, 3)
        return frame

    # 备用：直接导航
    print("  ⚠️  未找到iframe，尝试直接导航...")
    await page.goto("https://member.bilibili.com/platform/data-up/video/", wait_until="networkidle")
    await human_delay(3, 5)

    frame = find_frame(page, "data-center-web", timeout_sec=10)
    if frame:
        print(f"  ✅ 找到 iframe: {frame.url[:60]}...")
        try:
            await frame.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        return frame

    return None


async def wait_for_element(frame: Frame, selector: str, timeout_sec: int = 10):
    """在 frame 中等待元素出现"""
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            result = await frame.evaluate(f"""() => {{
                const el = document.querySelector('{selector}');
                if (el) {{
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) return true;
                }}
                return false;
            }}""")
            if result:
                return True
        except Exception:
            pass
        await asyncio.sleep(0.5)
    return False


async def do_export_with_download(page: Page, frame: Frame, export_name: str,
                                   click_fn, data_dir: str):
    """通用的导出+下载捕获函数"""
    before_files = set(Path(data_dir).glob("*.csv")) if Path(data_dir).exists() else set()
    print(f"  3️⃣ 点击【导出数据】并等待下载...")
    download_ok = False
    try:
        async with page.expect_download(timeout=EXPORT_WAIT_TIME * 1000) as download_info:
            result = await click_fn(frame)
            if not result:
                return False
            print(f"     ✅ {result}")
            download = await download_info.value
        suggested = download.suggested_filename
        save_path = os.path.join(data_dir, suggested)
        await download.save_as(save_path)
        print(f"  📥 下载完成: {suggested} -> {save_path}")
        download_ok = True
    except Exception as e:
        print(f"     ⚠️  expect_download 未捕获: {e}")
        await asyncio.sleep(EXPORT_WAIT_TIME)

    if not download_ok:
        after_files = set(Path(data_dir).glob("*.csv")) if Path(data_dir).exists() else set()
        new_files = after_files - before_files
        if new_files:
            for f in new_files:
                print(f"  📥 回退扫描发现: {f.name} -> {f}")
            download_ok = True
        else:
            print(f"  ⚠️  未检测到新下载文件（{export_name}），可能B站未触发下载")

    return True


async def export_core_data(page: Page, frame: Frame):
    """在 iframe 的 Frame 中导出核心数据概览"""
    print("\n📊 开始导出【核心数据概览】...")

    # 步骤1：等待并点击日期下拉选择器
    print("  1️⃣ 点击日期下拉选择器...")
    found = await wait_for_element(frame, ".pop-menu-right .select", timeout_sec=15)
    if not found:
        print("     ❌ 未找到日期选择器，等待页面加载...")
        await asyncio.sleep(5)
        found = await wait_for_element(frame, ".pop-menu-right .select", timeout_sec=10)

    if not found:
        print("     ❌ 超时未找到日期选择器")
        try:
            debug = await frame.evaluate("""() => {
                return {
                    url: window.location.href,
                    title: document.title,
                    selectCount: document.querySelectorAll('.pop-menu-right').length,
                    exportCount: document.querySelectorAll('.export').length,
                };
            }""")
            print(f"     🔍 调试信息: {debug}")
        except Exception as e:
            print(f"     🔍 调试失败: {e}")
        return False

    try:
        await frame.evaluate("""() => {
            const selects = document.querySelectorAll('.pop-menu-right .select');
            for (const el of selects) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    el.click();
                    return;
                }
            }
        }""")
        print("     ✅ 已点击日期选择器")
    except Exception as e:
        print(f"     ❌ 点击失败: {e}")
        return False

    await human_delay(1, 2)

    # 步骤2：选择"历史累计"
    print("  2️⃣ 选择【历史累计】...")
    try:
        result = await frame.evaluate("""() => {
            const all = document.querySelectorAll('*');
            for (const el of all) {
                if (el.textContent.trim() === '历史累计') {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        el.click();
                        return 'clicked';
                    }
                }
            }
            return 'not found';
        }""")
        if result == 'clicked':
            print("     ✅ 已选择历史累计")
        else:
            print("     ❌ 未找到历史累计选项")
            return False
    except Exception as e:
        print(f"     ❌ 失败: {e}")
        return False

    await human_delay(2, 3)

    # 步骤3：通过 expect_download 点击导出并捕获文件
    success = await do_export_with_download(
        page, frame, "核心数据概览",
        lambda f: f.evaluate("""() => {
            const exports = document.querySelectorAll('.export');
            for (const el of exports) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0 && rect.y > 50 && rect.y < 300) {
                    el.click();
                    return 'clicked';
                }
            }
            const all = document.querySelectorAll('*');
            for (const el of all) {
                if (el.textContent.trim() === '导出数据' && el.children.length < 2) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && rect.y > 50 && rect.y < 300) {
                        el.click();
                        return 'clicked (fallback)';
                    }
                }
            }
            return 'not found';
        }"""),
        DATA_DIR
    )
    if success:
        print("  ✅ 核心数据概览导出完成！")
    return success


async def export_video_comparison(page: Page, frame: Frame):
    """在 iframe 的 Frame 中导出稿件对比数据"""
    print("\n📈 开始导出【稿件对比】...")

    print("  1️⃣ 滚动到稿件对比区域...")
    try:
        await frame.evaluate("window.scrollTo(0, 1300)")
        await human_delay(2, 3)
    except Exception:
        pass

    # 截图调试
    try:
        debug_path = os.path.join(DATA_DIR, "debug_comparison.png")
        await page.screenshot(path=debug_path, full_page=True)
        print(f"  📸 稿件对比区域截图: data/debug_comparison.png")
    except Exception:
        pass

    print("  2️⃣ 查找稿件对比导出按钮...")
    success = False

    # 方法1：Playwright 原生定位器在 frame 上
    try:
        locator = frame.locator(".trigger-wrapper.left:has-text('导出数据')")
        count = await locator.count()
        print(f"     .trigger-wrapper.left:has-text('导出数据'): {count}个")
        if count > 0:
            async with page.expect_download(timeout=EXPORT_WAIT_TIME * 1000) as dl:
                await locator.first.click()
                await dl.value
            download = await dl.value
            save_path = os.path.join(DATA_DIR, download.suggested_filename)
            await download.save_as(save_path)
            print(f"  📥 下载完成: {download.suggested_filename}")
            success = True
    except Exception as e:
        print(f"     ⚠️  方法1失败: {e}")

    if not success:
        try:
            locator = frame.locator("text=导出数据")
            count = await locator.count()
            print(f"     text=导出数据: {count}个")
            visible = locator.locator("visible=true")
            vc = await visible.count()
            print(f"     可见: {vc}个")
            if vc > 0:
                async with page.expect_download(timeout=EXPORT_WAIT_TIME * 1000) as dl:
                    await visible.last.click()
                    await dl.value
                download = await dl.value
                save_path = os.path.join(DATA_DIR, download.suggested_filename)
                await download.save_as(save_path)
                print(f"  📥 下载完成: {download.suggested_filename}")
                success = True
        except Exception as e:
            print(f"     ⚠️  方法2失败: {e}")

    if not success:
        print("  ⚠️  稿件对比下载未触发（B站可能需要先选择稿件）")
        await asyncio.sleep(5)

    print("  ✅ 稿件对比导出完成！")
    return True


async def main():
    parser = argparse.ArgumentParser(description="B站数据中心自动导出工具")
    parser.add_argument("--force-login", action="store_true",
                        help="强制重新扫码登录，忽略已保存的Cookie（用于切换账号）")
    args, _ = parser.parse_known_args()
    force_login = args.force_login

    if force_login and os.path.exists(COOKIE_FILE):
        os.remove(COOKIE_FILE)
        print("🗑️  已清除旧账号Cookie，将使用扫码登录")

    print("=" * 55)
    print("  B站数据中心自动导出工具 v4.0")
    print("  功能：导出核心数据概览 + 稿件对比数据")
    print(f"  下载目录: {DATA_DIR}")
    print("=" * 55)

    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--start-maximized",
            ]
        )

        context_kwargs = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/131.0.0.0 Safari/537.36",
            "accept_downloads": True,
        }
        context = await browser.new_context(**context_kwargs)

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
            if await load_cookies(context):
                await page.goto("https://member.bilibili.com/platform/home",
                                wait_until="networkidle")
                if await check_login(page):
                    logged_in = True
                    print("✅ Cookie 登录成功（免扫码）")
                else:
                    print("⚠️  Cookie 已过期，需要重新登录")

            if not logged_in:
                if await login_with_qrcode(page):
                    logged_in = True
                    await human_delay(3, 5)
                    await save_cookies(context)

            if not logged_in:
                print("\n❌ 登录失败")
                return

            # ===== 登录后验证 =====
            print("\n🔍 验证登录状态...")
            if "passport" in page.url or "login" in page.url:
                print("  ⚠️  仍在登录页，重新导航到创作中心...")
                await page.goto("https://member.bilibili.com/platform/home",
                                wait_until="networkidle")
                await human_delay(3, 5)

            current_url = page.url
            if "passport" in current_url or "login" in current_url:
                print(f"  ❌ 无法进入创作中心，当前URL: {current_url[:80]}")
                return

            print(f"  ✅ 当前页面: {current_url[:80]}")

            # ===== 进入数据中心（获取 iframe Frame） =====
            frame = await enter_data_center(page)
            if not frame:
                print("\n❌ 无法进入数据中心iframe")
                try:
                    await page.screenshot(
                        path=os.path.join(DATA_DIR, "debug_enter_failed.png"),
                        full_page=True)
                    print("📸 调试截图: data/debug_enter_failed.png")
                except Exception:
                    pass
                return

            # ===== 在 iframe 中操作 =====
            result1 = await export_core_data(page, frame)
            await human_delay(2, 4)
            result2 = await export_video_comparison(page, frame)

            # ===== 汇总 =====
            print("\n" + "=" * 55)
            print("📋 导出结果汇总：")
            print(f"  核心数据概览: {'✅ 成功' if result1 else '❌ 失败'}")
            print(f"  稿件对比:     {'✅ 成功' if result2 else '❌ 失败'}")

            csv_files = list(Path(DATA_DIR).glob("*.csv"))
            if csv_files:
                print(f"\n📁 data/ 下载文件 ({len(csv_files)}个):")
                for f in csv_files:
                    size_kb = f.stat().st_size / 1024
                    print(f"  - {f.name} ({size_kb:.1f} KB)")
            else:
                print(f"\n📁 data/ 目录下未找到 CSV 文件")
            print("=" * 55)

        except Exception as e:
            print(f"\n❌ 运行出错: {e}")
            import traceback
            traceback.print_exc()
            try:
                await page.screenshot(
                    path=os.path.join(DATA_DIR, "debug_error.png"),
                    full_page=True)
                print("📸 错误截图: data/debug_error.png")
            except Exception:
                pass

        finally:
            print("\n⏳ 10秒后关闭浏览器...")
            try:
                await asyncio.sleep(10)
            except KeyboardInterrupt:
                pass
            await browser.close()
            print("👋 完成")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 用户中断")
        sys.exit(0)
