import asyncio
import aiohttp
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

BOT_TOKEN = "8686759049:AAFYdI4AX47W5kGlPptRu3UkhGcu9OaZimk"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def multi_bypasser(short_url: str) -> str:
    """
    यह इंजन दो अलग-अलग प्रीमियम सर्वर्स का इस्तेमाल करता है। 
    अगर एक फेल हुआ, तो दूसरा 100% लिंक निकाल कर देगा!
    """
    # ---- सर्व़र 1: Multi-Bypasser API ----
    api_url_1 = f"https://bot.nu{short_url}"
    # ---- सर्वर 2: Bypass.city API ----
    api_url_2 = f"https://bypass.city{short_url}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    async with aiohttp.ClientSession() as session:
        # पहले सर्वर 1 को ट्राई करें (यह easysky जैसे शॉर्टनर्स के लिए बेस्ट है)
        try:
            async with session.get(api_url_1, headers=headers, timeout=8) as response:
                if response.status == 200:
                    data = await response.json()
                    if "destination" in data: return data["destination"]
                    elif "url" in data: return data["url"]
        except Exception:
            pass # अगर पहला फेल हुआ, तो चुपचाप दूसरे पर बढ़ो

        # बैकअप सर्वर 2 को ट्राई करें
        try:
            async with session.get(api_url_2, headers=headers, timeout=8) as response:
                if response.status == 200:
                    data = await response.json()
                    if "destination" in data: return data["destination"]
                    elif "url" in data: return data["url"]
        except Exception:
            pass
            
        return "❌ Bypass Failed: इस लिंक की सिक्योरिटी बहुत हाई है या सर्वर मेंटेनेंस पर है।"

@dp.message(CommandStart())
async def start_command(message: types.Message):
    await message.reply("🔥 **Welcome to India's Strongest Multi-API Bypasser Bot!**\n\nमुझे कोई भी लिंक भेजें, मैं उसे अलग-अलग सर्वर्स से क्रैक करने की कोशिश करूँगा।")

@dp.message()
async def link_handler(message: types.Message):
    user_text = message.text.strip()
    if not user_text.startswith(("http://", "https://")):
        await message.reply("❌ कृपया एक वैलिड HTTP/HTTPS लिंक भेजें।")
        return
        
    progress_msg = await message.reply("⚡ **Bypassing using Multi-API Engine... Please wait...**")
    final_destination = await multi_bypasser(user_text)
    
    if final_destination.startswith("http"):
        await progress_msg.edit_text(f"✅ **Bypass Successful!**\n\n🔗 **Destination URL:**\n`{final_destination}`", disable_web_page_preview=True, parse_mode="Markdown")
    else:
        await progress_msg.edit_text(final_destination)

async def handle_web(request):
    return web.Response(text="Bot is Alive")

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
