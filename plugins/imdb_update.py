from pyrogram import filters
from bot import Bot
import aiohttp
from config import TMDB_API_KEY


@Bot.on_message(filters.command("imdb") & filters.private)
async def imdb_update(client, message):

    name = message.text.replace("/imdb", "").strip()

    if not name:
        return await message.reply("❌ Send movie name\nExample: /imdb Avatar")

    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={name}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            r = await resp.json()

    if not r.get("results"):
        return await message.reply("❌ Movie not found")

    d = r["results"][0]

    title = d.get("title", "N/A")
    year = d.get("release_date", "")[:4]
    rating = d.get("vote_average", "N/A")
    overview = d.get("overview", "No description available.")

    text = f"""🎬 {title} ({year})

⭐ IMDb: {rating}/10

📝 {overview}
"""

    await message.reply(text)
