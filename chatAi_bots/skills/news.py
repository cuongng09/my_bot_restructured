"""
skills/news.py — Plugin lấy tin tức nhanh từ các nguồn RSS (VnExpress, Tuổi Trẻ, ...).
Triển khai dạng BaseSkill theo kiến trúc mô-đun Plug & Play.
"""

from __future__ import annotations

import re
from typing import Optional

from config import NEWS_FEEDS
from skills.base import BaseSkill, SkillResult


class NewsSkill(BaseSkill):
    name = "news"
    display_name = "Tin tức thời sự RSS"
    description = (
        "Lấy các tin tức mới nhất từ các kênh báo điện tử lớn của Việt Nam "
        "(VnExpress, Tuổi Trẻ, Thanh Niên, VietNamNet, Dân Trí)."
    )
    command = "news"
    parameters_schema = {
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "description": "Nguồn báo: vnexpress, tuoitre, thanhnien, vietnamnet, dantri (mặc định là vnexpress).",
                "default": "vnexpress",
            },
            "count": {
                "type": "integer",
                "description": "Số lượng bài viết mới cần lấy (1 đến 10). Mặc định là 5.",
                "default": 5,
            },
        },
    }

    async def execute(self, source: str = "vnexpress", count: int = 5, **kwargs) -> SkillResult:
        key = str(source or "vnexpress").lower().strip()
        if key not in NEWS_FEEDS:
            key = "vnexpress"

        count = max(1, min(int(count or 5), 10))
        display, url = NEWS_FEEDS[key]

        try:
            resp = await self.http_client.get(url, timeout=12)
            xml = resp.text
            items = re.findall(r'<item>(.*?)</item>', xml, re.DOTALL)[:count]
            if not items:
                return SkillResult(
                    success=False,
                    text=f"❓ Không lấy được tin từ *{display}* lúc này. Thử lại sau nhé.",
                )

            lines = [f"📰 *Tin mới — {display}*\n"]
            articles = []
            for item in items:
                title_match = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
                if not title_match:
                    continue
                title = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title_match.group(1)).strip()
                link_match = re.search(r'<link>(.*?)</link>', item, re.DOTALL)
                link = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', link_match.group(1)).strip() if link_match else ""
                lines.append(f"• [{title}]({link})" if link else f"• {title}")
                articles.append({"title": title, "link": link})

            return SkillResult(success=True, text="\n".join(lines), data=articles)
        except Exception as e:
            return SkillResult(success=False, text=f"❌ Lỗi lấy tin từ {display}: {e}")


# ── Tương thích ngược (Backward Compatibility) ──────────────────────────────
_default_news_skill = NewsSkill()


def set_http_client(client):
    _default_news_skill.set_http_client(client)
    try:
        from skills.registry import default_registry
        skill = default_registry.get("news")
        if skill:
            skill.set_http_client(client)
    except Exception:
        pass


async def skill_news(source: str = "vnexpress", count: int = 5) -> str:
    try:
        from skills.registry import default_registry
        skill = default_registry.get("news") or _default_news_skill
    except Exception:
        skill = _default_news_skill
    res = await skill.execute(source=source, count=count)
    return res.text
