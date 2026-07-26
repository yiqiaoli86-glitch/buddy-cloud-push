# 搭档Buddy - 每日课程推送（云端版）

京博控股集团 2026届新员工培训每日课程提醒，通过钉钉自定义机器人 Webhook 自动推送次日课程。

## 工作流程

1. GitHub Actions 每天北京时间 20:00（UTC 12:00）自动触发
2. 读取 `courses.json` 中次日课程数据
3. 通过钉钉 Webhook 发送 Markdown 消息到群聊
4. 无课程日发送休息提醒

## 必须配置的 Secrets

在仓库 Settings → Secrets and variables → Actions → New repository secret 添加：

| Secret 名称 | 值 |
|---|---|
| `DINGTALK_WEBHOOK` | 钉钉机器人的 Webhook URL |
| `DINGTALK_SECRET` | 钉钉机器人的加签密钥（SEC开头） |

## 手动测试

在仓库 Actions 页面找到「每日次日课程推送」→ Run workflow 可手动触发测试。
