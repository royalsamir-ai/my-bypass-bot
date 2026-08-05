import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

BOT_TOKEN = "8686759049:AAFYdI4AX47W5kGlPptRu3UkhGcu9OaZimk"


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def greasyfork_secret_bypass(short_url: str) -> str:
    """
    Greasy Fork की स्क्रिप्ट से चुराया हुआ प्रीमियम API इंजन।
    यह क्लाउडफ्लेयर, कैप्चा और एड्स को 0.5 सेकंड में बायपास करता है।
    """
    # Greasy Fork स्क्रिप्ट का हिडन बैकएंड API एंडपॉइंट
    api_url = f"https://bypass.city{short_url}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # API अलग-अलग नाम से लिंक देता है, हम सब चेक करेंगे
                    if "destination" in data:
                        return data["destination"]
                    elif "url" in data:
                        return data["url"]
                    elif "target" in data:
                        return data["target"]
                    
                return "❌ Bypass Failed: Shortner security is too high or link is broken."
        except Exception as e:
            return f"❌ Error connecting to Bypass Server: {str(e)}"

# --- टेलीग्राम बॉट कमांड्स ---
@dp.message(CommandStart())
async def start_command(message: types.Message):
    await message.reply(
        "🔥 **Welcome to the Super-Fast Link Bypasser Bot!**\n\n"
        "मुझे कोई भी प्रोटेक्टेड शॉर्टनर लिंक भेजें, मैं उसे **1 सेकंड** में क्रैक कर दूँगा।"
    )

@dp.message()
async def link_handler(message: types.Message):
    user_text = message.text.strip()
    
    if not user_text.startswith(("http://", "https://")):
        await message.reply("❌ कृपया एक वैलिड HTTP/HTTPS लिंक भेजें।")
        return

    progress_msg = await message.reply("⚡ **Bypassing with GreasyFork Engine... Please wait...**")
    
    # बाईपास इंजन को रन करना
    final_destination = await greasyfork_secret_bypass(user_text)
    
    if final_destination.startswith("http"):
        # विज्ञापन रहित साफ-सुथरा मैसेज डिलीवर करना
        await progress_msg.edit_text(
            f"✅ **Bypass Successful!**\n\n"
            f"🔗 **Original Destination:**\n`{final_destination}`",
            disable_web_page_preview=True,
            parse_mode="Markdown"
        )
    else:
        await progress_msg.edit_text(final_destination)

async def main():
    print("[SYSTEM] Bot is successfully running with GreasyFork Engine...")
    await dp.start_polling(bot)

async def dummy_server():
    # रेंडर (Render) को खुश रखने के लिए बैकग्राउंड में एक छोटा सा वेब पोर्ट चालू करना
    import os
    from aiohttp import web
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is Alive"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"[SYSTEM] Dummy server started on port {port}")

async def start_all():
    # दोनों काम एक साथ चलेंगे: डमी सर्वर भी और टेलीग्राम बोट भी
    await dummy_server()
    await main()

if __name__ == "__main__":
    asyncio.run(start_all())


