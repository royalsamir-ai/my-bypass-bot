import os
import time
import threading
import telebot
import cloudscraper
from bs4 import BeautifulSoup
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
        self.wfile.write(b"Bot is Running Perfectly!")
def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

# === GOD-TIER BYPASS ENGINE ===
def million_dollar_bypass(url):
    # Cloudflare security bypass karne ke liye cloudscraper
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    # Method 1: Native VpLink / EasySky Bypass (Bot Khud Karega)
    try:
        res = scraper.get(url, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Website ke hidden tokens nikaalo
        inputs = soup.find_all('input')
        data = {inp.get('name'): inp.get('value') for inp in inputs if inp.get('name')}
        
        if data and "_method" in data:  
            time.sleep(4)  # Timer bypass wait
            domain = url.split('/')[2]
            post_url = f"https://{domain}/links/go"
            headers = {
                'X-Requested-With': 'XMLHttpRequest',
                'Origin': f"https://{domain}",
                'Referer': url
            }
            
            # Seedha token bhej kar link mango
            res2 = scraper.post(post_url, data=data, headers=headers, timeout=15)
            json_data = res2.json()
            if 'url' in json_data:
                return json_data['url']
    except Exception as e:
        print(f"Native Error: {e}")

    # Method 2: Premium Fallback APIs (Agar Method 1 fail hua toh)
    apis = [
        f"https://api.bypass.vip/bypass?url={url}",
        f"https://api.bypassi.com/bypass?url={url}",
        f"https://dlp.hasanali.me/api/bypass?url={url}"
    ]
    for api in apis:
        try:
            r = scraper.get(api, timeout=10).json()
            for key in ["result", "url", "destination", "bypassed_link"]:
                if key in r and r[key] and str(r[key]).startswith("http"):
                    return r[key]
        except:
            continue

    return None

# === MAIN PROCESSING THREAD ===
def process_link(message, url, msg):
    chat_id = message.chat.id
    message_id = msg.message_id
    
    bot.edit_message_text("🔗 *SCANNING...* ⚡\n`▬▬▬▬▬[------]`\n*50%* 🔥", chat_id=chat_id, message_id=message_id, parse_mode="Markdown")
    
    result = million_dollar_bypass(url)
    
    time.sleep(1)
    bot.edit_message_text("🔗 *SCANNING...* ⚡\n`▬▬▬▬▬▬▬▬▬▬[-]`\n*99%* 🔥", chat_id=chat_id, message_id=message_id, parse_mode="Markdown")
    time.sleep(1)

    if result and result.startswith("http"):
        cache_db[url] = result
        bot.edit_message_text(f"✅ *Bypass Successful!*\n\n🔗 *Original:* {url}\n🔓 *Bypassed:* `{result}`", chat_id=chat_id, message_id=message_id, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        bot.edit_message_text("❌ *Bypass Failed*\nLink ka server block kar raha hai ya Cloudflare security bahut high hai.", chat_id=chat_id, message_id=message_id, parse_mode="Markdown")

# === TELEGRAM HANDLERS ===
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🚀 *Advanced Bypasser Bot is Online!*\n\nSend me your vplink.in or easysky.in link.", parse_mode="Markdown")

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
    keep_alive()
    bot.infinity_polling()
    
