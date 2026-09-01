import asyncio
import re
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.errors import FloodWait

# --- CONFIGURATION ---
API_ID = 1234567  # Apna API ID dalo
API_HASH = "your_api_hash"
BOT_TOKEN = "your_bot_token"
SESSION_STRING = "your_userbot_session_string"

SECRET_GROUP_ID = -1001234567890  # Apna Secret Group ID dalo
NICK_BOT_USERNAME = "Nick_Bypass_Bot"

# Clients initialize karo
app = Client("main_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
userbot = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# Yeh dictionary Race Condition roki gi (Message ID -> asyncio.Future)
pending_requests = {}

def extract_bypassed_link(text: str):
    """
    Image 1000022784.png ke hisaab se Nick Bot ka format parse karega.
    Dhundta hai: 'Bypassed Link: \n ✅ [URL]'
    """
    if not text:
        return None
    match = re.search(r"Bypassed Link:.*?\n\s*✅\s*(https?://[^\s]+)", text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1)
    return None

# ==========================================
# ENGINE 1: LIVE LISTENERS (Fastest)
# ==========================================
@userbot.on_message(filters.chat(SECRET_GROUP_ID) & filters.reply)
async def userbot_message_listener(client, message: Message):
    if not message.from_user or message.from_user.username != NICK_BOT_USERNAME:
        return
    
    replied_to_id = message.reply_to_message_id
    if replied_to_id in pending_requests:
        future = pending_requests[replied_to_id]
        extracted_link = extract_bypassed_link(message.text)
        
        # Agar link mil gaya aur future abhi pending hai, toh resolve kardo
        if extracted_link and not future.done():
            future.set_result(extracted_link)


@userbot.on_edited_message(filters.chat(SECRET_GROUP_ID) & filters.reply)
async def userbot_edit_listener(client, message: Message):
    # Same logic as message listener, catching those 0-second fast edits
    if not message.from_user or message.from_user.username != NICK_BOT_USERNAME:
        return
    
    replied_to_id = message.reply_to_message_id
    if replied_to_id in pending_requests:
        future = pending_requests[replied_to_id]
        extracted_link = extract_bypassed_link(message.text)
        
        if extracted_link and not future.done():
            future.set_result(extracted_link)


# ==========================================
# MAIN BOT LOGIC & ENGINE 2 (Fallback)
# ==========================================
@app.on_message(filters.private & filters.regex(r"https?://"))
async def handle_user_link(client, message: Message):
    # STATIC Message: Animation hata di gayi hai taki FloodWait na aaye
    status_msg = await message.reply_text("✨ Processing your link... Please wait.")
    
    try:
        # Step 1: Userbot se link secret group mein bhejo
        sent_msg = await userbot.send_message(SECRET_GROUP_ID, message.text)
    except FloodWait as e:
        await status_msg.edit_text(f"❌ Rate limit hit. Please try after {e.value} seconds.")
        return
    except Exception as e:
        await status_msg.edit_text("❌ Failed to forward to processing group.")
        return

    # Step 2: Future create aur pre-register karo (Race condition solved)
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    pending_requests[sent_msg.id] = future

    # Step 3: ENGINE 2 - Background Polling Task (WebSocket drop fix)
    async def poll_fallback(msg_id, fut):
        for _ in range(10):  # 15-20 sec tak poll karega (every 2 seconds)
            await asyncio.sleep(2)
            if fut.done():
                return
            try:
                # Group ki history check karo just in case event miss ho gaya ho
                async for hist_msg in userbot.get_chat_history(SECRET_GROUP_ID, limit=5):
                    if hist_msg.reply_to_message_id == msg_id and hist_msg.from_user and hist_msg.from_user.username == NICK_BOT_USERNAME:
                        extracted = extract_bypassed_link(hist_msg.text)
                        if extracted and not fut.done():
                            fut.set_result(extracted)
                            return
            except Exception:
                pass # Polling mein error aaye toh ignore karo, live listener pe rely karenge
                
        if not fut.done():
            fut.set_exception(TimeoutError("Timeout"))

    # Polling task ko background mein start kar do
    polling_task = asyncio.create_task(poll_fallback(sent_msg.id, future))

    try:
        # Dono engines me se jo bhi pehle URL laaye, uska wait karo (Max wait: 20 seconds)
        bypassed_link = await asyncio.wait_for(future, timeout=20.0)
        await status_msg.edit_text(f"✅ **Bypass Successful!**\n\n🔗 **Bypassed Link:** {bypassed_link}", disable_web_page_preview=True)
        
    except TimeoutError:
        await status_msg.edit_text("❌ Oops Cutie! Bypass failed. (Link took too long or format was wrong. Try again!)")
    except Exception as e:
        await status_msg.edit_text("❌ An unexpected error occurred.")
    finally:
        # Cleanup: Dictionary se memory leak na ho
        if sent_msg.id in pending_requests:
            del pending_requests[sent_msg.id]
        # Background task ko kill kardo
        polling_task.cancel()

# --- START CLIENTS ---
async def main():
    await app.start()
    await userbot.start()
    print("🤖 Both Main Bot and Userbot Started Successfully!")
    await idle()
    await app.stop()
    await userbot.stop()

if __name__ == "__main__":
    asyncio.run(main())
