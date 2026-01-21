from pyrogram import filters
from pyrogram.types import InlineQueryResultArticle, InputTextMessageContent
from bot import Bot
from database.database import search_titles

@Bot.on_inline_query()
async def inline_handler(client,query):

    q=query.query.lower().strip()
    if not q: return

    results=[]
    data=await search_titles(q)

    for i in data:
        results.append(
            InlineQueryResultArticle(
                title=i["title"],
                description="Tap to open post",
                input_message_content=InputTextMessageContent(i["url"])
            )
        )

    await query.answer(results,cache_time=1)
