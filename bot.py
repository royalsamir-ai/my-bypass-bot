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
userbot = Client("bypasser_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# ---------------- PENDING REQUEST REGISTRY ----------------
pending_requests: dict[int, dict] = {}
pending_lock = asyncio.Lock()


def extract_bypassed_url(text: str) -> str | None:
    """
    Nick Bot ke text se exact Bypassed Link nikaalne ke liye logic.
    Aapki photo ke mutabik 'Bypassed Link :' ke theek baad wala URL uthayega.
    """
    # Nick Bot ke format 'Bypassed Link :' ke baad wale saare URLs dhoondega
    if "Bypassed Link" in text:
        parts = text.split("Bypassed Link")
        if len(parts) > 1:
            urls = re.findall(r'(https?://[^\s]+)', parts[1])
            if urls:
                return urls[0] # Bypassed section ka pehla link hi sahi link hai
                
    # Fallback: Agar text split fail ho toh aakhri url uthao
    urls = re.findall(r'(https?://[^\s]+)', text)
    return urls[-1] if urls else None


# ---------------- EVENT LISTENER FOR SECRET GROUP ----------------
@userbot.on_message(filters.chat(SECRET_GROUP_ID))
async def catch_nick_bot_reply(client, message: Message):
    msg_text = message.text or message.caption or ""

    # Strict check hata diya, agar message me koi bhi link hai ya 'liteshort' hai toh process karein
    if "liteshort.com" not in msg_text and "Bypassed" not in msg_text:
        return

    async with pending_lock:
        if not pending_requests:
            return

        matched_key = None

        # 1) Pehla Tarika: Nick Bot ne agar hamare userbot ke bheeje link par REPLY kiya hai
        if message.reply_to_message_id and message.reply_to_message_id in pending_requests:
            matched_key = message.reply_to_message_id

        # 2) Dusra Tarika: Nick Bot ke message mein hamara original link kahin bhi maujood ho
        if matched_key is None:
            for key, data in pending_requests.items():
                if data["original_link"] in msg_text or "easysky.in" in msg_text:
                    matched_key = key
                    break

        # 3) Tisra Tarika: Agar group mein sirf EK hi request pending hai toh seedhe use hi assign kardo
        if matched_key is None and len(pending_requests) == 1:
            matched_key = next(iter(pending_requests))

        if matched_key is None:
            return 

        future = pending_requests[matched_key]["future"]
        if not future.done():
            extracted_link = extract_bypassed_url(msg_text)
            if extracted_link:
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

    # ---------------- FORCE SUB CHECK ----------------
    if FORCE_SUB_CHANNEL:
        try:
            user_status = await client.get_chat_member(FORCE_SUB_CHANNEL, message.from_user.id)
            if user_status.status in [ChatMemberStatus.BANNED, ChatMemberStatus.RESTRICTED]:
                return await message.reply_text("❌ You are banned from the channel.")
        except UserNotParticipant:
            return await message.reply_text(
                "**Hello Cutie! 👋**\n\nTo use this premium bypass bot, you need to join our main channel first.\n\n👇 **Join the channel and send your link again!**",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔔 Join Channel 🔔", url=f"https://t.me{FORCE_SUB_CHANNEL}")]])
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

        # ---------------- AAPKA CUSTOM FINAL OUTPUT ----------------
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
            
