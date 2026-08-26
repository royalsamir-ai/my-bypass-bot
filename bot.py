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
SECRET_GROUP_ID = int(os.environ.get("SECRET_GROUP_ID", 0))

# Tera main channel jahan Force Sub lagana hai (Bina '@' ke)
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
            # Check karte hain ki user ne channel join kiya hai ya nahi
            user_status = await client.get_chat_member(FORCE_SUB_CHANNEL, message.from_user.id)
            if user_status.status in [ChatMemberStatus.BANNED, ChatMemberStatus.RESTRICTED]:
                return await message.reply_text("❌ Cutie, tum channel se banned ho. Main tumhari help nahi kar sakta.")
                
        except UserNotParticipant:
            # Agar join nahi kiya, toh pyaar se "cutie" language me bolenge
            return await message.reply_text(
                "**Hey cuties! 🥺**\n\nMujhse fast link bypass karwana hai? Toh phle jaldi se humara main channel join kar lo! Join karne ke baad hi main aage process karunga na.\n\n👇 **Fast Join Main Channel (Delete in 24 hr) & Send Link Again!**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔔 Join Channel 🔔", url=f"https://t.me/{FORCE_SUB_CHANNEL}")]
                ])
            )
        except Exception as e:
            print(f"Force Sub Error: {e}")
            # Agar bot channel me admin nahi hoga toh yahan error aayega

    # ---------------- 2. PROCESS LINK ----------------
    msg = await message.reply_text("⏳ **Bypassing your link cutie... Please wait!**")
    
    try:
        # Userbot chupchap link ko secret group me bhejega
        sent_msg = await userbot.send_message(SECRET_GROUP_ID, user_text)
        
        # Nick ka reply aane ka wait
        await asyncio.sleep(6) 
        
        # Secret group se reply fetch karna
        bypassed_link = None
        async for reply in userbot.get_chat_history(SECRET_GROUP_ID, limit=5):
            if reply.reply_to_message_id == sent_msg.id or (reply.from_user and reply.from_user.is_bot):
                bypassed_link = reply.text
                break
        
        # Final Message with Footer
        if bypassed_link:
            final_text = (
                f"✅ **Bypass Successful!**\n\n"
                f"{bypassed_link}\n\n"
                f"⚡ **Powered by @StudyWallahSamir**\n"
                f"🎁 **Want paid batches free access? Join @studywallahsamir**"
            )
            await msg.edit_text(final_text, disable_web_page_preview=True)
        else:
            await msg.edit_text("❌ **Oops cutie!** Bypass fail ho gaya. Link check karo ya thodi der baad aana.")
            
    except Exception as e:
        await msg.edit_text("❌ Aww, kuch technical error aa gaya cutie! Admin ko batao.")
        print(f"Error: {e}")


# ---------------- START SERVICES ----------------
async def start_services():
    print("Main Bot Start ho raha hai...")
    await bot.start()
    print("Background Userbot Start ho raha hai...")
    await userbot.start()
    print("🔥 TERA SYSTEM EKDUM READY HAI! 🔥")
    
    await idle()
    
    await bot.stop()
    await userbot.stop()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_services())
