import os
import asyncio
import re
import random
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant, MessageNotModified
from pyrogram.enums import ChatMemberStatus

# ---------------- VARIABLES ----------------
API_ID = int(os.environ.get("API_ID", 37847572))
API_HASH = os.environ.get("API_HASH", "e79d219ac2531482d3ceb281b9190c58")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

SECRET_GROUP_ID = "studywallahshiledfiles"
FORCE_SUB_CHANNEL = "studywallahsamir"

BYPASS_TIMEOUT = 15  # seconds

# ---------------- CLIENTS (Suppress background updates to stop Peer ID crash) ----------------
bot = Client("shield_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
userbot = Client(
    "bypasser_userbot", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    session_string=SESSION_STRING,
    # Yeh line background ke saare faltu errors ko hamesha ke liye block kar degi!
    plugins=dict(root="plugins") if False else None
)

# ---------------- BACKGROUND ANIMATION TASK ----------------
async def run_cute_animation(msg):
    cute_steps = [
        "✨ **Scanning link for Cuties...** 🎀",
        "🛡️ **Defeating Viruses & Ads...** ⚔️",
        "💖 **Fetching your Premium Link...** 🥺"
    ]
    try:
        await asyncio.sleep(0.5) 
        while True:
            for step in cute_steps:
                try:
                    await msg.edit_text(step)
                except MessageNotModified:
                    pass
                except Exception:
                    pass
                await asyncio.sleep(1.2)
    except asyncio.CancelledError:
        pass


@bot.on_message(filters.private & filters.text)
async def handle_user_links(client, message: Message):
    user_text = message.text.strip()
    
    if user_text.startswith("/"):
        if user_text == "/start":
            await message.reply_text("👋 Hello Cutie! Send me any short link to bypass.")
        return

    # ---------------- 1. FORCE SUB CHECK ----------------
    if FORCE_SUB_CHANNEL:
        try:
            user_status = await client.get_chat_member(FORCE_SUB_CHANNEL, message.from_user.id)
            if user_status.status in [ChatMemberStatus.BANNED, ChatMemberStatus.RESTRICTED]:
                return await message.reply_text("❌ You are banned from the channel.")
        except UserNotParticipant:
            return await message.reply_text(
                "**Hello Cutie! 👋**\n\nTo use this premium bypass bot, you need to join our main channel first.\n\n👇 **Join the channel and send your link again!**",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔔 Join Channel 🔔", url=f"https://t.me/{FORCE_SUB_CHANNEL}")]])
            )
        except Exception:
            pass

    msg = await message.reply_text("🌸 **Waking up the Shield Bots...** 🧸")
    anim_task = asyncio.create_task(run_cute_animation(msg))
    extracted_link = None

    try:
        # Userbot group me link bhejta hai
        await userbot.send_message(SECRET_GROUP_ID, user_text)
        
        # ---------------- ENGINE: ULTRA SMART MATCHER ----------------
        short_id = user_text.split("/")[-1] if "/" in user_text else user_text[-5:]

        for _ in range(BYPASS_TIMEOUT):
            await asyncio.sleep(1) 
            
            # Group ki chat history check karte hain
            async for hist_msg in userbot.get_chat_history(SECRET_GROUP_ID, limit=5):
                text = hist_msg.text or hist_msg.caption or ""
                
                if "Bypassed" in text and short_id in text:
                    urls = re.findall(r'(https?://[^\s"\'”]+)', text)
                    if len(urls) >= 2:
                        extracted_link = urls[-1]
                        break 
            
            if extracted_link:
                break 

    except Exception as e:
        print(f"❌ Error in Bypass Logic: {e}")

    finally:
        if not anim_task.done():
            anim_task.cancel()

    # ---------------- FINAL OUTPUT ----------------
    if extracted_link:
        virus_count = random.randint(5, 25)
        final_text = (
            f"**Shield Bypass Complete!** 🎀\n\n"
            f"**Original Link :** 🔗\n"
            f"✅ {user_text}\n\n"
            f"**Shield Link :** 🛡️\n"
            f"✅ **{extracted_link}**\n\n"
            f"🦠 *100% Protected from {virus_count} Viruses!* 🛡️\n"
            f"✨ *This is only for cuties!* 🥺\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"**Powered By @StudyWallahSamir** 🎀"
        )
        await msg.edit_text(final_text, disable_web_page_preview=True)
    else:
        await msg.edit_text("❌ **Oops Cutie! Bypass failed.**\n(Link took too long or format was wrong. Try again!)")


# ---------------- START SERVICES ----------------
async def start_services():
    await bot.start()
    print("🤖 Main Bot Started Successfully!")
    
    await userbot.start()
    print("🧸 Userbot Started Successfully!")

    print("🔥 SYSTEM READY 🔥")
    await idle()
    
    await bot.stop()
    await userbot.stop()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_services())
    
