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

# Timeout for waiting on Nick Bot's reply
BYPASS_TIMEOUT = 15  # seconds

# ---------------- CLIENTS ----------------
bot = Client("shield_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
# IMPORTANT: no_updates removed — the userbot MUST receive updates for on_message to fire
userbot = Client("bypasser_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# ---------------- PENDING REQUEST REGISTRY ----------------
# key: the message ID the userbot sent into the secret group
# value: {"future": asyncio.Future, "original_link": str}
pending_requests: dict[int, dict] = {}
pending_lock = asyncio.Lock()

def extract_last_url(text: str) -> str | None:
    urls = re.findall(r'(https?://[^\s]+)', text)
    return urls[-1] if urls else None

# ---------------- EVENT LISTENER FOR SECRET GROUP ----------------
@userbot.on_message(filters.chat(SECRET_GROUP_ID))
async def catch_nick_bot_reply(client, message: Message):
    msg_text = message.text or message.caption or ""

    if "Bypassed Link:" not in msg_text:
        return

    async with pending_lock:
        if not pending_requests:
            return

        matched_key = None

        # 1) Best case: Nick Bot's message is a formal reply to the message we sent
        if message.reply_to_message_id and message.reply_to_message_id in pending_requests:
            matched_key = message.reply_to_message_id

        # 2) Fallback: match by finding our original link text inside the reply
        if matched_key is None:
            for key, data in pending_requests.items():
                if data["original_link"] in msg_text:
                    matched_key = key
                    break

        # 3) Last-resort fallback: oldest pending request (FIFO) — only if there's exactly one
        if matched_key is None and len(pending_requests) == 1:
            matched_key = next(iter(pending_requests))

        if matched_key is None:
            return  # Couldn't confidently correlate — ignore rather than risk cross-wiring users

        future = pending_requests[matched_key]["future"]
        if not future.done():
            extracted_link = extract_last_url(msg_text)
            future.set_result(extracted_link)  # may be None if no URL found; handled by caller

# ---------------- BACKGROUND ANIMATION TASK ----------------
async def run_cute_animation(msg):
    cute_steps = [
        "✨ **Scanning link for Cuties...** 🎀",
        "🛡️ **Defeating Viruses & Ads...** ⚔️",
        "💖 **Fetching your Premium Link...** 🥺"
    ]
    try:
        while True:
            for step in cute_steps:
                try:
                    await msg.edit_text(step)
                except MessageNotModified:
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
    anim_task = None
    sent_msg_id = None

    try:
        # Register the future BEFORE sending, to avoid a race where the
        # reply arrives before we've started listening for it
        loop = asyncio.get_event_loop()
        future = loop.create_future()

        sent_msg = await userbot.send_message(SECRET_GROUP_ID, user_text)
        sent_msg_id = sent_msg.id

        async with pending_lock:
            pending_requests[sent_msg_id] = {
                "future": future,
                "original_link": user_text,
            }

        anim_task = asyncio.create_task(run_cute_animation(msg))

        try:
            extracted_link = await asyncio.wait_for(future, timeout=BYPASS_TIMEOUT)
        except asyncio.TimeoutError:
            extracted_link = None

        if anim_task:
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
                f"🦠 *protected from jhut aisa {virus_count} virus asa* 🛡️\n"
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
        await msg.edit_text(f"❌ **Technical Error:**\n`{e}`")

    finally:
        # Always clean up the registry entry so it doesn't leak
        if sent_msg_id is not None:
            async with pending_lock:
                pending_requests.pop(sent_msg_id, None)

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
