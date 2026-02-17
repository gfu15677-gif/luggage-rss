import feedparser
import os
import time
import requests
from dotenv import load_dotenv
from helpers import time_difference

load_dotenv()

RUN_FREQUENCY = int(os.getenv("RUN_FREQUENCY", "3600"))

# ===== 箱包拉杆 RSS 源（包含 Google News + RSSHub 微信/抖音/B站/微博）=====
RSS_URLS = [
    # Google News 多关键词搜索（基础）
    "https://news.google.com/rss/search?q=%E6%8B%89%E6%9D%86%E7%AE%B1+OR+%E8%A1%8C%E6%9D%8E%E7%AE%B1+OR+%E7%AE%B1%E5%8C%85+OR+luggage+OR+suitcase+OR+trolley+case+OR+travel+bag+OR+%E4%B8%AD%E6%B8%AF%E7%9A%AE%E5%85%B7%E5%9F%8E+OR+%E6%8A%A4%E8%84%8A%E6%8B%89%E6%9D%86%E4%B9%A6%E5%8C%85&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",

    # 行业垂直媒体
    "https://www.luggagemagazine.com/feed/",
    "https://www.travelaccessories.org/feed/",
    "https://www.themoodieblog.com/feed/",

    # 品牌官方博客（示例）
    "https://www.samsonite.com/blog/feed/",
    "https://www.rimowa.com/blog/feed/",

    # 国内科技/消费媒体
    "https://36kr.com/feed",
    "https://www.huxiu.com/rss/",
    "https://rss.sina.com.cn/finance/rollnews.xml",

    # 国外时尚/消费品媒体
    "https://www.businessoffashion.com/feed/",
    "https://www.voguebusiness.com/feed/",
    "https://wwd.com/feed/",

    # RSSHub 生成的社交媒体搜索（需要自己部署或使用公共实例）
    "https://rsshub.app/wechat/search/拉杆箱",
    "https://rsshub.app/douyin/search/拉杆箱",
    "https://rsshub.app/bilibili/vsearch/拉杆箱",
    "https://rsshub.app/weibo/search/拉杆箱",
]

def _parse_struct_time_to_timestamp(st):
    if st:
        return time.mktime(st)
    return 0

def send_feishu_message(text):
    webhook_url = os.getenv("FEISHU_WEBHOOK")   # 统一使用 FEISHU_WEBHOOK
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

    # 只推送飞书，不涉及 Notion
    for item in all_new_feed_items:
        text = f"{item['title']}\n{item['link']}"
        send_feishu_message(text)

    return all_new_feed_items
