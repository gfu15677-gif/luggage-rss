import feedparser
import os
import time
import requests
from dotenv import load_dotenv
from helpers import time_difference

load_dotenv()

RUN_FREQUENCY = int(os.getenv("RUN_FREQUENCY", "3600"))

# ===== 拉杆箱 RSS 源（只保留真正相关的源）=====
RSS_URLS = [
    # 1. Google News 精准搜索（聚焦拉杆箱关键词）
    "https://news.google.com/rss/search?q=%E6%8B%89%E6%9D%86%E7%AE%B1+OR+%E8%A1%8C%E6%9D%8E%E7%AE%B1+OR+luggage+OR+suitcase+OR+%E7%AE%B1%E5%8C%85%E5%93%81%E7%89%8C+OR+%E6%96%B0%E5%93%81%E6%8B%89%E6%9D%86%E7%AE%B1&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",

    # 2. 行业垂直媒体（只保留会持续报道箱包的）
    "https://www.luggagemagazine.com/feed/",                    # 箱包行业专业杂志
    "https://www.travelaccessories.org/feed/",                  # 旅行用品协会

    # 3. 品牌官方博客（如果提供 RSS）
    "https://www.samsonite.com/blog/feed/",                     # 新秀丽
    "https://www.rimowa.com/blog/feed/",                        # Rimowa
    "https://www.tumi.com/blog/feed/",                          # Tumi
    "https://www.americantourister.com/blog/feed/",             # 美旅

    # 4. 零售行业新闻（偶尔涉及箱包）
    "https://www.themoodieblog.com/feed/",                      # 旅游零售

    # 5. 商业媒体中仅保留箱包标签（如果有）
    # 注意：以下需要确认是否存在，如果不存在 Google News 会覆盖
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
    print(f"总共 {len(all_new_feed_items)} 条新文章待推送（去重前）")

    # 去重逻辑
    unique_items_dict = {}
    for item in all_new_feed_items:
        link_key = item['link'].strip().lower()
        if link_key not in unique_items_dict:
            unique_items_dict[link_key] = item

    unique_items = list(unique_items_dict.values())
    print(f"总共 {len(unique_items)} 条新文章待推送（去重后）")

    for item in unique_items:
        text = f"{item['title']}\n{item['link']}"
        send_feishu_message(text)

    return unique_items
