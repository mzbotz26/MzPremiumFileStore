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

# ================= REFERRAL HANDLER =================

async def handle_referral(client, uid, ref_id):
    if uid == ref_id:
        return
    v = await get_verify_status(ref_id)
    count = v.get("referrals", 0) + 1
    await update_verify_status(ref_id, referrals=count)

# ================= TEMPLATES =================

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

    if not msg or not (msg.document or msg.video):
        return "📂 File"

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

    quality = "N/A"
    for q in ["2160p", "1080p", "720p", "480p"]:
        if q in name.lower():
            quality = q
            break

    aud = []
    for a in ["hindi","english","telugu","tamil","malayalam","marathi","kannada"]:
        if a in name.lower():
            aud.append(a.capitalize())
    audio = " / ".join(aud) if aud else "Unknown"

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

# ================= SEND VERIFY =================

async def send_verify(client, message, uid):

    token = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

    await update_verify_status(uid, verify_token=token, is_verified=False)

    link = await get_shortlink(
        SHORTLINK_URL,
        SHORTLINK_API,
        f"https://t.me/{client.username}?start=verify_{token}"
    )

    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Verify Step 1", url=link)],
        [InlineKeyboardButton("📘 Tutorial Step 1", url=VERIFY_TUT_1)],
        [InlineKeyboardButton("📗 Tutorial Step 2", url=VERIFY_TUT_2)]
    ])

    await message.reply(
        "🔐 2-Step Verification Required\n\n"
        "👉 Complete verification first\n"
        "👉 Then return to bot\n\n"
        "⏳ Verification valid for 12 hours",
        reply_markup=btn
    )

# ================= FORCE SUBSCRIBE =================

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

# ================= HOME UI =================

async def send_home(client, message):

    uid = message.from_user.id
    verify = await get_verify_status(uid)
    premium = await get_premium(uid)

    ref_link = f"https://t.me/{client.username}?start=ref_{uid}"

    text = f"""👋 {message.from_user.mention}

🤖 Welcome to Premium File Store Bot!

━━━━━━━━━━━━━━
🔐 Verify : {"✅" if verify["is_verified"] else "❌"}
👑 Premium : {"✅" if premium and premium.get("is_premium") else "❌"}
👥 Referrals : {verify.get("referrals",0)}/5
━━━━━━━━━━━━━━

🎁 Invite friends:
{ref_link}
"""

    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("👑 Premium", callback_data="premium")],
        [InlineKeyboardButton("🎁 Referral Info", callback_data="refinfo")],
        [InlineKeyboardButton("📊 My Premium", callback_data="mypremium")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")],
        [
            InlineKeyboardButton("🎬 Movie Group", url=f"https://t.me/{MOVIE_GROUP}"),
            InlineKeyboardButton("👤 Owner", url=f"https://t.me/{OWNER_USERNAME}")
        ]
    ])

    await message.reply_photo(START_PIC, caption=text, reply_markup=btn, parse_mode=ParseMode.HTML)

# ================= START =================

@Bot.on_message(filters.command("start") & filters.private & subscribed)
async def start_command(client, message):

    uid = message.from_user.id

    if not await present_user(uid):
        await add_user(uid)

    verify = await get_verify_status(uid)
    premium = await get_premium(uid)

    # ---- VERIFY TOKEN ----
    if message.text.startswith("/start verify_"):
        token = message.text.split("_",1)[1]

        if verify["verify_token"] != token:
            return await message.reply("❌ Invalid or expired verification link.")

        await update_verify_status(uid, is_verified=True, verified_time=time.time())

        return await message.reply(
            "🎉 Verification Successful!\n\n"
            "✅ Now you can use bot for next 12 hours.\n\n"
            "📂 Click your file link again."
        )

    if len(message.command) > 1:

        arg1 = message.command[1]

        if arg1.startswith("post_"):
            pid = int(arg1.split("_")[1])
            return await client.forward_messages(uid, POST_CHANNEL, pid)

        if arg1.startswith("ref_"):
            await handle_referral(client, uid, int(arg1.split("_")[1]))
            return await send_home(client, message)

        try:
            decoded = decode(arg1)
            arg = decoded.split("-")
        except:
            return await message.reply("❌ Invalid file link.")

        if not premium:
            if not verify["is_verified"] or verify_expired(verify):
                return await send_verify(client, message, uid)

        if len(arg) == 2:
            ids = [int(int(arg[1]) / abs(client.db_channel.id))]
        elif len(arg) == 3:
            s = int(int(arg[1]) / abs(client.db_channel.id))
            e = int(int(arg[2]) / abs(client.db_channel.id))
            ids = range(s, e + 1)
        else:
            return await message.reply("❌ Invalid link format.")

        temp = await message.reply("📤 Fetching your file...")

        msgs = await get_messages(client, ids)

        await temp.delete()

        sent = []

        for m in msgs:
            s = await m.copy(
                uid,
                caption=build_user_caption(m, premium and premium.get("is_premium")),
                parse_mode=ParseMode.HTML,
                protect_content=PROTECT_CONTENT
            )
            sent.append(s)
            await asyncio.sleep(0.4)

        note = await message.reply("⚠ Files auto delete after 10 minutes.")
        await asyncio.sleep(600)

        for m in sent:
            try: await m.delete()
            except: pass
        try: await note.delete()
        except: pass
        return

    await send_home(client, message)

# ================= CALLBACKS =================

@Bot.on_callback_query(filters.regex("^home$"))
async def home_back(client, q):
    await q.answer()
    await send_home(client, q.message)

@Bot.on_callback_query(filters.regex("^premium$"))
async def prem(client, q):
    await q.message.edit(
        "👑 Premium Plans\n\n7 Days ₹10\n30 Days ₹30",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📩 Contact Owner", url=f"https://t.me/{OWNER_USERNAME}")],
            [InlineKeyboardButton("🔙 Back", callback_data="home")]
        ])
    )

@Bot.on_callback_query(filters.regex("^refinfo$"))
async def ref(client, q):
    await q.message.edit(
        "🎁 Invite 5 users → Get 30 Days Premium Free",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="home")]
        ])
@Bot.on_callback_query(filters.regex("^home$"))
async def home_back(client, q):
    await q.answer()
    await send_home(client, q.message)


@Bot.on_callback_query(filters.regex("^premium$"))
async def prem(client, q):
    await q.message.edit_media(
        InputMediaPhoto(
            media=START_PIC,
            caption="👑 Premium Plans\n\n7 Days ₹10\n30 Days ₹30",
            parse_mode=ParseMode.HTML
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📩 Contact Owner", url=f"https://t.me/{OWNER_USERNAME}")],
            [InlineKeyboardButton("🔙 Back", callback_data="home")]
        ])
    )


@Bot.on_callback_query(filters.regex("^refinfo$"))
async def ref(client, q):
    await q.message.edit_media(
        InputMediaPhoto(
            media=START_PIC,
            caption="🎁 Invite 5 users → Get 30 Days Premium Free",
            parse_mode=ParseMode.HTML
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="home")]
        ])
    )


@Bot.on_callback_query(filters.regex("^mypremium$"))
async def myp(client, q):
    uid = q.from_user.id
    p = await get_premium(uid)

    if not p:
        text = "❌ You are not premium."
    else:
        left = int((p["expire_time"] - time.time()) / 3600)
        text = f"👑 Premium Active\n⏳ Left: {left} Hours"

    await q.message.edit_media(
        InputMediaPhoto(
            media=START_PIC,
            caption=text,
            parse_mode=ParseMode.HTML
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="home")]
        ])
    )


@Bot.on_callback_query(filters.regex("^leaderboard$"))
async def lb(client, q):
    await q.message.edit_media(
        InputMediaPhoto(
            media=START_PIC,
            caption="🏆 Referral Leaderboard coming soon.",
            parse_mode=ParseMode.HTML
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="home")]
        ])
    )

# ================= COMMANDS =================

@Bot.on_message(filters.command("reset") & filters.private & filters.user(ADMINS), group=-1)
async def reset_movie(client, message):

    if len(message.command) < 2:
        return await message.reply("❌ Usage:\n/reset movie_name")

    title = " ".join(message.command[1:])
    key = re.sub(r"[^a-z0-9]", "", title.lower())

    from database.database import series_catalog

    r = await series_catalog.delete_one({"_id": key})

    if r.deleted_count:
        await message.reply(f"✅ Movie reset done:\n{title.title()}")
    else:
        await message.reply("⚠ Movie not found in database.")

@Bot.on_message(filters.command("addpremium") & filters.private & filters.user(ADMINS), group=-1)
async def add_premium_cmd(client, message):

    if len(message.command) < 3:
        return await message.reply("❌ Usage:\n/addpremium user_id days")

    uid = int(message.command[1])
    days = int(message.command[2])

    expire = int(time.time()) + days * 86400
    await add_premium(uid, expire)

    await message.reply(f"👑 Premium activated for {days} days\nUser: {uid}")

@Bot.on_message(filters.command("removepremium") & filters.private & filters.user(ADMINS), group=-1)
async def remove_premium_cmd(client, message):

    if len(message.command) < 2:
        return await message.reply("❌ Usage:\n/removepremium user_id")

    uid = int(message.command[1])
    await remove_premium(uid)

    await message.reply(f"🗑 Premium removed for user {uid}")

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
