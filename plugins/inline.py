from pyrogram import Client
from pyrogram.types import (
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
import re

from bot import Bot
from database.database import series_catalog   # agar name alag ho to change karo

# ---------------- HELPERS ----------------

def clean_query(q: str):
    return re.sub(r"[^a-z0-9 ]", "", q.lower()).strip()

def display_title(key: str):
    return key.replace("_", " ").title()

# ---------------- INLINE SEARCH ----------------

@Bot.on_inline_query()
async def inline_search(client: Client, inline_query):

    query = clean_query(inline_query.query)

    if not query or len(query) < 2:
        await inline_query.answer([], cache_time=1, is_personal=True)
        return

    results = []

    # Case-insensitive regex search
    cursor = series_catalog.find(
        {"_id": {"$regex": query, "$options": "i"}}
    ).limit(20)

    async for doc in cursor:

        title_key = doc.get("_id")
        post_id = doc.get("post_id")
        episodes = doc.get("episodes", [])

        if not title_key or not post_id:
            continue

        title_display = display_title(title_key)

        preview_eps = episodes[:5]
        preview_text = "\n\n".join(preview_eps) if preview_eps else "No files yet."

        text = f"🎬 {title_display}\n\n{preview_text}"

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "📂 Open Post",
                    url=f"https://t.me/{client.username}?start=post_{post_id}"
                )
            ]
        ])

        results.append(
            InlineQueryResultArticle(
                title=title_display,
                description=f"{len(episodes)} files available",
                input_message_content=InputTextMessageContent(
                    text,
                    disable_web_page_preview=True
                ),
                reply_markup=buttons
            )
        )

    await inline_query.answer(
        results,
        cache_time=5,
        is_personal=True
        )
