"""Get your Telegram ID
Syntax: /id"""

from pyrogram import filters, enums
from pyrogram.types import Message
from bot import Bot


@Bot.on_message(filters.command("id") & filters.private)
async def showid(client, message: Message):

    if message.chat.type == enums.ChatType.PRIVATE:
        user_id = message.from_user.id

        await message.reply(
            f"<b>Your User ID is:</b> <code>{user_id}</code>",
            quote=True
        )
