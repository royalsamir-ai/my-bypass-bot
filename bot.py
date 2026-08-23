import os
import time
import threading
import nest_asyncio
from urllib.parse import urlparse
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
        self.wfile.write(b"Ultimate Bot Engine is Running in 2026!")

def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

# === THE ULTIMATE PLAYWRIGHT BYPASS ENGINE ===
def bypass_with_browser(url):
    """
    Advanced Chrome browser engine to bypass ANY AdLinkFly clones
    Optimized for Speed, Ad-Blocking, and Stealth.
    """
    final_url = None
    
    with sync_playwright() as p:
        # Launch real invisible chromium browser with stealth args
        browser = p.chromium.launch(
            headless=True, 
            args=[
                '--no-sandbox', 
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled', # Stealth mode
                '--disable-infobars',
                '--window-size=1280,720'
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        
        # Kill all popups immediately to prevent getting stuck
        context.on("page", lambda new_page: new_page.close())
        
        page = context.new_page()

        # SPEED OPTIMIZATION: Block heavy resources and ads
        def intercept_route(route):
            # Only allow essential resources to load (HTML, JS, API calls)
            if route.request.resource_type in ["image", "media", "font", "stylesheet"]:
                route.abort()
            else:
                route.continue_()
                
        page.route("**/*", intercept_route)

        try:
            # Go to the target url
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            
            # Check for Cloudflare Turnstile / Captcha
            if "Just a moment" in page.title() or "Cloudflare" in page.title():
                page.wait_for_timeout(5000) # Wait for Cloudflare to clear automatically
                
            # ADLINKFLY LOGIC: Click forms and wait for timers
            for step in range(5): # Maximum 5 redirect steps
                page.wait_for_load_state("domcontentloaded", timeout=10000)
                
                # CRITICAL: Auto-scroll to trigger lazy-loaded JS timers
                page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2) 
                
                current_url = page.url
                # If we left the shortener domain, we found the final link!
                if not any(domain in current_url for domain in ["earnlinks", "vplink", "inddrive", "urllinkshort", "indianshortner", "shortxlinks", "liteshort", "easysky", "vipshort"]):
                    if current_url != "about:blank" and url not in current_url:
                        final_url = current_url
                    break
                
                # STEP 1: Invisible Captcha Form (Common in AdLinkFly)
                captcha_form = page.locator('form[id="invisibleCaptchaShortlink"]')
                if captcha_form.count() > 0:
                    try:
                        btn = captcha_form.locator('button[type="submit"]')
                        if btn.count() > 0:
                            btn.first.click(force=True) # force=True bypasses invisible ad overlays
                        else:
                            captcha_form.evaluate("form => form.submit()")
                        page.wait_for_timeout(2000)
                        continue
                    except Exception:
                        pass

                # STEP 2: The Final 'go-link' Form
                go_form = page.locator('form[id="go-link"]')
                if go_form.count() > 0:
                    try:
                        # Wait for the JS timer to finish and button to enable
                        page.wait_for_timeout(5000) 
                        btn = go_form.locator('button')
                        if btn.count() > 0:
                            btn.first.click(force=True)
                        else:
                            go_form.evaluate("form => form.submit()")
                        page.wait_for_timeout(2000)
                        continue
                    except Exception:
                        pass
                
                # STEP 3: Fallback for generic "Get Link" or "Continue" buttons
                gen_btns = page.locator('button:has-text("Get Link"), button:has-text("Continue"), a.get-link')
                if gen_btns.count() > 0:
                    try:
                        gen_btns.first.click(force=True)
                        page.wait_for_timeout(2000)
                    except Exception:
                        pass

        except PlaywrightTimeoutError:
            pass # Timeout means it probably got stuck or hit the final page
        except Exception as e:
            print(f"Browser Error: {e}")
        finally:
            # Final Safety Check: Did the URL change successfully but the loop broke?
            if not final_url and page.url and page.url != url and "about:blank" not in page.url:
                final_url = page.url
            browser.close()
            
    return final_url

# === TELEGRAM HANDLERS ===
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🚀 *Ultimate Link Bypasser Bot 2026 is Online!*\n\nSend me your links (earnlinks.in, vplink.in, etc.) and I will bypass them instantly using a Headless Stealth Browser!", parse_mode="Markdown")

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
        bot.reply_to(message, f"⚡ *[CACHED FAST]*\n🔗 *Bypassed Link:*\n`{cache_db[url]}`", parse_mode="Markdown")
        return

    msg = bot.reply_to(message, "⏳ *Bypassing...* Please wait.\n_(Stealth Browser Engine Active 🛡️)_", parse_mode="Markdown")
    
    # Send directly to the real browser engine
    result = bypass_with_browser(url)

    if result:
        cache_db[url] = result 
        bot.edit_message_text(f"✅ *Success!*\n\n🔗 *Bypassed Link:*\n`{result}`", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
    else:
        bot.edit_message_text("❌ *Error*\nSorry, I couldn't bypass this link. The site might be down, has a hard CAPTCHA, or the timer didn't load.", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

if __name__ == "__main__":
    print("Starting Keep-Alive Server...")
    keep_alive()
    print("Bot Engine 2026 is Running with Playwright Stealth...")
    bot.infinity_polling()
