# (©)Mzbotz

import base64
import re
import asyncio
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from config import FORCESUB_CHANNEL, FORCESUB_CHANNEL2, FORCESUB_CHANNEL3, ADMINS
from pyrogram.errors import FloodWait
from shortzy import Shortzy
from database.database import db_verify_status, db_update_verify_status

# ================= FORCE SUB FILTER =================

async def is_subscribed(_, client, message):
    user_id = message.from_user.id

    if user_id in ADMINS:
        return True

    for channel_id in [FORCESUB_CHANNEL, FORCESUB_CHANNEL2, FORCESUB_CHANNEL3]:
        if not channel_id:
            continue
        try:
            member = await client.get_chat_member(channel_id, user_id)
            if member.status not in (
                ChatMemberStatus.OWNER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.MEMBER
            ):
                return False
        except:
            return False

    return True

subscribed = filters.create(is_subscribed)

# ================= ENCODE / DECODE =================

def encode(string: str):
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    return base64_bytes.decode("ascii").rstrip("=")

def decode(base64_string: str):
    base64_string = base64_string.rstrip("=")
    base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
    return base64.urlsafe_b64decode(base64_bytes).decode("ascii")

# ================= MESSAGE FETCH =================

async def get_messages(client, message_ids):
    messages = []
    total = 0

    while total != len(message_ids):
        temp_ids = message_ids[total:total+200]
        try:
            msgs = await client.get_messages(
                chat_id=client.db_channel.id,
                message_ids=temp_ids
            )
        except FloodWait as e:
            await asyncio.sleep(e.value)
            msgs = await client.get_messages(
                chat_id=client.db_channel.id,
                message_ids=temp_ids
            )
        except:
            msgs = []

        total += len(temp_ids)
        messages.extend(msgs)

    return messages

# ================= MESSAGE ID EXTRACT =================

async def get_message_id(client, message):

    if message.forward_from_chat:
        if message.forward_from_chat.id == client.db_channel.id:
            return message.forward_from_message_id
        return 0

    if message.forward_sender_name:
        return 0

    if message.text:
        pattern = r"https://t\.me/(?:c/)?(.*)/(\d+)"
        matches = re.match(pattern, message.text)
        if not matches:
            return 0

        channel_id = matches.group(1)
        msg_id = int(matches.group(2))

        if channel_id.isdigit():
            if f"-100{channel_id}" == str(client.db_channel.id):
                return msg_id
        else:
            if channel_id == client.db_channel.username:
                return msg_id

    return 0

# ================= VERIFY SYSTEM =================

async def get_verify_status(user_id):
    return await db_verify_status(user_id)

async def update_verify_status(user_id, verify_token="", is_verified=False, verified_time=0, link=""):

    current = await db_verify_status(user_id)

    current["verify_token"] = verify_token
    current["is_verified"] = is_verified
    current["verified_time"] = verified_time
    current["link"] = link

    await db_update_verify_status(user_id, current)

# ================= SHORTLINK =================

async def get_shortlink(url, api, link):
    shortzy = Shortzy(api_key=api, base_site=url)
    return await shortzy.convert(link)

# ================= TIME FORMAT =================

def get_exp_time(seconds):
    periods = [
        ('days', 86400),
        ('hours', 3600),
        ('mins', 60),
        ('secs', 1)
    ]
    result = ''
    for name, sec in periods:
        if seconds >= sec:
            val, seconds = divmod(seconds, sec)
            result += f'{int(val)}{name}'
    return result

def get_readable_time(seconds: int) -> str:
    count = 0
    time_list = []
    suffix = ["s", "m", "h", "days"]

    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)

    for i in range(len(time_list)):
        time_list[i] = str(time_list[i]) + suffix[i]

    if len(time_list) == 4:
        time_list.pop()

    time_list.reverse()
    return ":".join(time_list)
