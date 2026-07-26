# 搭档Buddy — 每日课程推送（云端版）

京博控股集团 2026届新员工入职训练营课程提醒系统。

每天 20:00 自动推送次日课程安排到钉钉群，**电脑关机也能正常运行**。

## 工作原理

```
Gitee Go 定时触发 (每天20:00)
    → 运行 cloud_push.py
    → 读取 courses.json 计算明日课程
    → 通过钉钉自定义机器人 Webhook 发送到群
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `cloud_push.py` | 云端推送脚本（纯标准库，无需安装依赖） |
| `courses.json` | 课程数据（107门课程） |
| `.workflow/daily-push.yml` | Gitee Go 流水线配置（定时触发） |

## 配置方法

1. 在钉钉群添加「自定义机器人」，获取 Webhook URL 和加签 Secret
2. Fork 本仓库
3. 进入仓库 **设置 → 流水线变量**，添加两个密钥变量：
   - `DINGTALK_WEBHOOK`：机器人 Webhook URL
   - `DINGTALK_SECRET`：加签密钥（SEC 开头）
4. 进入 **流水线** 页面，启用 `daily-course-push` 流水线
5. 流水线将在每天 20:00（北京时间）自动执行
