import os
import time
import threading
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from http.server import BaseHTTPRequestHandler, HTTPServer

# === BOT SETUP ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHANNEL_USERNAME = "@studywallahshield"  # Channel username

bot = telebot.TeleBot(BOT_TOKEN)
cache_db = {}
user_coins = {}

# === RAILWAY KEEP-ALIVE SERVER ===
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Study Wallah Cuties Bypasser is Running!")
def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

# === FORCE SUB CHECKER ===
def is_subscribed(user_id):
    try:
        chat_member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        # Agar user member, admin, ya creator hai to True
        if chat_member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except Exception as e:
        print(f"Force Sub Error (Bot admin hai ya nahi check karein): {e}")
        return False

# === BYPASS ENGINE ===
def get_bypassed_link(url):
    apis = [
        f"https://api.bypass.vip/bypass?url={url}",
        f"https://dlp.hasanali.me/api/bypass?url={url}",
        f"https://api.bypassi.com/bypass?url={url}",
        f"https://bypass.city/api/bypass?url={url}"
    ]
    
    for api in apis:
        try:
            r = requests.get(api, timeout=12).json()
            for key in ["result", "url", "destination", "bypassed_link"]:
                if key in r and r[key] and str(r[key]).startswith("http"):
                    return r[key]
        except:
            continue
    return None

# === BUTTON CALLBACK HANDLERS ===
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    # 1. Withdrawal Button
    if call.data == "withdraw_coins":
        bot.answer_callback_query(call.id, "Bot coming soon 🎀", show_alert=True)
    
    # 2. Re-check / Verify Button
    elif call.data == "check_sub":
        if is_subscribed(call.from_user.id):
            bot.answer_callback_query(call.id, "✅ Verification Successful! Ab aap link bhej sakte hain 🎀", show_alert=True)
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            bot.send_message(call.message.chat.id, "🎉 *Welcome Cutie!* Ab aap apna short link bhej sakte hain bypass karne ke liye.", parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "❌ Aapne abhi tak channel join nahi kiya hai! Pehle join karein 🥺", show_alert=True)

# === MAIN PROCESSING THREAD ===
def process_link(message, url, msg, start_time):
    chat_id = message.chat.id
    user_id = message.from_user.id
    message_id = msg.message_id
    
    bot.edit_message_text("🔗 *SCANNING...* ⚡\n`▬▬▬▬▬[------]`\n*50%* 🎀", chat_id=chat_id, message_id=message_id, parse_mode="Markdown")
    
    result = get_bypassed_link(url)
    
    bot.edit_message_text("🔗 *SCANNING...* ⚡\n`▬▬▬▬▬▬▬▬▬▬[-]`\n*99%* 🎀", chat_id=chat_id, message_id=message_id, parse_mode="Markdown")
    time.sleep(1)

    time_taken = round(time.time() - start_time, 1)

    if result and result.startswith("http"):
        cache_db[url] = result
        user_coins[user_id] = user_coins.get(user_id, 0) + 10
        current_coins = user_coins[user_id]

        success_text = (
            f"*Original Link :* ❞\n"
            f"✅ {url}\n\n"
            f"*Bypassed Link:* ❞\n"
            f"✅ `{result}`\n\n"
            f"*Time Taken : {time_taken} seconds* ❞\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"*Powered By @studywallahshield* ❞\n\n"
            f"💰 *Coins Earned:* +10 🪙 (Total: {current_coins})"
        )
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💸 Withdrawal", callback_data="withdraw_coins"))

        bot.edit_message_text(success_text, chat_id=chat_id, message_id=message_id, parse_mode="Markdown", reply_markup=markup, disable_web_page_preview=True)
    else:
        bot.edit_message_text("❌ *Bypass Failed*\nOh no cutie! Link bahut zyada encrypted hai ya server offline hai 🥺.", chat_id=chat_id, message_id=message_id, parse_mode="Markdown")

# === TELEGRAM HANDLERS ===
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🎀 Join Our Cute Channel", url="https://t.me/studywallahshield"))
        markup.add(InlineKeyboardButton("✅ I Have Joined", callback_data="check_sub"))
        bot.reply_to(message, f"⚠️ **This is only for cuties 🎀**\n\nHi {message.from_user.first_name}, bot use karne ke liye pehle hamara channel join karein!", parse_mode="Markdown", reply_markup=markup)
        return

    bot.reply_to(message, "🚀 *Study Wallah Bypasser Bot is Online! 🎀*\n\nSend me any short link to bypass and earn coins!", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    url = message.text.strip()

    if not is_subscribed(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🎀 Join Our Cute Channel", url="https://t.me/studywallahshield"))
        markup.add(InlineKeyboardButton("✅ I Have Joined", callback_data="check_sub"))
        bot.reply_to(message, f"⚠️ **This is only for cuties 🎀**\n\nHi {message.from_user.first_name}, bot use karne ke liye pehle hamara channel join karein!", parse_mode="Markdown", reply_markup=markup)
        return
    
    if not url.startswith("http"):
        bot.reply_to(message, "⚠️ Cutie, please send a valid URL starting with http 🥺")
        return

    start_time = time.time()
    msg = bot.reply_to(message, "🔗 *SCANNING...* ⚡\n`▬[----------]`\n*12%* 🎀", parse_mode="Markdown")
    threading.Thread(target=process_link, args=(message, url, msg, start_time)).start()

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
    
