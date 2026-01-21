from pyrogram import Client, filters
from pyrogram.types import (
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
import re

from bot import Bot
from database.database import series_catalog   # ⚠️ agar tumhare DB file me name alag ho to yahi change karo

# ---------------- HELPERS ----------------

def clean_query(q):
    return re.sub(r"[^a-z0-9 ]","",q.lower()).strip()

# ---------------- INLINE SEARCH ----------------

@Bot.on_inline_query()
async def inline_search(client: Client, inline_query):

    query = clean_query(inline_query.query)

    if len(query) < 2:
        await inline_query.answer([], cache_time=1)
        return

    results = []

    # Mongo regex search on title key
    cursor = series_catalog.find({"_id": {"$regex": query}}).limit(20)

    async for doc in cursor:

        title_key = doc["_id"]
        post_id = doc["post_id"]
        episodes = doc.get("episodes", [])

        title_display = title_key.replace("_"," ").title()

        text = f"🎬 {title_display}\n\n" + "\n\n".join(episodes[:5])

        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 Open Post", url=f"https://t.me/{client.username}?start=post_{post_id}")]
        ])

        results.append(
            InlineQueryResultArticle(
                title=title_display,
                description=f"{len(episodes)} files available",
                input_message_content=InputTextMessageContent(text),
                reply_markup=btn
            )
        )

    await inline_query.answer(results, cache_time=5)
