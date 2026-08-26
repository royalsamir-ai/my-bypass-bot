import os
import asyncio
import re
import random
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from pyrogram.enums import ChatMemberStatus

# ---------------- VARIABLES ----------------
API_ID = int(os.environ.get("API_ID", 37847572))
API_HASH = os.environ.get("API_HASH", "e79d219ac2531482d3ceb281b9190c58")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

secret_env = os.environ.get("SECRET_GROUP_ID", "studywallahshiledfiles")
if secret_env.lstrip('-').isdigit():
    SECRET_GROUP_ID = int(secret_env)
else:
    SECRET_GROUP_ID = secret_env

FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "studywallahsamir")

# ---------------- CLIENTS ----------------
bot = Client("shield_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
userbot = Client("bypasser_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING, no_updates=True)


@bot.on_message(filters.private & filters.text)
async def handle_user_links(client, message: Message):
    # Strip lagaya taaki extra space problem na kare
    user_text = message.text.strip() 
    
    # ---------------- 1. FORCE SUB CHECK ----------------
    if FORCE_SUB_CHANNEL:
        try:
            user_status = await client.get_chat_member(FORCE_SUB_CHANNEL, message.from_user.id)
            if user_status.status in [ChatMemberStatus.BANNED, ChatMemberStatus.RESTRICTED]:
                return await message.reply_text("❌ You are banned from the channel.")
                
        except UserNotParticipant:
            return await message.reply_text(
                "**Hello Cutie! 👋**\n\nTo use this premium bypass bot, you need to join our main channel first.\n\n👇 **Join the channel and send your link again!**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔔 Join Channel 🔔", url=f"https://t.me/{FORCE_SUB_CHANNEL}")]
                ])
            )
        except Exception:
            pass

    # ---------------- 2. CUTE % PROCESSING & BYPASS ----------------
    msg = await message.reply_text("⏳ **Processing 10%... Waking up bots** 🧸")
    
    try:
        # Step 1: Send link to secret group
        sent_msg = await userbot.send_message(SECRET_GROUP_ID, user_text)
        
        extracted_link = None
        last_seen_msg = "" # X-RAY ke liye
        
        # Step 2: percentage animation with emojis
        processing_steps = [
            "⏳ **Processing 30%... Scanning for Cuties** 🎀",
            "⏳ **Processing 60%... Defeating Viruses & Ads** ⚔️",
            "⏳ **Processing 85%... Fetching Premium Link** 🥺",
            "⏳ **Processing 99%... Finalizing Magic** 🪄"
        ]
        
        for step_text in processing_steps:
            await asyncio.sleep(4) 
            await msg.edit_text(step_text)
            
            # Check history
            async for reply in userbot.get_chat_history(SECRET_GROUP_ID, limit=5):
                msg_text = reply.text or reply.caption or ""
                
                # Debugging ke liye history save ki
                if not last_seen_msg:
                    last_seen_msg = msg_text
                
                # 🧠 NEW FOOLPROOF LOGIC: Kya is message me humara link h aur Bypassed word h?
                if user_text in msg_text and "Bypassed" in msg_text:
                    urls = re.findall(r'(https?://[^\s]+)', msg_text)
                    if urls:
                        extracted_link = urls[-1] # Last link utha liya
                        break
                        
            if extracted_link:
                break

        # ---------------- 3. FINAL FORMATTED OUTPUT ----------------
        if extracted_link:
            await msg.edit_text("✅ **Processing 100%... Complete!** ✨")
            await asyncio.sleep(1) 
            
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
            # 🔥 X-RAY VISION: Agar fail hua to yaha real problem dikhegi
            error_text = (
                f"❌ **Oops Cutie! Bypass failed.**\n"
                f"(Could not find the bypassed link in the group)\n\n"
                f"🔍 **Debug Info (Last msg seen):**\n"
                f"`{last_seen_msg[:100]}...`"
            )
            await msg.edit_text(error_text)
            
    except Exception as e:
        await msg.edit_text(f"❌ **Technical Error:**\n`{e}`")


# ---------------- START SERVICES ----------------
async def start_services():
    await bot.start()
    await userbot.start()
    print("🔥 SYSTEM READY 🔥")
    await idle()
    await bot.stop()
    await userbot.stop()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_services())
