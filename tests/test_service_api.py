from pathlib import Path

from fastapi.testclient import TestClient

from macbook_wechat_zhuaqu.service.app import create_app
from macbook_wechat_zhuaqu.service.models import (
    AppConfig,
    ExtractStatus,
    FeishuDeliveryConfig,
    GenerateReportRequest,
    ReportResult,
    ScanResult,
    SummarySettings,
    WechatTarget,
)
from macbook_wechat_zhuaqu.service.runtime import ServiceRuntime
from macbook_wechat_zhuaqu.service.wechat import match_captured_keys_to_databases


class FakeRuntime(ServiceRuntime):
    def __init__(self, config_path: Path):
        super().__init__(config_path=config_path, keys_path=config_path.with_name("keys.json"))
        self.generated = []
        self.sent = []

    def scan_targets(self) -> ScanResult:
        return ScanResult(
            groups=["【已毕业】航海家俱乐部🎢｜生财", "奇点Token"],
            contacts=["老婆", "文件传输助手"],
        )

    def extract_keys_status(self) -> ExtractStatus:
        return ExtractStatus(
            stage="matched",
            wechat_installed=True,
            desktop_copy_ready=True,
            frida_ready=True,
            captured_key_count=3,
            matched_databases=["message_0", "contact", "session"],
            hints=[],
        )

    def generate_report(self, request: GenerateReportRequest) -> ReportResult:
        self.generated.append(request)
        self.latest_report = ReportResult(
            report_date=request.target_date or "latest",
            markdown_path="/tmp/wechat-daily/latest.md",
            raw_markdown="# 微信日报\n\n- 重点讨论：生财群在聊 AI 提效\n- 待跟进：跟老婆确认周末安排",
            summary_text="今天最重要的是 AI 提效讨论，以及一个需要跟进的家庭安排。",
        )
        return self.latest_report

    def send_feishu_message(self, markdown: str, test_mode: bool) -> dict:
        self.sent.append({"markdown": markdown, "test_mode": test_mode})
        return {"ok": True, "test_mode": test_mode}


def test_match_captured_keys_to_database_salts():
    salts = {
        "message_0": "33aec3e3fb13a5caf101ae31d8e87671",
        "contact": "b438f523e4c9ce9c4d76f62dc2d28aef",
        "session": "429f7188867b5f1b4d234f1e57977ec8",
    }
    captured_keys = [
        {"rounds": 2, "salt": "0994f9d9c1299ff0cb3b940be2d24c4b", "dk": "x" * 64, "dkLen": 32},
        {
            "rounds": 256000,
            "salt": "b438f523e4c9ce9c4d76f62dc2d28aef",
            "dk": "0ce7be23a5c06ce9f13a41984bbf5743202e1b244b3cefbae621cf8b787dc175",
            "dkLen": 32,
        },
        {
            "rounds": 256000,
            "salt": "429f7188867b5f1b4d234f1e57977ec8",
            "dk": "b70c88c64d840dafd999794df0a937219e893e3e74142097baf505cedcf47842",
            "dkLen": 32,
        },
        {
            "rounds": 256000,
            "salt": "33aec3e3fb13a5caf101ae31d8e87671",
            "dk": "e99747bcd6df70591438fd68a86dd040b8e0003978b7c80b7d39eed49c102125",
            "dkLen": 32,
        },
    ]

    assert match_captured_keys_to_databases(salts, captured_keys) == {
        "message_0": "e99747bcd6df70591438fd68a86dd040b8e0003978b7c80b7d39eed49c102125",
        "contact": "0ce7be23a5c06ce9f13a41984bbf5743202e1b244b3cefbae621cf8b787dc175",
        "session": "b70c88c64d840dafd999794df0a937219e893e3e74142097baf505cedcf47842",
    }


def test_config_api_persists_targets_and_feishu_settings(tmp_path: Path):
    runtime = FakeRuntime(tmp_path / "wechat-daily.json")
    client = TestClient(create_app(runtime))

    payload = AppConfig(
        wxid="wxid_demo",
        db_base_path="/tmp/db_storage",
        monitor_groups=[WechatTarget(name="【已毕业】航海家俱乐部🎢｜生财", enabled=True)],
        monitor_contacts=[WechatTarget(name="老婆", enabled=True, source_id="Dahooluu")],
        report_dir="~/Documents/wechat-daily",
        time_mode="8am_to_8am",
        feishu_delivery=FeishuDeliveryConfig(enabled=True, webhook_url="https://example.com/hook"),
        summary=SummarySettings(template="focus", ai_enabled=True),
    ).model_dump(mode="json")

    response = client.put("/api/config", json=payload)
    assert response.status_code == 200
    assert response.json()["monitor_contacts"][0]["name"] == "老婆"

    persisted = client.get("/api/config")
    assert persisted.status_code == 200
    assert persisted.json()["feishu_delivery"]["webhook_url"] == "https://example.com/hook"


def test_generate_report_and_send_to_feishu(tmp_path: Path):
    runtime = FakeRuntime(tmp_path / "wechat-daily.json")
    client = TestClient(create_app(runtime))

    response = client.post("/api/reports/generate", json={"target_date": "2026-04-24"})
    assert response.status_code == 200
    assert "AI 提效" in response.json()["raw_markdown"]

    send_response = client.post("/api/feishu/send", json={"test_mode": False})
    assert send_response.status_code == 200
    assert send_response.json()["ok"] is True
    assert runtime.sent[-1]["test_mode"] is False
