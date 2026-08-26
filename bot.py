import os
import asyncio
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from pyrogram.enums import ChatMemberStatus

# ---------------- VARIABLES ----------------
API_ID = int(os.environ.get("API_ID", 37847572))
API_HASH = os.environ.get("API_HASH", "e79d219ac2531482d3ceb281b9190c58")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

# Secret Group Variable (Supports both ID and Username)
secret_env = os.environ.get("SECRET_GROUP_ID", "")
if secret_env.lstrip('-').isdigit():
    SECRET_GROUP_ID = int(secret_env)
else:
    SECRET_GROUP_ID = secret_env

FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "studywallahsamir")

# ---------------- CLIENTS ----------------
bot = Client("shield_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
userbot = Client("bypasser_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)


@bot.on_message(filters.private & filters.text)
async def handle_user_links(client, message: Message):
    user_text = message.text
    
    # ---------------- 1. FORCE SUB CHECK ----------------
    if FORCE_SUB_CHANNEL:
        try:
            user_status = await client.get_chat_member(FORCE_SUB_CHANNEL, message.from_user.id)
            if user_status.status in [ChatMemberStatus.BANNED, ChatMemberStatus.RESTRICTED]:
                return await message.reply_text("❌ You are banned from the channel. I cannot process your request.")
                
        except UserNotParticipant:
            return await message.reply_text(
                "**Hello! 👋**\n\nTo use this fast link bypass bot, you need to join our main channel first.\n\n👇 **Please join the channel using the button below and send your link again!**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔔 Join Channel 🔔", url=f"https://t.me/{FORCE_SUB_CHANNEL}")]
                ])
            )
        except Exception as e:
            print(f"Force Sub Error: {e}")

    # ---------------- 2. PROCESS LINK ----------------
    msg = await message.reply_text("⏳ **Bypassing your link... Please wait!**")
    
    try:
        # Userbot sends the link to the secret group
        sent_msg = await userbot.send_message(SECRET_GROUP_ID, user_text)
        
        # Wait for Nick's reply (10 seconds)
        await asyncio.sleep(10) 
        
        # Fetch the reply from the secret group
        bypassed_link = None
        async for reply in userbot.get_chat_history(SECRET_GROUP_ID, limit=5):
            # Check if Nick (a bot) replied with text or a photo caption
            if reply.from_user and reply.from_user.is_bot:
                bypassed_link = reply.text or reply.caption
                break
        
        # Final Message with Footer
        if bypassed_link:
            final_text = (
                f"✅ **Bypass Successful!**\n\n"
                f"{bypassed_link}\n\n"
                f"⚡ **Powered by @StudyWallahSamir**\n"
                f"🎁 **Want free access to paid batches? Join @studywallahsamir**"
            )
            await msg.edit_text(final_text, disable_web_page_preview=True)
        else:
            await msg.edit_text("❌ **Oops!** Bypass failed. Please check your link or try again later.")
            
    except Exception as e:
        await msg.edit_text("❌ An unexpected technical error occurred! Please contact the admin.")
        print(f"Bypass Error: {e}")


# ---------------- START SERVICES ----------------
async def start_services():
    print("Starting Main Bot...")
    await bot.start()
    print("Starting Background Userbot...")
    await userbot.start()
    
    print("🔥 SYSTEM IS FULLY READY! 🔥")
    
    await idle()
    
    await bot.stop()
    await userbot.stop()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_services())
