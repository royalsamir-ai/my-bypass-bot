import os
import asyncio
import re
from pyrogram import Client, filters, idle
from pyrogram.types import Message

# ----------------- CONFIGURATION -----------------
API_ID = int(os.environ.get("API_ID", 37847572))
API_HASH = os.environ.get("API_HASH", "e79d219ac2531482d3ceb281b9190c58")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
SESSION_STRING = os.environ.get("SESSION_STRING", "YOUR_USERBOT_SESSION_HERE")

# Screenshot ke hisab se Group ID (Better hai ki number wali ID use karo jaise -100xxxx)
SECRET_GROUP_ID = os.environ.get("SECRET_GROUP_ID", "studywallahshiledfiles")
if str(SECRET_GROUP_ID).lstrip('-').isdigit():
    SECRET_GROUP_ID = int(SECRET_GROUP_ID)

# ------------------- CLIENTS -------------------
bot = Client("main_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
userbot = Client("helper_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# Global memory map
active_routing_map = {}
map_lock = asyncio.Lock()

# ----------------- 1. USER LINK HANDLER -----------------
@bot.on_message(filters.private & filters.text)
async def handle_incoming_link(client, message: Message):
    user_link = message.text.strip()
    user_id = message.from_user.id
    
    if not user_link.startswith(("http://", "https://")):
        await message.reply_text("❌ Please send a valid link starting with http or https")
        return

    status_msg = await message.reply_text("⏳ **Processing your link through Shield Engines...**")
    
    try:
        # Userbot group me bhejega (Royal Samir ke naam se)
        sent_in_group = await userbot.send_message(SECRET_GROUP_ID, user_link)
        
        async with map_lock:
            active_routing_map[sent_in_group.id] = (user_id, status_msg.id)
            
        print(f"📥 Tracked: Group Message ID {sent_in_group.id} for User {user_id}")
        
    except Exception as e:
        print(f"❌ Error sending to group: {e}")
        await status_msg.edit_text("❌ Configuration Error: Could not reach processing group.")


# ----------------- 2. GROUP RESPONSE LISTENER -----------------
@userbot.on_message(filters.chat(SECRET_GROUP_ID))
async def catch_bypass_reply(client, message: Message):
    # Agar kisi message ka reply hai tabhi aage badhega
    if not message.reply_to_message:
        return
        
    target_reply_id = message.reply_to_message.id
    
    async with map_lock:
        if target_reply_id not in active_routing_map:
            return
        original_user_id, status_message_id = active_routing_map[target_reply_id]

    msg_text = message.text or message.caption or ""
    
    # Screenshot ke exact text "Bypassed Link :" ko target karo
    if "bypassed link" in msg_text.lower():
        # Text me se saare links ki list nikalo
        extracted_urls = re.findall(r'(https?://[^\s\)\]\}"\'”]+)', msg_text)
        
        if extracted_urls:
            # Screenshot me final link hamesha sabse AAKHIRI me hai (devuploads wala link)
            final_bypass_url = extracted_urls[-1]
            
            try:
                # User ko reply edit karke link deliver karo
                await bot.send_message(
                    chat_id=original_user_id,
                    text=f"✅ **Bypass Complete!** 🎀\n\n"
                         f"🛡️ **Your Protected Link:**\n"
                         f"👉 {final_bypass_url}\n\n"
                         f"━━━━━━━━━━━━━━━━━\n"
                         f"**Powered By @StudyWallahSamir** 🎀",
                    disable_web_page_preview=True
                )
                
                # Pehle wale loading/status message ko delete kar do
                try:
                    await bot.delete_messages(chat_id=original_user_id, message_ids=status_message_id)
                except Exception:
                    pass
                
                # Dictionary saaf karo
                async with map_lock:
                    active_routing_map.pop(target_reply_id, None)
                    
                print(f"✨ Successfully bypassed and delivered to User {original_user_id}")
                
            except Exception as e:
                print(f"❌ Error delivering message to user: {e}")


# ----------------- SYSTEM RUNNER -----------------
async def start_system():
    print("🛰️ Starting clean routing system engine...")
    await bot.start()
    await userbot.start()
    print("🚀 System is ONLINE! Waiting for user links...")
    await idle()
    await bot.stop()
    await userbot.stop()

if __name__ == "__main__":
    asyncio.run(start_system())
    
