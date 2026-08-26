import os
import asyncio
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
    user_text = message.text
    
    # ---------------- 1. FORCE SUB CHECK ----------------
    if FORCE_SUB_CHANNEL:
        try:
            user_status = await client.get_chat_member(FORCE_SUB_CHANNEL, message.from_user.id)
            if user_status.status in [ChatMemberStatus.BANNED, ChatMemberStatus.RESTRICTED]:
                return await message.reply_text("❌ You are banned from the channel.")
        except UserNotParticipant:
            return await message.reply_text(
                "**Hello! 👋 Join channel first!**",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔔 Join Channel 🔔", url=f"https://t.me/{FORCE_SUB_CHANNEL}")]])
            )
        except Exception:
            pass

    # ---------------- 2. PROCESS LINK ----------------
    msg = await message.reply_text("⏳ **Link check kar raha hu...**")
    
    try:
        # Pata karo account kiska hai
        me = await userbot.get_me()
        my_id = me.id
        my_name = me.first_name

        # Userbot link bhejega
        sent_msg = await userbot.send_message(SECRET_GROUP_ID, user_text)
        
        # 🔥 YAHAN PATA CHALEGA LINK KAHAN GAYA! 🔥
        await msg.edit_text(f"✅ **Tracker Active:**\n\nLink Sent By: **{my_name}**\nSent to Group: **{sent_msg.chat.title}**\n\n⏳ Ab 15 sec wait kar raha hu reply ka...")
        
        # 15 sec wait karega Nick ke reply ka
        await asyncio.sleep(15) 
        
        bypassed_link = None
        async for reply in userbot.get_chat_history(SECRET_GROUP_ID, limit=5):
            if reply.from_user and reply.from_user.id != my_id:
                bypassed_link = reply.text or reply.caption
                break
        
        if bypassed_link:
            final_text = (
                f"✅ **Bypass Successful!**\n\n{bypassed_link}\n\n"
                f"⚡ **Powered by @StudyWallahSamir**"
            )
            await msg.edit_text(final_text, disable_web_page_preview=True)
        else:
            await msg.edit_text("❌ **Oops! Bypass failed.**\n(Link group me toh chala gaya, par Nick ne wahan 15 second tak reply nahi diya)")
            
    except Exception as e:
        # 🔥 AGAR LINK SEND HONE ME ERROR AAYA TO YAHAN DIKHEGA 🔥
        await msg.edit_text(f"❌ **Code ne Secret Group me Link Bhejne se mana kar diya! Asli Error ye hai:**\n`{e}`")


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
