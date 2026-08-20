import os
import re
import time
import base64
import threading
from urllib.parse import urlparse, parse_qs, unquote, quote
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot
from bs4 import BeautifulSoup
from curl_cffi import requests as cf_requests

# === BOT TOKEN SETUP ===
# Render par Environment Variables mein BOT_TOKEN naam se apna token daalna
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
bot = telebot.TeleBot(BOT_TOKEN)

# === SMART CACHE SYSTEM ===
# Ek baar bypass hua link yaad rakhega taaki agli baar 0.1s mein de sake
cache_db = {}

# === RENDER KEEP-ALIVE SERVER ===
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Ultimate Bypass Bot is Alive and Kicking!")

def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

# === BYPASS LOGIC ENGINES ===

def simple_hash(string):
    """SakirMobile Hash Logic Converted from JS"""
    h = 0
    for char in string:
        h = ((h << 5) - h + ord(char)) & 0xFFFFFFFF
        if h & 0x80000000:
            h = -((h ^ 0xFFFFFFFF) + 1)
    return hex(abs(h))[2:]

def bypass_sakirmobile():
    """Bypass SakirMobile Panel"""
    secret = 'SAKIR_SEC_K3Y_2026'
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    device_id = base64.b64encode(user_agent[:60].encode()).decode()[:40]
    ts = int(time.time() * 1000)
    sig = simple_hash(device_id + str(ts) + secret)[:12]
    return f"https://getkey.sakirmobilepanel.shop/verify-key?device={quote(device_id)}&t={ts}&sig={sig}"

def bypass_vipteam(game="OrangeFox"):
    """Bypass VIP Team using curl_cffi for Cloudflare"""
    try:
        res = cf_requests.post(
            "https://vipteam.store/Getkey.php",
            data={"action": "generate", "game": game},
            impersonate="chrome"
        )
        data = res.json()
        if data.get("success"):
            return f"VIP Key: {data.get('key')}"
    except Exception as e:
        pass
    return None

def bypass_nicktrick(url):
    """Bypass Smart Nicktrick"""
    parsed = urlparse(url)
    target = parse_qs(parsed.query).get('nicktrick', [None])[0]
    if target:
        while '%2' in target or '%3' in target:
            target = unquote(target)
        return target
    return None

def bypass_lksfy_xtg(url):
    """Bypass LKSFY and Xtglinks"""
    qs = parse_qs(urlparse(url).query)
    id_val = qs.get('id', [None])[0] or qs.get('token', [None])[0]
    if not id_val:
        return None
    if "lksfy" in url or "sharclub" in url or "sportswordz" in url:
        return f"https://lksfy.com/{id_val}"
    if "mealcold" in url or "xtglinks" in url or "7vibelife" in url:
        return f"https://xtglinks.com/{id_val}"
    return None

def bypass_alpharede(url):
    """Bypass Alpharede via Regex scraping"""
    try:
        res = cf_requests.get(url, impersonate="chrome")
        match = re.search(r'destination["\']?\s*:\s*["\']([^"\']+)["\']', res.text)
        if match:
            return match.group(1).replace('\\"', '"')
    except:
        pass
    return None

def bypass_gplinks(url):
    """Bypass GPLinks extracting hidden cookies"""
    try:
        res = cf_requests.get(url, impersonate="chrome")
        cookies = res.cookies.get_dict()
        if 'lid' in cookies and 'pid' in cookies and 'vid' in cookies:
            return f"https://gplinks.co/{cookies['lid']}?pid={cookies['pid']}&vid={cookies['vid']}"
    except:
        pass
    return None


# === TELEGRAM HANDLERS ===

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "🚀 *Ultimate Link Bypasser Bot is Online!*\n\n"
        "Please send your link to bypass it instantly.\n"
        "Supported shorteners: GPLinks, LKSFY, VIP Team, SakirMobile, Nicktrick, and more."
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    
    if not url.startswith("http"):
        bot.reply_to(message, "⚠️ *Invalid Input*\nPlease send a valid URL starting with 'http' or 'https'.", parse_mode="Markdown")
        return

    # Check Cache
    if url in cache_db:
        bot.reply_to(message, f"⚡ *[CACHED]*\n🔗 *Bypassed Link:*\n{cache_db[url]}", parse_mode="Markdown")
        return

    msg = bot.reply_to(message, "⏳ *Bypassing...* Please wait.\n_(Cloudflare Engine Active 🛡️)_", parse_mode="Markdown")
    
    result = None
    
    # URL Routing Logic
    if "sakirmobilepanel.shop" in url:
        result = bypass_sakirmobile()
    elif "vipteam.store" in url:
        result = bypass_vipteam()
    elif "nicktrick=" in url:
        result = bypass_nicktrick(url)
    elif any(x in url for x in ["lksfy", "sharclub", "sportswordz", "mealcold", "xtglinks", "7vibelife"]):
        result = bypass_lksfy_xtg(url)
    elif "getkey" in url:  # Usually Alpharede
        result = bypass_alpharede(url)
    elif "gplinks" in url:
        result = bypass_gplinks(url)
    else:
        # Generic Attempt using Alpharede logic as fallback
        result = bypass_alpharede(url)

    # Response
    if result:
        cache_db[url] = result # Save to cache
        bot.edit_message_text(f"✅ *Success!*\n\n🔗 *Bypassed Link:*\n`{result}`", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
    else:
        bot.edit_message_text("❌ *Error*\nSorry, I couldn't bypass this link. It might be invalid, expired, or currently unsupported.", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

# === START ENGINE ===
if __name__ == "__main__":
    print("Starting Keep-Alive Server...")
    keep_alive()
    print("Bot Engine is Running...")
    bot.infinity_polling()
    
