#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
京博培训每日摘要推送脚本
- 默认推送今日课程总结（--dry-run 可预览）
- 推送目标：钉钉自定义机器人 Webhook（支持加签）
- H5 链接：CloudStudio 精美卡片站点
"""

import json, os, sys, time, hmac, hashlib, base64, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

# ── 常量 ────────────────────────────────────────────────────────────────────
H5_BASE_URL = "https://e2344249635c4818be33421d4cc0f151.app.codebuddy.work"
COURSES_FILE = os.path.join(os.path.dirname(__file__), "courses.json")

WEEKDAY_CN = ["周一","周二","周三","周四","周五","周六","周日"]


def load_courses():
    """加载课程数据"""
    with open(COURSES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def query_by_date(courses, date_str):
    """按日期筛选课程"""
    return [c for c in courses if c.get("date") == date_str]


def format_summary_text(courses, date_str):
    """格式化今日课程总结文本（简洁版）"""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    weekday = WEEKDAY_CN[d.weekday()]

    if not courses:
        return f"📅 **{date_str} {weekday}**\n\n今日无课程记录。"

    # 过滤非课程类别，按时间排序
    filtered = [c for c in courses
               if c.get("category") not in ["团队活动", "文化活动", "体育赛事", "休息", "考试"]]
    sorted_courses = sorted(filtered, key=lambda x: x.get("start_time", ""))

    if not sorted_courses:
        return f"📅 **{date_str} {weekday}**\n\n今日无课程记录。"

    lines = [
        f"📅 **{date_str} {weekday}** 今日课程回顾",
        "",
        "**今日课程：**"
    ]

    for c in sorted_courses:
        time_str = f"{c.get('start_time', '')[:5]}-{c.get('end_time', '')[:5]}"
        title = c.get("title", "未知课程")
        lines.append(f"• **{time_str}** {title}")

    lines.extend([
        "",
        "📝 详细内容请点击卡片链接查看",
        "",
        "⚠️ **提醒：课后评价 & 随堂作业还未完成的同学，请尽快完成哦！**"
    ])

    return "\n".join(lines)


def build_h5_url(date_str):
    """构建 H5 卡片站点链接"""
    return f"{H5_BASE_URL}?v=6&date={date_str}"


def sign_webhook(webhook_url, secret):
    """钉钉加签"""
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code).decode())
    separator = "&" if "?" in webhook_url else "?"
    return f"{webhook_url}{separator}timestamp={timestamp}&sign={sign}"


def send_to_dingtalk(webhook_url, secret, title, card_text, h5_url):
    """发送 ActionCard 消息到钉钉"""
    url = sign_webhook(webhook_url, secret) if secret else webhook_url

    payload = json.dumps({
        "msgtype": "actionCard",
        "actionCard": {
            "title": title,
            "text": card_text,
            "singleTitle": "📖 打开知识卡片",
            "singleURL": h5_url,
        },
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json",
    })

    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        return result


def main():
    # ── 参数解析 ──────────────────────────────────────────────────────────
    date_str  = None
    dry_run   = False
    args      = sys.argv[1:]
    i         = 0
    while i < len(args):
        if args[i] == "--date" and i + 1 < len(args):
            date_str = args[i + 1]
            i += 2
        elif args[i] == "--dry-run":
            dry_run = True
            i += 1
        else:
            i += 1

    # ── 日期：默认今天（北京时间）──────────────────────────────────────────
    if date_str is None:
        # 北京时间 +8h
        beijing_tz = timezone(timedelta(hours=8))
        now_bj = datetime.now(beijing_tz)
        date_str = now_bj.strftime("%Y-%m-%d")

    print(f"📅 推送日期：{date_str}")

    # ── 加载课程 ──────────────────────────────────────────────────────────
    courses       = load_courses()
    day_courses   = query_by_date(courses, date_str)
    card_text     = format_summary_text(day_courses, date_str)
    h5_url        = build_h5_url(date_str)

    print(f"\n{'='*50}")
    print(card_text)
    print(f"{'='*50}\n")
    print(f"🔗 {h5_url}\n")

    if dry_run:
        print("✅ dry-run 模式，仅预览不发送")
        return

    # ── 读取 Secrets ──────────────────────────────────────────────────────
    webhook_url = os.environ.get("DINGTALK_WEBHOOK", "")
    secret      = os.environ.get("DINGTALK_SECRET", "")

    if not webhook_url:
        print("❌ 缺少 DINGTALK_WEBHOOK，请检查 GitHub Secrets 设置")
        print("   → Secrets → Actions → 新建 DINGTALK_WEBHOOK")
        return

    # ── 发送钉钉 ──────────────────────────────────────────────────────────
    title = f"📋 {date_str} 培训课程总结"
    print(f"🚀 正在发送钉钉 ActionCard ...")
    result = send_to_dingtalk(webhook_url, secret, title, card_text, h5_url)

    if result.get("errcode") == 0:
        print("✅ 推送成功！")
    else:
        print(f"❌ 推送失败：{result.get('errmsg', str(result))}")


if __name__ == "__main__":
    main()
