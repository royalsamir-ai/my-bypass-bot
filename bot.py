import os
import time
import threading
import nest_asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Playwright async fix[span_0](start_span)[span_0](end_span)
nest_asyncio.apply()

# === BOT TOKEN SETUP ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
bot = telebot.TeleBot(BOT_TOKEN)
cache_db = {}

# === RENDER/RAILWAY KEEP-ALIVE SERVER ===
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Fixed Playwright Bypasser Running!")
def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

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
            # Timeout 30 seconds kar diya hai taaki slow load hone par bhi crash na ho
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Cloudflare ko aaram se pass hone ke liye 6 second ka wait (Kill switch hataya gaya)
            page.wait_for_timeout(6000)
            
            # AdLinkFly aur VpLink logic[span_1](start_span)[span_1](end_span)
            for _ in range(5): 
                page.wait_for_load_state("domcontentloaded", timeout=15000)
                
                current_url = page.url
                # Agar hum shortener domain se bahar aa gaye, matlab link mil gaya
                if not any(domain in current_url for domain in ["earnlinks", "vplink", "inddrive", "easysky", "cuty.io"]):
                    if current_url != "about:blank" and url not in current_url:
                        final_url = current_url
                    break
                
                # Timer start karne ke liye Auto-Scroll
                page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                page.wait_for_timeout(4000) # Wait for 10-second timers to tick down
                
                # Hidden forms and submit buttons search[span_2](start_span)[span_2](end_span)
                form = page.locator('form[id="go-link"]')
                if form.count() > 0:
                    try:
                        btn = form.locator('button')
                        if btn.count() > 0:
                            btn.click(force=True)
                        else:
                            form.evaluate("form => form.submit()")
                    except:
                        pass
                else:
                    # Common adlinkfly buttons[span_3](start_span)[span_3](end_span)
                    btns = page.locator('a.btn, button.btn, button[type="submit"]')
                    if btns.count() > 0:
                        try:
                            btns.last.click(force=True)
                        except:
                            pass
                
                # Click hone ke baad agle page ka wait
                page.wait_for_timeout(3000)

        except PlaywrightTimeoutError:
            pass # Manual captcha timeout
        except Exception as e:
            print(f"Browser Error: {e}")
        finally:
            browser.close()
            
    return final_url

# === MAIN PROCESSING THREAD ===
def process_link(message, url, msg):
    chat_id = message.chat.id
    message_id = msg.message_id
    
    bot.edit_message_text("🔗 *SCANNING...* ⚡\n`▬▬▬▬▬[------]`\n*50%* 🔥", chat_id=chat_id, message_id=message_id, parse_mode="Markdown")
    
    result = bypass_with_browser(url)
    
    time.sleep(1)
    bot.edit_message_text("🔗 *SCANNING...* ⚡\n`▬▬▬▬▬▬▬▬▬▬[-]`\n*99%* 🔥", chat_id=chat_id, message_id=message_id, parse_mode="Markdown")
    time.sleep(1)

    if result and result.startswith("http"):
        cache_db[url] = result 
        bot.edit_message_text(f"✅ *Bypass Successful!*\n\n🔗 *Original:* {url}\n🔓 *Bypassed:* `{result}`", chat_id=chat_id, message_id=message_id, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        bot.edit_message_text("❌ *Bypass Failed*\nHigh Security Captcha Detect hua ya page load nahi ho paya.", chat_id=chat_id, message_id=message_id, parse_mode="Markdown")


# === TELEGRAM HANDLERS ===
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🚀 *Fixed Playwright Bypasser is Online!*\n\nSend me your links. I will bypass normal timers automatically!", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    
    if not url.startswith("http"):
        bot.reply_to(message, "⚠️ Please send a valid URL starting with 'http' or 'https'.")
        return

    if url in cache_db:
        bot.reply_to(message, f"⚡ *[CACHED]*\n🔗 *Bypassed Link:*\n`{cache_db[url]}`", parse_mode="Markdown", disable_web_page_preview=True)
        return

    msg = bot.reply_to(message, "🔗 *SCANNING...* ⚡\n`▬[----------]`\n*12%* 🔥", parse_mode="Markdown")
    
    threading.Thread(target=process_link, args=(message, url, msg)).start()

if __name__ == "__main__":
    print("Starting Server...")
    keep_alive()
    bot.infinity_polling()
    
