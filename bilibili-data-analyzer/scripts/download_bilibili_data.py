"""
B站数据中心自动导出脚本 - 实战验证版 v3.1
=============================================
修复：不脱离iframe，直接在iframe内部操作元素
"""

import argparse
import asyncio
import time
import os
import sys
import json
import shutil
from pathlib import Path
from playwright.async_api import async_playwright, Page, BrowserContext, Frame


# ======================== 配置区 ========================

COOKIE_FILE = str(Path(__file__).resolve().parent.parent.parent / ".bili_cookies.json")
DOWNLOAD_DIR = ""
EXPORT_WAIT_TIME = 15
OUTPUT_DIR = ""

# ========================================================


async def human_delay(min_sec=0.5, max_sec=2.0):
    import random
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
    try:
        resp = await page.goto("https://api.bilibili.com/x/web-interface/nav", wait_until="commit")
        if resp and resp.status == 200:
            data = await resp.json()
            return data.get("data", {}).get("isLogin", False)
    except Exception:
        pass
    return False


async def login_with_qrcode(page: Page):
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
                return True
            if await check_login(page):
                return True
        except Exception:
            continue
    return False


def find_frame(page: Page, url_keyword: str, timeout_sec: int = 15) -> Frame:
    """等待并找到包含指定关键词的 iframe，找到任何有实质内容的 iframe 也行"""
    start = time.time()
    while time.time() - start < timeout_sec:
        for f in page.frames:
            if url_keyword in f.url:
                return f
        # 如果没有匹配关键词的，找最大的 iframe（通常是数据中心）
        for f in page.frames:
            if f.url.startswith("https://") and "bilibili.com" in f.url and f.url != page.url:
                return f
        time.sleep(1)
    return None


async def enter_data_center(page: Page) -> Frame:
    """
    进入数据中心并返回 iframe 的 Frame 对象
    关键修复：不脱离iframe，而是获取iframe的Frame引用来操作内部元素
    """
    print("\n🚀 正在进入数据中心...")

    # 进入创作中心首页
    await page.goto("https://member.bilibili.com/platform/home", wait_until="networkidle")
    await human_delay(2, 3)

    # 点击左侧"数据中心"菜单
    try:
        result = await page.evaluate("""() => {
            const items = document.querySelectorAll('.bcc-nav-slider-item__wrap, .router-item, .router_wrap');
            for (const el of items) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0 && el.textContent.trim().includes('数据中心')) {
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

    await human_delay(5, 7)

    # 方法1：获取 iframe 的 Frame 对象（推荐）
    print("  🔍 查找数据中心 iframe...")
    frame = find_frame(page, "data-center-web", timeout_sec=20)

    if frame:
        print(f"  ✅ 找到 iframe: {frame.url[:60]}...")
        # 等待 iframe 内容加载
        try:
            await frame.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await human_delay(2, 3)
        return frame

    # 方法2：如果找不到iframe，多轮重试
    print("  ⚠️  未找到iframe，尝试备用方案...")
    backup_urls = [
        "https://member.bilibili.com/platform/data-up/video/",
        "https://member.bilibili.com/platform/upload-data/frame",
    ]
    for url in backup_urls:
        print(f"  尝试: {url}")
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(8)

        frame = find_frame(page, "data-center-web", timeout_sec=20)
        if frame:
            print(f"  ✅ 找到 iframe: {frame.url[:60]}...")
            try:
                await frame.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            await human_delay(2, 3)
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


async def export_core_data(frame: Frame):
    """
    在 iframe 的 Frame 中导出核心数据概览
    """
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
        # 打印调试信息
        try:
            debug = await frame.evaluate("""() => {
                return {
                    url: window.location.href,
                    title: document.title,
                    bodyText: document.body ? document.body.innerText.substring(0, 200) : 'no body',
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
                    return 'clicked';
                }
            }
            return 'not found';
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
            print(f"     ❌ 未找到历史累计选项")
            return False
    except Exception as e:
        print(f"     ❌ 失败: {e}")
        return False

    await human_delay(2, 3)

    # 步骤3：点击"导出数据"
    print("  3️⃣ 点击【导出数据】...")
    try:
        result = await frame.evaluate("""() => {
            const exports = document.querySelectorAll('.export');
            for (const el of exports) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0 && rect.y > 50 && rect.y < 300) {
                    el.click();
                    return 'clicked';
                }
            }
            // 备用：查找所有包含"导出数据"文本的可见元素
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
        }""")
        if 'clicked' in result:
            print(f"     ✅ {result}")
        else:
            print("     ❌ 未找到导出按钮")
            return False
    except Exception as e:
        print(f"     ❌ 失败: {e}")
        return False

    print(f"  ⏳ 等待下载完成（{EXPORT_WAIT_TIME}秒）...")
    await asyncio.sleep(EXPORT_WAIT_TIME)
    print("  ✅ 核心数据概览导出完成！")
    return True


async def export_video_comparison(frame: Frame):
    """
    在 iframe 的 Frame 中导出稿件对比数据
    """
    print("\n📈 开始导出【稿件对比】...")

    # 滚动到稿件对比区域
    print("  1️⃣ 滚动到稿件对比区域...")
    try:
        await frame.evaluate("window.scrollTo(0, 1300)")
        await human_delay(1, 2)
    except Exception:
        pass

    # 点击"导出数据"按钮
    print("  2️⃣ 点击稿件对比的【导出数据】...")
    try:
        result = await frame.evaluate("""() => {
            // 查找 .trigger-wrapper.left 中文本为"导出数据"的元素
            const triggers = document.querySelectorAll('.trigger-wrapper');
            for (const el of triggers) {
                if (el.textContent.trim() === '导出数据') {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        el.click();
                        return 'clicked';
                    }
                }
            }
            // 备用：查找所有可见的"导出数据"文本
            const all = document.querySelectorAll('*');
            for (const el of all) {
                if (el.textContent.trim() === '导出数据' && el.children.length < 2) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && rect.y > 200) {
                        el.click();
                        return 'clicked (fallback)';
                    }
                }
            }
            return 'not found';
        }""")
        if 'clicked' in result:
            print(f"     ✅ {result}")
        else:
            print("     ❌ 未找到导出按钮")
            return False
    except Exception as e:
        print(f"     ❌ 失败: {e}")
        return False

    print(f"  ⏳ 等待下载完成（{EXPORT_WAIT_TIME}秒）...")
    await asyncio.sleep(EXPORT_WAIT_TIME)
    print("  ✅ 稿件对比导出完成！")
    return True


async def main():
    global OUTPUT_DIR

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="", help="CSV 输出目录")
    parser.add_argument("--login-method", choices=["cookie","qr"], default="cookie")
    args, _ = parser.parse_known_args()
    if args.output_dir:
        OUTPUT_DIR = os.path.abspath(args.output_dir)
    login_method = args.login_method

    print("=" * 55)
    print("  B站数据中心自动导出工具 v3.1")
    if OUTPUT_DIR:
        print(f"  输出: {OUTPUT_DIR}")
    print("=" * 55)

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
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "accept_downloads": True,
        }
        if DOWNLOAD_DIR:
            Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
            context_kwargs["downloads_path"] = DOWNLOAD_DIR

        context = await browser.new_context(**context_kwargs)
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
            window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){} };
            Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
            // Prevent detection of headless mode
            Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 5});
            Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
            // Override permissions
            const iframeDescriptor = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow');
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
        """)

        page = await context.new_page()

        try:
            # ===== 登录 =====
            logged_in = False
            if await load_cookies(context):
                await page.goto("https://member.bilibili.com/platform/home")
                await page.wait_for_load_state("networkidle")
                if await check_login(page):
                    logged_in = True
                    print("✅ Cookie 登录成功（免扫码）")

            if not logged_in:
                if login_method == "qr":
                    if await login_with_qrcode(page):
                        logged_in = True
                        await save_cookies(context)
                else:
                    print("\n⚠️  Cookie 未登录，自动切换扫码...")
                    if await login_with_qrcode(page):
                        logged_in = True
                        await save_cookies(context)

            if not logged_in:
                print("\n❌ 登录失败")
                return

            # ===== 进入数据中心（获取iframe Frame） =====
            frame = await enter_data_center(page)
            if not frame:
                print("\n⚠️  无法找到iframe，尝试直接在主页面操作...")
                # 最后一搏：看主页面本身有没有数据
                try:
                    body_text = await page.locator("body").inner_text()
                    if "导出数据" in body_text or "历史累计" in body_text:
                        print("  主页面包含数据，直接在主页面操作")
                        frame = page.main_frame
                except Exception:
                    pass
                if not frame:
                    print("\n❌ 无法进入数据中心")
                    return

            # ===== 在 iframe 中操作 =====
            result1 = await export_core_data(frame)
            await human_delay(2, 4)
            result2 = await export_video_comparison(frame)

            # ===== 汇总 =====
            print("\n" + "=" * 55)
            print("📋 导出结果汇总：")
            print(f"  核心数据概览: {'✅ 成功' if result1 else '❌ 失败'}")
            print(f"  稿件对比:     {'✅ 成功' if result2 else '❌ 失败'}")
            print("=" * 55)

            # ===== 收集文件到 OUTPUT_DIR =====
            if OUTPUT_DIR:
                Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
                _collect_csv_files(OUTPUT_DIR)
                print("\n📋 输出目录文件：")
                for f in sorted(os.listdir(OUTPUT_DIR)):
                    if f.endswith(".csv"):
                        print(f"  📄 {f} ({os.path.getsize(os.path.join(OUTPUT_DIR, f))} 字节)")

        except Exception as e:
            print(f"\n❌ 运行出错: {e}")
            import traceback
            traceback.print_exc()
            try:
                await page.screenshot(path="debug_error.png", full_page=True)
                print("📸 错误截图: debug_error.png")
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


def _collect_csv_files(output_dir: str):
    """扫描所有可能的位置，收集最近3分钟内的CSV文件"""
    download_dirs = [
        os.path.expanduser("~/Downloads"),
        os.path.expanduser("~/下载"),
        os.path.join(os.environ.get("USERPROFILE", ""), "Downloads"),
        os.path.join(os.environ.get("USERPROFILE", ""), "下载"),
        os.path.join(os.environ.get("TEMP", ""), ""),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp"),
    ]
    now = time.time()
    # 按时间排序，第一个=核心概览，第二个=稿件对比
    found = []
    for d in download_dirs:
        if not os.path.isdir(d):
            continue
        try:
            for f in os.listdir(d):
                fpath = os.path.join(d, f)
                if not f.endswith(".csv"):
                    continue
                if now - os.path.getmtime(fpath) > 180:
                    continue
                found.append((os.path.getmtime(fpath), fpath, f))
        except Exception:
            continue
    found.sort()
    # 避免重复（已经在output_dir的文件跳过）
    for mtime, src, fname in found:
        dest_dir = os.path.abspath(output_dir)
        if os.path.abspath(os.path.dirname(src)) == dest_dir:
            continue
        if "历史累计" in fname or "trend" in fname.lower():
            dest = os.path.join(output_dir, "历史累计数据趋势.csv")
        elif "稿件" in fname or "video" in fname.lower() or "对比" in fname:
            dest = os.path.join(output_dir, "近期稿件对比.csv")
        else:
            # 无法识别，按顺序分配
            existing = [x for x in os.listdir(output_dir) if x.endswith(".csv")]
            if len(existing) == 0:
                dest = os.path.join(output_dir, "历史累计数据趋势.csv")
            elif len(existing) == 1:
                dest = os.path.join(output_dir, "近期稿件对比.csv")
            else:
                continue
        shutil.move(src, dest)
        print(f"  📁 {fname} → {os.path.basename(dest)}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 用户中断")
        sys.exit(0)
