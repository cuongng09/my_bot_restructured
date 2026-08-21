"""
skills/news.py — Lấy tin tức nhanh từ các nguồn RSS (VnExpress, Tuổi Trẻ, ...).
"""

from __future__ import annotations

import re

from config import NEWS_FEEDS

_http_client = None


def set_http_client(client):
    global _http_client
    _http_client = client


async def skill_news(source: str = "vnexpress", count: int = 5) -> str:
    key = source.lower() if source.lower() in NEWS_FEEDS else "vnexpress"
    display, url = NEWS_FEEDS[key]
    try:
        resp = await _http_client.get(url, timeout=12)
        xml = resp.text
        items = re.findall(r'<item>(.*?)</item>', xml, re.DOTALL)[:count]
        if not items:
            return f"❓ Không lấy được tin từ *{display}* lúc này. Thử lại sau nhé."
        lines = [f"📰 *Tin mới — {display}*\n"]
        for item in items:
            title_match = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
            if not title_match:
                continue
            title = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title_match.group(1)).strip()
            link_match = re.search(r'<link>(.*?)</link>', item, re.DOTALL)
            link = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', link_match.group(1)).strip() if link_match else ""
            lines.append(f"• [{title}]({link})" if link else f"• {title}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Lỗi lấy tin từ {display}: {e}"
