import asyncio
import os
import re
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
import aiohttp

# Logs Setup
logging.basicConfig(level=logging.INFO)

# Token setup directly from Render Environment
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# Extra premium bypass domains for Indian shortners
PREMIUM_BYPASS_API = "https://bypass.vip"
BACKUP_BYPASS_API = "https://bypass.city"

async def advanced_bypasser(url: str) -> str:
    """
    🔥 100X Premium Hybrid Bypass Engine
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with aiohttp.ClientSession() as session:
        # Layer 1: Universal Premium API (Handles Arolinks, GPLinks etc)
        try:
            async with session.get(f"{PREMIUM_BYPASS_API}{url}", headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Check common json keys
                    for key in ["destination", "url", "bypassed", "direct"]:
                        if key in data and data[key].startswith("http"):
                            return data[key]
                    if "result" in data and str(data["result"]).startswith("http"):
                        return data["result"]
        except Exception:
            pass

        # Layer 2: Bypass.city Advanced Fallback
        try:
            async with session.get(f"{BACKUP_BYPASS_API}{url}", headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "destination" in data:
                        return data["destination"]
        except Exception:
            pass
            
        # Layer 3: Direct Scraper Request
        try:
            async with session.get(url, headers=headers, allow_redirects=True, timeout=10) as resp:
                final_url = str(resp.url)
                if final_url != url and "arolinks" not in final_url:
                    return final_url
        except Exception:
            pass

        return None

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.reply("⚡ **Welcome to India's Most Powerful 100X Bypasser Bot!**\n\nमुझे कोई भी कड़क लिंक (जैसे Arolinks, GPLinks) या बल्क मैसेज भेजें, मैं उसे तुरंत क्रैक कर दूंगा।")

@dp.message()
async def msg_handler(message: types.Message):
    text = message.text.strip()
    
    # Extract all links using regex
    urls = re.findall(r'(https?://[^\s]+)', text)
    
    if not urls:
        await message.reply("❌ कृपया एक वैध लिंक भेजें।")
        return

    progress = await message.reply("⏳ **Bypassing Link(s) with 100X Hybrid Engine... Please wait...**")
    
    results = []
    for url in urls:
        # Normalize trailing signs
        clean_url = url.rstrip("),].;!?")
        res = await advanced_bypasser(clean_url)
        if res:
            results.append(f"✅ **Success:**\n🔗 {res}")
        else:
            results.append(f"❌ **Failed:** `{clean_url}` (यह लिंक बहुत सुरक्षित है)")

    final_text = "\n\n====================\n\n".join(results)
    await progress.edit_text(final_text, disable_web_page_preview=True)

async def handle_web(request):
    return web.Response(text="Bot is Running Flawlessly")

async def main():
    app = web.Application()
    app.router.add_get('/', handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
