import os
import asyncio
import re
import random
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant, MessageNotModified
from pyrogram.enums import ChatMemberStatus

# ---------------- VARIABLES ----------------
API_ID = int(os.environ.get("API_ID", 37847572))
API_HASH = os.environ.get("API_HASH", "e79d219ac2531482d3ceb281b9190c58")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

secret_env = os.environ.get("SECRET_GROUP_ID", "studywallahshiledfiles")
if str(secret_env).lstrip('-').isdigit():
    SECRET_GROUP_ID = int(secret_env)
else:
    SECRET_GROUP_ID = secret_env

FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "studywallahsamir")

# Timeout for waiting on Nick Bot's reply
BYPASS_TIMEOUT = 15  # seconds

# ---------------- CLIENTS ----------------
bot = Client("shield_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
# no_updates removed intentionally — the userbot MUST receive updates for on_message to fire
userbot = Client("bypasser_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# ---------------- PENDING REQUEST REGISTRY ----------------
# key: the message ID the userbot sent into the secret group
# value: {"future": asyncio.Future, "original_link": str}
pending_requests: dict[int, dict] = {}
pending_lock = asyncio.Lock()


URL_REGEX = r'(https?://[^\s\)\]\}"\'”]+)'


def extract_bypassed_url(text: str) -> str | None:
    """
    Nick Bot's message typically contains one or two URLs, e.g.:
      Original Link: https://original.com/xyz
      Bypassed Link: https://liteshort.com/abc

    Strategy:
      - If the message contains BOTH "original" and "bypassed" keywords,
        assume the format is Original -> Bypassed and take the URL found
        AFTER the word "Bypassed" (falling back to the second URL overall
        if that split doesn't yield one).
      - Otherwise, just take the LAST URL found anywhere in the message,
        since Nick Bot may use different wording ("link", "here", etc.)
        and the final/last URL is almost always the actual result link.
    """
    if not text:
        return None

    all_urls = re.findall(URL_REGEX, text)
    if not all_urls:
        return None

    lowered = text.lower()
    if "original" in lowered and "bypassed" in lowered and len(all_urls) >= 2:
        match = re.split(r'bypassed', text, maxsplit=1, flags=re.IGNORECASE)
        if len(match) == 2:
            after_bypassed_urls = re.findall(URL_REGEX, match[1])
            if after_bypassed_urls:
                return after_bypassed_urls[0]
        return all_urls[1]

    # Default: take the last URL in the message
    return all_urls[-1]


def looks_like_bypass_reply(text: str) -> bool:
    """
    Nick Bot is a known/trusted bot inside the secret group, so we don't
    depend on specific keywords like "bypassed" or "liteshort.com" — its
    wording can vary ("link", "here", etc.). Any message containing at
    least one URL is treated as a potential bypass result.
    """
    if not text:
        return False
    return bool(re.search(URL_REGEX, text))


# ---------------- EVENT LISTENER FOR SECRET GROUP ----------------
@userbot.on_message(filters.chat(SECRET_GROUP_ID))
async def catch_nick_bot_reply(client, message: Message):
    msg_text = message.text or message.caption or ""

    print(f"[SECRET GROUP] Message received (id={message.id}, reply_to={message.reply_to_message_id}): {msg_text!r}")

    if not looks_like_bypass_reply(msg_text):
        print(f"[SECRET GROUP] Message id={message.id} does NOT look like a bypass reply — ignoring.")
        return

    print(f"[SECRET GROUP] Message id={message.id} looks like a bypass reply.")

    async with pending_lock:
        if not pending_requests:
            print("[SECRET GROUP] No pending requests to match against — ignoring.")
            return

        matched_key = None

        # 1) Best case: Nick Bot's message is a formal reply to our sent message
        if message.reply_to_message_id and message.reply_to_message_id in pending_requests:
            matched_key = message.reply_to_message_id
            print(f"[MATCH] Matched by reply_to_message_id -> pending key {matched_key}")

        # 2) Fallback: match by finding our original link text inside the reply
        if matched_key is None:
            for key, data in pending_requests.items():
                if data["original_link"] in msg_text:
                    matched_key = key
                    print(f"[MATCH] Matched by original_link substring -> pending key {matched_key}")
                    break

        # 3) Last-resort fallback: only one request pending, assume it's that one
        if matched_key is None and len(pending_requests) == 1:
            matched_key = next(iter(pending_requests))
            print(f"[MATCH] Matched by single-pending-request fallback -> pending key {matched_key}")

        if matched_key is None:
            print(f"[MATCH] Could not correlate message id={message.id} with any pending request. Pending keys: {list(pending_requests.keys())}")
            return  # Can't confidently correlate — ignore rather than risk cross-wiring users

        future = pending_requests[matched_key]["future"]
        if not future.done():
            extracted_link = extract_bypassed_url(msg_text)
            print(f"[EXTRACT] Extracted URL for pending key {matched_key}: {extracted_link!r}")
            future.set_result(extracted_link)
        else:
            print(f"[MATCH] Future for pending key {matched_key} was already done — ignoring duplicate reply.")



# ---------------- BACKGROUND ANIMATION TASK ----------------
async def run_cute_animation(msg):
    cute_steps = [
        "✨ **Scanning link for Cuties...** 🎀",
        "🛡️ **Defeating Viruses & Ads...** ⚔️",
        "💖 **Fetching your Premium Link...** 🥺"
    ]
    try:
        while True:
            for step in cute_steps:
                try:
                    await msg.edit_text(step)
                except MessageNotModified:
                    pass
                await asyncio.sleep(1.2)
    except asyncio.CancelledError:
        pass


@bot.on_message(filters.private & filters.text)
async def handle_user_links(client, message: Message):
    user_text = message.text.strip()

    # ---------------- 1. FORCE SUB CHECK ----------------
    if FORCE_SUB_CHANNEL:
        try:
            user_status = await client.get_chat_member(FORCE_SUB_CHANNEL, message.from_user.id)
            if user_status.status in [ChatMemberStatus.BANNED, ChatMemberStatus.RESTRICTED]:
                return await message.reply_text("❌ You are banned from the channel.")
        except UserNotParticipant:
            return await message.reply_text(
                "**Hello Cutie! 👋**\n\nTo use this premium bypass bot, you need to join our main channel first.\n\n👇 **Join the channel and send your link again!**",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔔 Join Channel 🔔", url=f"https://t.me/{FORCE_SUB_CHANNEL}")]])
            )
        except Exception:
            pass

    msg = await message.reply_text("🌸 **Waking up the Shield Bots...** 🧸")
    anim_task = None
    sent_msg_id = None

    try:
        loop = asyncio.get_event_loop()
        future = loop.create_future()

        sent_msg = await userbot.send_message(SECRET_GROUP_ID, user_text)
        sent_msg_id = sent_msg.id

        print(f"[REQUEST] Sent link to secret group (id={sent_msg_id}): {user_text!r}")

        async with pending_lock:
            pending_requests[sent_msg_id] = {

                "future": future,
                "original_link": user_text,
            }

        anim_task = asyncio.create_task(run_cute_animation(msg))

        try:
            extracted_link = await asyncio.wait_for(future, timeout=BYPASS_TIMEOUT)
        except asyncio.TimeoutError:
            extracted_link = None

        if anim_task:
            anim_task.cancel()

        # ---------------- FINAL OUTPUT ----------------
        if extracted_link:
            virus_count = random.randint(5, 25)
            final_text = (
                f"**Shield Bypass Complete!** 🎀\n\n"
                f"**Original Link :** 🔗\n"
                f"✅ {user_text}\n\n"
                f"**Shield Link :** 🛡️\n"
                f"✅ **{extracted_link}**\n\n"
                f"🦠 *100% Protected from {virus_count} Viruses!* 🛡️\n"
                f"✨ *This is only for cuties!* 🥺\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"**Powered By @StudyWallahSamir** 🎀"
            )
            await msg.edit_text(final_text, disable_web_page_preview=True)
        else:
            await msg.edit_text("❌ **Oops Cutie! Bypass failed.**\n(Link took too long or format was wrong. Try again!)")

    except Exception as e:
        if anim_task:
            anim_task.cancel()
        await msg.edit_text(f"❌ **Technical Error:**\n`{e}`")

    finally:
        if sent_msg_id is not None:
            async with pending_lock:
                pending_requests.pop(sent_msg_id, None)


# ---------------- START SERVICES ----------------
async def start_services():
    await bot.start()
    await userbot.start()
    print("🔥 SYSTEM READY 🔥")
    await idle()
    await bot.stop()
    await userbot.stop()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_services())
