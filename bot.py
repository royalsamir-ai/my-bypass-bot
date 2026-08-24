import os
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# === ENVIRONMENT VARIABLES SE DETAILS UTHANA ===
API_ID = int(os.environ.get("API_ID", "37847572"))
API_HASH = os.environ.get("API_HASH", "e79d219ac2531482d3ceb281b9190c58")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8686759049:AAHxpXOjt97ApkXXIranQxJSGQYIUBHU7hY")
SECRET_GROUP_ID = int(os.environ.get("SECRET_GROUP_ID", "-1004308606160"))

# Initialize Pyrogram Bot & Userbot
app = Client(
    "studywallah_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

pending_requests = {}

# === 1. START COMMAND ===
@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    await message.reply_text(
        "✨ *Hello cutie!* 🎀\n\n"
        "I am your personal link bypasser bot. Send me any short link to get started and earn coins! 🚀\n\n"
        "⚡ *Powered By @studywallahshield*",
        parse_mode="markdown"
    )

# === 2. HANDLE INCOMING LINKS FROM USERS ===
@app.on_message(filters.text & filters.private & ~filters.command(["start", "help"]))
async def link_handler(client, message):
    url = message.text.strip()
    
    if not url.startswith("http"):
        await message.reply_text("⚠️ Cutie, please send a valid URL starting with http/https 🥺")
        return

    msg = await message.reply_text("🔗 *SCANNING...* ⚡\n`▬[----------]`\n*12%* 🎀", parse_mode="markdown")
    
    try:
        # Link ko secret group me bhejo jahan Nick baitha hai
        sent_msg = await client.send_message(SECRET_GROUP_ID, url)
        
        pending_requests[sent_msg.id] = {
            "chat_id": message.chat.id,
            "message_id": msg.id,
            "original_url": url,
            "start_time": time.time()
        }
        
    except Exception as e:
        await msg.edit_text(f"❌ *Error:* Secret group mein link nahi bhej paya.\nDetails: `{e}`", parse_mode="markdown")

# === 3. LISTEN TO NICK BOT'S REPLY IN THE SECRET GROUP ===
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
                f"*Original Link :* ❞\n"
                f"✅ {original_url}\n\n"
                f"*Bypassed Link:* ❞\n"
                f"✅ `{bypassed_link}`\n\n"
                f"*Time Taken : {time_taken} seconds* ❞\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"*Powered By @studywallahshield* ❞\n\n"
                f"💰 *Coins Earned:* +10 🪙 (Total: 10)"
            )
            
            markup = InlineKeyboardMarkup([[
                InlineKeyboardButton("💸 Withdrawal", callback_data="withdraw_coins")
            ]])
            
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=success_text,
                parse_mode="markdown",
                reply_markup=markup,
                disable_web_page_preview=True
            )
        else:
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text="❌ *Bypass Failed*\nNick bot couldn't extract the link properly 🥺.",
                parse_mode="markdown"
            )

# === 4. CALLBACK BUTTON HANDLER ===
@app.on_callback_query()
async def callback_handler(client, callback_query):
    if callback_query.data == "withdraw_coins":
        await callback_query.answer("✨ Bot coming soon 🎀", show_alert=True)

if __name__ == "__main__":
    print("🚀 Study Wallah Userbot Bypasser is Starting...")
    app.run()
    
