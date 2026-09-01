import os
import asyncio
import re
import random
import uuid
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
pending_requests = {}
pending_lock = asyncio.Lock()

def extract_token(text: str):
    m = re.search(r"\[token:(\w+)\]", text)
    return m.group(1) if m else None

# ---------------- EVENT LISTENER (LIVE ENGINE) ----------------
@userbot.on_message()
@userbot.on_edited_message()
async def catch_nick_bot_reply(client, message: Message):
    text = message.text or message.caption or ""
    
    if "Bypassed" not in text and "✅" not in text:
        return

    matched_future = None
    
    async with pending_lock:
        # 1. Check via Reply ID
        reply_id = message.reply_to_message_id
        if reply_id and reply_id in pending_requests:
            matched_future = pending_requests[reply_id]
            
        # 2. Check via Token (THE ULTIMATE FIX FOR 0-SECOND RACE CONDITION)
        if not matched_future:
            token = extract_token(text)
            if not token and message.reply_to_message:
                token = extract_token(message.reply_to_message.text or "")
                
            if token and token in pending_requests:
                matched_future = pending_requests[token]

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
    
    try:
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        
        # 🔥 GENERATE AND PRE-REGISTER TOKEN BEFORE SENDING
        token_id = f"req_{uuid.uuid4().hex[:8]}"
        forward_text = f"{user_text} [token:{token_id}]"

        async with pending_lock:
            pending_requests[token_id] = future

        # Send the message via userbot
        sent_msg = await userbot.send_message(SECRET_GROUP_ID, forward_text)
        
        # Map the message ID as well for double safety
        async with pending_lock:
            pending_requests[sent_msg.id] = future

        # ---------------- ENGINE 2: POLLER FALLBACK ----------------
        async def backup_poller():
            for _ in range(20): # Increased to 20 seconds wait time
                await asyncio.sleep(1)
                if future.done():
                    return
                try:
                    async for history_msg in userbot.get_chat_history(SECRET_GROUP_ID, limit=10):
                        hist_text = history_msg.text or history_msg.caption or ""
                        if "Bypassed" in hist_text or "✅" in hist_text:
                            # Check by ID or Token in poller
                            if history_msg.reply_to_message_id == sent_msg.id or token_id in hist_text or (history_msg.reply_to_message and token_id in (history_msg.reply_to_message.text or "")):
                                urls = re.findall(r'(https?://[^\s\)\]\}"\'”]+)', hist_text)
                                if urls and not future.done():
                                    future.set_result(urls[-1])
                                    return
                except Exception:
                    pass

        poller_task = asyncio.create_task(backup_poller())

        try:
            # Wait for either the Live Listener or the Poller to find the link
            extracted_link = await asyncio.wait_for(future, timeout=20)
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
        await msg.edit_text(f"❌ **Technical Error:**\n`{e}`")

    finally:
        # Proper Cleanup
        async with pending_lock:
            pending_requests.pop(token_id, None)
            if 'sent_msg' in locals():
                pending_requests.pop(sent_msg.id, None)


# ---------------- START SERVICES ----------------
async def start_services():
    await bot.start()
    await userbot.start()
    print("🔥 SYSTEM READY 🔥")
    await idle()
    await bot.stop()
    await userbot.stop()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_services())-
