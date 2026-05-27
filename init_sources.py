#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化更多采集源到数据库
"""
import json
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

from app.models.db import get_connection

# 默认 headers
DEFAULT_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    "accept-encoding": "gzip, deflate, br",
    "connection": "keep-alive",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
}

# 新增采集源
SOURCES = [
    {
        "name": "知乎热榜",
        "url_pattern": "https://www.zhihu.com/hot",
        "params": None
    },
    {
        "name": "微博热搜",
        "url_pattern": "https://s.weibo.com/top/summary",
        "params": None
    },
    {
        "name": "今日头条",
        "url_pattern": "https://www.toutiao.com/search/?keyword={关键词}&pd=information",
        "params": None
    },
    {
        "name": "网易新闻",
        "url_pattern": "https://www.163.com/search?keyword={关键词}",
        "params": None
    },
    {
        "name": "腾讯新闻",
        "url_pattern": "https://new.qq.com/search?query={关键词}",
        "params": None
    },
    {
        "name": "澎湃新闻",
        "url_pattern": "https://www.thepaper.cn/searchResult.jsp?searchword={关键词}",
        "params": None
    },
    {
        "name": "36氪",
        "url_pattern": "https://36kr.com/search/articles/{关键词}",
        "params": None
    },
    {
        "name": "虎嗅",
        "url_pattern": "https://www.huxiu.com/search.html?q={关键词}",
        "params": None
    }
]

def init_sources():
    print("正在初始化采集源...")
    with get_connection() as conn:
        for source in SOURCES:
            # 检查是否已存在
            existing = conn.execute(
                "SELECT id FROM watch_sources WHERE name = ?", 
                (source["name"],)
            ).fetchone()
            
            if not existing:
                conn.execute(
                    "INSERT INTO watch_sources(name, url_pattern, headers, params) VALUES(?,?,?,?)",
                    (
                        source["name"], 
                        source["url_pattern"], 
                        json.dumps(DEFAULT_HEADERS), 
                        source["params"]
                    )
                )
                print(f"✓ 添加采集源: {source['name']}")
            else:
                print(f"- 采集源已存在: {source['name']}")
        conn.commit()
    print("\n采集源初始化完成！")

if __name__ == "__main__":
    init_sources()
