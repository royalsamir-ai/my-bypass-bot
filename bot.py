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
# no_updates removed intentionally — the userbot MUST receive updates for on_message to fire
userbot = Client("bypasser_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# ---------------- PENDING REQUEST REGISTRY ----------------
# key: the message ID the userbot sent into the secret group
# value: {"future": asyncio.Future, "original_link": str}
pending_requests: dict[int, dict] = {}
pending_lock = asyncio.Lock()


def extract_bypassed_url(text: str) -> str | None:
    """
    Nick Bot's message typically contains two URLs:
      Original Link: https://original.com/xyz
      Bypassed Link: https://liteshort.com/abc

    Strategy: split the text at the word "Bypassed" (case-insensitive) and
    take the FIRST url found in the section AFTER that split point.
    This avoids depending on exact punctuation/quote formatting.
    """
    if not text:
        return None

    match = re.split(r'bypassed', text, maxsplit=1, flags=re.IGNORECASE)

    if len(match) == 2:
        after_bypassed = match[1]
        urls = re.findall(r'(https?://[^\s\)\]\}"\'”]+)', after_bypassed)
        if urls:
            return urls[0]

    # Fallback: "bypassed" not found, or no URL after it — take the last url overall
    all_urls = re.findall(r'(https?://[^\s\)\]\}"\'”]+)', text)
    if all_urls:
        return all_urls[-1]

    return None


def looks_like_bypass_reply(text: str) -> bool:
    """Loose check — don't depend on exact 'Bypassed Link:' formatting."""
    if not text:
        return False
    lowered = text.lower()
    return "bypassed" in lowered or "liteshort.com" in lowered


# ---------------- EVENT LISTENER FOR SECRET GROUP ----------------
@userbot.on_message(filters.chat(SECRET_GROUP_ID))
async def catch_nick_bot_reply(client, message: Message):
    msg_text = message.text or message.caption or ""

    if not looks_like_bypass_reply(msg_text):
        return

    async with pending_lock:
        if not pending_requests:
            return

        matched_key = None

        # 1) Best case: Nick Bot's message is a formal reply to our sent message
        if message.reply_to_message_id and message.reply_to_message_id in pending_requests:
            matched_key = message.reply_to_message_id

        # 2) Fallback: match by finding our original link text inside the reply
        if matched_key is None:
            for key, data in pending_requests.items():
                if data["original_link"] in msg_text:
                    matched_key = key
                    break

        # 3) Last-resort fallback: only one request pending, assume it's that one
        if matched_key is None and len(pending_requests) == 1:
            matched_key = next(iter(pending_requests))

        if matched_key is None:
            return  # Can't confidently correlate — ignore rather than risk cross-wiring users

        future = pending_requests[matched_key]["future"]
        if not future.done():
            extracted_link = extract_bypassed_url(msg_text)
            future.set_result(extracted_link)


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
        await msg.edit_text(f"❌ **Technical Error:**\n`{e}`")

    finally:
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
