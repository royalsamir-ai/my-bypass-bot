import os
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Details direct yahan daal rahe hain taaki variable ka koi lafda na rahe
API_ID = 37847572
API_HASH = "e79d219ac2531482d3ceb281b9190c58"
BOT_TOKEN = "8686759049:AAHxpXOjt97ApkXXIranQxJSGQYIUBHU7hY"
SECRET_GROUP_ID = -1004308606160

# Pyrogram Client (Userbot + Bot dono ek sath)
app = Client(
    "studywallah_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

pending_requests = {}

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    await message.reply_text(
        "✨ *Hello cutie!* 🎀\n\n"
        "I am your personal link bypasser bot. Send me any short link to get started! 🚀\n\n"
        "⚡ *Powered By @studywallahshield*",
        parse_mode="markdown"
    )

@app.on_message(filters.text & filters.private & ~filters.command(["start", "help"]))
async def link_handler(client, message):
    url = message.text.strip()
    if not url.startswith("http"):
        await message.reply_text("⚠️ Please send a valid URL starting with http/https 🥺")
        return

    msg = await message.reply_text("🔗 *SCANNING...* ⚡\n`▬[----------]`\n*12%* 🎀", parse_mode="markdown")
    try:
        sent_msg = await client.send_message(SECRET_GROUP_ID, url)
        pending_requests[sent_msg.id] = {
            "chat_id": message.chat.id,
            "message_id": msg.id,
            "original_url": url,
            "start_time": time.time()
        }
    except Exception as e:
        await msg.edit_text(f"❌ *Error:* {e}", parse_mode="markdown")

@app.on_message(filters.chat(SECRET_GROUP_ID) & filters.incoming)
async def nick_listener(client, message):
    if message.reply_to_message and message.reply_to_message.id in pending_requests:
        req_info = pending_requests.pop(message.reply_to_message.id)
        chat_id = req_info["chat_id"]
        msg_id = req_info["message_id"]
        original_url = req_info["original_url"]
        time_taken = round(time.time() - req_info["start_time"], 1)
        
        response_text = message.text or message.caption or ""
        bypassed_link = None
        for word in response_text.split():
            if word.startswith("http") and word != original_url:
                bypassed_link = word
                break
                
        if bypassed_link:
            success_text = (
                f"*Original Link :* ❞\n✅ {original_url}\n\n"
                f"*Bypassed Link:* ❞\n✅ `{bypassed_link}`\n\n"
                f"*Time Taken : {time_taken} seconds* ❞\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"*Powered By @studywallahshield* ❞\n\n"
                f"💰 *Coins Earned:* +10 🪙"
            )
            await client.edit_message_text(chat_id=chat_id, message_id=msg_id, text=success_text, parse_mode="markdown", disable_web_page_preview=True)
        else:
            await client.edit_message_text(chat_id=chat_id, message_id=msg_id, text="❌ *Bypass Failed* 🥺", parse_mode="markdown")

if __name__ == "__main__":
    print("🚀 Starting Userbot...")
    app.run()
    
