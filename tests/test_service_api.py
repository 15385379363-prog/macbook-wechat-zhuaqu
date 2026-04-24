from pathlib import Path
from unittest.mock import Mock

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
            generated_at="2026-04-24T08:00:00",
            bullet_count=2,
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
        feishu_delivery=FeishuDeliveryConfig(
            enabled=True,
            mode="lark_cli",
            cli_user_id="ou_demo_user",
            cli_profile="personal",
            cli_identity="user",
            message_title="微信重点日报",
        ),
        summary=SummarySettings(template="focus", ai_enabled=True),
    ).model_dump(mode="json")

    response = client.put("/api/config", json=payload)
    assert response.status_code == 200
    assert response.json()["monitor_contacts"][0]["name"] == "老婆"

    persisted = client.get("/api/config")
    assert persisted.status_code == 200
    assert persisted.json()["feishu_delivery"]["mode"] == "lark_cli"
    assert persisted.json()["feishu_delivery"]["cli_user_id"] == "ou_demo_user"
    assert persisted.json()["feishu_delivery"]["message_title"] == "微信重点日报"


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


def test_latest_report_endpoint_returns_preview_metadata(tmp_path: Path):
    runtime = FakeRuntime(tmp_path / "wechat-daily.json")
    client = TestClient(create_app(runtime))

    client.post("/api/reports/generate", json={"target_date": "2026-04-24"})
    response = client.get("/api/reports/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["report_date"] == "2026-04-24"
    assert body["summary_text"].startswith("今天最重要的是")
    assert body["raw_markdown"].startswith("# 微信日报")


def test_lark_cli_send_uses_direct_message(monkeypatch, tmp_path: Path):
    runtime = ServiceRuntime(tmp_path / "config.json", tmp_path / "keys.json", Path("/tmp/project"))
    runtime.save_config(
        AppConfig(
            feishu_delivery=FeishuDeliveryConfig(
                enabled=True,
                mode="lark_cli",
                cli_user_id="ou_demo_user",
                cli_profile="personal",
                cli_identity="user",
                message_title="每日微信重点",
            )
        )
    )

    captured = {}

    mocked_result = Mock()
    mocked_result.stdout = '{"code":0,"msg":"success"}'
    mocked_result.returncode = 0

    def fake_run(cmd, check, capture_output, text):
        captured["cmd"] = cmd
        captured["check"] = check
        captured["capture_output"] = capture_output
        captured["text"] = text
        return mocked_result

    monkeypatch.setattr("macbook_wechat_zhuaqu.service.runtime.subprocess.run", fake_run)

    result = runtime.send_feishu_message("# 微信日报\n\n- 一条重点", test_mode=False)

    assert result["ok"] is True
    assert captured["cmd"][:8] == [
        "lark-cli",
        "im",
        "+messages-send",
        "--profile",
        "personal",
        "--as",
        "user",
        "--user-id",
    ]
    assert captured["cmd"][8] == "ou_demo_user"
    assert captured["cmd"][9] == "--text"
    assert "每日微信重点" in captured["cmd"][10]


def test_webhook_send_still_supported_as_fallback(monkeypatch, tmp_path: Path):
    runtime = ServiceRuntime(tmp_path / "config.json", tmp_path / "keys.json", Path("/tmp/project"))
    runtime.save_config(
        AppConfig(
            feishu_delivery=FeishuDeliveryConfig(
                enabled=True,
                mode="webhook",
                webhook_url="https://example.com/hook",
                secret="demo-secret",
                message_title="每日微信重点",
            )
        )
    )

    mocked_response = Mock()
    mocked_response.status_code = 200
    mocked_response.raise_for_status = Mock()
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return mocked_response

    monkeypatch.setattr("macbook_wechat_zhuaqu.service.runtime.httpx.post", fake_post)

    result = runtime.send_feishu_message("# 微信日报\n\n- 一条重点", test_mode=False)

    assert result["ok"] is True
    assert captured["url"] == "https://example.com/hook"
    assert captured["json"]["msg_type"] == "text"
    assert "每日微信重点" in captured["json"]["content"]["text"]
    assert "timestamp" in captured["json"]
    assert "sign" in captured["json"]
