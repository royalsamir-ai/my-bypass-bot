import asyncio
import aiohttp
import os
import re
from urllib.parse import urlparse, parse_qs
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

BOT_TOKEN = "8686759049:AAFYdI4AX47W5kGlPptRu3UkhGcu9OaZimk"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def greasyfork_lksfy_bypass(short_url: str) -> str:
    """
    GreasyFork स्क्रिप्ट का पायथन रूपांतरण:
    यह सीधे URL से ID निकालता है और 'ab=1' कुकी का उपयोग करके फाइनल लिंक प्राप्त करता है।
    """
    try:
        parsed_url = urlparse(short_url)
        queries = parse_qs(parsed_url.query)
        
        # यूआरएल से 'id' पैरामीटर को निकालना
        link_id = queries.get("id", [None])[0]
        
        # अगर सीधे ID नहीं मिली, तो हो सकता है वह फाइनल रीडायरेक्ट यूआरएल ही हो
        if not link_id:
            if "lksfy.com" in short_url:
                link_id = parsed_url.path.strip("/")
            else:
                # यदि सामान्य यूआरएल है, तो पहले उसका वास्तविक ठिकाना जानने के लिए एक रिक्वेस्ट भेजें
                async with aiohttp.ClientSession() as session:
                    async with session.get(short_url, allow_redirects=True, timeout=5) as res:
                        queries = parse_qs(urlparse(str(res.url)).query)
                        link_id = queries.get("id", [None])[0]
        
        if not link_id:
            return "❌ Error: इस लिंक से 'id' नहीं निकाली जा सकी।"

        # GreasyFork के अनुसार lksfy.com का फाइनल टारगेट यूआरएल बनाना
        target_url = f"https://lksfy.com{link_id}"
        
        # स्क्रिप्ट की तरह बैकग्राउंड में 'ab=1' कुकी सेट करना ताकि एंटी-बॉट बाईपास हो सके
        cookies = {"ab": "1"}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": short_url
        }

        async with aiohttp.ClientSession(cookies=cookies) as session:
            async with session.get(target_url, headers=headers, timeout=8, allow_redirects=True) as response:
                # रीडायरेक्शन के बाद जो अंतिम यूआरएल मिलेगा, वही हमारा असली गंतव्य (Destination) है
                final_link = str(response.url)
                if "lksfy.com" not in final_link:
                    return final_link
                
                # यदि सीधे रीडायरेक्ट नहीं हुआ, तो पेज के कंटेंट में से फाइनल लिंक ढूंढना
                html_text = await response.text()
                match = re.search(r'window\.location\.replace\(["\'](https?://[^"\']+)["\']\)', html_text)
                if match:
                    return match.group(1)
                
                return f"✅ Target Page Reached: {final_link} (कृपया इसे ब्राउज़र में खोलें)"

    except Exception as e:
        return f"❌ Bypass Error: {str(e)}"

@dp.message(CommandStart())
async def start_command(message: types.Message):
    await message.reply("🔥 **Welcome to India's Smartest LKSFY Bypasser Bot!**\n\nमुझे easysky या कोई भी lksfy नेटवर्क का लिंक भेजें, मैं उसे तुरंत क्रैक कर दूँगा।")

@dp.message()
async def link_handler(message: types.Message):
    user_text = message.text.strip()
    if not user_text.startswith(("http://", "https://")):
        await message.reply("❌ कृपया एक वैलिड HTTP/HTTPS लिंक भेजें।")
        return
        
    progress_msg = await message.reply("⚡ **Extracting ID & Bypassing via Cookie Injection...**")
    final_destination = await greasyfork_lksfy_bypass(user_text)
    
    if final_destination.startswith("http"):
        await progress_msg.edit_text(f"✅ **Bypass Successful!**\n\n🔗 **Destination URL:**\n`{final_destination}`", disable_web_page_preview=True, parse_mode="Markdown")
    else:
        await progress_msg.edit_text(final_destination)

async def handle_web(request):
    return web.Response(text="Bot is Alive and Running!")

async def main():
    app = web.Application()
    app.router.add_get('/', handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"[SYSTEM] Dummy Server started on port {port}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
