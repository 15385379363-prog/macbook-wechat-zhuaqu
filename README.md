# macbook-wechat-zhuaqu

Skill 优先、本地服务驱动的微信日报 MVP。目标是把 macOS 微信 4.x 的本地数据库能力包装成一个更稳定的 Skill + Web 设置面板。

## 第一阶段能力

- 初始化微信数据库访问并显示状态
- 自动扫描群聊/联系人，并允许手动补充
- 生成本地 Markdown 日报
- 页面内预览最近日报
- 手动同步到飞书消息

## 项目结构

- `skill/`: Skill 入口与说明
- `scripts/`: 已验证的微信数据库脚本
- `src/macbook_wechat_zhuaqu/service/`: 本地 FastAPI 服务
- `src/macbook_wechat_zhuaqu/web/`: 前端设置页
- `tests/`: API 与核心逻辑测试

## 启动

```bash
cd macbook-wechat-zhuaqu
PYTHONPATH=src python3 scripts/start_server.py
```

## Skill 风格入口

```bash
cd macbook-wechat-zhuaqu
python3 scripts/skill_entry.py open
python3 scripts/skill_entry.py generate --date 2026-04-24
python3 scripts/skill_entry.py send --test-mode
```

打开 <http://127.0.0.1:8765>。

## 隐私与边界

- 仅支持 macOS 微信 4.x
- 数据默认只在本机处理
- 不要把真实微信密钥和包含隐私内容的日报提交到公开仓库
