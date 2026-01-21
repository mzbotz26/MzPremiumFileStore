import re, asyncio, aiohttp
import PTN
from collections import defaultdict
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

# ---------------- CLEAN TITLE ----------------

def clean_title(name):
    if not name:
        return "", None

    name = name.replace(".", " ").replace("_", " ").replace("-", " ")

    year_match = re.search(r"\b(19|20)\d{2}\b", name)
    year = year_match.group(0) if year_match else None

    name = re.sub(r"\b(19|20)\d{2}\b", "", name)

    name = re.sub(
        r"\b(480p|720p|1080p|2160p|4k|x264|x265|hevc|hdrip|webdl|webrip|bluray|brrip|hdtc|hdts|cam|telegram|tme|movieshub|filmyzilla|mzmoviiez|mzmoviies|hindi|english|marathi|tamil|telugu|malayalam|dual|audio)\b",
        "", name, flags=re.I
    )

    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)
    name = re.sub(r"[^a-zA-Z0-9 ]", "", name)
    name = re.sub(r"\s+", " ", name).strip()

    return name.title(), year

def merge_key(title, year=None, season=None):
    key = re.sub(r"[^a-z0-9]", "", title.lower())
    if year:
        key += year
    if season:
        key += f"s{season}"
    return key

# ---------------- UTILS ----------------

def bytes_to_size(size):
    mb = round(size / 1024 / 1024, 2)
    return f"{mb} MB" if mb < 1024 else f"{round(mb/1024,2)} GB"

def detect_audio(name):
    langs=[x.capitalize() for x in ["hindi","english","telugu","tamil","malayalam","marathi","kannada","punjabi"] if x in name.lower()]
    return " / ".join(langs) if langs else "Unknown"

def detect_quality(res):
    if not res: return ""
    for q in ["2160","1080","720","480"]:
        if q in res: return f"{q}p"
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

# ---------------- API FETCH ----------------

def imdb_fetch(title, year=None):
    try:
        s = ia.search_movie(title)
        if not s:
            return None,None,None,None,None,None

        m = None
        for r in s:
            if year and str(r.get("year","")) == year:
                m = ia.get_movie(r.movieID)
                break

        if not m:
            m = ia.get_movie(s[0].movieID)

        return (
            m.get("full-size cover url"),
            str(m.get("rating","N/A")),
            str(m.get("year","")),
            m.get("plot outline"),
            " / ".join(m.get("genres",[])),
            m.movieID
        )
    except:
        return None,None,None,None,None,None

async def tmdb_fetch(title, year=None, is_tv=False):
    try:
        url="tv" if is_tv else "movie"
        async with aiohttp.ClientSession() as s:
            r = await (await s.get(f"https://api.themoviedb.org/3/search/{url}?api_key={TMDB_API_KEY}&query={title}")).json()
            if not r.get("results"): 
                return None,None,None,None,None,None

            mid = r["results"][0]["id"]

            d = await (await s.get(f"https://api.themoviedb.org/3/{url}/{mid}?api_key={TMDB_API_KEY}")).json()

        return (
            "https://image.tmdb.org/t/p/w500"+d.get("poster_path","") if d.get("poster_path") else None,
            str(d.get("vote_average","N/A")),
            d.get("release_date","")[:4] or d.get("first_air_date","")[:4],
            d.get("overview"),
            " / ".join([g["name"] for g in d.get("genres",[])]),
            d.get("imdb_id","")
        )
    except:
        return None,None,None,None,None,None

# ---------------- MAIN ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client,message):

    if not (message.document or message.video):
        return

    media = message.document or message.video
    if not media.file_name:
        return

    parsed = PTN.parse(media.file_name) or {}

    title, title_year = clean_title(parsed.get("title",""))

    if not title:
        return

    season = parsed.get("season")
    episode = parsed.get("episode")
    is_series = bool(season or episode)

    poster,rating,year,story,genres,imdb_id = imdb_fetch(title, title_year)

    if not poster or not story:
        t = await tmdb_fetch(title, title_year, is_series)
        poster = poster or t[0]
        rating = rating or t[1]
        year   = year   or t[2]
        story  = story  or t[3]
        genres = genres or t[4]
        imdb_id= imdb_id or t[5]

    if not story:
        story = f"{title} is a popular movie loved by audiences."

    display_title = f"{title} ({year})" if year else title

    key = merge_key(title, year, season)

    async with locks[key]:

        code = encode(f"get-{message.id*abs(client.db_channel.id)}")
        link = f"https://t.me/{client.username}?start={code}"

        res = detect_quality(parsed.get("resolution",""))
        src = detect_source(media.file_name)
        codec = parsed.get("codec","x264")
        size = bytes_to_size(media.file_size)

        ep_tag = f"S{season:02d}E{episode:02d} " if season and episode else ""

        line = f"📂 ➤ {ep_tag}{res} {codec} {src}\n🔗 ➪ <a href='{link}'>Get File</a> ({size})"

        head = f"""🎬 {display_title}

🎞 Genres: {genres or "N/A"}
⭐ Rating: {rating or "N/A"}/10
📆 Year: {year or "N/A"}

📖 Story:
{story}

"""

        footer = f"""

🔊 Audio: {detect_audio(media.file_name)}

💪 Powered By : <a href="https://t.me/MzMoviiez">MzMoviiez</a>
"""

        imdb_url = f"https://www.imdb.com/title/tt{imdb_id}/" if imdb_id and imdb_id.isdigit() else f"https://google.com/search?q={display_title}+imdb"

        imdb_btn = InlineKeyboardButton("🎬 IMDb", url=imdb_url)
        search_btn = InlineKeyboardButton("🔍 Search", url=f"https://t.me/{client.username}?inlinequery={display_title}")

        kb = InlineKeyboardMarkup([[imdb_btn,search_btn]])

        old = await get_series(key)

        if old:
            eps = old["episodes"]
            if line not in eps:
                eps.append(line)
                eps.sort(key=sort_key)
                await update_series_episodes(key,eps)

            await client.edit_message_text(
                POST_CHANNEL,
                old["post_id"],
                head+"\n\n".join(eps)+footer,
                parse_mode=ParseMode.HTML,
                reply_markup=kb
            )
            return

        if poster:
            msg = await client.send_photo(
                POST_CHANNEL,
                poster,
                caption=head+line+footer,
                parse_mode=ParseMode.HTML,
                reply_markup=kb
            )
        else:
            msg = await client.send_message(
                POST_CHANNEL,
                head+line+footer,
                parse_mode=ParseMode.HTML,
                reply_markup=kb
            )

        await save_series(key,msg.id,[line])
