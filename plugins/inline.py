from pyrogram import Client
from pyrogram.types import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
import re
from bot import Bot
from database.database import series_catalog

@Bot.on_inline_query()
async def inline_search(client: Client, iq):

    q=re.sub(r"[^a-z0-9]","",iq.query.lower())

    if len(q)<2:
        return await iq.answer([],cache_time=1)

    res=[]
    cur=series_catalog.find({"_id":{"$regex":q}}).limit(20)

    async for d in cur:
        title=re.sub(r"(\d{4})",r" \1",d["_id"]).title()
        pid=d["post_id"]
        eps=d.get("episodes",[])

        text=f"🎬 {title}\n\n"+ "\n\n".join(eps[:5])

        kb=InlineKeyboardMarkup([[InlineKeyboardButton("📂 Open Post",url=f"https://t.me/{client.username}?start=post_{pid}")]])

        res.append(InlineQueryResultArticle(title=title,description=f"{len(eps)} files",input_message_content=InputTextMessageContent(text),reply_markup=kb))

    await iq.answer(res,cache_time=5)
