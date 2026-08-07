"""
Telegram Link Bypasser Bot
Primary engine : Bypass.city
Backup engines : adbypass.org mirror, Bypass.vip API, direct redirect resolver
Render-ready   : aiohttp health server on PORT (default 10000)
"""

from __future__ import annotations

import asyncio
import html
import logging
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import quote, urlparse

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
PORT = int(os.environ.get("PORT", "10000"))
MAX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT", "5"))
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "45"))

USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/132.0.0.0 Mobile Safari/537.36"
)

URL_REGEX = re.compile(
    r"(?i)\b("
    r"https?://[^\s<>\"']+"
    r"|"
    r"(?:linkvertise\.com|work\.ink|loot-link\.com|loot-links\.com|"
    r"lootdest\.(?:info|org|com)|boost\.ink|mboost\.me|rekonise\.com|"
    r"sub2unlock\.(?:com|net)|adfoc\.us|adf\.ly|cuty\.io|cety\.io|"
    r"socialwolvez\.com|paster\.so|paste-drop\.com|bit\.ly|tinyurl\.com|"
    r"is\.gd|t\.co|v\.gd|ouo\.io|sh\.st|shorte\.st)/[^\s<>\"']+"
    r")"
)

TRAILING_PUNCT = re.compile(r"[)\].,;:!?]+$")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("bypass-bot")

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class BypassResult:
    original: str
    success: bool
    destination: Optional[str] = None
    engine: str = "unknown"
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------


def normalize_url(raw: str) -> str:
    cleaned = TRAILING_PUNCT.sub("", raw.strip())
    if not cleaned.lower().startswith(("http://", "https://")):
        cleaned = "https://" + cleaned
    return cleaned


def extract_urls(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    for match in URL_REGEX.finditer(text or ""):
        url = normalize_url(match.group(1))
        key = url.rstrip("/").lower()
        if key not in seen:
            seen.add(key)
            found.append(url)

    return found


def is_valid_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def shorten_for_display(url: str, limit: int = 72) -> str:
    if len(url) <= limit:
        return url
    return url[: limit - 3] + "..."


def result_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Open Direct Link", url=url)],
            [InlineKeyboardButton(text="Copy-friendly", callback_data="noop")],
        ]
    )


# ---------------------------------------------------------------------------
# Bypass engines
# ---------------------------------------------------------------------------


class BypassService:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self.session = session

    async def bypass(self, url: str) -> BypassResult:
        engines = (
            self._bypass_city_get,
            self._bypass_city_api,
            self._adbypass_mirror,
            self._bypass_vip,
            self._direct_redirect,
        )

        last_error = "All bypass engines failed."

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
                logger.exception("Engine %s crashed for %s", engine.__name__, url)

        return BypassResult(
            original=url,
            success=False,
            engine="none",
            error=last_error,
        )

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[dict[str, str]] = None,
        json_payload: Optional[dict[str, Any]] = None,
        allow_redirects: bool = False,
    ) -> aiohttp.ClientResponse:
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        default_headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
        }
        if headers:
            default_headers.update(headers)

        return await self.session.request(
            method,
            url,
            headers=default_headers,
            json=json_payload,
            allow_redirects=allow_redirects,
            timeout=timeout,
        )

    @staticmethod
    def _extract_destination_from_json(data: Any) -> Optional[str]:
        if not isinstance(data, dict):
            return None

        candidate_keys = (
            "destination",
            "result",
            "url",
            "bypassed",
            "bypassed_url",
            "direct_link",
            "link",
            "final",
            "final_url",
        )

        for key in candidate_keys:
            value = data.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                return value

        nested = data.get("data")
        if isinstance(nested, dict):
            return BypassService._extract_destination_from_json(nested)

        return None

    @staticmethod
    def _extract_from_html(text: str) -> Optional[str]:
        patterns = (
            r'"destination"\s*:\s*"([^"]+)"',
            r'"result"\s*:\s*"([^"]+)"',
            r'href="(https?://[^"]+)"[^>]*>\s*Continue',
            r'window\.location(?:\.href)?\s*=\s*[\'"](https?://[^\'"]+)[\'"]',
        )
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).replace("\\/", "/")
        return None

    async def _read_json_safe(self, response: aiohttp.ClientResponse) -> Any:
        try:
            return await response.json(content_type=None)
        except Exception:
            return None

    async def _bypass_city_get(self, url: str) -> BypassResult:
        engine = "Bypass.city (GET)"
        api_url = f"https://bypass.city/bypass?bypass={quote(url, safe='')}"

        try:
            async with await self._request("GET", api_url, allow_redirects=False) as resp:
                if resp.status in {301, 302, 303, 307, 308}:
                    location = resp.headers.get("Location")
                    if location and location.startswith(("http://", "https://")):
                        if location.rstrip("/") != url.rstrip("/"):
                            return BypassResult(
                                original=url,
                                success=True,
                                destination=location,
                                engine=engine,
                            )

                body = await resp.text(errors="ignore")
                data = await self._read_json_safe(resp)
                destination = self._extract_destination_from_json(data) or self._extract_from_html(body)

                if destination and destination.rstrip("/") != url.rstrip("/"):
                    return BypassResult(
                        original=url,
                        success=True,
                        destination=destination,
                        engine=engine,
                    )

                return BypassResult(
                    original=url,
                    success=False,
                    engine=engine,
                    error=f"Bypass.city GET returned no destination (HTTP {resp.status}).",
                )
        except Exception as exc:
            return BypassResult(original=url, success=False, engine=engine, error=str(exc))

    async def _bypass_city_api(self, url: str) -> BypassResult:
        engine = "Bypass.city (API)"
        headers = {
            "Content-Type": "application/json",
            "Origin": "https://bypass.city",
            "Referer": "https://bypass.city/",
        }

        try:
            async with await self._request(
                "POST",
                "https://api2.bypass.city/bypass",
                headers=headers,
                json_payload={"url": url},
                allow_redirects=False,
            ) as resp:
                data = await self._read_json_safe(resp)
                destination = self._extract_destination_from_json(data)

                if destination and destination.rstrip("/") != url.rstrip("/"):
                    return BypassResult(
                        original=url,
                        success=True,
                        destination=destination,
                        engine=engine,
                    )

                if resp.status >= 400:
                    return BypassResult(
                        original=url,
                        success=False,
                        engine=engine,
                        error=f"Bypass.city API HTTP {resp.status}.",
                    )

                return BypassResult(
                    original=url,
                    success=False,
                    engine=engine,
                    error="Bypass.city API returned no destination.",
                )
        except Exception as exc:
            return BypassResult(original=url, success=False, engine=engine, error=str(exc))

    async def _adbypass_mirror(self, url: str) -> BypassResult:
        engine = "adbypass.org (mirror)"
        api_url = f"https://adbypass.org/bypass?bypass={quote(url, safe='')}"

        try:
            async with await self._request("GET", api_url, allow_redirects=False) as resp:
                if resp.status in {301, 302, 303, 307, 308}:
                    location = resp.headers.get("Location")
                    if location and location.startswith(("http://", "https://")):
                        if location.rstrip("/") != url.rstrip("/"):
                            return BypassResult(
                                original=url,
                                success=True,
                                destination=location,
                                engine=engine,
                            )

                data = await self._read_json_safe(resp)
                destination = self._extract_destination_from_json(data)

                if not destination:
                    body = await resp.text(errors="ignore")
                    destination = self._extract_from_html(body)

                if destination and destination.rstrip("/") != url.rstrip("/"):
                    return BypassResult(
                        original=url,
                        success=True,
                        destination=destination,
                        engine=engine,
                    )

                return BypassResult(
                    original=url,
                    success=False,
                    engine=engine,
                    error=f"adbypass.org mirror failed (HTTP {resp.status}).",
                )
        except Exception as exc:
            return BypassResult(original=url, success=False, engine=engine, error=str(exc))

    async def _bypass_vip(self, url: str) -> BypassResult:
        engine = "Bypass.vip API"
        api_url = f"https://api.bypass.vip/bypass?url={quote(url, safe='')}"

        try:
            async with await self._request("GET", api_url, allow_redirects=False) as resp:
                data = await self._read_json_safe(resp)

                if isinstance(data, dict):
                    if data.get("status") == "success":
                        destination = data.get("result")
                        if isinstance(destination, str) and destination.startswith(("http://", "https://")):
                            return BypassResult(
                                original=url,
                                success=True,
                                destination=destination,
                                engine=engine,
                            )

                    message = data.get("message")
                    if isinstance(message, str):
                        return BypassResult(
                            original=url,
                            success=False,
                            engine=engine,
                            error=message,
                        )

                return BypassResult(
                    original=url,
                    success=False,
                    engine=engine,
                    error=f"Bypass.vip failed (HTTP {resp.status}).",
                )
        except Exception as exc:
            return BypassResult(original=url, success=False, engine=engine, error=str(exc))

    async def _direct_redirect(self, url: str) -> BypassResult:
        engine = "Direct redirect resolver"

        try:
            async with await self._request("GET", url, allow_redirects=True) as resp:
                final_url = str(resp.url)
                if final_url.rstrip("/") != url.rstrip("/"):
                    return BypassResult(
                        original=url,
                        success=True,
                        destination=final_url,
                        engine=engine,
                    )

                return BypassResult(
                    original=url,
                    success=False,
                    engine=engine,
                    error="Direct resolver could not reach a different destination.",
                )
        except Exception as exc:
            return BypassResult(original=url, success=False, engine=engine, error=str(exc))


# ---------------------------------------------------------------------------
# Bot setup
# ---------------------------------------------------------------------------

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

dp = Dispatcher()

http_session: Optional[aiohttp.ClientSession] = None
bypass_service: Optional[BypassService] = None
bypass_semaphore = asyncio.Semaphore(MAX_CONCURRENT)


# ---------------------------------------------------------------------------
# Message builders
# ---------------------------------------------------------------------------


def welcome_text() -> str:
    return (
        "<b>Link Bypasser Bot</b>\n\n"
        "Send me one or many short/ad links — even inside long messages with "
        "movie names, emojis, or random text.\n\n"
        "<b>Examples</b>\n"
        "• Single link\n"
        "• Multiple links in one message\n"
        "• Mixed text + links\n\n"
        "<b>Supported</b>\n"
        "Linkvertise, Work.ink, Lootlinks, Boost.ink, Sub2Unlock, AdFoc.us, "
        "paste sites, and many more.\n\n"
        "Just paste your links and I will bypass them automatically."
    )


def help_text() -> str:
    return (
        "<b>How to use</b>\n\n"
        "1. Paste any supported short link.\n"
        "2. Or paste a long message — I auto-detect all links.\n"
        "3. Wait a few seconds while I bypass them.\n"
        "4. Tap <b>Open Direct Link</b> to open the result.\n\n"
        "<b>Commands</b>\n"
        "/start — Welcome message\n"
        "/help — This help message\n\n"
        "<i>Tip: You can send 10+ links in one message.</i>"
    )


def progress_text(done: int, total: int) -> str:
    bar_len = 10
    filled = int((done / total) * bar_len) if total else 0
    bar = "█" * filled + "░" * (bar_len - filled)
    percent = int((done / total) * 100) if total else 0

    return (
        "<b>Processing your links...</b>\n\n"
        f"Progress: <code>{done}/{total}</code>\n"
        f"<code>[{bar}] {percent}%</code>\n\n"
        "<i>Please wait, bypassing concurrently...</i>"
    )


def format_single_result(result: BypassResult) -> str:
    original = html.escape(shorten_for_display(result.original))
    if result.success and result.destination:
        destination = html.escape(shorten_for_display(result.destination))
        return (
            "<b>Bypass Successful</b>\n\n"
            f"<b>Original</b>\n<code>{original}</code>\n\n"
            f"<b>Direct Link</b>\n<code>{destination}</code>\n\n"
            f"<b>Engine</b>: <i>{html.escape(result.engine)}</i>"
        )

    error = html.escape(result.error or "Unknown error")
    return (
        "<b>Bypass Failed</b>\n\n"
        f"<b>Original</b>\n<code>{original}</code>\n\n"
        f"<b>Reason</b>: <i>{error}</i>"
    )


def format_bulk_results(results: list[BypassResult]) -> list[str]:
    chunks: list[str] = []
    current = "<b>Bulk Bypass Results</b>\n\n"
    success_count = sum(1 for r in results if r.success)
    current += f"<b>Summary</b>: {success_count}/{len(results)} successful\n\n"

    for index, result in enumerate(results, start=1):
        original = html.escape(shorten_for_display(result.original, 60))

        if result.success and result.destination:
            destination = html.escape(shorten_for_display(result.destination, 60))
            block = (
                f"<b>{index}.</b> Success\n"
                f"• Original: <code>{original}</code>\n"
                f"• Direct: <code>{destination}</code>\n"
                f"• Engine: <i>{html.escape(result.engine)}</i>\n\n"
            )
        else:
            error = html.escape(shorten_for_display(result.error or "Failed", 80))
            block = (
                f"<b>{index}.</b> Failed\n"
                f"• Original: <code>{original}</code>\n"
                f"• Reason: <i>{error}</i>\n\n"
            )

        if len(current) + len(block) > 3800:
            chunks.append(current.rstrip())
            current = block
        else:
            current += block

    if current.strip():
        chunks.append(current.rstrip())

    return chunks or ["<b>No results to display.</b>"]


async def safe_edit(message: Message, text: str, **kwargs: Any) -> None:
    try:
        await message.edit_text(text, **kwargs)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            logger.warning("Could not edit message: %s", exc)
    except Exception as exc:
        logger.warning("Edit failed: %s", exc)


async def bypass_one(url: str) -> BypassResult:
    if not bypass_service:
        return BypassResult(
            original=url,
            success=False,
            engine="none",
            error="Bypass service is not initialized.",
        )

    if not is_valid_http_url(url):
        return BypassResult(
            original=url,
            success=False,
            engine="validator",
            error="Invalid URL format.",
        )

    async with bypass_semaphore:
        try:
            return await bypass_service.bypass(url)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Unexpected bypass failure for %s", url)
            return BypassResult(
                original=url,
                success=False,
                engine="none",
                error=str(exc),
            )


async def bypass_many(urls: list[str], progress_message: Message) -> list[BypassResult]:
    total = len(urls)
    completed = 0
    results: list[Optional[BypassResult]] = [None] * total
    lock = asyncio.Lock()

    async def worker(index: int, url: str) -> None:
        nonlocal completed
        result = await bypass_one(url)

        async with lock:
            results[index] = result
            completed += 1
            await safe_edit(progress_message, progress_text(completed, total))

    await asyncio.gather(*(worker(i, url) for i, url in enumerate(urls)))
    return [r for r in results if r is not None]


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    try:
        await message.answer(welcome_text())
    except Exception as exc:
        logger.exception(" /start failed: %s", exc)


@dp.message(Command("help"))
async def cmd_help(message: Message) -> None:
    try:
        await message.answer(help_text())
    except Exception as exc:
        logger.exception("/help failed: %s", exc)


@dp.callback_query(F.data == "noop")
async def noop_callback(callback) -> None:
    try:
        await callback.answer("Use the Open Direct Link button above.", show_alert=False)
    except Exception:
        pass


@dp.message(F.text)
async def handle_text(message: Message) -> None:
    progress_message: Optional[Message] = None

    try:
        urls = extract_urls(message.text or "")
        if not urls:
            await message.answer(
                "<b>No links detected</b>\n\n"
                "Please send a valid short link.\n"
                "Example:\n"
                "<code>https://linkvertise.com/12345/example</code>"
            )
            return

        progress_message = await message.answer(progress_text(0, len(urls)))

        results = await bypass_many(urls, progress_message)

        if len(results) == 1:
            result = results[0]
            reply_markup = None
            if result.success and result.destination:
                reply_markup = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="Open Direct Link", url=result.destination)]
                    ]
                )

            await safe_edit(
                progress_message,
                format_single_result(result),
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
            return

        chunks = format_bulk_results(results)
        await safe_edit(
            progress_message,
            chunks[0],
            disable_web_page_preview=True,
        )

        for chunk in chunks[1:]:
            await message.answer(chunk, disable_web_page_preview=True)

        for result in results:
            if result.success and result.destination:
                await message.answer(
                    f"<b>Direct link</b>\n<code>{html.escape(result.destination)}</code>",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="Open Direct Link", url=result.destination)]
                        ]
                    ),
                    disable_web_page_preview=True,
                )

    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception("Text handler crashed: %s", exc)
        fallback = (
            "<b>Something went wrong</b>\n\n"
            "The bot is still running. Please try again in a few seconds."
        )
        try:
            if progress_message:
                await safe_edit(progress_message, fallback)
            else:
                await message.answer(fallback)
        except Exception:
            pass


@dp.errors()
async def global_error_handler(event) -> bool:
    logger.exception("Unhandled dispatcher error: %s", event.exception)
    return True


# ---------------------------------------------------------------------------
# Render health server
# ---------------------------------------------------------------------------


async def health_handler(_: web.Request) -> web.Response:
    return web.json_response(
        {
            "status": "ok",
            "service": "telegram-bypass-bot",
            "bot_token_loaded": bool(BOT_TOKEN),
        }
    )


async def start_web_server() -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/", health_handler)
    app.router.add_get("/health", health_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()

    logger.info("Health server listening on 0.0.0.0:%s", PORT)
    return runner


async def on_startup() -> None:
    global http_session, bypass_service

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing.")

    http_session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
        headers={"User-Agent": USER_AGENT},
    )
    bypass_service = BypassService(http_session)
    logger.info("Bot startup complete.")


async def on_shutdown() -> None:
    global http_session, bypass_service

    bypass_service = None
    if http_session and not http_session.closed:
        await http_session.close()
    http_session = None
    logger.info("Bot shutdown complete.")


async def main() -> None:
    web_runner: Optional[web.AppRunner] = None

    try:
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)

        web_runner = await start_web_server()

        logger.info("Starting Telegram polling...")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            handle_signals=True,
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception("Fatal error in main(): %s", exc)
    finally:
        try:
            if web_runner is not None:
                await web_runner.cleanup()
        except Exception as exc:
            logger.warning("Web runner cleanup failed: %s", exc)

        try:
            await bot.session.close()
        except Exception as exc:
            logger.warning("Bot session close failed: %s", exc)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped by user.")
