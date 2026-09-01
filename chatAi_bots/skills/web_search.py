"""
skills/web_search.py — Tìm kiếm web (DuckDuckGo) + cào nội dung trang + format kết quả cho RAG.
"""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import os
import re
import socket
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, parse_qs, unquote

from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

import database as db
from bot_logger import logger

_http_client = None
# Executor riêng cho DDGS (sync/blocking) — tối đa 4 luồng, tách khỏi pool chung
_SEARCH_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ddg-search")

# ── Cấu hình nguồn search & cache (đọc từ biến môi trường) ────────────────────
# SearXNG tự host — đặt làm nguồn chính. Cần bật `json` trong `search:
# formats` của settings.yml SearXNG thì endpoint mới trả JSON được.
SEARXNG_URL = os.getenv("SEARXNG_URL", "http://localhost:8081").rstrip("/")
SEARCH_CACHE_TTL_SEC = int(os.getenv("SEARCH_CACHE_TTL_SEC", "900"))  # mặc định 15 phút


# ── SSRF guard ─────────────────────────────────────────────────────────────
def _is_ip_blocked(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # không parse được -> chặn cho an toàn
    if (
        ip.is_private or ip.is_loopback or ip.is_link_local
        or ip.is_multicast or ip.is_reserved or ip.is_unspecified
    ):
        return True
    if ip_str == "169.254.169.254":  # cloud metadata endpoint (AWS/GCP/Azure)
        return True
    return False


def _is_safe_url_sync(url: str) -> bool:
    """Kiểm tra (blocking, chạy trong executor) xem URL có an toàn để bot tự
    fetch hay không: chỉ http/https, hostname không phải localhost/nội bộ,
    và mọi IP mà hostname resolve tới đều không nằm trong dải private/loopback/
    link-local/metadata. Chặn ở đây để tránh bot bị lợi dụng cào vào hạ tầng
    nội bộ (SSRF) qua URL độc hại lẫn trong kết quả search."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
    lowered = hostname.lower()
    if lowered in ("localhost", "0.0.0.0") or lowered.endswith(".local"):
        return False
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    if not infos:
        return False
    for info in infos:
        ip_str = info[4][0]
        if _is_ip_blocked(ip_str):
            return False
    return True


async def _is_safe_url(url: str) -> bool:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _is_safe_url_sync, url)


def set_http_client(client):
    global _http_client
    _http_client = client


def get_search_executor() -> ThreadPoolExecutor:
    return _SEARCH_EXECUTOR


def shutdown_executor():
    _SEARCH_EXECUTOR.shutdown(wait=False, cancel_futures=True)


# ── Query cleaning ────────────────────────────────────────────────────────────
_SEARCH_FILLER_PATTERNS = [
    r'^(ơi|này|à|ê|nè)\s+', r'\b(bạn ơi|ê bạn|này bạn)\b',
    r'^(cho\s+(tôi|mình|em|anh|chị)\s+(hỏi|biết)\s*)', r'^(làm ơn\s+)', r'^(hãy\s+)',
    r'\b(giúp\s+(tôi|mình|em|anh|chị)\s*(với)?)\b', r'\b(là gì vậy|đúng không|nhỉ|nha|nhé|ạ|vậy đó|thế nhỉ)\b',
    r'^(cho\s+(tôi|mình)\s+)', r'\b(vậy|thế)\s*$',
]


def clean_search_query(text: str) -> str:
    q = text.strip()
    for pat in _SEARCH_FILLER_PATTERNS:
        q = re.sub(pat, ' ', q, flags=re.IGNORECASE)
    q = re.sub(r'[?？!！]+$', '', q).strip()
    q = re.sub(r'\s+', ' ', q).strip()
    return q if len(q) >= 3 else text.strip()


async def _to_english(text: str) -> str:
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(
            None, lambda: GoogleTranslator(source='vi', target='en').translate(text)
        )
    except Exception:
        return ""


# ── Page content fetching ─────────────────────────────────────────────────────
async def _fetch_page_snippet(url: str, max_chars: int = 2000) -> str:
    headers = {
        "User-Agent": "MyTelegramBot/1.0 (https://t.me/my_bot; contact: admin@example.com)",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
    }

    # 🛡️ Chặn SSRF: không tự fetch URL nào trỏ về hostname/IP nội bộ, kể cả
    # khi URL đó đến từ kết quả search (không kiểm soát được nguồn gốc).
    if not await _is_safe_url(url):
        logger.warning(f"🛡️ Chặn fetch URL không an toàn (SSRF guard): {url}")
        return ""

    if "wikipedia.org/wiki/" in url:
        try:
            title = url.split("/wiki/")[-1]
            lang = url.split("//")[1].split(".")[0]
            api_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
            if await _is_safe_url(api_url):
                resp = await _http_client.get(api_url, headers=headers, timeout=8.0)
                if resp.status_code == 200:
                    extract = resp.json().get("extract", "")
                    if extract:
                        return extract[:max_chars]
        except Exception as e:
            logger.warning(f"⚠️ Lỗi API Wikipedia ({url}): {e}")

    try:
        resp = await _http_client.get(url, headers=headers, timeout=9.0, follow_redirects=True)
        resp.raise_for_status()

        # Recheck sau khi theo redirect: URL ban đầu có thể an toàn nhưng
        # redirect tới một địa chỉ nội bộ (open redirect làm bàn đạp SSRF).
        final_url = str(resp.url)
        if final_url != url and not await _is_safe_url(final_url):
            logger.warning(f"🛡️ Chặn nội dung sau redirect không an toàn: {url} → {final_url}")
            return ""

        try:
            import trafilatura
            extracted = trafilatura.extract(resp.text, include_links=False, include_images=False)
            if extracted and len(extracted) > 100:
                return extracted[:max_chars]
        except ImportError:
            pass

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header",
                         "noscript", "aside", "form", "button", "iframe", "svg"]):
            tag.decompose()

        main_block = (
            soup.find("article") or soup.find("main")
            or soup.find(attrs={"itemprop": "articleBody"})
            or soup.find(class_=re.compile(r'(article|content|post|detail|entry|body)', re.I))
            or soup.body
        )
        if not main_block:
            return ""

        lines = (line.strip() for line in main_block.get_text(separator="\n").splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\n".join(chunk for chunk in chunks if chunk)
        return text[:max_chars]

    except Exception as e:
        logger.warning(f"⚠️ Lỗi cào nội dung link {url}: {e}")
        return ""


async def enrich_with_page_content(results: list[dict], max_pages: int = 3) -> list[dict]:
    targets = [r for r in results[:max_pages] if r.get("href")]
    if not targets:
        return results
    fetched = await asyncio.gather(*[_fetch_page_snippet(r["href"]) for r in targets],
                                   return_exceptions=True)
    for r, content in zip(targets, fetched):
        if isinstance(content, str) and len(content) > 50:
            r["body"] = content
    return results


# ── SearXNG (tự host) — nguồn search chính ────────────────────────────────────
async def _searxng_search(query: str, max_results: int = 5) -> list[dict]:
    """Gọi instance SearXNG tự host (SEARXNG_URL). Cần bật `json` trong
    `search.formats` của settings.yml SearXNG. Trả về [] nếu chưa cấu hình
    SEARXNG_URL hoặc instance lỗi/timeout — để raw_search_data() rơi xuống
    các nguồn dự phòng (DDGS / cào HTML)."""
    if not SEARXNG_URL:
        return []
    try:
        resp = await _http_client.get(
            f"{SEARXNG_URL}/search",
            params={"q": query, "format": "json", "language": "vi"},
            timeout=6.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"⚠️ SearXNG search lỗi/timeout cho '{query}': {e}")
        return []

    results = []
    for item in data.get("results", [])[:max_results]:
        href = item.get("url", "")
        if not href:
            continue
        results.append({
            "title": item.get("title", ""),
            "body": item.get("content", ""),
            "href": href,
        })
    return results


# ── DuckDuckGo search (dự phòng) ───────────────────────────────────────────────
async def _raw_search_fallback(query: str, max_results: int = 5) -> list[dict]:
    """Cào trực tiếp DuckDuckGo HTML (fallback khi DDGS bị block)."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = await _http_client.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query, "kl": "vn-vi"}, headers=headers, timeout=5,
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []

        def _resolve_real_url(raw_href: str) -> str:
            if not raw_href:
                return ""
            if raw_href.startswith("//"):
                raw_href = "https:" + raw_href
            try:
                qs = parse_qs(urlparse(raw_href).query)
                if "uddg" in qs and qs["uddg"]:
                    return unquote(qs["uddg"][0])
            except Exception:
                pass
            return raw_href

        for result_div in soup.find_all('div', class_=lambda c: c and 'result' in c and 'web-result' in c):
            a_tag = result_div.find('a', class_='result__url')
            if not a_tag:
                continue
            real_url = _resolve_real_url(a_tag.get('href', ''))
            if not real_url.startswith("http"):
                continue
            title_tag   = result_div.find('h2', class_='result__title')
            snippet_tag = result_div.find('a', class_='result__snippet')
            results.append({
                "title": title_tag.text.strip() if title_tag else "",
                "body":  snippet_tag.text.strip() if snippet_tag else "",
                "href":  real_url,
            })
            if len(results) >= max_results:
                break
        return results
    except Exception as e:
        logger.warning(f"Fallback Search Error: {e}")
        return []


def _cache_key(query: str) -> str:
    return hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()


async def raw_search_data(query: str) -> list[dict]:
    original_query = query
    query = clean_search_query(query)
    if query != original_query:
        logger.info(f"🔎 Search query: gốc='{original_query}' → đã làm sạch='{query}'")
    else:
        logger.info(f"🔎 Search query: '{query}'")

    # 🆕 Cache hit? Trả thẳng, khỏi gọi search engine + cào trang lại.
    cache_key = _cache_key(query)
    try:
        cached = await db.get_cached_search(cache_key, SEARCH_CACHE_TTL_SEC)
    except Exception as e:
        cached = None
        logger.warning(f"⚠️ Lỗi đọc search cache cho '{query}': {e}")
    if cached is not None:
        logger.info(f"🔎 Cache HIT cho '{query}' ({len(cached)} kết quả, ttl={SEARCH_CACHE_TTL_SEC}s).")
        return cached

    loop = asyncio.get_event_loop()

    def _ddg(q: str):
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            return [
                {"title": r.get("title", ""), "body": r.get("body", ""), "href": r.get("href", "")}
                for r in ddgs.text(q, region="vn-vi", max_results=5)
            ]

    # 1) SearXNG (tự host) — nguồn chính, nếu đã cấu hình SEARXNG_URL
    results = await _searxng_search(query)
    method = "searxng"

    # 2) DDGS — dự phòng nếu SearXNG chưa cấu hình hoặc không có kết quả
    if not results:
        method = "ddgs"
        try:
            results = await asyncio.wait_for(
                loop.run_in_executor(_SEARCH_EXECUTOR, _ddg, query), timeout=4.0
            )
        except Exception as e:
            logger.warning(f"⚠️ DDGS search lỗi/timeout cho '{query}': {e} — chuyển sang fallback HTML.")
            results = []

    # 3) Cào trực tiếp HTML DuckDuckGo (tiếng Việt)
    if not results:
        method = "fallback_vi"
        results = await _raw_search_fallback(query)

    # 4) Dịch sang tiếng Anh rồi thử lại nếu vẫn không có gì
    if not results:
        en_query = await _to_english(query)
        if en_query and en_query.lower() != query.lower():
            method = "fallback_en"
            logger.info(f"🔎 Không có kết quả tiếng Việt, thử bản dịch tiếng Anh: '{query}' → '{en_query}'")
            results = await _raw_search_fallback(en_query)

    if results:
        titles = " | ".join(f"[{r.get('title','')[:60]}]({r.get('href','')})" for r in results[:5])
        logger.info(f"🔎 Kết quả search (method={method}, {len(results)} kết quả): {titles}")
    else:
        logger.warning(f"🔎 Search '{query}' KHÔNG có kết quả nào (đã thử searxng + ddgs + fallback vi/en).")
        return results

    enriched = await enrich_with_page_content(results, max_pages=3)

    # 🆕 Ghi cache sau khi đã cào xong nội dung trang, để lần sau (trong TTL)
    # không phải gọi search engine lẫn cào trang lại từ đầu.
    try:
        await db.set_cached_search(cache_key, query, enriched)
    except Exception as e:
        logger.warning(f"⚠️ Lỗi ghi search cache cho '{query}': {e}")

    return enriched


# ── Format for RAG ────────────────────────────────────────────────────────────
def format_web_context(raw_data: list[dict]) -> str:
    context_bits = []
    for i, r in enumerate(raw_data, 1):
        body_text = r['body'].strip() if r['body'].strip() else "Không cào được nội dung chi tiết."
        context_bits.append(f"Nguồn [{i}]:\nTiêu đề: {r['title']}\nURL: {r['href']}\nNội dung: {body_text}")
    return "\n\n".join(context_bits)


def format_sources_footer(raw_data: list[dict]) -> str:
    if not raw_data:
        return ""
    lines = ["\n\n📎 *Nguồn tham khảo:*"]
    for i, r in enumerate(raw_data, 1):
        title = (r.get("title") or "").strip() or r.get("href", "")
        href  = r.get("href", "")
        if not href:
            continue
        lines.append(f"[{i}] [{title}]({href})")
    return "\n".join(lines) if len(lines) > 1 else ""