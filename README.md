# macbook-wechat-zhuaqu

Skill 优先、本地服务驱动的微信日报 MVP。目标是把 macOS 微信 4.x 的本地数据库能力包装成一个更稳定的 Skill + Web 设置面板。

## 第一阶段能力

- 初始化微信数据库访问并显示状态
- 自动扫描群聊/联系人，并允许手动补充
- 生成本地 Markdown 日报
- 页面内预览最近日报
- 手动同步到飞书消息，优先支持 `lark-cli` 直发给自己

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

## 飞书发送

推荐在设置页里把发送模式设为 `lark_cli`，并填写你自己的飞书 `open_id`。默认发送内容为 `summary`，也就是只把 AI 分析结果发到飞书，原始聊天日志仍然保留在页面预览和本地 Markdown 文件里。项目会直接调用：

```bash
lark-cli im +messages-send --as user --user-id ou_xxx --text "..."
```

如果你更习惯机器人方式，也可以切回 `webhook` 模式，并继续填写 `webhook_url` 和可选 `secret`。如果你确实需要把完整原始日志发出去，可以把“飞书发送内容”切成 `full`。

## 隐私与边界

- 仅支持 macOS 微信 4.x
- 数据默认只在本机处理
- 不要把真实微信密钥和包含隐私内容的日报提交到公开仓库
