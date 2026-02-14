import feedparser
import os
import time
import requests
from dotenv import load_dotenv
from helpers import time_difference

load_dotenv()

RUN_FREQUENCY = int(os.getenv("RUN_FREQUENCY", "3600"))  # 单位：秒（默认1小时）

# ===== 拉杆箱包 RSS 源列表 =====
# 你可以在下面添加或删除链接，一行一个
RSS_URLS = [
    # 1. Google News 多关键词搜索（中英文全覆盖）
    "https://news.google.com/rss/search?q=%E6%8B%89%E6%9D%86%E7%AE%B1+OR+%E8%A1%8C%E6%9D%8E%E7%AE%B1+OR+luggage+OR+suitcase+OR+trolley+case+OR+travel+bag&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",

    # 2. 科技媒体 The Verge 的 luggage 标签
    "https://www.theverge.com/luggage/feed.xml",

    # 3. 科技媒体 TechCrunch 的 luggage 标签（如果有）
    # 注意：TechCrunch 可能没有专门标签，暂用通用版
    "https://techcrunch.com/tag/luggage/feed/",

    # 4. 知名箱包品牌 Samsonite 官方新闻（如果提供 RSS）
    "https://www.samsonite.com/on/demandware.store/Sites-Samsonite-Site/default/Blog-Feed",

    # 5. 行业资讯网站：Business of Travel
    "https://www.businesstravelnews.com/RSS",

    # 6. 如果将来发现新的 RSS 源，直接在这里追加一行即可
]

# ============================

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

    return all_new_feed_items
