import os
import asyncio
import re
import random
from urllib.parse import quote
from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# ----------------- CONFIGURATION -----------------
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SESSION_STRING = os.environ.get("SESSION_STRING")

# Screenshot ke hisab se Group ID (Better hai ki number wali ID use karo jaise -100xxxx)
SECRET_GROUP_ID = os.environ.get("SECRET_GROUP_ID", "studywallahshiledfiles")
if str(SECRET_GROUP_ID).lstrip('-').isdigit():
    SECRET_GROUP_ID = int(SECRET_GROUP_ID)

# ----------------- TARGET BOTS (NEW) -----------------
# Usernames of the two engines that answer inside SECRET_GROUP_ID (without @)
TARGET_BOT_A = os.environ.get("TARGET_BOT_A", "Target_Bot_A").lstrip("@")
TARGET_BOT_B = os.environ.get("TARGET_BOT_B", "Target_Bot_B").lstrip("@")

# Both bots get the same link at the same time; the FIRST valid response wins
TARGET_BOTS = [TARGET_BOT_A, TARGET_BOT_B]
RESPONSE_TIMEOUT = 60   # max seconds to wait for either bot

# ----------------- LISTENER / DELIVERY SETTINGS -----------------
SETTLE_DELAY = 2.0      # seconds of quiet after the last chunk/edit before delivering
ACTION_DELAY = 3.0      # mandatory gap between userbot actions (anti-spam)
FLOOD_RETRIES = 3       # how many times to retry after a FloodWait

# If a target bot replies with one of these (and no "bypassed link"), fall back immediately
FAIL_KEYWORDS = ("failed", "error", "invalid", "unable", "not supported")

# Tier-1 load-balancing pool. Replace with your 5 real server URLs.
# "{link}" (optional) is replaced with the URL-encoded bypassed link.
BUTTON_URLS = [
    "https://URL1.example.com/unlock?u={link}",
    "https://URL2.example.com/unlock?u={link}",
    "https://URL3.example.com/unlock?u={link}",
    "https://URL4.example.com/unlock?u={link}",
    "https://URL5.example.com/unlock?u={link}",
]

# ------------------- CLIENTS -------------------
bot = Client("main_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
userbot = Client("helper_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# Global memory map
active_routing_map = {}
map_lock = asyncio.Lock()

# Listener state
pending_final = {}     # group_msg_id -> asyncio.Task (debounced delivery)
latest_urls = {}       # group_msg_id -> URLs from the most recent matching response
request_targets = {}   # group_msg_id -> set of bot usernames (lowercase) allowed to answer
request_state = {}     # group_msg_id -> {"event": asyncio.Event, "result": None|"ok"|"failed"}
background_tasks = set()

# ----------------- ANTI-SPAM / FLOODWAIT HELPERS (NEW) -----------------
_userbot_lock = asyncio.Lock()
_last_userbot_action = 0.0


def _flood_seconds(e: FloodWait) -> int:
    # Pyrogram 2.x uses .value, Pyrogram 1.x uses .x
    return int(getattr(e, "value", None) or getattr(e, "x", 0) or 0)


async def flood_safe(func, *args, **kwargs):
    """Run an API call; on FloodWait sleep the required time and retry."""
    for attempt in range(FLOOD_RETRIES + 1):
        try:
            return await func(*args, **kwargs)
        except FloodWait as e:
            if attempt == FLOOD_RETRIES:
                raise
            wait_s = _flood_seconds(e) + 1
            print(f"⏳ FloodWait: sleeping {wait_s}s (attempt {attempt + 1}/{FLOOD_RETRIES})")
            await asyncio.sleep(wait_s)


async def userbot_call(func, *args, **kwargs):
    """Every userbot action goes through here: 3s gap + FloodWait protection."""
    global _last_userbot_action
    async with _userbot_lock:
        loop = asyncio.get_running_loop()
        gap = ACTION_DELAY - (loop.time() - _last_userbot_action)
        if gap > 0:
            await asyncio.sleep(gap)
        try:
            return await flood_safe(func, *args, **kwargs)
        finally:
            _last_userbot_action = loop.time()


# ----------------- 1. USER LINK HANDLER -----------------
@bot.on_message(filters.private & filters.text)
async def handle_incoming_link(client, message: Message):
    user_link = message.text.strip()
    user_id = message.from_user.id

    if not user_link.startswith(("http://", "https://")):
        await flood_safe(message.reply_text, "❌ Please send a valid link starting with http or https")
        return

    status_msg = await flood_safe(message.reply_text, "⏳ **Processing your link through Shield Engines...**")

    # Fallback orchestration runs in the background so the handler never blocks
    task = asyncio.create_task(run_with_fallback(user_link, user_id, status_msg.id))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)


# ----------------- 2. GROUP RESPONSE LISTENER -----------------
URL_REGEX = r'(https?://[^\s\)\]\}"\'”]+)'


def _extract_urls(message: Message, text: str):
    # Visible links first (your original logic)
    urls = re.findall(URL_REGEX, text)
    if urls:
        return urls
    # Fallback: links hidden behind text (e.g. "Bypassed Link: [Click Here](url)")
    entities = message.entities or message.caption_entities or []
    return [e.url for e in entities if getattr(e, "url", None)]


def pick_unlock_url(final_url: str) -> str:
    if not BUTTON_URLS:
        return final_url
    template = random.choice(BUTTON_URLS)
    return template.replace("{link}", quote(final_url, safe=""))


async def _drop_request(group_msg_id: int):
    async with map_lock:
        active_routing_map.pop(group_msg_id, None)
        latest_urls.pop(group_msg_id, None)
        request_targets.pop(group_msg_id, None)
        request_state.pop(group_msg_id, None)
        task = pending_final.pop(group_msg_id, None)
    if task and not task.done():
        task.cancel()


async def _finalize_delivery(group_msg_id: int):
    # Wait for the response to settle (covers multi-part replies and quick edits)
    try:
        await asyncio.sleep(SETTLE_DELAY)
    except asyncio.CancelledError:
        return

    async with map_lock:
        entry = active_routing_map.pop(group_msg_id, None)
        urls = latest_urls.pop(group_msg_id, [])
        pending_final.pop(group_msg_id, None)
        request_targets.pop(group_msg_id, None)
        state = request_state.pop(group_msg_id, None)

    if not entry or not urls:
        return

    original_user_id, status_message_id = entry

    # Screenshot me final link hamesha sabse AAKHIRI me hai (devuploads wala link)
    final_bypass_url = urls[-1]
    unlock_url = pick_unlock_url(final_bypass_url)

    try:
        await flood_safe(
            bot.send_message,
            chat_id=original_user_id,
            text=f"✅ **Bypass Complete!** 🎀\n\n"
                 f"🔐 **Your protected link is ready.**\n"
                 f"Tap the button below to unlock it.\n\n"
                 f"━━━━━━━━━━━━━━━━━\n"
                 f"**Powered By @StudyWallahSamir** 🎀",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔓 Unlock Content", url=unlock_url)]]
            ),
            disable_web_page_preview=True
        )

        # Pehle wale loading/status message ko delete kar do
        try:
            await flood_safe(bot.delete_messages, chat_id=original_user_id, message_ids=status_message_id)
        except Exception:
            pass

        print(f"✨ Successfully bypassed and delivered to User {original_user_id}")

    except Exception as e:
        print(f"❌ Error delivering message to user: {e}")

    finally:
        # Response was received and handled -> no fallback needed
        if state:
            state["result"] = "ok"
            state["event"].set()


# Catches new messages AND edits (target bots often edit "processing..." into the final result)
@userbot.on_message(filters.chat(SECRET_GROUP_ID))
@userbot.on_edited_message(filters.chat(SECRET_GROUP_ID))
async def catch_bypass_reply(client, message: Message):
    # Agar kisi message ka reply hai tabhi aage badhega
    target_reply_id = getattr(message, "reply_to_message_id", None)
    if not target_reply_id:
        return

    sender = (message.from_user.username or "").lower() if message.from_user else ""
    msg_text = message.text or message.caption or ""
    lowered = msg_text.lower()

    async with map_lock:
        if target_reply_id not in active_routing_map:
            return

        # Accept answers from either target bot - first valid response wins
        if sender not in request_targets.get(target_reply_id, set()):
            return

        # Screenshot ke exact text "Bypassed Link :" ko target karo
        if "bypassed link" in lowered:
            extracted_urls = _extract_urls(message, msg_text)
            if not extracted_urls:
                return

            latest_urls[target_reply_id] = extracted_urls

            # Debounce: every new chunk/edit restarts the settle timer
            old_task = pending_final.get(target_reply_id)
            if old_task and not old_task.done():
                old_task.cancel()
            pending_final[target_reply_id] = asyncio.create_task(_finalize_delivery(target_reply_id))
            return

        # A target bot reported a failure -> keep waiting for the other one
        if target_reply_id not in pending_final and any(k in lowered for k in FAIL_KEYWORDS):
            state = request_state.get(target_reply_id)
            if state and state["result"] is None:
                state["failed_bots"].add(sender)
                # Only give up early when BOTH bots have reported failure
                if state["failed_bots"] >= request_targets[target_reply_id]:
                    state["result"] = "failed"
                    state["event"].set()


# ----------------- 3. DUAL-BOT RACE ORCHESTRATOR (NEW) -----------------
async def run_with_fallback(link: str, user_id: int, status_msg_id: int):
    try:
        # Userbot group me bhejega (Royal Samir ke naam se) - ONE send serves both bots
        sent_in_group = await userbot_call(userbot.send_message, SECRET_GROUP_ID, link)
    except Exception as e:
        print(f"❌ Error sending to group: {e}")
        try:
            await flood_safe(
                bot.edit_message_text,
                chat_id=user_id,
                message_id=status_msg_id,
                text="❌ Configuration Error: Could not reach processing group."
            )
        except Exception:
            pass
        return

    state = {"event": asyncio.Event(), "result": None, "failed_bots": set()}
    async with map_lock:
        active_routing_map[sent_in_group.id] = (user_id, status_msg_id)
        request_targets[sent_in_group.id] = {t.lower() for t in TARGET_BOTS}
        request_state[sent_in_group.id] = state

    print(f"📥 Tracked: Group Message ID {sent_in_group.id} for User {user_id} -> {TARGET_BOTS}")

    try:
        await asyncio.wait_for(state["event"].wait(), timeout=RESPONSE_TIMEOUT)
    except asyncio.TimeoutError:
        # A valid response may be mid-settle -> give delivery a short grace period
        async with map_lock:
            delivering = sent_in_group.id in pending_final
        if delivering:
            try:
                await asyncio.wait_for(state["event"].wait(), timeout=SETTLE_DELAY + 15)
            except asyncio.TimeoutError:
                pass

    if state["result"] == "ok":
        return

    # Neither bot answered in time (or both failed)
    await _drop_request(sent_in_group.id)
    print(f"⚠️ No valid response from {TARGET_BOTS} for Group Message ID {sent_in_group.id}")
    try:
        await flood_safe(
            bot.edit_message_text,
            chat_id=user_id,
            message_id=status_msg_id,
            text="⚠️ **All engines are busy right now cuties !!.**\nPlease send your link again in a minute."
        )
    except Exception:
        pass


# ----------------- SYSTEM RUNNER -----------------
async def start_system():
    print("🛰️ Starting clean routing system engine...")
    await bot.start()
    await userbot.start()
    print("🚀 System is ONLINE! Waiting for user links...")
    await idle()
    await bot.stop()
    await userbot.stop()

if __name__ == "__main__":
    asyncio.run(start_system())
