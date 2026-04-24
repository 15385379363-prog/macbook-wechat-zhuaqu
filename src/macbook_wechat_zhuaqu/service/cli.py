from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from .app import create_app
from .runtime import ServiceRuntime


def main() -> None:
    parser = argparse.ArgumentParser(description="Run macbook-wechat-zhuaqu local service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--config", default=str(Path.home() / ".config/macbook-wechat-zhuaqu/config.json"))
    parser.add_argument("--keys", default=str(Path.home() / ".config/macbook-wechat-zhuaqu/keys.json"))
    args = parser.parse_args()

    runtime = ServiceRuntime(config_path=Path(args.config), keys_path=Path(args.keys))
    app = create_app(runtime)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
