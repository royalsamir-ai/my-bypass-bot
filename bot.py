import os
import time
import threading
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from http.server import BaseHTTPRequestHandler, HTTPServer

# === BOT SETUP ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHANNEL_USERNAME = "@studywallahshield"  # Tumhara apna channel

bot = telebot.TeleBot(BOT_TOKEN)

# Database Setup (Abhi ke liye temporary dictionary, jab real DB banaoge tab change kar lena)
cache_db = {}
user_coins = {}  # Yahan Cuties ke coins store honge

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
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Force Sub Error: {e}")
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

# === WITHDRAWAL BUTTON HANDLER (The Popup Alert) ===
@bot.callback_query_handler(func=lambda call: call.data == "withdraw_coins")
def handle_withdrawal(call):
    # Ye popup message show karega mobile screen par!
    bot.answer_callback_query(call.id, "Bot coming soon 🎀", show_alert=True)

# === MAIN PROCESSING THREAD ===
def process_link(message, url, msg, start_time):
    chat_id = message.chat.id
    user_id = message.from_user.id
    message_id = msg.message_id
    
    # Progress Bar (Cute Version)
    bot.edit_message_text("🔗 *SCANNING...* ⚡\n`▬▬▬▬▬[------]`\n*50%* 🎀", chat_id=chat_id, message_id=message_id, parse_mode="Markdown")
    
    result = get_bypassed_link(url)
    
    bot.edit_message_text("🔗 *SCANNING...* ⚡\n`▬▬▬▬▬▬▬▬▬▬[-]`\n*99%* 🎀", chat_id=chat_id, message_id=message_id, parse_mode="Markdown")
    time.sleep(1)

    # Time Calculation (Kitne seconds lage)
    time_taken = round(time.time() - start_time, 1)

    if result and result.startswith("http"):
        cache_db[url] = result
        
        # 10 Coins per bypass add kar rahe hain
        user_coins[user_id] = user_coins.get(user_id, 0) + 10
        current_coins = user_coins[user_id]

        # 👑 EXACT SCREENSHOT FORMAT WITH "STUDY WALLAH" BRANDING
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
        
        # Withdrawal Button
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💸 Withdrawal", callback_data="withdraw_coins"))

        bot.edit_message_text(success_text, chat_id=chat_id, message_id=message_id, parse_mode="Markdown", reply_markup=markup, disable_web_page_preview=True)
    else:
        bot.edit_message_text("❌ *Bypass Failed*\nOh no cutie! Link bahut zyada encrypted hai ya server offline hai 🥺.", chat_id=chat_id, message_id=message_id, parse_mode="Markdown")

# === TELEGRAM HANDLERS ===
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🚀 *Study Wallah Bypasser Bot is Online! 🎀*\n\nSend me any short link to bypass and earn coins!", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    url = message.text.strip()

    # 1. Force Subscribe for "Cuties"
    if not is_subscribed(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🎀 Join Our Cute Channel", url="https://t.me/studywallahshield"))
        bot.reply_to(message, f"⚠️ **This is only for cuties 🎀**\n\nHi {message.from_user.first_name}, bot use karne ke liye pehle hamara channel join karein! Join karne ke baad wapas aa kar apna link bhejein.", parse_mode="Markdown", reply_markup=markup)
        return
    
    if not url.startswith("http"):
        bot.reply_to(message, "⚠️ Cutie, please send a valid URL starting with http 🥺")
        return

    # Timer Start (Time taken calculate karne ke liye)
    start_time = time.time()

    msg = bot.reply_to(message, "🔗 *SCANNING...* ⚡\n`▬[----------]`\n*12%* 🎀", parse_mode="Markdown")
    threading.Thread(target=process_link, args=(message, url, msg, start_time)).start()

if __name__ == "__main__":
    print("Starting Study Wallah Shield Bypasser...")
    keep_alive()
    bot.infinity_polling()
    
