import re, asyncio, aiohttp
import PTN
from urllib.parse import quote_plus
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

# ---------------- HELPERS ----------------

def extract_year(name):
    m = re.search(r"\b(19|20)\d{2}\b", name)
    return m.group(0) if m else None

def clean_title(name):
    if not name:
        return "", None

    name = name.replace(".", " ").replace("_", " ").replace("-", " ")
    year = extract_year(name)
    name = re.sub(r"\b(19|20)\d{2}\b", "", name)

    name = re.sub(
        r"\b(480p|720p|1080p|2160p|4k|x264|x265|hevc|hdrip|webdl|webrip|bluray|brrip|hdtc|hdts|cam|telegram|tme|movieshub|filmyzilla|mzmoviiez|mzmoviies|season|complete|pack|hindi|english|marathi|tamil|telugu|malayalam|dual|audio)\b",
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
    langs = [x.capitalize() for x in ["hindi","english","telugu","tamil","malayalam","marathi","kannada","punjabi"] if x in name.lower()]
    return langs

def audio_label(name):
    langs = detect_audio(name)
    if len(langs) > 1:
        return "Dual Audio" if len(langs) == 2 else "Multi Audio"
    return langs[0] if langs else "Unknown"

def detect_quality(res):
    if not res:
        return ""
    for q in ["2160","1080","720","480"]:
        if q in res:
            return f"{q}p"
    return res

def detect_source(name):
    for s in ["bluray","brrip","webdl","webrip","hdrip","cam","hdts","hdtc"]:
        if s in name.lower():
            return s.upper()
    return "WEB-DL"

def sort_key(x):
    for i, o in enumerate(["480","720","1080","2160"]):
        if o in x:
            return i
    return 99

# ---------------- IMDb ----------------

def imdb_fetch(title, year=None):
    try:
        query = f"{title} {year}" if year else title
        s = ia.search_movie(query)
        if not s:
            return None,None,None,None,None,None

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

# ---------------- TMDB ----------------

async def tmdb_fetch(title, year=None, is_tv=False):
    try:
        url = "tv" if is_tv else "movie"
        query = f"{title} {year}" if year else title

        async with aiohttp.ClientSession() as s:
            r = await (await s.get(
                f"https://api.themoviedb.org/3/search/{url}?api_key={TMDB_API_KEY}&query={quote_plus(query)}"
            )).json()

            if not r.get("results"):
                return None,None,None,None,None,None

            d0 = r["results"][0]
            mid = d0["id"]

            d = await (await s.get(
                f"https://api.themoviedb.org/3/{url}/{mid}?api_key={TMDB_API_KEY}"
            )).json()

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
async def auto_post(client, message):

    if not (message.document or message.video):
        return

    media = message.document or message.video
    if not media.file_name:
        return

    parsed = PTN.parse(media.file_name) or {}

    raw_title = parsed.get("title") or media.file_name
    title, year = clean_title(raw_title)

    file_year = extract_year(media.file_name)
    if not year:
        year = file_year

    if not title:
        title, _ = clean_title(media.file_name)

    season = parsed.get("season")
    episode = parsed.get("episode")
    is_series = bool(season or episode)

    title_year = year

    poster, rating, year, story, genres, imdb_id = await tmdb_fetch(title, title_year, is_series)

    if not poster:
        poster, rating, year, story, genres, imdb_id = await tmdb_fetch(title, None, is_series)

    i = imdb_fetch(title, title_year)
    poster = poster or i[0]
    rating = rating or i[1]
    year   = year   or i[2]
    story  = story  or i[3]
    genres = genres or i[4]
    imdb_id= imdb_id or i[5]

    display_title = f"{title} ({year})" if year else title.title()
    badge = "📺 Series" if is_series else "🎬 Movie"

    key = merge_key(title, year, season)

    async with locks[key]:

        code = encode(f"get-{message.id*abs(client.db_channel.id)}")
        link = f"https://t.me/{client.username}?start={code}"

        res = detect_quality(parsed.get("resolution",""))
        src = detect_source(media.file_name)
        codec = parsed.get("codec","x264")
        size = bytes_to_size(media.file_size)

        ep_tag = f"E{episode:02d}" if episode else "Season Pack"

        line = f"📂 ➤ {res} {codec} {src} {ep_tag}\n🔗 ➪ <a href='{link}'>Get File</a> ({size})"

        head = f"""🎬 {display_title}

🏷 Type: {badge}
🎞 Genres: {genres or "N/A"}
⭐ Rating: {rating or "N/A"}/10
📆 Year: {year or "N/A"}

📖 Story:
{story or "Story not available."}

"""

        footer = f"""

🔊 Audio: {audio_label(media.file_name)}

💪 Powered By : <a href="https://t.me/MzMoviiez">MzMoviiez</a>
"""

        safe_title = quote_plus(display_title)

        imdb_url = f"https://www.imdb.com/title/tt{imdb_id}/" if imdb_id and str(imdb_id).isdigit() else f"https://google.com/search?q={safe_title}+imdb"
        search_url = f"https://t.me/{client.username}?inlinequery={safe_title}"

        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎬 IMDb", url=imdb_url),
                InlineKeyboardButton("🔍 Search", url=search_url)
            ]
        ])

        old = await get_series(key)

        season_title = f"\n📺 Season {season}\n" if season else ""

        if old:
            eps = old["episodes"]

            if line not in eps:
                eps.append(line)
                eps.sort(key=sort_key)
                await update_series_episodes(key, eps)

            await client.edit_message_text(
                POST_CHANNEL,
                old["post_id"],
                head + season_title + "\n\n".join(eps) + footer,
                parse_mode=ParseMode.HTML,
                reply_markup=kb
            )
            return

        if poster:
            msg = await client.send_photo(
                POST_CHANNEL,
                poster,
                caption=head + season_title + line + footer,
                parse_mode=ParseMode.HTML,
                reply_markup=kb
            )
        else:
            msg = await client.send_message(
                POST_CHANNEL,
                head + season_title + line + footer,
                parse_mode=ParseMode.HTML,
                reply_markup=kb
            )

        await save_series(key, msg.id, [line])
