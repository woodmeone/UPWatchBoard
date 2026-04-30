#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站视频数据分析全流程启动入口

串联 数据下载 → 数据分析 → 可视化看板 的完整闭环。

用法:
  # 仅启动看板（使用已有的 data/ 目录数据）
  python main.py

  # 先下载数据，再启动看板
  python main.py --download

  # 指定端口，不自动打开浏览器
  python main.py --port 8080 --no-browser

  # 仅运行数据分析，输出到控制台
  python main.py --analyze-only
"""

import argparse
import http.server
import json
import os
import socketserver
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SKILL_DIR = PROJECT_ROOT / "bilibili-data-analyzer"
DATA_DIR = PROJECT_ROOT / "data"
ASSETS_DIR = SKILL_DIR / "assets"
COOKIE_FILE = PROJECT_ROOT / ".bili_cookies.json"

sys.path.insert(0, str(SKILL_DIR))


def get_analyzer():
    from analyzer.data_analyzer import DataAnalyzer
    return DataAnalyzer()


def get_ai_analyzer():
    from analyzer.ai_analyzer import load_config, save_config, call_ai_api, build_analysis_prompt, get_providers
    return load_config, save_config, call_ai_api, build_analysis_prompt, get_providers


VIDEO_CSV = DATA_DIR / "近期稿件对比.csv"
HISTORY_CSV = DATA_DIR / "历史累计数据趋势.csv"
ANALYSIS_JSON = DATA_DIR / "analysis_result.json"

download_status = {"running": False, "message": "", "ok": False, "started_at": ""}
switch_account_status = {"running": False, "message": "", "ok": False, "started_at": ""}


def run_download():
    global download_status
    download_script = SKILL_DIR / "scripts" / "download_bilibili_data.py"
    if not download_script.exists():
        download_status["message"] = f"下载脚本不存在: {download_script}"
        download_status["ok"] = False
        download_status["running"] = False
        return

    download_status["running"] = True
    download_status["message"] = "正在启动浏览器导出数据..."
    download_status["started_at"] = datetime.now().strftime("%H:%M:%S")

    try:
        result = subprocess.run(
            [sys.executable, str(download_script), "--output-dir", str(DATA_DIR)],
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            download_status["ok"] = True
            download_status["message"] = "数据下载完成，正在分析..."
            run_analysis_safe()
            download_status["message"] = "数据下载和分析已完成，刷新页面即可查看"
        else:
            download_status["ok"] = False
            download_status["message"] = "下载失败，查看上方终端日志"
    except Exception as e:
        download_status["ok"] = False
        download_status["message"] = f"下载异常: {e}"
    finally:
        download_status["running"] = False


def run_switch_account():
    global switch_account_status
    switch_account_status = {
        "running": True,
        "message": "正在清除旧账号登录状态...",
        "ok": False,
        "started_at": datetime.now().strftime("%H:%M:%S"),
    }

    try:
        deleted = False
        if COOKIE_FILE.exists():
            COOKIE_FILE.unlink()
            deleted = True
            print("[OK] 已删除旧账号Cookie文件")

        if deleted:
            switch_account_status["message"] = "旧账号Cookie已清除，请点击「下载数据」扫码登录新账号"
        else:
            switch_account_status["message"] = "未找到Cookie文件，可直接点击「下载数据」扫码登录"
        switch_account_status["ok"] = True
    except Exception as e:
        switch_account_status["message"] = f"清除Cookie失败: {e}"
        switch_account_status["ok"] = False
        print(f"[ERROR] 切换账号失败: {e}")
    finally:
        switch_account_status["running"] = False


def run_analysis_safe():
    try:
        return run_analysis()
    except Exception as e:
        print(f"[WARN] 自动分析失败: {e}")
        return None


def run_analysis():
    video_path = str(VIDEO_CSV) if VIDEO_CSV.exists() else ""
    history_path = str(HISTORY_CSV) if HISTORY_CSV.exists() else ""

    if not video_path:
        print("[WARN] 未找到视频数据CSV，跳过分析")
        return None

    analyzer = get_analyzer()
    result = analyzer.analyze(video_path, history_path)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(ANALYSIS_JSON, "w", encoding="utf-8") as f:
        json.dump(result.to_json(), f, ensure_ascii=False, indent=2)

    print(f"[OK] 分析结果已保存: {ANALYSIS_JSON}")
    print(result.to_markdown())
    return result


def launch_browser(port):
    url = f"http://localhost:{port}"
    try:
        webbrowser.open(url)
        print(f"[OK] 浏览器已打开: {url}")
    except Exception:
        print(f"[INFO] 请手动打开浏览器访问: {url}")


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        kwargs["directory"] = str(PROJECT_ROOT)
        super().__init__(*args, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self._serve_dashboard()
            return

        if path == "/api/data/videos":
            self._serve_csv(VIDEO_CSV)
            return

        if path == "/api/data/history":
            self._serve_csv(HISTORY_CSV)
            return

        if path == "/api/analysis":
            self._serve_json(ANALYSIS_JSON)
            return

        if path == "/api/status":
            self._serve_status()
            return

        if path == "/api/refresh":
            self._handle_refresh()
            return

        if path == "/api/download":
            self._handle_download_api()
            return

        if path == "/api/download-status":
            self._handle_download_status()
            return

        if path == "/api/switch-account":
            self._handle_switch_account()
            return

        if path == "/api/switch-account-status":
            self._handle_switch_account_status()
            return

        if path == "/api/ai-config":
            self._handle_ai_config_get()
            return

        if path == "/api/ai-providers":
            self._handle_ai_providers()
            return

        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/ai-config":
            self._handle_ai_config_post()
            return

        if path == "/api/ai-analyze":
            self._handle_ai_analyze()
            return

        self.send_error(404, "Not Found")

    def _serve_dashboard(self):
        dashboard_path = ASSETS_DIR / "dashboard-template.html"
        try:
            with open(dashboard_path, "r", encoding="utf-8") as f:
                content = f.read()
            self._send_response(200, content, "text/html; charset=utf-8")
        except FileNotFoundError:
            self.send_error(404, "Dashboard not found")

    def _serve_csv(self, filepath):
        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8-sig") as f:
                    content = f.read()
                self._send_response(200, content, "text/csv; charset=utf-8")
                return
            except Exception:
                pass
        self.send_error(404, "CSV not found")

    def _serve_json(self, filepath):
        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                self._send_response(200, content, "application/json; charset=utf-8")
                return
            except Exception:
                pass
        self.send_error(404, "Analysis not found")

    def _serve_status(self):
        status = {
            "videos_exist": VIDEO_CSV.exists(),
            "history_exist": HISTORY_CSV.exists(),
            "analysis_exist": ANALYSIS_JSON.exists(),
            "videos_count": 0,
            "history_count": 0,
            "download": {
                "running": download_status["running"],
                "message": download_status["message"],
                "ok": download_status["ok"],
            },
        }
        if VIDEO_CSV.exists():
            import csv
            with open(VIDEO_CSV, "r", encoding="utf-8-sig") as f:
                status["videos_count"] = sum(1 for _ in csv.reader(f)) - 1
        if HISTORY_CSV.exists():
            import csv
            with open(HISTORY_CSV, "r", encoding="utf-8-sig") as f:
                status["history_count"] = sum(1 for _ in csv.reader(f)) - 1
        if ANALYSIS_JSON.exists():
            with open(ANALYSIS_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                status["scores"] = data.get("scores", {})

        self._send_json(200, status)

    def _handle_refresh(self):
        try:
            result = run_analysis_safe()
            resp = {"ok": True, "message": "分析完成"}
            if result:
                resp["scores"] = result.to_json().get("scores", {})
        except Exception as e:
            resp = {"ok": False, "message": str(e)}
        self._send_json(200, resp)

    def _handle_download_api(self):
        global download_status
        if download_status["running"]:
            self._send_json(200, {
                "ok": False,
                "running": True,
                "message": "下载任务进行中: " + download_status["message"],
            })
            return

        download_status = {
            "running": True,
            "message": "正在启动下载线程...",
            "ok": False,
            "started_at": datetime.now().strftime("%H:%M:%S"),
        }
        t = threading.Thread(target=run_download, daemon=True)
        t.start()

        self._send_json(200, {
            "ok": True,
            "running": True,
            "message": "下载已启动，打开浏览器窗口扫码登录B站。可通过 /api/download-status 查询进度",
        })

    def _handle_download_status(self):
        self._send_json(200, {
            "running": download_status["running"],
            "message": download_status["message"],
            "ok": download_status["ok"],
            "started_at": download_status.get("started_at", ""),
        })

    def _handle_switch_account(self):
        try:
            global switch_account_status
            if switch_account_status["running"]:
                self._send_json(200, {
                    "ok": False,
                    "running": True,
                    "message": "切换任务进行中: " + switch_account_status["message"],
                })
                return

            run_switch_account()
            self._send_json(200, {
                "ok": switch_account_status["ok"],
                "running": switch_account_status["running"],
                "message": switch_account_status["message"],
            })
        except Exception as e:
            switch_account_status["running"] = False
            switch_account_status["ok"] = False
            switch_account_status["message"] = f"操作异常: {e}"
            self._send_json(200, {
                "ok": False,
                "running": False,
                "message": switch_account_status["message"],
            })

    def _handle_switch_account_status(self):
        self._send_json(200, {
            "running": switch_account_status["running"],
            "message": switch_account_status["message"],
            "ok": switch_account_status["ok"],
            "started_at": switch_account_status.get("started_at", ""),
        })

    def _handle_ai_config_get(self):
        try:
            load_config, _, _, _, _ = get_ai_analyzer()
            config = load_config()
            config["api_key"] = "***" if config.get("api_key") else ""
            self._send_json(200, {"ok": True, "config": config})
        except Exception as e:
            self._send_json(200, {"ok": False, "error": str(e)})

    def _handle_ai_config_post(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)

            _, save_config, _, _, _ = get_ai_analyzer()

            config = {
                "enabled": data.get("enabled", False),
                "provider": data.get("provider", "openai"),
                "base_url": data.get("base_url", ""),
                "api_key": data.get("api_key", ""),
                "model": data.get("model", ""),
                "max_tokens": data.get("max_tokens", 2000),
                "temperature": data.get("temperature", 0.7),
            }

            if save_config(config):
                self._send_json(200, {"ok": True, "message": "配置已保存"})
            else:
                self._send_json(200, {"ok": False, "error": "保存配置失败"})
        except Exception as e:
            self._send_json(200, {"ok": False, "error": str(e)})

    def _handle_ai_providers(self):
        try:
            _, _, _, _, get_providers = get_ai_analyzer()
            providers = get_providers()
            self._send_json(200, {"ok": True, "providers": providers})
        except Exception as e:
            self._send_json(200, {"ok": False, "error": str(e)})

    def _handle_ai_analyze(self):
        try:
            load_config, _, call_ai_api, build_analysis_prompt, _ = get_ai_analyzer()
            config = load_config()

            if not config.get("enabled"):
                self._send_json(200, {"ok": False, "error": "AI 分析未启用，请先在设置中配置并启用"})
                return

            if not ANALYSIS_JSON.exists():
                self._send_json(200, {"ok": False, "error": "请先运行数据分析（点击「重新分析」按钮）"})
                return

            with open(ANALYSIS_JSON, "r", encoding="utf-8") as f:
                analysis_data = json.load(f)

            prompt = build_analysis_prompt(analysis_data)
            result = call_ai_api(prompt, config)

            if result["ok"]:
                self._send_json(200, {
                    "ok": True,
                    "content": result["content"],
                    "model": result.get("model", ""),
                    "usage": result.get("usage", {})
                })
            else:
                self._send_json(200, {"ok": False, "error": result["error"]})
        except Exception as e:
            self._send_json(200, {"ok": False, "error": str(e)})

    def _send_response(self, code, content, content_type):
        data = content if isinstance(content, bytes) else content.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, code, data):
        content = json.dumps(data, ensure_ascii=False)
        self._send_response(code, content, "application/json; charset=utf-8")

    def log_message(self, format, *args):
        if "/api/" in str(args[0]):
            print(f"[API] {args[0]}")


class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    parser = argparse.ArgumentParser(description="B站视频数据分析全流程工具")
    parser.add_argument("--port", type=int, default=8765, help="HTTP 服务端口 (默认: 8765)")
    parser.add_argument("--download", action="store_true", help="启动前先下载数据（首次需扫码，后续自动复用cookie）")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--analyze-only", action="store_true", help="仅运行分析，不启动看板")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if args.analyze_only:
        run_analysis()
        return

    if args.download:
        print("=" * 50)
        print("正在从B站创作中心下载数据...")
        print("优先使用本地 Chrome 登录态（免扫码）")
        print("如失败会自动回退到扫码登录模式")
        print("=" * 50)
        run_download()
        if not download_status["ok"]:
            print(f"[WARN] 数据下载未完全成功: {download_status['message']}")
            print("将使用已有数据继续")
        else:
            print("[OK] 数据下载完成")

    print("=" * 50)
    print("正在分析数据...")
    print("=" * 50)
    run_analysis()

    print("=" * 50)
    print(f"看板服务已启动: http://localhost:{args.port}")
    print("按 Ctrl+C 停止服务")
    print("=" * 50)

    server = ThreadedServer(("", args.port), DashboardHandler)

    if not args.no_browser:
        threading.Timer(1.5, launch_browser, args=[args.port]).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[OK] 服务已停止")
        server.shutdown()


if __name__ == "__main__":
    main()
