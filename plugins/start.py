# © MzBotz Premium File Store Bot

import asyncio, time, random, string, re
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait

from bot import Bot
from config import *

from helper_func import (
    subscribed, encode, decode, get_messages, get_shortlink,
    get_verify_status, update_verify_status, get_exp_time
)

from database.database import (
    add_user, del_user, full_userbase, present_user,
    get_premium, add_premium, remove_premium
)

BOT_START_TIME = time.time()

# ================= TEXT TEMPLATES =================

PREMIUM_BADGE = "👑 PREMIUM USER\n\n"

AUTO_INVOICE_TEXT = """🧾 Premium Invoice

User ID : {uid}
Plan : {days} Days
Status : Approved

Thank you for purchasing premium ❤️
"""

ADMIN_APPROVAL_TEXT = """✅ Premium Approved

User : {uid}
Plan : {days} Days
Activated Successfully
"""

PAYMENT_SUCCESS_TEXT = """💳 Payment Successful

Your premium will be activated shortly.
Thank you for supporting us ❤️
"""

REFERRAL_REWARD_TEXT = """🎉 Congratulations!

You earned 30 Days Premium from referrals 🎁
Enjoy premium access ❤️
"""

# ================= USER CAPTION =================

def build_user_caption(msg, is_premium=False):
    name = msg.document.file_name if msg.document else msg.video.file_name

    title = name.rsplit(".", 1)[0]

    title = re.sub(r"@\w+", "", title)
    title = re.sub(
        r"\b(onlymovies|onlymoviiies|mzmoviiez|mzmoviies|movieshub|filmyzilla|telegram|tme)\b",
        "", title, flags=re.I
    )

    year_match = re.search(r"\b(19|20)\d{2}\b", title)
    year = year_match.group(0) if year_match else ""
    title = re.sub(r"\b(19|20)\d{2}\b", "", title)

    title = re.sub(
        r"\b(480p|720p|1080p|2160p|x264|x265|webdl|webrip|bluray|hdrip|marathi|hindi|english|telugu|tamil|malayalam|kannada)\b",
        "", title, flags=re.I
    )

    title = title.replace(".", " ").replace("_", " ").replace("-", " ")
    title = title.replace("(", "").replace(")", "").replace("[", "").replace("]", "")
    title = re.sub(r"\s+", " ", title).strip()

    if year:
        title = f"{title} {year}"

    # -------- QUALITY --------
    quality = "N/A"
    for q in ["2160p", "1080p", "720p", "480p"]:
        if q in name.lower():
            quality = q
            break

    # -------- AUDIO --------
    aud = []
    for a in ["hindi","english","telugu","tamil","malayalam","marathi","kannada"]:
        if a in name.lower():
            aud.append(a.capitalize())
    audio = " / ".join(aud) if aud else "Unknown"

    # -------- SEASON / EP --------
    se = ""
    m = re.search(r"s(\d+)e(\d+)", name, re.I)
    if m:
        se = f"\n📺 Season {int(m.group(1))} Episode {int(m.group(2))}"

    caption = f"""🎬 {title}

🎞 Quality : {quality}
🔊 Audio : {audio}{se}

━━━━━━━━━━━━
"""

    if is_premium:
        caption = PREMIUM_BADGE + caption

    if CUSTOM_CAPTION:
        caption += CUSTOM_CAPTION

    return caption

# ================= VERIFY EXPIRE =================

def verify_expired(v):
    return v["verified_time"] + VERIFY_STEP_TIME < time.time()

# ================= REFERRAL =================

async def handle_referral(client, uid, ref_id):

    if uid == ref_id:
        return

    ref = await get_verify_status(ref_id)
    count = ref.get("referrals", 0) + 1
    await update_verify_status(ref_id, referrals=count)

    try:
        await client.send_message(ref_id, f"🎉 New Referral!\nTotal: {count}/5")
    except:
        pass

    if count >= 5:
        expire = int(time.time()) + 3 * 86400
        await add_premium(ref_id, expire)
        await update_verify_status(ref_id, referrals=0)

        try:
            await client.send_message(ref_id, REFERRAL_REWARD_TEXT)
        except:
            pass

# ================= HOME UI FUNCTION =================

async def send_home(client, message):

    uid = message.from_user.id
    verify = await get_verify_status(uid)
    premium = await get_premium(uid)

    ref_link = f"https://t.me/{client.username}?start=ref_{uid}"

    text = f"""👋 {message.from_user.mention}

🤖 Welcome to Premium File Store Bot!

📂 Secure Private File Storage
🔗 Auto Generated Access Links
🔐 2-Step Verification Protection
👑 Premium Users = No Verification
🎁 Referral Rewards Available

━━━━━━━━━━━━━━
🔐 Verify : {"✅" if verify["is_verified"] else "❌"}
👑 Premium : {"✅" if premium and premium.get("is_premium") else "❌"}
👥 Referrals : {verify.get("referrals",0)}/5
━━━━━━━━━━━━━━

🎁 Invite friends:
{ref_link}

💪 Powered By : @MzMoviiez
"""

    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("👑 Premium", callback_data="premium")],
        [InlineKeyboardButton("🎁 Referral Info", callback_data="refinfo")],
        [InlineKeyboardButton("📊 My Premium", callback_data="mypremium")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")]
    ])

    try:
        await message.edit_media(
            InputMediaPhoto(media=START_PIC, caption=text, parse_mode=ParseMode.HTML),
            reply_markup=btn
        )
    except:
        await message.edit_text(text, reply_markup=btn, parse_mode=ParseMode.HTML)
