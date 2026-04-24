#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DEFAULT_BASE = "http://127.0.0.1:8765"


def is_service_ready(base_url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{base_url}/api/config", timeout=1.5) as response:
            return response.status == 200
    except Exception:
        return False


def ensure_service(base_url: str) -> None:
    if is_service_ready(base_url):
        return
    command = [sys.executable, str(ROOT / "scripts" / "start_server.py")]
    subprocess.Popen(
        command,
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )
    for _ in range(20):
        time.sleep(0.5)
        if is_service_ready(base_url):
            return
    raise RuntimeError("本地服务启动失败，请手动运行 scripts/start_server.py")


def post_json(path: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"{DEFAULT_BASE}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Skill entry for macbook-wechat-zhuaqu")
    parser.add_argument("action", choices=["open", "generate", "send"])
    parser.add_argument("--date", default=None)
    parser.add_argument("--test-mode", action="store_true")
    args = parser.parse_args()

    ensure_service(DEFAULT_BASE)
    if args.action == "open":
        webbrowser.open(DEFAULT_BASE)
        print(f"已打开设置页：{DEFAULT_BASE}")
        return
    if args.action == "generate":
        payload = {"target_date": args.date}
        result = post_json("/api/reports/generate", payload)
        print(f"日报已生成：{result['markdown_path']}")
        print(result["summary_text"])
        return
    if args.action == "send":
        result = post_json("/api/feishu/send", {"test_mode": args.test_mode})
        print("飞书同步成功")
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
