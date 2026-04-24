# macbook-wechat-zhuaqu Architecture

## MVP Layers

1. `skill/`
   Skill 文案与入口说明，默认通过 `scripts/skill_entry.py` 调起本地服务或执行常用动作。

2. `scripts/`
   已验证的微信数据库脚本，负责密钥提取、群聊联系人扫描、日报生成。

3. `src/macbook_wechat_zhuaqu/service/`
   FastAPI 本地服务，负责配置持久化、任务编排、飞书同步和前端 API。

4. `src/macbook_wechat_zhuaqu/web/`
   静态前端页面，作为本地工作台。

## Key Runtime Decisions

- 配置文件与密钥文件都由本地服务统一管理。
- 底层脚本通过环境变量接收配置路径和密钥路径，避免写死到旧的 `wechat-daily` 文件位置。
- 飞书同步第一阶段使用 webhook 消息发送。
- AI 摘要第一阶段使用重点摘要模式，先保留本地启发式摘要入口，后续再接模型调用。
