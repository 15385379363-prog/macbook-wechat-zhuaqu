from __future__ import annotations

import base64
import hashlib
import hmac
import importlib.util
import json
import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

from .models import AppConfig, ExtractStatus, GenerateReportRequest, ReportResult, ScanResult
from .wechat import build_focus_summary, parse_list_contacts_output


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ServiceRuntime:
    def __init__(self, config_path: Path, keys_path: Path, project_root: Optional[Path] = None):
        self.config_path = config_path
        self.keys_path = keys_path
        self.project_root = project_root or Path(__file__).resolve().parents[3]
        self.scripts_dir = self.project_root / "scripts"
        self.latest_report: Optional[ReportResult] = None
        self.extract_status_state = ExtractStatus(
            stage="idle",
            wechat_installed=Path("/Applications/WeChat.app").exists(),
            desktop_copy_ready=Path.home().joinpath("Desktop/WeChat.app").exists(),
            frida_ready=self._module_available("frida"),
            hints=["登录微信后打开聊天或通讯录页面，可触发数据库密钥加载。"],
        )

    @staticmethod
    def _module_available(name: str) -> bool:
        return importlib.util.find_spec(name) is not None

    def load_config(self) -> AppConfig:
        if not self.config_path.exists():
            return AppConfig()
        return AppConfig.model_validate_json(self.config_path.read_text(encoding="utf-8"))

    def save_config(self, config: AppConfig) -> AppConfig:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(config.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return config

    def scan_targets(self) -> ScanResult:
        script = self.scripts_dir / "list_contacts.py"
        env = os.environ.copy()
        env["MACBOOK_WECHAT_ZHUAQU_CONFIG_FILE"] = str(self.config_path)
        env["MACBOOK_WECHAT_ZHUAQU_KEYS_FILE"] = str(self.keys_path)
        result = subprocess.run(
            [sys.executable, str(script), "--config", str(self.config_path)],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        groups, contacts = parse_list_contacts_output(result.stdout)
        return ScanResult(groups=groups, contacts=contacts)

    def extract_keys_status(self) -> ExtractStatus:
        status = self.extract_status_state.model_copy(deep=True)
        status.wechat_installed = Path("/Applications/WeChat.app").exists()
        status.desktop_copy_ready = Path.home().joinpath("Desktop/WeChat.app").exists()
        status.frida_ready = self._module_available("frida")
        if self.keys_path.exists():
            try:
                keys = json.loads(self.keys_path.read_text(encoding="utf-8"))
                status.matched_databases = sorted(keys.keys())
                status.captured_key_count = max(status.captured_key_count, len(keys))
                if status.matched_databases and status.stage != "running":
                    status.stage = "matched"
            except json.JSONDecodeError:
                status.last_error = "密钥文件损坏，请重新初始化。"
        return status

    def run_extract_keys_task(self) -> None:
        if self.extract_status_state.stage == "running":
            return

        def _worker():
            self.extract_status_state = self.extract_status_state.model_copy(
                update={"stage": "running", "last_error": None}
            )
            script = self.scripts_dir / "extract_keys.py"
            env = os.environ.copy()
            env["MACBOOK_WECHAT_ZHUAQU_CONFIG_FILE"] = str(self.config_path)
            env["MACBOOK_WECHAT_ZHUAQU_KEYS_FILE"] = str(self.keys_path)
            try:
                result = subprocess.run(
                    [sys.executable, str(script)],
                    check=True,
                    capture_output=True,
                    text=True,
                    env=env,
                )
                keys = json.loads(self.keys_path.read_text(encoding="utf-8")) if self.keys_path.exists() else {}
                self.extract_status_state = self.extract_status_state.model_copy(
                    update={
                        "stage": "matched" if keys else "failed",
                        "captured_key_count": len(keys),
                        "matched_databases": sorted(keys.keys()),
                        "last_error": None if keys else "未生成数据库密钥。",
                    }
                )
            except subprocess.CalledProcessError as exc:
                self.extract_status_state = self.extract_status_state.model_copy(
                    update={
                        "stage": "failed",
                        "last_error": (exc.stderr or exc.stdout or str(exc)).strip()[-1000:],
                    }
                )

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def generate_report(self, request: GenerateReportRequest) -> ReportResult:
        script = self.scripts_dir / "wechat_daily.py"
        config = self.load_config()
        cmd = [sys.executable, str(script), "--config", str(self.config_path)]
        if request.target_date:
            cmd.insert(2, request.target_date)
        env = os.environ.copy()
        env["MACBOOK_WECHAT_ZHUAQU_CONFIG_FILE"] = str(self.config_path)
        env["MACBOOK_WECHAT_ZHUAQU_KEYS_FILE"] = str(self.keys_path)
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)

        report_path = None
        for line in result.stdout.splitlines():
            if line.startswith("日报已生成:"):
                report_path = line.split(":", 1)[1].strip()
                break
        if not report_path:
            report_date = request.target_date or "latest"
            report_path = str(Path(os.path.expanduser(config.report_dir)) / f"{report_date}.md")

        markdown = Path(os.path.expanduser(report_path)).read_text(encoding="utf-8")
        summary = build_focus_summary(markdown) if config.summary.ai_enabled else markdown[:200]
        bullet_count = sum(1 for line in markdown.splitlines() if line.startswith("- "))
        report = ReportResult(
            report_date=request.target_date or "latest",
            markdown_path=report_path,
            raw_markdown=markdown,
            summary_text=summary,
            generated_at=datetime.now().isoformat(timespec="seconds"),
            bullet_count=bullet_count,
        )
        self.latest_report = report
        return report

    def get_latest_report(self) -> Optional[ReportResult]:
        if self.latest_report is not None:
            return self.latest_report
        config = self.load_config()
        report_dir = Path(os.path.expanduser(config.report_dir))
        if not report_dir.exists():
            return None
        files = sorted(report_dir.glob("*.md"))
        if not files:
            return None
        latest = files[-1]
        markdown = latest.read_text(encoding="utf-8")
        self.latest_report = ReportResult(
            report_date=latest.stem,
            markdown_path=str(latest),
            raw_markdown=markdown,
            summary_text=build_focus_summary(markdown),
            generated_at=datetime.fromtimestamp(latest.stat().st_mtime).isoformat(timespec="seconds"),
            bullet_count=sum(1 for line in markdown.splitlines() if line.startswith("- ")),
        )
        return self.latest_report

    def send_feishu_message(self, markdown: str, test_mode: bool) -> dict:
        config = self.load_config()
        delivery = config.feishu_delivery
        if not delivery.enabled and not test_mode:
            raise ValueError("飞书同步未启用。")
        if not delivery.webhook_url:
            raise ValueError("请先在设置页填写飞书 webhook_url。")

        title = delivery.message_title.strip() or "微信日报"
        prefix = "[测试发送]\n" if test_mode else ""
        content = f"{prefix}{title}\n\n{markdown}"
        payload = {"msg_type": "text", "content": {"text": content}}
        if delivery.secret:
            timestamp = str(int(datetime.now().timestamp()))
            sign = base64.b64encode(
                hmac.new(
                    f"{timestamp}\n{delivery.secret}".encode("utf-8"),
                    digestmod=hashlib.sha256,
                ).digest()
            ).decode("utf-8")
            payload["timestamp"] = timestamp
            payload["sign"] = sign
        response = httpx.post(
            delivery.webhook_url,
            json=payload,
            timeout=20.0,
        )
        response.raise_for_status()
        return {"ok": True, "test_mode": test_mode, "status_code": response.status_code}
