"""
云端每日课程推送脚本 — 不依赖 DWS，通过钉钉自定义机器人 Webhook 发送
设计用于 GitHub Actions 定时触发，电脑关机也能正常运行

推送格式：ActionCard 卡片 + "查看完整课程表" 按钮，点击打开 GitHub Pages 网页

用法:
  python cloud_push.py                    # 推送明日课程
  python cloud_push.py --date 2026-07-27  # 指定日期
  python cloud_push.py --dry-run          # 仅预览不发送

环境变量:
  DINGTALK_WEBHOOK  - 钉钉自定义机器人 Webhook URL（必填）
  DINGTALK_SECRET   - 机器人加签密钥（选填，如启用了加签安全设置）
  PAGES_BASE_URL    - GitHub Pages 基础 URL（选填，默认为仓库 Pages 地址）
"""
import json
import os
import sys
import time
import hmac
import hashlib
import base64
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

# ── 配置 ──────────────────────────────────────────────────
COURSES_FILE = os.path.join(os.path.dirname(__file__), "courses.json")

# GitHub Pages 基础 URL（可通过环境变量覆盖）
PAGES_BASE_URL = os.environ.get("PAGES_BASE_URL", "https://yiqiaoli86-glitch.github.io/buddy-cloud-push/")

WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def load_courses():
    """加载课程数据"""
    with open(COURSES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def query_by_date(courses, date_str):
    """查询指定日期的课程"""
    return [c for c in courses if c.get("date") == date_str]


def format_card_text(courses, date_str):
    """生成 ActionCard 卡片正文（精简版，详情点开网页查看）"""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    weekday = WEEKDAY_CN[d.weekday()]

    if not courses:
        return f"### 📅 {date_str} {weekday}\n\n明天没有培训安排，好好休息~ ☀️"

    lines = [f"### 📋 {date_str} {weekday} 课程提醒\n"]

    # 最多显示前 4 门课程的简要信息
    sorted_courses = sorted(courses, key=lambda x: x.get("start_time", ""))
    show_count = min(len(sorted_courses), 4)

    for c in sorted_courses[:show_count]:
        time_str = f"{c['start_time'][:5]}-{c['end_time'][:5]}"
        title = c.get("title", "")
        loc = c.get("location", "")
        loc_str = f"  📍{loc}" if loc else ""
        lines.append(f"- **{time_str}** {title}{loc_str}")

    if len(sorted_courses) > 4:
        lines.append(f"\n...还有 **{len(sorted_courses) - 4}** 门课程")

    lines.append(f"\n> 共 **{len(courses)}** 门课程，点击下方按钮查看完整日程 💪")
    return "\n".join(lines)


def build_pages_url(date_str):
    """构建 GitHub Pages URL，带日期参数"""
    base = PAGES_BASE_URL.rstrip("/")
    return f"{base}/?date={date_str}"


def sign_webhook(webhook_url, secret):
    """如果启用了加签，计算签名并拼接到 URL"""
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    separator = "&" if "?" in webhook_url else "?"
    return f"{webhook_url}{separator}timestamp={timestamp}&sign={sign}"


def send_to_dingtalk(webhook_url, secret, title, card_text, pages_url):
    """通过 Webhook 发送 ActionCard 消息到钉钉群"""
    url = sign_webhook(webhook_url, secret) if secret else webhook_url

    payload = json.dumps({
        "msgtype": "actionCard",
        "actionCard": {
            "title": title,
            "text": card_text,
            "singleTitle": "📋 查看完整课程表",
            "singleURL": pages_url,
        },
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json",
    })

    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        return result


def main():
    # 解析参数
    date_str = None
    dry_run = False
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--date" and i + 1 < len(args):
            date_str = args[i + 1]
            i += 2
        elif args[i] == "--dry-run":
            dry_run = True
            i += 1
        else:
            i += 1

    # 默认推送明日课程（固定使用北京时间 UTC+8，适配云端服务器）
    if date_str is None:
        beijing_tz = timezone(timedelta(hours=8))
        tomorrow = datetime.now(beijing_tz) + timedelta(days=1)
        date_str = tomorrow.strftime("%Y-%m-%d")

    print(f"📅 推送日期: {date_str}")

    # 加载课程并生成消息
    courses = load_courses()
    day_courses = query_by_date(courses, date_str)
    card_text = format_card_text(day_courses, date_str)
    pages_url = build_pages_url(date_str)

    print("\n--- 推送内容预览 ---")
    print(card_text)
    print(f"\n🔗 网页链接: {pages_url}")
    print("--- 预览结束 ---\n")

    if dry_run:
        print("🔍 dry-run 模式，不发送")
        return

    # 获取 Webhook 配置
    webhook_url = os.environ.get("DINGTALK_WEBHOOK", "")
    secret = os.environ.get("DINGTALK_SECRET", "")

    if not webhook_url:
        print("❌ 未设置 DINGTALK_WEBHOOK 环境变量")
        print("   请在 GitHub 仓库 Settings → Secrets → Actions 中添加 DINGTALK_WEBHOOK")
        return

    # 发送
    title = f"明日课程提醒 {date_str}"
    print(f"🚀 正在发送 ActionCard 到钉钉群 ...")
    result = send_to_dingtalk(webhook_url, secret, title, card_text, pages_url)

    if result.get("errcode") == 0:
        print("✅ 推送成功！")
    else:
        print(f"❌ 推送失败: {result.get('errmsg', '未知错误')}")
        print(f"   完整响应: {json.dumps(result, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
