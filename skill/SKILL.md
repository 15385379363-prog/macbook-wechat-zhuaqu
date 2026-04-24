---
name: macbook-wechat-zhuaqu
description: |
  微信日报工作台。优先通过 Skill 打开本地服务面板，完成初始化、监控对象配置、日报预览和飞书同步。
  触发词：微信日报、打开微信日报设置、同步微信日报到飞书
---

# macbook-wechat-zhuaqu

## 入口策略

- 用户说“打开微信日报设置”时，优先启动本地服务面板
- 用户说“微信日报”时，调用本地服务生成最近日报
- 用户说“同步微信日报到飞书”时，调用本地服务发送最近日报

## 服务地址

默认本地服务地址：`http://127.0.0.1:8765`

## 本地入口脚本

- 打开设置页：`python3 scripts/skill_entry.py open`
- 生成日报：`python3 scripts/skill_entry.py generate --date 2026-04-24`
- 发送飞书：`python3 scripts/skill_entry.py send`

## 推荐流程

1. 先打开设置页
2. 点击“初始化微信数据库访问”
3. 扫描群聊/联系人并保存
4. 配置飞书 webhook
5. 生成日报并预览
6. 手动同步到飞书
