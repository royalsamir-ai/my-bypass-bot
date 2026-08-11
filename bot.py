"""
Universal Telegram Link Bypasser Bot - Final Matrix
Integrated with high-tier DOM engines, fallback API routers, and live anomaly logging.
Render-ready with aiohttp health server on PORT (default 10000).
"""

from __future__ import annotations

import asyncio
import base64
import html as html_lib
import json
import logging
import os
import random
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import quote, urljoin, urlparse

import aiohttp
from aiohttp import ClientTimeout, TCPConnector, web
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
PORT = int(os.environ.get("PORT", "10000"))
MAX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT", "50"))
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "45"))
MAX_HOPS = int(os.environ.get("MAX_HOPS", "15"))
MAX_RESPONSE_BYTES = int(os.environ.get("MAX_RESPONSE_BYTES", "2000000"))

# PUBLIC BYPASSING API MATRIX - For advanced multi-layer fallback routines
UNIVERSAL_BYPASS_API = "https://bypass.vip"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("universal-bypass-bot")

# ---------------------------------------------------------------------------
# User-Agent rotation pool
# ---------------------------------------------------------------------------

DESKTOP_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]

MOBILE_AGENTS = [
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1",
]

URL_REGEX = re.compile(
    r"(?i)\b((?:https?://)[^\s<>\"'\[\]{}|\\^`]+)",
    re.IGNORECASE,
)

TRAILING_PUNCT = re.compile(r"[)\].,;:!?>\]]+$")

JS_REDIRECT_PATTERNS = [
    re.compile(r"""window\.location(?:\.href)?\s*=\s*['"]([^'"]+)['"]""", re.I),
    re.compile(r"""location\.(?:replace|assign)\(\s*['"]([^'"]+)['"]\s*\)""", re.I),
    re.compile(r"""window\.location\.replace\(\s*['"]([^'"]+)['"]\s*\)""", re.I),
    re.compile(r"""document\.location\s*=\s*['"]([^'"]+)['"]""", re.I),
    re.compile(r"""href\s*=\s*['"](https?://[^'"]+)['"]""", re.I),
    re.compile(r"""url\s*[:=]\s*['"](https?://[^'"]+)['"]""", re.I),
]

ATOB_PATTERNS = [
    re.compile(r"""atob\s*\(\s*['"]([A-Za-z0-9+/=]+)['"]\s*\)""", re.I),
    re.compile(r"""decodeURIComponent\s*\(\s*atob\s*\(\s*['"]([A-Za-z0-9+/=]+)['"]\s*\)""", re.I),
]

META_REFRESH = re.compile(
    r"""<meta[^>]+http-equiv\s*=\s*['"]?refresh['"]?[^>]+content\s*=\s*['"][^;'"]*;\s*url=([^'">\s]+)""", re.I
)

JSON_URL_KEYS = re.compile(
    r'"(?:url|link|destination|redirect|result|bypassed|final|target|href)"\s*:\s*"([^"\\]+(?:\\.[^"\\]*)*)"', re.I
)

CLOUDFLARE_MARKERS = ("cf-ray", "cloudflare", "just a moment", "checking your browser", "challenge-platform")

# ---------------------------------------------------------------------------
# Data models & Helper Utils
# ---------------------------------------------------------------------------

@dataclass
class BypassResult:
    original: str
    success: bool
    destination: Optional[str] = None
    engine: str = "unknown"
    hops: int = 0
    error: Optional[str] = None
    elapsed_ms: int = 0

@dataclass
class RequestProfile:
    user_agent: str
    is_mobile: bool = False

@dataclass
class HopContext:
    url: str
    referer: Optional[str] = None
    hop: int = 0
    visited: set[str] = field(default_factory=set)

def pick_profile() -> RequestProfile:
    mobile = random.random() < 0.35
    agents = MOBILE_AGENTS if mobile else DESKTOP_AGENTS
    return RequestProfile(user_agent=random.choice(agents), is_mobile=mobile)

def build_browser_headers(url: str, profile: RequestProfile, referer: Optional[str] = None) -> dict[str, str]:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    headers = {
        "User-Agent": profile.user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Referer": referer or origin,
        "Origin": origin,
    }
    return headers

def normalize_url(raw: str) -> str:
    cleaned = TRAILING_PUNCT.sub("", (raw or "").strip())
    if not cleaned:
        return cleaned
    if not cleaned.lower().startswith(("http://", "https://")):
        cleaned = "https://" + cleaned
    return cleaned

def extract_urls(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for match in URL_REGEX.finditer(text or ""):
        url = normalize_url(match.group(1))
        if not url or len(url) < 8:
            continue
        key = url.rstrip("/").lower()
        if key not in seen:
            seen.add(key)
            found.append(url)
    return found

def is_valid_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in {"http", "https"} and bool(p.netloc)
    except Exception:
        return False

def shorten(url: str, limit: int = 72) -> str:
    if len(url) <= limit:
        return url
    return url[: limit - 3] + "..."

# ---------------------------------------------------------------------------
# Core Multi-Layer Link Bypasser Client
# ---------------------------------------------------------------------------

class AdvancedBypasserClient:
    def __init__(self, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore):
        self.session = session
        self.semaphore = semaphore

    async def execute_api_fallback(self, target_url: str) -> Optional[str]:
        """Smart Failover Router: Secondary network arrays execution if internal core fails."""
        try:
            api_endpoint = f"{UNIVERSAL_BYPASS_API}{quote(target_url)}"
            async with self.session.get(api_endpoint, timeout=ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success") and data.get("destination"):
                        return str(data["destination"])
                    elif data.get("bypassed_url"):
                        return str(data["bypassed_url"])
        except Exception as e:
            logger.error(f"Fallback Matrix Request Exception: {str(e)}")
        return None

    async def resolve_url(self, target_url: str) -> BypassResult:
        start_time = time.perf_counter()
        current = normalize_url(target_url)

        if not is_valid_url(current):
            return BypassResult(original=target_url, success=False, error="Malformed URL topology", engine="validator")

        ctx = HopContext(url=current)
        ctx.visited.add(current.lower())
        profile = pick_profile()
        engine_used = "http_head"

        async with self.semaphore:
            while ctx.hop < MAX_HOPS:
                ctx.hop += 1
                headers = build_browser_headers(ctx.url, profile, ctx.referer)
                
                try:
                    # FIXED/COMPLETED: Hop Step 1 - Location Extraction Route Check
                    async with self.session.head(ctx.url, headers=headers, allow_redirects=False, timeout=ClientTimeout(total=6)) as resp:
                        if resp.status in (301, 302, 303, 307, 308):
                            loc = resp.headers.get("Location")
                            if loc:
                                next_url = urljoin(ctx.url, loc)
                                if next_url.lower() in ctx.visited:
                                    break
                                ctx.referer = ctx.url
                                ctx.url = next_url
                                ctx.visited.add(next_url.lower())
                                engine_used = "network_redirection"
                                continue

                    # Hop Step 2: Extracting Deeper Content Nodes
                    async with self.session.get(ctx.url, headers=headers, allow_redirects=False, timeout=ClientTimeout(total=REQUEST_TIMEOUT)) as resp:
                        if resp.status in (301, 302, 303, 307, 308):
                            loc = resp.headers.get("Location")
                            if loc:
                                next_url = urljoin(ctx.url, loc)
                                ctx.referer = ctx.url
                                ctx.url = next_url
                                ctx.visited.add(next_url.lower())
                                engine_used = "network_redirection"
                                continue

                        body_bytes = await resp.read()
                        html_content = body_bytes.decode("utf-8", errors="ignore")

                        if any(m in html_content.lower() for m in CLOUDFLARE_MARKERS) or resp.status in (403, 503):
