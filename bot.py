import os
import time
import threading
import nest_asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Playwright aur Telegram ko ek sath chalane ke liye
nest_asyncio.apply()

# === BOT TOKEN SETUP ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
bot = telebot.TeleBot(BOT_TOKEN)
cache_db = {}

# Progress Bar ko control karne ke liye dictionary
progress_status = {}

# === RENDER/RAILWAY KEEP-ALIVE SERVER ===
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running with UI!")
def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

# === PROGRESS BAR ANIMATION ===
def run_progress_bar(chat_id, message_id):
    stages = [
        ("12%", "▬[----------]"),
        ("35%", "▬▬▬[--------]"),
        ("52%", "▬▬▬▬▬[------]"),
        ("78%", "▬▬▬▬▬▬▬▬[---]"),
        ("99%", "▬▬▬▬▬▬▬▬▬▬[-]")
    ]
    
    for percent, bar in stages:
        if progress_status.get(message_id) == "done":
            break
        try:
            text = f"🔗 *SCANNING...* ⚡\n`{bar}`\n*{percent}* 🔥"
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, parse_mode="Markdown")
            time.sleep(2) # Har 2 second me bar aage badhega
        except Exception:
            pass

# === PLAYWRIGHT BYPASS ENGINE ===
def bypass_with_browser(url):
    final_url = None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000)
            
            if "Just a moment" in page.title() or "Cloudflare" in page.title():
                page.wait_for_timeout(5000)
                
            for _ in range(5):
                page.wait_for_load_state("domcontentloaded", timeout=10000)
                
                if not any(domain in page.url for domain in ["earnlinks", "vplink", "easysky", "cuty.io", "inddrive"]):
                    if page.url != "about:blank" and url not in page.url:
                        final_url = page.url
                    break
                
                # Auto-Scroll to trigger lazy timers
                page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)

                # Force click common shortener buttons
                btn = page.locator('button, a.btn, #go-link, form button').last
                if btn.count() > 0:
                    try:
                        btn.click(force=True, timeout=3000)
                    except:
                        pass
                page.wait_for_timeout(2000)

        except Exception as e:
            print(f"Browser Error: {e}")
        finally:
            browser.close()
            
    return final_url

# === MAIN PROCESSING THREAD ===
def process_link(message, url, msg):
    message_id = msg.message_id
    chat_id = message.chat.id
    
    # Start Progress Bar
    progress_status[message_id] = "running"
    threading.Thread(target=run_progress_bar, args=(chat_id, message_id)).start()

    # Start Bypassing
    result = bypass_with_browser(url)

    # Stop Progress Bar
    progress_status[message_id] = "done"
    time.sleep(1) # Thoda wait taaki last animation clear ho jaye

    if result:
        cache_db[url] = result 
        bot.edit_message_text(f"✅ *Bypass Successful!*\n\n🔗 *Original:* {url}\n🔓 *Bypassed:* `{result}`", chat_id=chat_id, message_id=message_id, parse_mode="Markdown")
    else:
        bot.edit_message_text("❌ *Bypass Failed*\nTimeout ya Hard Captcha detect hua. Kripya thodi der baad try karein.", chat_id=chat_id, message_id=message_id, parse_mode="Markdown")


# === TELEGRAM HANDLERS ===
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🚀 *Advanced Bypasser Bot is Online!*\n\nSend me any supported short link.", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    
    if not url.startswith("http"):
        bot.reply_to(message, "⚠️ Please send a valid URL.")
        return

    if url in cache_db:
        bot.reply_to(message, f"⚡ *[CACHED]*\n🔗 *Bypassed Link:*\n`{cache_db[url]}`", parse_mode="Markdown")
        return

    # Initial Message
    msg = bot.reply_to(message, "⏳ *Initializing Engine...*", parse_mode="Markdown")
    
    # Run processing in a background thread so the bot never freezes!
    threading.Thread(target=process_link, args=(message, url, msg)).start()

if __name__ == "__main__":
    print("Starting Server...")
    keep_alive()
    print("Bot is Running with new UI...")
    bot.infinity_polling()
