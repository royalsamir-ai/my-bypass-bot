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

# ---------------- GLOBAL MESSAGE MAPPING ----------------
# Yeh dictionary group_message_id ko user_id se map karti hai
message_mapping: dict[int, int] = {}
mapping_lock = asyncio.Lock()

# ---------------- PENDING REQUEST REGISTRY ----------------
pending_requests: dict[str, dict] = {}
pending_lock = asyncio.Lock()

# ---------------- ENGINE 1: LIVE EVENT LISTENER (Enhanced) ----------------
@userbot.on_message(filters.chat(SECRET_GROUP_ID))
async def catch_nick_bot_reply(client, message: Message):
    """Enhanced listener jo Nik ke replies ko group me catch karta hai"""
    
    # Check karo ki yeh reply humare forwarded message ka hai ya nahi
    if message.reply_to_message and message.reply_to_message.id in message_mapping:
        replied_msg_id = message.reply_to_message.id
        original_user_id = message_mapping[replied_msg_id]
        
        msg_text = message.text or message.caption or ""
        
        # Check karo ki bypass indicators hain ya nahi
        if "Bypassed" in msg_text or "✅" in msg_text or "bypassed" in msg_text.lower():
            # Saare URLs extract karo
            all_urls = re.findall(r'(https?://[^\s\)\]\}"\'”]+)', msg_text)
            
            if all_urls:
                # Bypassed link usually last URL hota hai
                bypassed_link = all_urls[-1]
                
                # User ko bypassed link bhejo
                try:
                    await bot.send_message(
                        original_user_id,
                        f"✅ **Shield Bypass Complete!** 🎀\n\n"
                        f"**Shield Link :** 🛡️\n"
                        f"✅ **{bypassed_link}**\n\n"
                        f"🦠 *100% Protected from Viruses!* 🛡️\n"
                        f"✨ *This is only for cuties!* 🥺\n"
                        f"━━━━━━━━━━━━━━━━━\n"
                        f"**Powered By @StudyWallahSamir** 🎀",
                        disable_web_page_preview=True
                    )
                    
                    # Mapping clean karo
                    async with mapping_lock:
                        message_mapping.pop(replied_msg_id, None)
                    
                    print(f"✅ Bypassed link user {original_user_id} ko bhej diya")
                    
                    # Pending requests ko bhi update karo agar exist karta hai
                    async with pending_lock:
                        for key, data in pending_requests.items():
                            if data.get("group_msg_id") == replied_msg_id:
                                future = data["future"]
                                if not future.done():
                                    future.set_result(bypassed_link)
                                break
                    
                except Exception as e:
                    print(f"❌ User {original_user_id} ko bhejne me error: {e}")
    
    # Original logic backward compatibility ke liye
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
    user_id = message.from_user.id
    
    anim_task = None
    poller_task = None
    
    try:
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        
        async with pending_lock:
            pending_requests[task_id] = {
                "future": future,
                "original_link": user_text,
                "user_id": user_id,
            }
        
        # Userbot message group me bhejta hai
        sent_msg = await userbot.send_message(SECRET_GROUP_ID, user_text)
        
        # Mapping store karo: group_message_id -> user_id
        async with mapping_lock:
            message_mapping[sent_msg.id] = user_id
        
        # Pending requests me group_msg_id bhi store karo
        async with pending_lock:
            pending_requests[task_id]["group_msg_id"] = sent_msg.id
        
        print(f"📤 Message {sent_msg.id} user {user_id} se group me forward kiya")
        
        # Cute animation update shuru karo
        anim_task = asyncio.create_task(run_cute_animation(msg))
        
        # ---------------- ENGINE 2: ACTIVE BACKUP POLLER (Fixed & Completed) ----------------
        async def backup_poller():
            for _ in range(BYPASS_TIMEOUT):  # 15 seconds max wait
                await asyncio.sleep(1)
                if future.done():
                    return
                try:
                    # History check karo hamare forwarded message ke replies ke liye
                    async for history_msg in userbot.get_chat_history(SECRET_GROUP_ID, limit=10):
                        if history_msg.reply_to_message and history_msg.reply_to_message.id == sent_msg.id:
                            hist_text = history_msg.text or history_msg.caption or ""
                            if "Bypassed" in hist_text or "✅" in hist_text:
                                urls = re.findall(r'(https?://[^\s\)\]\}"\'”]+)', hist_text)
                                if urls and not future.done():
                                    future.set_result(urls[-1])
                                    return
                except Exception as e:
                    print(f"⚠️ Poller history check warning: {e}")
        
        poller_task = asyncio.create_task(backup_poller())
        
        try:
            # Wait for either event or backup poller to resolve the URL
            bypassed_link = await asyncio.wait_for(future, timeout=BYPASS_TIMEOUT)
            try:
                await msg.delete()
            except Exception:
                pass
        except asyncio.TimeoutError:
            try:
                await msg.edit_text("❌ **Bypass Failed!** Timed out waiting for response.")
            except Exception:
                pass
                
    except Exception as e:
        print(f"❌ Core processing error: {e}")
        try:
            await msg.edit_text("❌ **An error occurred** while processing your request.")
        except Exception:
            pass
            
    finally:
        # Cleanup routine
        if anim_task and not anim_task.done():
            anim_task.cancel()
        if poller_task and not poller_task.done():
            poller_task.cancel()
        async with pending_lock:
            pending_requests.pop(task_id, None)
        async with mapping_lock:
            message_mapping.pop(sent_msg.id, None)

# ---------------- CLIENT EXECUTOR ----------------
async def main():
    print("🚀 Starting Main Bot and Backup Userbot...")
