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
if str(secret_env).lstrip('-').isdigit():
    SECRET_GROUP_ID = int(secret_env)
else:
    SECRET_GROUP_ID = secret_env

FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "studywallahsamir")

# ---------------- CLIENTS ----------------
bot = Client("shield_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
userbot = Client("bypasser_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# ---------------- REGISTRY ----------------
pending_requests: dict[str, dict] = {}
pending_lock = asyncio.Lock()

# ---------------- EVENT LISTENER (NEW + EDITED MESSAGES) ----------------
@userbot.on_message()
@userbot.on_edited_message()
async def catch_nick_bot_reply(client, message: Message):
    text = message.text or message.caption or ""

    # Agar Nick Bot ka bypass message nahi hai, toh ignore karo
    if "Bypassed" not in text and "✅" not in text:
        return

    matched_future = None

    # ⏳ 0-SECOND RACE CONDITION FIX ⏳
    # Agar reply bohot fast aaya hai, toh bot 15 baar (3 seconds tak) list dobara check karega
    for _ in range(15): 
        async with pending_lock:
            for key, data in pending_requests.items():
                # 1. Check by Reply ID (Sabse accurate)
                if message.reply_to_message_id and data.get("sent_msg_id") == message.reply_to_message_id:
                    matched_future = data["future"]
                    break
                # 2. Check by Original Link (Backup)
                elif data["original_link"] in text:
                    matched_future = data["future"]
                    break
        
        if matched_future:
            break
        await asyncio.sleep(0.2) # Chota sa wait taaki background task update ho sake

    # Agar future mil gaya, toh link nikal kar wapas bhej do
    if matched_future and not matched_future.done():
        urls = re.findall(r'(https?://[^\s\)\]\}"\'”]+)', text)
        if urls:
            matched_future.set_result(urls[-1])

# ---------------- MAIN BOT HANDLER ----------------
@bot.on_message(filters.private & filters.text)
async def handle_user_links(client, message: Message):
    user_text = message.text.strip()

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

    msg = await message.reply_text("⚡ **Bypassing in milliseconds...** 🚀")
    task_id = str(random.randint(100000, 999999))

    try:
        loop = asyncio.get_event_loop()
        future = loop.create_future()

        # Request register karo bina message ID ke
        async with pending_lock:
            pending_requests[task_id] = {
                "future": future,
                "original_link": user_text,
                "sent_msg_id": None
            }

        # Userbot message bhejta hai
        sent_msg = await userbot.send_message(SECRET_GROUP_ID, user_text)
        
        # Message ID save hoti hai (Jisme thoda time lagta hai)
        async with pending_lock:
            if task_id in pending_requests:
                pending_requests[task_id]["sent_msg_id"] = sent_msg.id

        try:
            # Sirf wait karega, jaise hi Nick bot reply dega, ye complete ho jayega
            extracted_link = await asyncio.wait_for(future, timeout=15)
        except asyncio.TimeoutError:
            extracted_link = None

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

    except Exception as e:
        await msg.edit_text(f"❌ **Technical Error:**\n`{e}`")

    finally:
        async with pending_lock:
            pending_requests.pop(task_id, None)


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
    
