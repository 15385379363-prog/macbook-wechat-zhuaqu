from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .models import AppConfig, FeishuSendRequest, GenerateReportRequest
from .runtime import ServiceRuntime


def create_app(runtime: ServiceRuntime) -> FastAPI:
    app = FastAPI(title="macbook-wechat-zhuaqu", version="0.1.0")
    web_root = Path(__file__).resolve().parents[1] / "web"

    @app.get("/")
    def index():
        return FileResponse(web_root / "index.html")

    @app.get("/api/config")
    def get_config():
        return runtime.load_config()

    @app.put("/api/config")
    def put_config(config: AppConfig):
        return runtime.save_config(config)

    @app.get("/api/scan/targets")
    def scan_targets():
        try:
            return runtime.scan_targets()
        except Exception as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/extract/status")
    def extract_status():
        return runtime.extract_keys_status()

    @app.post("/api/extract/run")
    def run_extract():
        runtime.run_extract_keys_task()
        return runtime.extract_keys_status()

    @app.post("/api/reports/generate")
    def generate_report(request: GenerateReportRequest):
        try:
            return runtime.generate_report(request)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/reports/latest")
    def latest_report():
        report = runtime.get_latest_report()
        if report is None:
            raise HTTPException(status_code=404, detail="还没有可预览的日报。")
        return report

    @app.post("/api/feishu/send")
    def send_feishu(request: FeishuSendRequest):
        report = runtime.get_latest_report()
        if report is None:
            raise HTTPException(status_code=400, detail="请先生成日报。")
        try:
            return runtime.send_feishu_message(
                report.raw_markdown,
                request.test_mode,
                summary_text=report.summary_text,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app
