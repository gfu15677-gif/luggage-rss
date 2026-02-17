import feedparser
import os
import time
import requests
from dotenv import load_dotenv
from helpers import time_difference

load_dotenv()

RUN_FREQUENCY = int(os.getenv("RUN_FREQUENCY", "3600"))

# ===== 箱包拉杆 RSS 源 =====
RSS_URLS = [
    # --- 国内新闻源 ---
    "https://news.google.com/rss/search?q=%E6%8B%89%E6%9D%86%E7%AE%B1+OR+%E8%A1%8C%E6%9D%8E%E7%AE%B1+OR+%E7%AE%B1%E5%8C%85&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
    "https://36kr.com/feed",
    "https://www.huxiu.com/rss/",
    "https://rss.sina.com.cn/finance/rollnews.xml",
    "https://www.thepaper.cn/rss/news.xml",
    "https://www.guancha.cn/feed/news.xml",

    # --- 国内社交媒体（RSSHub公共实例）---
    "https://rsshub.uneasy.win/wechat/search/拉杆箱",
    "https://rsshub.uneasy.win/weibo/search/拉杆箱",
    "https://rsshub.uneasy.win/bilibili/vsearch/拉杆箱",
    "https://rsshub.uneasy.win/douyin/search/拉杆箱",

    # --- 国外行业媒体 ---
    "https://www.luggagemagazine.com/feed/",
    "https://www.travelaccessories.org/feed/",
    "https://www.themoodieblog.com/feed/",
    "https://www.businessoffashion.com/feed/",
    "https://www.voguebusiness.com/feed/",
    "https://wwd.com/feed/",

    # --- 品牌官方博客 ---
    "https://www.samsonite.com/blog/feed/",
    "https://www.rimowa.com/blog/feed/",
]

def _parse_struct_time_to_timestamp(st):
    if st:
        return time.mktime(st)
    return 0

def send_feishu_message(text):
    webhook_url = os.getenv("FEISHU_WEBHOOK")
    if not webhook_url:
        print("❌ 环境变量 FEISHU_WEBHOOK 未设置")
        return
    payload = {
        "msg_type": "text",
        "content": {"text": text}
    }
    try:
        resp = requests.post(webhook_url, json=payload)
        if resp.status_code == 200:
            print("✅ 飞书消息发送成功")
        else:
            print(f"❌ 飞书消息发送失败: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ 飞书请求异常: {e}")

def get_new_feed_items_from(feed_url):
    print(f"正在抓取 RSS: {feed_url}")
    try:
        rss = feedparser.parse(feed_url)
        print(f"RSS 解析成功，条目总数: {len(rss.entries)}")
    except Exception as e:
        print(f"Error parsing feed {feed_url}: {e}")
        return []

    current_time_struct = rss.get("updated_parsed") or rss.get("published_parsed")
    current_time = _parse_struct_time_to_timestamp(current_time_struct) if current_time_struct else time.time()

    new_items = []
    for item in rss.entries:
        pub_date = item.get("published_parsed") or item.get("updated_parsed")
        if pub_date:
            blog_published_time = _parse_struct_time_to_timestamp(pub_date)
        else:
            continue

        diff = time_difference(current_time, blog_published_time)
        if diff["diffInSeconds"] < RUN_FREQUENCY:
            new_items.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "content": item.get("content", [{}])[0].get("value", item.get("summary", "")),
                "published_parsed": pub_date
            })

    print(f"本次抓取到 {len(new_items)} 条新文章")
    return new_items

def get_new_feed_items():
    all_new_feed_items = []
    for feed_url in RSS_URLS:
        feed_items = get_new_feed_items_from(feed_url)
        all_new_feed_items.extend(feed_items)

    all_new_feed_items.sort(
        key=lambda x: _parse_struct_time_to_timestamp(x.get("published_parsed"))
    )
    print(f"总共 {len(all_new_feed_items)} 条新文章待推送")

    for item in all_new_feed_items:
        text = f"{item['title']}\n{item['link']}"
        send_feishu_message(text)

    return all_new_feed_items
