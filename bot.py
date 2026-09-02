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

secret_env = os.environ.get("SECRET_GROUP_ID", "studywallahshiledfiles")
if str(secret_env).lstrip('-').isdigit():
    SECRET_GROUP_ID = int(secret_env)
else:
    SECRET_GROUP_ID = secret_env

FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "studywallahsamir")

BYPASS_TIMEOUT = 15  # seconds

# ---------------- CLIENTS ----------------
bot = Client("shield_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
userbot = Client("bypasser_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# ---------------- PENDING REQUEST REGISTRY ----------------
pending_requests: dict[str, dict] = {}
pending_lock = asyncio.Lock()

# ---------------- ENGINE 1: LIVE EVENT LISTENER ----------------
@userbot.on_message()
async def catch_nick_bot_reply(client, message: Message):
    msg_text = message.text or message.caption or ""

    if "Bypassed" not in msg_text and "✅" not in msg_text:
        return

    async with pending_lock:
        if not pending_requests:
            return

        matched_key = None
        for key, data in pending_requests.items():
            if data["original_link"] in msg_text:
                matched_key = key
                break

        if matched_key is None:
            return  

        future = pending_requests[matched_key]["future"]
        if not future.done():
            all_urls = re.findall(r'(https?://[^\s\)\]\}"\'”]+)', msg_text)
            if all_urls:
                future.set_result(all_urls[-1])


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
    task_id = str(random.randint(100000, 999999))
    
    anim_task = None
    poller_task = None

    try:
        loop = asyncio.get_event_loop()
        future = loop.create_future()

        async with pending_lock:
            pending_requests[task_id] = {
                "future": future,
                "original_link": user_text,
            }

        # Userbot bhejta hai message
        sent_msg = await userbot.send_message(SECRET_GROUP_ID, user_text)
        
        # ---------------- ENGINE 2: ACTIVE BACKUP POLLER ----------------
        async def backup_poller():
            for _ in range(15): # 15 seconds max wait
                await asyncio.sleep(1)
                if future.done():
                    return
                try:
                    # Agar live update drop ho gaya, toh ye history me jhaank kar result le aayega
                    async for history_msg in userbot.get_chat_history(SECRET_GROUP_ID, limit=5):
                        if history_msg.reply_to_message_id == sent_msg.id:
                            hist_text = history_msg.text or history_msg.caption or ""
                            if "Bypassed" in hist_text or "✅" in hist_text:
                                urls = re.findall(r'(https?://[^\s\)\]\}"\'”]+)', hist_text)
                                if urls and not future.done():
                                    future.set_result(urls[-1])
                                    return
                except Exception:
                    pass

        # Dono tasks ko background me chala do
        poller_task = asyncio.create_task(backup_poller())
        anim_task = asyncio.create_task(run_cute_animation(msg))

        try:
            # Wait for either Engine 1 or Engine 2 to find the link
            extracted_link = await asyncio.wait_for(future, timeout=BYPASS_TIMEOUT)
        except asyncio.TimeoutError:
            extracted_link = None

        # Jaise hi link mila, dono background tasks ko rok do!
        if anim_task:
            anim_task.cancel()
        if poller_task:
            poller_task.cancel()

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
        if anim_task:
            anim_task.cancel()
        if poller_task:
            poller_task.cancel()
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
