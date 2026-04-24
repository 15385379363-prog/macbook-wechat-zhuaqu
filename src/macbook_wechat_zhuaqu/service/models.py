from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class WechatTarget(BaseModel):
    name: str
    enabled: bool = True
    source_id: Optional[str] = None
    manual: bool = False


class FeishuDeliveryConfig(BaseModel):
    enabled: bool = False
    mode: Literal["lark_cli", "webhook"] = "lark_cli"
    send_content: Literal["summary", "full"] = "summary"
    cli_user_id: Optional[str] = None
    cli_profile: Optional[str] = None
    cli_identity: Literal["user", "bot"] = "user"
    webhook_url: Optional[str] = None
    secret: Optional[str] = None
    message_title: str = "微信日报"


class SummarySettings(BaseModel):
    template: str = "focus"
    ai_enabled: bool = True


class AppConfig(BaseModel):
    wxid: Optional[str] = None
    db_base_path: Optional[str] = None
    monitor_groups: List[WechatTarget] = Field(default_factory=list)
    monitor_contacts: List[WechatTarget] = Field(default_factory=list)
    report_dir: str = "~/Documents/wechat-daily"
    time_mode: str = "8am_to_8am"
    feishu_delivery: FeishuDeliveryConfig = Field(default_factory=FeishuDeliveryConfig)
    summary: SummarySettings = Field(default_factory=SummarySettings)


class ScanResult(BaseModel):
    groups: List[str] = Field(default_factory=list)
    contacts: List[str] = Field(default_factory=list)


class ExtractStatus(BaseModel):
    stage: Literal["idle", "running", "matched", "failed"] = "idle"
    wechat_installed: bool = False
    desktop_copy_ready: bool = False
    frida_ready: bool = False
    captured_key_count: int = 0
    matched_databases: List[str] = Field(default_factory=list)
    hints: List[str] = Field(default_factory=list)
    last_error: Optional[str] = None


class GenerateReportRequest(BaseModel):
    target_date: Optional[str] = None


class ReportResult(BaseModel):
    report_date: str
    markdown_path: str
    raw_markdown: str
    summary_text: str
    generated_at: Optional[str] = None
    bullet_count: int = 0


class FeishuSendRequest(BaseModel):
    test_mode: bool = False
