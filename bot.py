"""
Universal Telegram Link Bypasser Bot - Production Ready (Fixed Version)
Advanced multi-layer resolver: browser-mimic scraper, JS/form automation, API matrix.
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("universal-bypass-bot")

# ---------------------------------------------------------------------------
# User-Agent rotation pool (desktop + mobile)
# ---------------------------------------------------------------------------

DESKTOP_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0",
]

MOBILE_AGENTS = [
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
]

# Universal URL detector — no hardcoded shortener domains
URL_REGEX = re.compile(
    r"(?i)\b("
    r"https?://[^\s<>\"'\[\]{}|\\^`]+"
    r"|"
    r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(?:/[^\s<>\"'\[\]{}|\\^`]+)?"
    r")",
    re.IGNORECASE,
)

TRAILING_PUNCT = re.compile(r"[)\].,;:!?>\]]+$")

# JS / meta redirect patterns
JS_REDIRECT_PATTERNS = [
    re.compile(r"""window\.location(?:\.href)?\s*=\s*['"]([^'"]+)['"]""", re.I),
    re.compile(r"""location\.(?:replace|assign)\(\s*['"]([^'"]+)['"]\s*\)""", re.I),
    re.compile(r"""window\.location\.replace\(\s*['"]([^'"]+)['"]\s*\)""", re.I),
    re.compile(r"""setTimeout\s*\(\s*function\s*\(\)\s*\{\s*window\.location\s*=\s*['"]([^'"]+)['"]""", re.I),
    re.compile(r"""document\.location\s*=\s*['"]([^'"]+)['"]""", re.I),
    re.compile(r"""top\.location\s*=\s*['"]([^'"]+)['"]""", re.I),
    re.compile(r"""href\s*=\s*['"](https?://[^'"]+)['"]""", re.I),
    re.compile(r"""url\s*[:=]\s*['"](https?://[^'"]+)['"]""", re.I),
    re.compile(r"""redirect(?:Url|URL|_url)?\s*[:=]\s*['"](https?://[^'"]+)['"]""", re.I),
    re.compile(r"""destination(?:Url|URL|_url)?\s*[:=]\s*['"](https?://[^'"]+)['"]""", re.I),
    re.compile(r"""final(?:Url|URL|_url)?\s*[:=]\s*['"](https?://[^'"]+)['"]""", re.I),
    re.compile(r"""go\s*\(\s*['"](https?://[^'"]+)['"]\s*\)""", re.I),
]

ATOB_PATTERNS = [
    re.compile(r"""atob\s*\(\s*['"]([A-Za-z0-9+/=]+)['"]\s*\)""", re.I),
    re.compile(r"""decodeURIComponent\s*\(\s*atob\s*\(\s*['"]([A-Za-z0-9+/=]+)['"]\s*\)""", re.I),
    re.compile(r"""btoa\s*\(\s*['"]([^'"]+)['"]\s*\)""", re.I),
]

META_REFRESH = re.compile(
    r"""<meta[^>]+http-equiv\s*=\s*['"]?refresh['"]?[^>]+content\s*=\s*['"][^;'"]*;\s*url=([^'">\s]+)""",
    re.I,
)

JSON_URL_KEYS = re.compile(
    r'"(?:url|link|destination|redirect|result|bypassed|final|target|href)"\s*:\s*"([^"\\]+(?:\\.[^"\\]*)*)"',
    re.I,
)

CLOUDFLARE_MARKERS = (
    "cf-ray",
    "cloudflare",
    "just a moment",
    "checking your browser",
    "attention required",
    "cf-browser-verification",
    "challenge-platform",
)

# ---------------------------------------------------------------------------
# Data models
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def pick_profile() -> RequestProfile:
    mobile = random.random() < 0.35
    agents = MOBILE_AGENTS if mobile else DESKTOP_AGENTS
    return RequestProfile(user_agent=random.choice(agents), is_mobile=mobile)


def build_browser_headers(url: str, profile: RequestProfile, referer: Optional[str] = None) -> dict[str, str]:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    ref = referer or origin

    headers = {
        "User-Agent": profile.user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": ref,
        "Origin": origin,
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin" if referer and urlparse(referer).netloc == parsed.netloc else "cross-site",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "DNT": "1",
    }

    if profile.is_mobile:
        headers["Sec-CH-UA-Mobile"] = "?1"
        headers["Sec-CH-UA-Platform"] = '"Android"'
    else:
        headers["Sec-CH-UA-Mobile"] = "?0"
        headers["Sec-CH-UA-Platform"] = '"Windows"'

    headers["Sec-CH-UA"] = '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"'
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
        try:
            parsed = urlparse(url)
            if not parsed.netloc or "." not in parsed.netloc:
                continue
        except Exception:
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


def clean_js_string(s: str) -> str:
    s = s.strip("'\"` ")
    try:
        s = s.encode("utf-8").decode("unicode_escape")
    except Exception:
        pass
    return html_lib.unescape(s)


def try_base64_decode(payload: str) -> Optional[str]:
    try:
        padded = payload + "=" * (-len(payload) % 4)
        decoded = base64.b64decode(padded).decode("utf-8", errors="ignore")
        if is_valid_url(decoded) or (len(decoded) > 4 and ("url" in decoded.lower() or "/" in decoded)):
            return decoded
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Deep-Parsing Automation Engines
# ---------------------------------------------------------------------------


def extract_javascript_redirects(html_content: str, current_url: str) -> Optional[str]:
    for pattern in JS_REDIRECT_PATTERNS:
        match = pattern.search(html_content)
        if match:
            target = clean_js_string(match.group(1))
            full_url = urljoin(current_url, target)
            if is_valid_url(full_url) and full_url.lower() != current_url.lower():
                return full_url

    for pattern in ATOB_PATTERNS:
        match = pattern.search(html_content)
        if match:
            raw_payload = match.group(1)
            decoded = try_base64_decode(raw_payload)
            if decoded:
                if not decoded.startswith(("http://", "https://")):
                    decoded = urljoin(current_url, decoded)
                if is_valid_url(decoded):
                    return decoded

