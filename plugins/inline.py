from pyrogram import filters
from pyrogram.types import (
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from bot import Bot
from database.database import full_userbase, get_series

# ================= INLINE SEARCH =================

@Bot.on_inline_query()
async def inline_search(client, query):

    text = query.query.strip().lower()

    if not text:
        return await query.answer([], cache_time=1)

    results = []

    # Fetch all series titles from DB
    data = await get_series_all()

    for item in data:

        title = item.get("title","")
        post_id = item.get("post_id")
        episodes = item.get("episodes",[])

        if text in title.lower():

            link = f"https://t.me/{client.username}/{post_id}"

            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎬 Open Post", url=link)]
            ])

            msg = f"🎬 <b>{title}</b>\n\n📺 Total Episodes: {len(episodes)}\n\n👇 Click below to open"

            results.append(
                InlineQueryResultArticle(
                    title=title,
                    description=f"{len(episodes)} Episodes",
                    input_message_content=InputTextMessageContent(
                        msg,
                        parse_mode="html"
                    ),
                    reply_markup=btn
                )
            )

        if len(results) >= 20:
            break

    await query.answer(results, cache_time=10, is_personal=True)


# ================= DB FETCH =================

async def get_series_all():
    from database.database import series_catalog
    cursor = series_catalog.find({})
    return [x async for x in cursor]
