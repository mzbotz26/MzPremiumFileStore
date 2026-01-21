import re, asyncio, aiohttp
import PTN
from collections import defaultdict
from difflib import get_close_matches
from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes
from imdb import Cinemagoer

ia = Cinemagoer()
locks = defaultdict(lambda: asyncio.Lock())

# ---------------- TITLE CLEAN ----------------

def clean_title_with_year(name):
    name = name.replace(".", " ").replace("_", " ").replace("-", " ")
    year_match = re.search(r"\b(19|20)\d{2}\b", name)
    year = year_match.group(0) if year_match else ""
    name = re.sub(r"\b(19|20)\d{2}\b", "", name)

    name = re.sub(
        r"\b(480p|720p|1080p|2160p|4k|x264|x265|hevc|hdrip|webdl|webrip|bluray|brrip|hdtc|hdts|cam|hindi|english|marathi|tamil|telugu|malayalam|dual|audio|telegram|tme|movieshub|filmyzilla|mzmoviiez|mzmoviies)\b",
        "", name, flags=re.I
    )

    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)
    name = re.sub(r"[^a-zA-Z0-9 ]", "", name)
    name = re.sub(r"\s+", " ", name).strip()

    return f"{name.title()} {year}" if year else name.title()

def merge_key_title(title):
    return re.sub(r"[^a-z0-9]", "", title.lower())

# ---------------- AUDIO ----------------

def detect_audio(name):
    langs=[]
    for a in ["hindi","english","telugu","tamil","malayalam","marathi","kannada","punjabi"]:
        if a in name.lower():
            langs.append(a.capitalize())
    return " / ".join(langs) if langs else "Unknown"

# ---------------- UTILS ----------------

def bytes_to_size(size):
    mb = round(size / 1024 / 1024, 2)
    return f"{mb} MB" if mb < 1024 else f"{round(mb/1024,2)} GB"

def detect_quality(res):
    if not res: return ""
    if "2160" in res or "4k" in res.lower(): return "2160p"
    if "1080" in res: return "1080p"
    if "720" in res: return "720p"
    if "480" in res: return "480p"
    return res

def detect_source(name):
    for s in ["bluray","brrip","webdl","webrip","hdrip","cam","hdts","hdtc"]:
        if s in name.lower():
            return s.upper()
    return "WEB-DL"

def sort_key(x):
    for i,o in enumerate(["480","720","1080","2160"]):
        if o in x: return i
    return 99

# ---------------- IMDb ----------------

def imdb_fetch(title):
    try:
        s = ia.search_movie(title)
        if not s: return None,None,None,None,None,None
        m = ia.get_movie(s[0].movieID)

        poster = m.get("full-size cover url")
        rating = str(m.get("rating","N/A"))
        year = str(m.get("year",""))
        story = m.get("plot outline")
        genres = " / ".join(m.get("genres",[]))
        imdb_id = m.movieID

        return poster,rating,year,story,genres,imdb_id
    except:
        return None,None,None,None,None,None

# ---------------- TMDB FALLBACK ----------------

async def tmdb_fetch(title):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
            ) as r:
                s = await r.json()

            if not s.get("results"):
                return None,None,None,None,None,None

            mid=s["results"][0]["id"]

            async with session.get(
                f"https://api.themoviedb.org/3/movie/{mid}?api_key={TMDB_API_KEY}"
            ) as r:
                d = await r.json()

        poster="https://image.tmdb.org/t/p/w500"+d.get("poster_path","") if d.get("poster_path") else None
        rating=str(d.get("vote_average","N/A"))
        year=d.get("release_date","")[:4]
        story=d.get("overview")
        genres=" / ".join([g["name"] for g in d.get("genres",[])])
        imdb_id=d.get("imdb_id","")

        return poster,rating,year,story,genres,imdb_id
    except:
        return None,None,None,None,None,None

# ---------------- AI STORY FALLBACK ----------------

def ai_story_fallback(title):
    return f"{title} is a must-watch movie packed with entertainment, emotions and unforgettable moments."

# ---------------- MAIN ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not (message.document or message.video):
        return

    media = message.document or message.video
    fname = media.file_name
    size = media.file_size

    audio = detect_audio(fname)

    parsed = PTN.parse(fname)
    raw_title = parsed.get("title","")

    title = clean_title_with_year(raw_title)
    if not title:
        return

    poster,rating,year,story,genres,imdb_id = imdb_fetch(title)

    if not poster or not story:
        tposter,trating,tyear,tstory,tgenres,timdb = await tmdb_fetch(title)
        poster=poster or tposter
        rating=rating or trating
        year=year or tyear
        story=story or tstory
        genres=genres or tgenres
        imdb_id=imdb_id or timdb

    if not story:
        story = ai_story_fallback(title)

    merge_key = merge_key_title(title)

    async with locks[merge_key]:

        code = encode(f"get-{message.id*abs(client.db_channel.id)}")
        link = f"https://t.me/{client.username}?start={code}"

        resolution = detect_quality(parsed.get("resolution",""))
        codec = parsed.get("codec","x264")
        source = detect_source(fname)
        size_text = bytes_to_size(size)

        line = f"""📂 ➤ {resolution} {codec} {source}
🔗 ➪ <a href='{link}'>Get File</a> ({size_text})"""

        imdb_btn = InlineKeyboardButton(
            "🎬 IMDb",
            url=f"https://www.imdb.com/title/tt{imdb_id}/" if imdb_id else f"https://www.google.com/search?q={title}+imdb"
        )

        search_btn = InlineKeyboardButton(
            "🔍 Search",
            url=f"https://t.me/{client.username}?inlinequery={title}"
        )

        buttons = InlineKeyboardMarkup([[imdb_btn, search_btn]])

        head = f"""🎬 {title}

🎞 Genres: {genres or "N/A"}
⭐ Rating: {rating or "N/A"}/10
📆 Year: {year or "N/A"}

📖 Story:
{story}

"""

        footer = f"""

🔊 Audio: {audio}

💪 Powered By : <a href="https://t.me/MzMoviiez">MzMoviiez</a>
"""

        text = head + line + footer

        if poster:
            await client.send_photo(POST_CHANNEL, poster, caption=text, parse_mode=ParseMode.HTML, reply_markup=buttons)
        else:
            await client.send_message(POST_CHANNEL, text, parse_mode=ParseMode.HTML, reply_markup=buttons)
