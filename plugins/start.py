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

# ---------------- FORCE SUBSCRIBE ----------------

@Bot.on_message(filters.command("start") & filters.private & ~subscribed)
async def not_joined(client, message):

    buttons = [
        [
            InlineKeyboardButton("Join Channel", url=client.invitelink),
            InlineKeyboardButton("Join Channel", url=client.invitelink2),
        ],
        [
            InlineKeyboardButton("Join Channel", url=client.invitelink3),
        ]
    ]

    try:
        buttons.append([
            InlineKeyboardButton(
                "Now Click Here",
                url=f"https://t.me/{client.username}?start={message.command[1]}"
            )
        ])
    except:
        pass

    await message.reply(
        FORCE_MSG.format(first=message.from_user.first_name),
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ================= START =================

@Bot.on_message(filters.command("start") & filters.private & subscribed)
async def start_command(client, message):

    uid = message.from_user.id

    if not await present_user(uid):
        await add_user(uid)

    if len(message.command) > 1 and message.command[1].startswith("ref_"):
        await handle_referral(client, uid, int(message.command[1].split("_")[1]))

    verify = await get_verify_status(uid)
    premium = await get_premium(uid)

    if verify["is_verified"] and verify_expired(verify):
        await update_verify_status(uid, is_verified=False)

    if premium and premium.get("expire_time"):
        left = premium["expire_time"] - time.time()
        if 0 < left < 86400:
            await client.send_message(uid, "⏰ Your premium will expire within 24 hours.")
        if left <= 0:
            await remove_premium(uid)
            premium = None
            await client.send_message(uid, "⚠ Your premium has expired.")

    if message.text.startswith("/start verify_"):
        token = message.text.split("_", 1)[1]
        if verify["verify_token"] != token:
            return await message.reply("❌ Invalid or expired verification link.")
        await update_verify_status(uid, is_verified=True, verified_time=time.time())
        return await message.reply(
            "🎉 Verification Successful!\n\n"
            "✅ Ab aap next 12 hours ke liye bot use kar sakte ho.\n\n"
            "📂 Apna file link dobara click kijiye aur file paayiye.\n\n"
            "⏳ 12 hours ke baad verification phir se karna hoga.\n\n"
            "❤️ Thanks for supporting our bot!"
        )

    if len(message.command) > 1 and not message.command[1].startswith("ref_"):

        if not premium or (premium and premium.get("expire_time") and time.time() > premium["expire_time"]):
            if IS_VERIFY and not verify["is_verified"]:
                return await send_verify(client, message, uid)

        try:
            decoded = decode(message.command[1])
            arg = decoded.split("-")
        except:
            return await message.reply("❌ Invalid file link.")

        if len(arg) == 2:
            ids = [int(int(arg[1]) / abs(client.db_channel.id))]
        elif len(arg) == 3:
            s = int(int(arg[1]) / abs(client.db_channel.id))
            e = int(int(arg[2]) / abs(client.db_channel.id))
            ids = range(s, e + 1)
        else:
            return await message.reply("❌ Invalid link format.")

        temp = await message.reply("📤 Fetching your file...")

        try:
            msgs = await get_messages(client, ids)
        except:
            return await temp.edit("❌ File not found.")

        await temp.delete()

        sent = []

        for m in msgs:
            try:
                cap = build_user_caption(m, premium and premium.get("is_premium"))
                s = await m.copy(uid, caption=cap, parse_mode=ParseMode.HTML, protect_content=PROTECT_CONTENT)
                sent.append(s)
                await asyncio.sleep(0.4)
            except FloodWait as e:
                await asyncio.sleep(e.value)

        note = await message.reply("⚠ Files auto delete after 10 minutes.")
        await asyncio.sleep(600)

        for m in sent:
            try:
                await m.delete()
            except:
                pass
        try:
            await note.delete()
        except:
            pass
        return

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

    await message.reply_photo(
        START_PIC,
        caption=text,
        reply_markup=btn
    )

# ================= VERIFY =================

async def send_verify(client, message, uid):

    token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    await update_verify_status(uid, verify_token=token, is_verified=False)

    link = await get_shortlink(
        SHORTLINK_URL, SHORTLINK_API,
        f"https://t.me/{client.username}?start=verify_{token}"
    )

    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Verify Step 1", url=link)],
        [InlineKeyboardButton("📘 Tutorial Step 1", url=VERIFY_TUT_1)],
        [InlineKeyboardButton("📗 Tutorial Step 2", url=VERIFY_TUT_2)]
    ])

    await message.reply(
        "🔐 2-Step Verification Required\n\n"
        "👉 First watch Step-1 tutorial\n"
        "👉 Complete verification\n"
        "👉 Then watch Step-2 tutorial",
        reply_markup=btn
    )

# ================= CALLBACK =================

@Bot.on_callback_query(filters.regex("^home$"), group=1)
async def home_back(client, q):
    await q.answer("Home")
    await send_home(client, q.message)

@Bot.on_callback_query(filters.regex("^premium$"), group=2)
async def prem(client, q):
    await q.answer()
    await q.message.edit(
        "👑 Premium Plans\n\n7 Days ₹10\n30 Days ₹30",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📩 Contact Owner", url=f"https://t.me/{OWNER_USERNAME}")],
            [InlineKeyboardButton("🔙 Back", callback_data="home")]
        ])
    )

@Bot.on_callback_query(filters.regex("^refinfo$"), group=2)
async def ref(client, q):
    await q.answer()
    await q.message.edit(
        "🎁 Invite 5 users → Get 30 Days Premium Free",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="home")]
        ])
    )

@Bot.on_callback_query(filters.regex("^mypremium$"), group=2)
async def myp(client, q):
    await q.answer()

    uid = q.from_user.id
    p = await get_premium(uid)

    if not p:
        return await q.message.edit(
            "❌ You are not premium.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="home")]
            ])
        )

    left = int((p["expire_time"] - time.time()) / 3600)

    await q.message.edit(
        f"👑 Premium Active\n⏳ Left: {left} Hours",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="home")]
        ])
    )

@Bot.on_callback_query(filters.regex("^leaderboard$"), group=2)
async def lb(client, q):
    await q.answer()
    await q.message.edit(
        "🏆 Referral Leaderboard coming soon.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="home")]
        ])
    )

# ================= COMMANDS =================

@Bot.on_message(filters.command("genlink") & filters.user(ADMINS))
async def genlink(client, m):
    if not m.reply_to_message:
        return await m.reply("Reply to a file.")

    code = encode(f"get-{m.reply_to_message.id*abs(client.db_channel.id)}")
    await m.reply(f"https://t.me/{client.username}?start={code}")

@Bot.on_message(filters.command("batch") & filters.user(ADMINS))
async def batch(client, m):
    try:
        s = int(m.command[1]); e = int(m.command[2])
    except:
        return await m.reply("/batch start end")

    code = encode(f"get-{s*abs(client.db_channel.id)}-{e*abs(client.db_channel.id)}")
    await m.reply(f"https://t.me/{client.username}?start={code}")

@Bot.on_message(filters.command("users") & filters.user(ADMINS))
async def users(client, m):
    u = await full_userbase()
    await m.reply(f"👥 Total Users: {len(u)}")

@Bot.on_message(filters.command("broadcast") & filters.user(ADMINS))
async def broadcast(client, m):
    if not m.reply_to_message:
        return await m.reply("Reply to a message to broadcast.")

    users = await full_userbase()
    sent = 0
    fail = 0

    for uid in users:
        try:
            await m.reply_to_message.copy(uid)
            sent += 1
            await asyncio.sleep(0.3)
        except:
            fail += 1

    await m.reply(f"✅ Broadcast Done\n\n✔ Sent: {sent}\n❌ Failed: {fail}")

@Bot.on_message(filters.command("forceverify") & filters.user(ADMINS), group=1)
async def fv(client, m):
    if len(m.command) < 2:
        return await m.reply("Usage: /forceverify user_id")
    uid = int(m.command[1])
    await update_verify_status(uid, is_verified=True, verified_time=time.time())
    await m.reply("✅ User force verified.")

@Bot.on_message(filters.command("unverify") & filters.user(ADMINS), group=1)
async def uv(client, m):
    if len(m.command) < 2:
        return await m.reply("Usage: /unverify user_id")
    await update_verify_status(int(m.command[1]), is_verified=False)
    await m.reply("❌ User unverified.")

@Bot.on_message(filters.command("addpremium") & filters.user(ADMINS), group=1)
async def ap(client, m):
    if len(m.command) < 3:
        return await m.reply("Usage: /addpremium user_id days")
    uid = int(m.command[1]); days = int(m.command[2])
    await add_premium(uid, int(time.time()) + days * 86400)
    await m.reply(ADMIN_APPROVAL_TEXT.format(uid=uid, days=days))

@Bot.on_message(filters.command("removepremium") & filters.user(ADMINS), group=1)
async def rp(client, m):
    if len(m.command) < 2:
        return await m.reply("Usage: /removepremium user_id")
    await remove_premium(int(m.command[1]))
    await m.reply("❌ Premium removed successfully.")
