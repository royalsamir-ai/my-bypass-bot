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
    Triple-API Power Engine: 
    3 अलग-अलग सर्वर्स की चेन। कोई न कोई एक तो लिंक निकाल कर देगा ही!
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    # ---- सर्वर 1: एडवांस्ड वर्कर एपीआई (भारतीय लिंक्स के लिए बेस्ट) ----
    api_url_1 = f"https://workers.dev{short_url}"
    # ---- सर्वर 2: Multi-Bypasser ----
    api_url_2 = f"https://bot.nu{short_url}"
    # ---- सर्वर 3: Bypass.city ----
    api_url_3 = f"https://bypass.city{short_url}"
    
    async with aiohttp.ClientSession() as session:
        # ट्राई सर्वर 1 (यह सबसे नया और एक्टिव है)
        try:
            async with session.get(api_url_1, headers=headers, timeout=8) as response:
                if response.status == 200:
                    data = await response.json()
                    # अगर रिस्पॉन्स में सीधे डेस्टिनेशन लिंक मिल जाए
                    if "destination" in data: return data["destination"]
                    elif "url" in data: return data["url"]
                    elif "bypassed_url" in data: return data["bypassed_url"]
        except Exception:
            pass

        # ट्राई सर्वर 2
        try:
            async with session.get(api_url_2, headers=headers, timeout=8) as response:
                if response.status == 200:
                    data = await response.json()
                    if "destination" in data: return data["destination"]
                    elif "url" in data: return data["url"]
        except Exception:
            pass

        # ट्राई सर्वर 3
        try:
            async with session.get(api_url_3, headers=headers, timeout=8) as response:
                if response.status == 200:
                    data = await response.json()
                    if "destination" in data: return data["destination"]
                    elif "url" in data: return data["url"]
        except Exception:
            pass
            
        return "❌ Bypass Failed: सभी सर्वर्स डाउन हैं या इस लिंक पर बहुत हाई कैप्चा सुरक्षा है।"

@dp.message(CommandStart())
async def start_command(message: types.Message):
    await message.reply("🔥 **Welcome to India's Strongest Multi-API Bypasser Bot!**\n\nमुझे कोई भी लिंक भेजें, मैं उसे 3 अलग-अलग प्रीमियम सर्वर्स से क्रैक कर दूँगा।")

@dp.message()
async def link_handler(message: types.Message):
    user_text = message.text.strip()
    if not user_text.startswith(("http://", "https://")):
        await message.reply("❌ कृपया एक वैलिड HTTP/HTTPS लिंक भेजें।")
        return
        
    progress_msg = await message.reply("⚡ **Bypassing using Triple-API Engine... Please wait...**")
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
