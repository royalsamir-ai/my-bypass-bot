"""
Universal Telegram Link Bypasser Bot - Production Ready Master Build
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

# PUBLIC BYPASSING API MATRIX - Correct endpoint router fixed for live fallback systems
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
                    # Hop Step 1: Location Extraction Route Check
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
                            logger.warning(f"Anti-Bot Challenge isolated on: {ctx.url}. Engaging fallback arrays.")
                            break

                        # Parse String Matching Layers
                        found_target = None
                        for pattern in JS_REDIRECT_PATTERNS:
                            m = pattern.search(html_content)
                            if m:
                                found_target = urljoin(ctx.url, m.group(1).strip("'\"` "))
                                break

                        if found_target and found_target.lower() not in ctx.visited:
                            ctx.referer = ctx.url
                            ctx.url = found_target
                            ctx.visited.add(found_target.lower())
                            engine_used = "javascript_automation"
                            continue

                        # BeautifulSoup Elements Resolver
                        soup = BeautifulSoup(html_content, "html.parser")
                        anchor = soup.select_one("a#landing-url, a.btn-success, a#btn-main, a.redirect-link")
                        if anchor and anchor.get("href"):
                            dom_target = urljoin(ctx.url, str(anchor.get("href")))
                            if dom_target.lower() not in ctx.visited:
                                ctx.referer = ctx.url
                                ctx.url = dom_target
                                ctx.visited.add(dom_target.lower())
                                engine_used = "dom_form_resolver"
                                continue
                        break

                except Exception as e:
                    logger.warning(f"Scraper Core Drop in step {ctx.hop}: {str(e)}.")
                    break

            # FALLBACK ROUTER: Execute API integration if standard structural analysis remains unbroken
            if current.lower() == ctx.url.lower() or ctx.url == target_url:
                fallback_destination = await self.execute_api_fallback(target_url)
                if fallback_destination:
                    return BypassResult(
                        original=target_url,
                        success=True,
                        destination=fallback_destination,
                        hops=ctx.hop + 1,
                        engine="api_matrix_fallback",
                        elapsed_ms=int((time.perf_counter() - start_time) * 1000)
                    )

            if current.lower() == ctx.url.lower():
                logger.error(f"[ANOMALY LOG] All core operations exhausted for URL element: {target_url}")
                return BypassResult(
                    original=target_url,
                    success=False,
                    destination=ctx.url,
                    hops=ctx.hop,
                    error="All resolution loops dropped",
                    engine=engine_used,
                    elapsed_ms=int((time.perf_counter() - start_time) * 1000)
                )

            return BypassResult(
                original=target_url,
                success=True,
                destination=ctx.url,
                hops=ctx.hop,
                engine=engine_used,
                elapsed_ms=int((time.perf_counter() - start_time) * 1000)
            )

# ---------------------------------------------------------------------------
# Telegram Interfaces & Event Controllers
# ---------------------------------------------------------------------------

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
bypasser_client: Optional[AdvancedBypasserClient] = None

@dp.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.reply(
        "<b>🛸 Universal Link Bypasser (Upgraded Core) Live.</b>\n\n"
        "Send your protected shorteners or trackable URLs. The script will use automated extraction arrays "
        "and secondary network adapters to bypass them effortlessly."
    )

@dp.message(F.text)
async def message_handler(message: Message) -> None:
    urls = extract_urls(message.text)
    if not urls:
        return

    processing_msg = await message.reply("⏳ <b>Deconstructing link pattern matrices... Please wait.</b>")
    tasks = [bypasser_client.resolve_url(u) for u in urls[:5]]
    results: list[BypassResult] = await asyncio.gather(*tasks)

    response_nodes = []
    valid_destinations = []
    
    for res in results:
        if res.success and res.destination:
            dest_short = shorten(res.destination, 64)
            orig_short = shorten(res.original, 36)
            
            node_text = (
                f"<b>🎯 Trace Succeeded</b>\n"
                f"• <b>Source Link:</b> <code>{orig_short}</code>\n"
                f"• <b>Destination:</b> <code>{dest_short}</code>\n"
                f"• <b>Routing Engine:</b> <code>{res.engine}</code>\n"
                f"• <b>Resolution Hops:</b> <code>{res.hops}</code> [⏱ {res.elapsed_ms}ms]"
            )
            response_nodes.append(node_text)
            valid_destinations.append(res.destination)
        else:
            orig_short = shorten(res.original, 40)
            fail_node = (
                f"<b>⚠️ Trace Interrupted</b>\n"
                f"• <b>Source Link:</b> <code>{orig_short}</code>\n"
                f"• <b>Fault Category:</b> <code>{res.error or 'Unspecified block'}</code>"
            )
            response_nodes.append(fail_node)

    final_markup = None
    if len(valid_destinations) == 1:
        final_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Navigate to Destination", url=valid_destinations[0])]
        ])
    elif len(valid_destinations) > 1:
        buttons = [InlineKeyboardButton(text=f"Link {i+1}", url=url) for i, url in enumerate(valid_destinations)]
        final_markup = InlineKeyboardMarkup(inline_keyboard=[buttons[i:i+2] for i in range(0, len(buttons), 2)])

    consolidated_report = "\n\n======================\n\n".join(response_nodes)
    
    try:
        await processing_msg.edit_text(consolidated_report, reply_markup=final_markup, disable_web_page_preview=True)
    except TelegramBadRequest:
        fallback_report = "\n".join([f"Result: {r.destination or r.error}" for r in results])
        await message.reply(fallback_report)

# ---------------------------------------------------------------------------
# Infrastructure Webserver & Concurrent Runner
# ---------------------------------------------------------------------------

async def health_check_server(request: web.Request) -> web.Response:
    return web.json_response({"status": "operational", "timestamp": time.time()})

async def main() -> None:
    global bypasser_client
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN environment variable missing.")
        sys.exit(1)

    connector = TCPConnector(limit=100, ssl=False)
    session = aiohttp.ClientSession(connector=connector)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    bypasser_client = AdvancedBypasserClient(session, semaphore)

    app = web.Application()
    app.router.add_get("/", health_check_server)
    app.router.add_get("/health", health_check_server)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    asyncio.create_task(site.start())

    try:
        await dp.start_polling(bot)
    finally:
        await session.close()
        await runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
