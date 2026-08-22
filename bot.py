import os
import re
import threading
import nest_asyncio
from urllib.parse import urlparse, parse_qs, unquote, quote
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Allow async loops to run in sync functions (Playwright fix for telebot)
nest_asyncio.apply()

# === BOT TOKEN SETUP ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
bot = telebot.TeleBot(BOT_TOKEN)
cache_db = {}

# === RENDER KEEP-ALIVE SERVER ===
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running with Playwright!")
def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

# === THE ULTIMATE PLAYWRIGHT BYPASS ENGINE ===
def bypass_with_browser(url):
    """
    Real Chrome browser engine to bypass ANY AdLinkFly clones
    (earnlinks.in, vplink.in, etc.)
    """
    final_url = None
    with sync_playwright() as p:
        # Launch real invisible chromium browser
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            # Go to the target url
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            
            # Check for Cloudflare Turnstile / Captcha
            if "Just a moment..." in page.title():
                page.wait_for_selector('div.cf-turnstile', timeout=10000)
                page.wait_for_timeout(5000) # Wait for Cloudflare to clear automatically
                
            # ADLINKFLY LOGIC: Click forms and wait for timers
            for _ in range(5): # Maximum 5 redirect steps
                page.wait_for_load_state("networkidle", timeout=10000)
                
                # If we left the shortener domain, we found the final link!
                if not any(domain in page.url for domain in ["earnlinks", "vplink", "inddrive", "urllinkshort", "indianshortner", "shortxlinks", "liteshort", "easysky", "vipshort"]):
                    if page.url != "about:blank" and url not in page.url:
                        final_url = page.url
                    break
                
                # Search for hidden forms (Adlinkfly specific)
                form = page.locator('form[id="go-link"]')
                if form.count() > 0:
                    try:
                        # Wait for the JS timer to finish and button to appear
                        page.wait_for_timeout(4000) # 4 seconds safety wait
                        btn = form.locator('button')
                        if btn.count() > 0:
                            btn.click()
                        else:
                            form.evaluate("form => form.submit()")
                    except Exception as e:
                        pass
                else:
                    # Look for other common submit buttons
                    btns = page.locator('button[type="submit"]')
                    if btns.count() > 0:
                         btns.first.click()
                         page.wait_for_timeout(2000)

        except PlaywrightTimeoutError:
            pass # Timeout means it probably got stuck on a manual captcha
        except Exception as e:
            print(f"Browser Error: {e}")
        finally:
            browser.close()
            
    return final_url


# === TELEGRAM HANDLERS ===
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🚀 *Ultimate Link Bypasser Bot is Online!*\n\nSend me your links (earnlinks.in, vplink.in, etc.) and I will bypass them using a Real Browser Engine!", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    
    if "t.me/" in url and "?single" in url:
         bot.reply_to(message, "⚠️ This looks like a direct Telegram post link, not a short link.")
         return

    if not url.startswith("http"):
        bot.reply_to(message, "⚠️ Please send a valid URL starting with 'http' or 'https'.")
        return

    if url in cache_db:
        bot.reply_to(message, f"⚡ *[CACHED]*\n🔗 *Bypassed Link:*\n{cache_db[url]}", parse_mode="Markdown")
        return

    msg = bot.reply_to(message, "⏳ *Bypassing...* Please wait.\n_(Headless Browser Engine Active 🛡️)_", parse_mode="Markdown")
    
    # Send directly to the real browser engine
    result = bypass_with_browser(url)

    if result:
        cache_db[url] = result 
        bot.edit_message_text(f"✅ *Success!*\n\n🔗 *Bypassed Link:*\n`{result}`", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
    else:
        bot.edit_message_text("❌ *Error*\nSorry, I couldn't bypass this link. It might have a hard CAPTCHA or requires manual verification.", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

if __name__ == "__main__":
    print("Starting Keep-Alive Server...")
    keep_alive()
    print("Bot Engine is Running with Playwright...")
    bot.infinity_polling()
