import os
import time
import threading
import requests
from bs4 import BeautifulSoup
import telebot
from http.server import BaseHTTPRequestHandler, HTTPServer

# === BOT TOKEN SETUP ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
bot = telebot.TeleBot(BOT_TOKEN)

# === RENDER/RAILWAY KEEP-ALIVE SERVER ===
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running via Requests!")
def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

# === ADLINKFLY / VPLINK / EASYSKY BYPASS ENGINE ===
def bypass_shortener(url):
    try:
        client = requests.Session()
        client.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        
        # Step 1: Website par jao aur hidden tokens nikal lo
        res = client.get(url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        inputs = soup.find_all('input')
        data = {inp.get('name'): inp.get('value') for inp in inputs if inp.get('name')}
        
        if not data:
            return None
            
        domain = url.split('/')[2]
        
        # Timer bypass karne ke liye thoda wait
        time.sleep(3)
        
        # Step 2: Seedha unke backend API par token bhej kar asli link mango
        post_url = f"https://{domain}/links/go"
        headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': f"https://{domain}",
            'Referer': url
        }
        
        res2 = client.post(post_url, data=data, headers=headers, timeout=10)
        
        # Step 3: Link mil gaya!
        json_data = res2.json()
        if 'url' in json_data:
            return json_data['url']
            
    except Exception as e:
        print("Bypass Error:", e)
        
    return None

# === MAIN PROCESSING THREAD ===
def process_link(message, url, msg):
    chat_id = message.chat.id
    message_id = msg.message_id
    
    # Progress Bar Update
    bot.edit_message_text("🔗 *SCANNING...* ⚡\n`▬▬▬▬▬[------]`\n*50%* 🔥", chat_id=chat_id, message_id=message_id, parse_mode="Markdown")
    
    result = bypass_shortener(url)
    
    bot.edit_message_text("🔗 *SCANNING...* ⚡\n`▬▬▬▬▬▬▬▬▬▬[-]`\n*99%* 🔥", chat_id=chat_id, message_id=message_id, parse_mode="Markdown")
    time.sleep(1)

    if result:
        bot.edit_message_text(f"✅ *Bypass Successful!*\n\n🔗 *Original:* {url}\n🔓 *Bypassed:* `{result}`", chat_id=chat_id, message_id=message_id, parse_mode="Markdown")
    else:
        bot.edit_message_text("❌ *Bypass Failed*\nAPI ko link nahi mila. Ye shortener alag system use kar raha hai.", chat_id=chat_id, message_id=message_id, parse_mode="Markdown")

# === TELEGRAM HANDLERS ===
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🚀 *Requests Bypasser Bot is Online!*\n\nSend me your vplink.in or easysky.in link.", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    
    if not url.startswith("http"):
        bot.reply_to(message, "⚠️ Please send a valid URL.")
        return

    msg = bot.reply_to(message, "🔗 *SCANNING...* ⚡\n`▬[----------]`\n*10%* 🔥", parse_mode="Markdown")
    threading.Thread(target=process_link, args=(message, url, msg)).start()

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
    
