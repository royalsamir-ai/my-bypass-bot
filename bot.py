import os
import time
import threading
import requests
import telebot
from http.server import BaseHTTPRequestHandler, HTTPServer

# === BOT TOKEN SETUP ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
bot = telebot.TeleBot(BOT_TOKEN)
cache_db = {}

# === RENDER/RAILWAY KEEP-ALIVE SERVER ===
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"API Bypasser Bot is Running!")
def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

# === API BYPASS ENGINE (The Secret of Big Bots) ===
def get_bypassed_link(url):
    # Hum multiple APIs use karenge. Agar ek fail hui, toh dusri try karegi.
    apis = [
        f"https://api.bypass.vip/bypass?url={url}",
        f"https://dlp.hasanali.me/api/bypass?url={url}"
    ]
    
    for api_url in apis:
        try:
            res = requests.get(api_url, timeout=15).json()
            
            # Alag-alag API ka JSON format alag hota hai, hum sab check karenge
            if "result" in res and res["result"]:
                return res["result"]
            elif "url" in res and res["url"]:
                return res["url"]
            elif "destination" in res and res["destination"]:
                return res["destination"]
            elif "bypassed_link" in res and res["bypassed_link"]:
                return res["bypassed_link"]
        except Exception as e:
            print(f"API Error with {api_url}: {e}")
            continue # Agar ye API fail hui, toh next API try karo
            
    return None

# === MAIN PROCESSING THREAD ===
def process_link(message, url, msg):
    chat_id = message.chat.id
    message_id = msg.message_id
    
    # Progress Bar UI
    bot.edit_message_text("🔗 *SCANNING...* ⚡\n`▬▬▬▬▬[------]`\n*50%* 🔥", chat_id=chat_id, message_id=message_id, parse_mode="Markdown")
    
    # API Call
    result = get_bypassed_link(url)
    
    # Fake progress delay for premium feel
    time.sleep(1)
    bot.edit_message_text("🔗 *SCANNING...* ⚡\n`▬▬▬▬▬▬▬▬▬▬[-]`\n*99%* 🔥", chat_id=chat_id, message_id=message_id, parse_mode="Markdown")
    time.sleep(1)

    if result and result.startswith("http"):
        cache_db[url] = result
        bot.edit_message_text(f"✅ *Bypass Successful!*\n\n🔗 *Original:* {url}\n🔓 *Bypassed:* `{result}`", chat_id=chat_id, message_id=message_id, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        bot.edit_message_text("❌ *Bypass Failed*\nAPI ko link nahi mila. Ye shortener abhi APIs par update nahi hua hai ya offline hai.", chat_id=chat_id, message_id=message_id, parse_mode="Markdown")

# === TELEGRAM HANDLERS ===
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🚀 *Smart API Bypasser Bot is Online!*\n\nSend me any short link (vplink, easysky, etc.)", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    
    if not url.startswith("http"):
        bot.reply_to(message, "⚠️ Please send a valid URL.")
        return

    if url in cache_db:
        bot.reply_to(message, f"⚡ *[CACHED]*\n🔗 *Bypassed Link:*\n`{cache_db[url]}`", parse_mode="Markdown", disable_web_page_preview=True)
        return

    msg = bot.reply_to(message, "🔗 *SCANNING...* ⚡\n`▬[----------]`\n*12%* 🔥", parse_mode="Markdown")
    threading.Thread(target=process_link, args=(message, url, msg)).start()

if __name__ == "__main__":
    print("Starting API Bypasser...")
    keep_alive()
    bot.infinity_polling()
    
