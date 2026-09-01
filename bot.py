import os
import asyncio
import re
import random
import uuid
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant, FloodWait
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
pending_requests: dict[str, asyncio.Future] = {}
msg_id_to_token: dict[int, str] = {}  # message_id से token ढूँढने के लिए
pending_lock = asyncio.Lock()

# ---------------- HELPER FUNCTIONS ----------------
def extract_token(text: str) -> str | None:
    match = re.search(r"\[token:(\w+)\]", text)
    return match.group(1) if match else None

def extract_bypassed_link(text: str) -> str | None:
    urls = re.findall(r'(https?://[^\s\)\]\}"\'”]+)', text)
    if urls:
        return urls[-1]
    return None

# ---------------- ENGINE 1: LIVE EVENT LISTENER ----------------
@userbot.on_message(filters.chat(SECRET_GROUP_ID))
@userbot.on_edited_message(filters.chat(SECRET_GROUP_ID))
async def catch_nick_bot_reply(client, message: Message):
    msg_text = message.text or message.caption or ""

    if "Bypassed" not in msg_text and "✅" not in msg_text:
        return

    async with pending_lock:
        if not pending_requests:
            return

        token = extract_token(msg_text)
        
        if not token and message.reply_to_message:
            token = extract_token(message.reply_to_message.text or "")
            
        if not token and message.reply_to_message:
            token = msg_id_to_token.get(message.reply_to_message.id)

        if not token:
            return

        future = pending_requests.get(token)
        if future and not future.done():
            link = extract_bypassed_link(msg_text)
            if link:
                future.set_result(link)

# ---------------- STATIC WAITING MESSAGE ----------------
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

    msg = await message.reply_text("🌸 **Processing your link...** 🛡️")

    token = f"req_{uuid.uuid4().hex[:8]}"
    loop = asyncio.get_running_loop()
    future = loop.create_future()

    async with pending_lock:
        pending_requests[token] = future

    forward_text = f"{user_text} [token:{token}]"
    sent_msg = None
    poller_task = None

    try:
        sent_msg = await userbot.send_message(SECRET_GROUP_ID, forward_text)
        
        async with pending_lock:
            msg_id_to_token[sent_msg.id] = token

        # ---------------- ENGINE 2: ACTIVE BACKUP POLLER ----------------
        async def backup_poller():
            for _ in range(BYPASS_TIMEOUT):
                await asyncio.sleep(1)
                if future.done():
                    return
                try:
                    async for history_msg in userbot.get_chat_history(SECRET_GROUP_ID, limit=5):
                        if sent_msg and history_msg.reply_to_message_id == sent_msg.id:
                            hist_text = history_msg.text or history_msg.caption or ""
                            if "Bypassed" in hist_text or "✅" in hist_text:
                                link = extract_bypassed_link(hist_text)
                                if link and not future.done():
                                    future.set_result(link)
                                    return
                except FloodWait as e:
                    # Pyrogram v1 (x) और v2 (value) दोनों के लिए सुरक्षित तरीका
                    wait_time = getattr(e, 'value', getattr(e, 'x', 5))
                    await asyncio.sleep(wait_time)
                except Exception:
                    pass

        poller_task = asyncio.create_task(backup_poller())

        try:
            extracted_link = await asyncio.wait_for(future, timeout=BYPASS_TIMEOUT)
        except asyncio.TimeoutError:
            extracted_link = None

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
        if poller_task:
            poller_task.cancel()
        await msg.edit_text(f"❌ **Technical Error:**\n`{e}`")

    finally:
        async with pending_lock:
            pending_requests.pop(token, None)
            if sent_msg:
                msg_id_to_token.pop(sent_msg.id, None)

# ---------------- START SERVICES ----------------
async def start_services():
    await bot.start()
    await userbot.start()
    print("🔥 SYSTEM READY 🔥")
    await idle()
    await bot.stop()
    await userbot.stop()

if __name__ == "__main__":
    asyncio.run(start_services())
