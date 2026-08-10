"""
Universal Telegram Link Bypasser Bot
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
    return url if len(url) <= limit else url[: limit - 3] + "..."


def escape_html(text: str) -> str:
    return html_lib.escape(text or "")


def is_cloudflare_blocked(status: int, body: str, headers: dict[str, str]) -> bool:
    if status in {403, 503, 429}:
        lower = (body or "").lower()
        header_blob = " ".join(f"{k}:{v}" for k, v in headers.items()).lower()
        for marker in CLOUDFLARE_MARKERS:
            if marker in lower or marker in header_blob:
                return True
    return False


def decode_base64_candidate(value: str) -> Optional[str]:
    try:
        padded = value + "=" * (-len(value) % 4)
        decoded = base64.b64decode(padded, validate=False).decode("utf-8", errors="ignore")
        if decoded.startswith(("http://", "https://", "/")):
            return decoded
    except Exception:
        pass
    return None


def unescape_json_url(value: str) -> str:
    return value.replace("\\/", "/").replace("\\u002F", "/")


# ---------------------------------------------------------------------------
# Redirect & form engines
# ---------------------------------------------------------------------------


class RedirectExtractor:
    @staticmethod
    def from_body(body: str, base_url: str) -> list[str]:
        candidates: list[str] = []
        if not body:
            return candidates

        for pattern in JS_REDIRECT_PATTERNS:
            for match in pattern.findall(body):
                url = unescape_json_url(match.strip())
                if url.startswith("//"):
                    url = "https:" + url
                elif url.startswith("/"):
                    url = urljoin(base_url, url)
                if url.startswith(("http://", "https://")):
                    candidates.append(url)

        for pattern in ATOB_PATTERNS:
            for match in pattern.findall(body):
                decoded = decode_base64_candidate(match)
                if decoded:
                    if decoded.startswith("/"):
                        decoded = urljoin(base_url, decoded)
                    if decoded.startswith(("http://", "https://")):
                        candidates.append(decoded)

        for match in META_REFRESH.findall(body):
            url = html_lib.unescape(match.strip().strip("'\""))
            if url.startswith("//"):
                url = "https:" + url
            elif url.startswith("/"):
                url = urljoin(base_url, url)
            if url.startswith(("http://", "https://")):
                candidates.append(url)

        for match in JSON_URL_KEYS.findall(body):
            url = unescape_json_url(match.strip())
            if url.startswith(("http://", "https://")):
                candidates.append(url)

        # Deduplicate preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for url in candidates:
            key = url.rstrip("/").lower()
            if key not in seen:
                seen.add(key)
                unique.append(url)
        return unique


class FormAutomator:
    @staticmethod
    def discover_forms(html: str, base_url: str) -> list[dict[str, Any]]:
        forms: list[dict[str, Any]] = []
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            return forms

        for form in soup.find_all("form"):
            action = form.get("action") or base_url
            method = (form.get("method") or "get").lower()
            target_url = urljoin(base_url, action)

            payload: dict[str, str] = {}
            for inp in form.find_all(["input", "textarea", "select"]):
                name = inp.get("name")
                if not name:
                    continue
                tag = inp.name.lower()
                if tag == "select":
                    selected = inp.find("option", selected=True) or inp.find("option")
                    payload[name] = (selected.get("value") if selected else "") or ""
                elif inp.get("type", "text").lower() in {"submit", "button", "image", "reset"}:
                    continue
                else:
                    payload[name] = inp.get("value") or ""

            if payload:
                forms.append(
                    {
                        "url": target_url,
                        "method": method,
                        "data": payload,
                    }
                )
        return forms

    @staticmethod
    def pick_best_form(forms: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
        if not forms:
            return None
        # Prefer POST forms with more hidden fields (likely token forms)
        forms_sorted = sorted(
            forms,
            key=lambda f: (f["method"] == "post", len(f["data"])),
            reverse=True,
        )
        return forms_sorted[0]


# ---------------------------------------------------------------------------
# HTTP client layer
# ---------------------------------------------------------------------------


class BrowserSession:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self.session = session

    async def request(
        self,
        method: str,
        url: str,
        *,
        referer: Optional[str] = None,
        data: Optional[dict[str, str]] = None,
        allow_redirects: bool = False,
        profile: Optional[RequestProfile] = None,
    ) -> tuple[int, str, dict[str, str], str]:
        profile = profile or pick_profile()
        headers = build_browser_headers(url, profile, referer)
        timeout = ClientTimeout(total=REQUEST_TIMEOUT)

        try:
            async with self.session.request(
                method.upper(),
                url,
                headers=headers,
                data=data,
                allow_redirects=allow_redirects,
                timeout=timeout,
            ) as resp:
                raw = await resp.content.read(MAX_RESPONSE_BYTES)
                body = raw.decode("utf-8", errors="ignore")
                resp_headers = {k: v for k, v in resp.headers.items()}
                final_url = str(resp.url)
                return resp.status, body, resp_headers, final_url
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.debug("Request failed %s %s: %s", method, url, exc)
            return 0, "", {}, url


# ---------------------------------------------------------------------------
# API fallback matrix
# ---------------------------------------------------------------------------


class APIFallbackMatrix:
    def __init__(self, browser: BrowserSession) -> None:
        self.browser = browser

    async def resolve(self, url: str) -> BypassResult:
        engines = (
            self._bypass_city_get,
            self._bypass_city_api,
            self._adbypasser,
            self._bypass_vip,
        )
        last_error = "API matrix exhausted."

        for engine in engines:
            try:
                result = await engine(url)
                if result.success and result.destination:
                    return result
                if result.error:
                    last_error = result.error
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                last_error = str(exc)
                logger.exception("API engine %s failed", engine.__name__)

        return BypassResult(original=url, success=False, engine="API matrix", error=last_error)

    @staticmethod
    def _parse_json_destination(data: Any) -> Optional[str]:
        if not isinstance(data, dict):
            return None
        keys = (
            "destination",
            "result",
            "url",
            "bypassed",
            "bypassed_url",
            "direct_link",
            "link",
            "final",
            "final_url",
            "target",
        )
        for key in keys:
            val = data.get(key)
            if isinstance(val, str) and val.startswith(("http://", "https://")):
                return val
        nested = data.get("data")
        if isinstance(nested, dict):
            return APIFallbackMatrix._parse_json_destination(nested)
        return None

    async def _read_json(self, status: int, body: str) -> Any:
        try:
            return json.loads(body)
        except Exception:
            return None

    async def _bypass_city_get(self, url: str) -> BypassResult:
        engine = "Bypass.city"
        api = f"https://bypass.city/bypass?bypass={quote(url, safe='')}"
        status, body, headers, final_url = await self.browser.request("GET", api, referer="https://bypass.city/")

        if status in {301, 302, 303, 307, 308}:
            loc = headers.get("Location") or headers.get("location")
            if loc and loc.startswith(("http://", "https://")) and loc.rstrip("/") != url.rstrip("/"):
                return BypassResult(original=url, success=True, destination=loc, engine=engine)

        data = await self._read_json(status, body)
        dest = self._parse_json_destination(data) or RedirectExtractor.from_body(body, api)
        if dest:
            dest = dest[0] if isinstance(dest, list) else dest
            if dest.rstrip("/") != url.rstrip("/"):
                return BypassResult(original=url, success=True, destination=dest, engine=engine)

        if final_url.rstrip("/") != api.rstrip("/") and final_url.rstrip("/") != url.rstrip("/"):
            return BypassResult(original=url, success=True, destination=final_url, engine=engine)

        return BypassResult(original=url, success=False, engine=engine, error=f"Bypass.city HTTP {status}")

    async def _bypass_city_api(self, url: str) -> BypassResult:
        engine = "Bypass.city API"
        api = "https://api2.bypass.city/bypass"
        profile = pick_profile()
        headers = build_browser_headers(api, profile, "https://bypass.city/")
        headers["Content-Type"] = "application/json"
        try:
            async with self.browser.session.post(
                api,
                headers=headers,
                json={"url": url},
                allow_redirects=False,
                timeout=ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                body = await resp.text(errors="ignore")
                status = resp.status
        except Exception as exc:
            return BypassResult(original=url, success=False, engine=engine, error=str(exc))

        data = await self._read_json(status, body)
        dest = self._parse_json_destination(data)
        if dest and dest.rstrip("/") != url.rstrip("/"):
            return BypassResult(original=url, success=True, destination=dest, engine=engine)
        return BypassResult(original=url, success=False, engine=engine, error=f"API HTTP {status}")

    async def _adbypasser(self, url: str) -> BypassResult:
        engine = "AdBypasser (adbypass.org)"
        api = f"https://adbypass.org/bypass?bypass={quote(url, safe='')}"
        status, body, headers, final_url = await self.browser.request("GET", api, referer="https://adbypass.org/")

        if status in {301, 302, 303, 307, 308}:
            loc = headers.get("Location") or headers.get("location")
   
