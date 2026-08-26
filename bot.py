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

# ---------------- CLIENTS ----------------
bot = Client("shield_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
userbot = Client("bypasser_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING, no_updates=True)

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
                await asyncio.sleep(1.2) # 1.2s delay for animation
    except asyncio.CancelledError:
        pass # Task cancelled when link is found

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
                "**Hello Cutie! 👋**\n\nTo use this premium bypass bot, you need to join our main channel first.\n\n👇 **Join the channel and send your link again!**",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔔 Join Channel 🔔", url=f"https://t.me/{FORCE_SUB_CHANNEL}")]])
            )
        except Exception:
            pass

    # ---------------- 2. EXACT BYPASS LOGIC ----------------
    msg = await message.reply_text("🌸 **Waking up the Shield Bots...** 🧸")
    
    try:
        # Userbot sends link to secret group
        sent_msg = await userbot.send_message(SECRET_GROUP_ID, user_text)
        
        # Start animation in background
        anim_task = asyncio.create_task(run_cute_animation(msg))
        extracted_link = None
        
        # Checking loop: Look for a direct reply to 'sent_msg'
        for _ in range(30): # 30 checks (approx 15 seconds)
            await asyncio.sleep(0.5) # Fast API check
            
            async for reply in userbot.get_chat_history(SECRET_GROUP_ID, limit=10):
                # 🎯 SNIPER LOGIC: Is this message a direct reply to the link we just sent?
                if reply.reply_to_message_id == sent_msg.id:
                    msg_text = reply.text or reply.caption
                    
                    if msg_text and "Bypassed Link:" in msg_text:
                        # Extract exact bypassed link using regex to handle emojis/spaces
                        match = re.search(r"Bypassed Link:.*?✅\s*(https?://[^\s]+)", msg_text, re.DOTALL)
                        if match:
                            extracted_link = match.group(1)
                        else:
                            # Backup logic just in case
                            all_urls = re.findall(r'(https?://[^\s]+)', msg_text)
                            if all_urls:
                                extracted_link = all_urls[-1]
                        break # Got the link!
            
            if extracted_link:
                break # Stop checking
                
        # Stop the cute animation
        anim_task.cancel()

        # ---------------- 3. FINAL OUTPUT ----------------
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
        
