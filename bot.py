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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
bot = telebot.TeleBot(BOT_TOKEN)

# === SMART CACHE SYSTEM ===
cache_db = {}

# === RENDER KEEP-ALIVE SERVER ===
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Ultimate Bypass Bot is Alive!")

def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

# === BYPASS LOGIC ENGINES ===

def simple_hash(string):
    h = 0
    for char in string:
        h = ((h << 5) - h + ord(char)) & 0xFFFFFFFF
        if h & 0x80000000:
            h = -((h ^ 0xFFFFFFFF) + 1)
    return hex(abs(h))[2:]

def bypass_sakirmobile():
    secret = 'SAKIR_SEC_K3Y_2026'
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    device_id = base64.b64encode(user_agent[:60].encode()).decode()[:40]
    ts = int(time.time() * 1000)
    sig = simple_hash(device_id + str(ts) + secret)[:12]
    return f"https://getkey.sakirmobilepanel.shop/verify-key?device={quote(device_id)}&t={ts}&sig={sig}"

def bypass_vipteam(game="OrangeFox"):
    try:
        res = cf_requests.post("https://vipteam.store/Getkey.php", data={"action": "generate", "game": game}, impersonate="chrome")
        data = res.json()
        if data.get("success"):
            return f"VIP Key: {data.get('key')}"
    except:
        pass
    return None

def bypass_nicktrick(url):
    parsed = urlparse(url)
    target = parse_qs(parsed.query).get('nicktrick', [None])[0]
    if target:
        while '%2' in target or '%3' in target:
            target = unquote(target)
        return target
    return None

def bypass_lksfy_xtg(url):
    qs = parse_qs(urlparse(url).query)
    id_val = qs.get('id', [None])[0] or qs.get('token', [None])[0]
    if not id_val:
        return None
    if any(x in url for x in ["lksfy", "sharclub", "sportswordz", "wblaxmibhandar", "schemepro", "recruitmentaim"]):
        return f"https://lksfy.com/{id_val}"
    if any(x in url for x in ["mealcold", "xtglinks", "7vibelife"]):
        return f"https://xtglinks.com/{id_val}"
    return None

def bypass_gplinks(url):
    try:
        res = cf_requests.get(url, impersonate="chrome")
        cookies = res.cookies.get_dict()
        if 'lid' in cookies and 'pid' in cookies and 'vid' in cookies:
            return f"https://gplinks.co/{cookies['lid']}?pid={cookies['pid']}&vid={cookies['vid']}"
    except:
        pass
    return None

def bypass_adlinkfly(url):
    """
    Master engine for all AdLinkFly clones (earnlinks, vplink, arolinks, etc.)
    Extracts hidden forms, waits for server timer, and hits /links/go
    """
    try:
        client = cf_requests.Session(impersonate="chrome110")
        # Step 1: Get the initial page and cookies
        res = client.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Step 2: Find all hidden input fields required for POST
        inputs = soup.find_all("input")
        data = {inp.get('name'): inp.get('value') for inp in inputs if inp.get('name')}
        
        if not data:
            return None
            
        # Step 3: Wait for server-side timer (Adlinkfly usually requires ~3 secs wait)
        time.sleep(3.5)
        
        # Step 4: Send Ajax POST request to /links/go
        parsed = urlparse(url)
        go_url = f"{parsed.scheme}://{parsed.netloc}/links/go"
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": url,
            "Origin": f"{parsed.scheme}://{parsed.netloc}"
        }
        
        post_res = client.post(go_url, data=data, headers=headers)
        
        # Step 5: Parse the final URL from JSON response
        try:
            js = post_res.json()
            if 'url' in js:
                return js['url']
        except:
            # Fallback if response isn't JSON
            pass
            
    except Exception as e:
        print(f"AdLinkFly Error: {e}")
        pass
    return None

def bypass_alpharede(url):
    try:
        res = cf_requests.get(url, impersonate="chrome")
        match = re.search(r'destination["\']?\s*:\s*["\']([^"\']+)["\']', res.text)
        if match:
            return match.group(1).replace('\\"', '"')
    except:
        pass
    return None

# === TELEGRAM HANDLERS ===

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "🚀 *Ultimate Link Bypasser Bot is Online!*\n\n"
        "Send your links to bypass instantly.\n"
        "Supported: GPLinks, LKSFY, VIP Team, SakirMobile, AdLinkFly Clones, etc."
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    
    # Validation
    if url.startswith("https://t.me/"):
        bot.reply_to(message, "⚠️ *Notice*\nThis is a direct Telegram post link. There's nothing to bypass here!", parse_mode="Markdown")
        return
        
    if not url.startswith("http"):
        bot.reply_to(message, "⚠️ *Invalid Input*\nPlease send a valid URL starting with 'http' or 'https'.", parse_mode="Markdown")
        return

    # Cache Check
    if url in cache_db:
        bot.reply_to(message, f"⚡ *[CACHED]*\n🔗 *Bypassed Link:*\n{cache_db[url]}", parse_mode="Markdown")
        return

    msg = bot.reply_to(message, "⏳ *Bypassing...* Please wait up to 5 seconds.\n_(Cracking Tokens 🛡️)_", parse_mode="Markdown")
    
    result = None
    
    # Lists of domains
    adlinkfly_domains = [
        "urllinkshort.in", "vplink.in", "earnlinks.in", "inddrive.com", 
        "indianshortner.in", "shortxlinks.in", "liteshort.com", "easysky.in", 
        "vipshort.in", "indiaearnx.in", "softurl.in", "rempo.xyz", 
        "arolinks.com", "bicolink.com", "shrinkme.click", "short4cash.com"
    ]
    
    lksfy_xtg_domains = [
        "lksfy", "sharclub", "sportswordz", "mealcold", "xtglinks", 
        "7vibelife", "wblaxmibhandar", "schemepro", "recruitmentaim"
    ]

    # === URL ROUTING LOGIC ===
    try:
        if "sakirmobilepanel.shop" in url:
            result = bypass_sakirmobile()
        elif "vipteam.store" in url:
            result = bypass_vipteam()
        elif "nicktrick=" in url:
            result = bypass_nicktrick(url)
        elif any(x in url for x in lksfy_xtg_domains):
            result = bypass_lksfy_xtg(url)
        elif any(x in url for x in adlinkfly_domains):
            result = bypass_adlinkfly(url)
        elif "gplinks" in url:
            result = bypass_gplinks(url)
        elif "alpharede" in url or "getkey" in url:
            result = bypass_alpharede(url)
        else:
            # Try AdLinkFly generically just in case it's an unknown clone
            result = bypass_adlinkfly(url)
            if not result:
                result = bypass_alpharede(url)
    except Exception as e:
        print(f"Routing Error: {e}")

    # Response Delivery
    if result and result.startswith("http"):
        cache_db[url] = result
        bot.edit_message_text(f"✅ *Success!*\n\n🔗 *Bypassed Link:*\n`{result}`", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
    elif result and "VIP Key" in result:
        cache_db[url] = result
        bot.edit_message_text(f"✅ *Success!*\n\n🔑 `{result}`", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
    else:
        bot.edit_message_text("❌ *Error*\nSorry, I couldn't bypass this link. It might be invalid, expired, or have a manual CAPTCHA.", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

# === START ENGINE ===
if __name__ == "__main__":
    print("Starting Keep-Alive Server...")
    keep_alive()
    print("Bot Engine is Running...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
