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

def detect_episode_range(name):
    m = re.search(
        r"(?:\[)?(?:E|EP|EPI|Episode)?\s*(\d{1,2})\s*(?:-|–|to)\s*(?:E|EP|EPI|Episode)?\s*(\d{1,2})(?:\])?",
        name,
        re.I
    )
    if m:
        return f"E{int(m.group(1)):02d}–E{int(m.group(2)):02d}"
    return None

def quality_badge(res):
    res = res or ""
    if "2160" in res: return "🔴 4K"
    if "1080" in res: return "🟣 1080p"
    if "720"  in res: return "🔵 720p"
    if "480"  in res: return "🟢 480p"
    return res

def clean_title(name):
    if not name:
        return "", None

    name = name.replace(".", " ").replace("_", " ").replace("-", " ")
    year = extract_year(name)
    name = re.sub(r"\b(19|20)\d{2}\b", "", name)

    name = re.sub(
        r"\b(480p|720p|1080p|2160p|4k|10bit|x264|x265|hevc|hdrip|webdl|webrip|bluray|brrip|amzn|nf|dsnp|hdtc|hdts|cam|telegram|tme|movieshub|filmyzilla|mzmoviiez|mzmoviies|season|complete|pack|combined|hindi|english|marathi|tamil|telugu|malayalam|dual|audio)\b",
        "",
        name,
        flags=re.I
    )

    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)
    name = re.sub(r"[^a-zA-Z0-9 ]", "", name)
    name = re.sub(r"\s+", " ", name).strip()

    return name.title(), year

def merge_key(title, year=None, season=None):
    key = re.sub(r"[^a-z0-9]", "", title.lower())
    if year: key += year
    if season: key += f"s{season}"
    return key

# ---------------- UTILS ----------------

def bytes_to_size(size):
    mb = round(size / 1024 / 1024, 2)
    return f"{mb} MB" if mb < 1024 else f"{round(mb/1024,2)} GB"

def detect_audio(name):
    return [x.capitalize() for x in ["hindi","english","telugu","tamil","malayalam","marathi","kannada","punjabi"] if x in name.lower()]

def audio_label(name):
    langs = detect_audio(name)
    if len(langs) > 1:
        return "Dual Audio" if len(langs) == 2 else "Multi Audio"
    return langs[0] if langs else "Unknown"

def detect_source(name):
    for s in ["bluray","brrip","webdl","webrip","hdrip","amzn","nf","dsnp","cam","hdts","hdtc"]:
        if s in name.lower():
            return s.upper()
    return "WEB-DL"

def sort_key(x):
    for i,o in enumerate(["480","720","1080","2160"]):
        if o in x:
            return i
    return 99

# ---------------- IMDb & TMDB ----------------

def imdb_fetch(title, year=None):
    try:
        q = f"{title} {year}" if year else title
        r = ia.search_movie(q)
        if not r:
            return None,None,None,None,None,None

        for m in r:
            if year and str(m.get("year","")) == str(year):
                m = ia.get_movie(m.movieID)
                break
        else:
            m = ia.get_movie(r[0].movieID)

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
        url = "tv" if is_tv else "movie"
        query = f"{title} {year}" if year else title

        async with aiohttp.ClientSession() as s:
            r = await (await s.get(
                f"https://api.themoviedb.org/3/search/{url}?api_key={TMDB_API_KEY}&query={quote_plus(query)}"
            )).json()

            res = r.get("results") or []
            if not res:
                return None,None,None,None,None,None

            d0 = next((x for x in res if str(year) in str(x.get("release_date",""))), res[0])
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
            d.get("imdb_id",""),
            mid
        )
    except:
        return None,None,None,None,None,None,None

async def fetch_season_poster(tmdb_id, season):
    try:
        async with aiohttp.ClientSession() as s:
            d = await (await s.get(
                f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season}?api_key={TMDB_API_KEY}"
            )).json()

        if d.get("poster_path"):
            return "https://image.tmdb.org/t/p/w500"+d["poster_path"]
    except:
        pass
    return None

# ---------------- MAIN ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not (message.document or message.video):
        return

    media = message.document or message.video
    if not media.file_name:
        return

    parsed = PTN.parse(media.file_name) or {}
    title, year = clean_title(parsed.get("title") or media.file_name)
    year = year or extract_year(media.file_name)

    season  = parsed.get("season")
    episode = parsed.get("episode")
    ep_range = detect_episode_range(media.file_name)

    is_series = bool(season or episode or ep_range)

    poster, rating, y, story, genres, imdb_id, tmdb_id = await tmdb_fetch(title, year, is_series)
    i = imdb_fetch(title, year)

    poster = poster or i[0]
    rating = rating or i[1]
    year   = y or i[2] or year
    story  = story or i[3]
    genres = genres or i[4]
    imdb_id= imdb_id or i[5]

    # 🎯 SEASON POSTER OVERRIDE
    if is_series and season and tmdb_id:
        sp = await fetch_season_poster(tmdb_id, season)
        if sp:
            poster = sp

    display_title = f"{title} ({year})"
    tag_label = "📺 Series" if is_series else "🎬 Movie"

    key = merge_key(title, year, season if is_series else None)

    async with locks[key]:

        code = encode(f"get-{message.id*abs(client.db_channel.id)}")
        link = f"https://t.me/{client.username}?start={code}"

        ep_tag = ep_range or (f"E{episode:02d}" if episode else "Movie")

        line = f"📂 ➤ {quality_badge(parsed.get('resolution',''))} {parsed.get('codec','x264')} {detect_source(media.file_name)} {ep_tag}\n🔗 ➪ <a href='{link}'>Get File</a> ({bytes_to_size(media.file_size)})"

        season_title = f"\n📺 <b>Season {season}</b>\n" if is_series and season else ""

        head = f"""🎬 {display_title}

🏷 Type: {tag_label}
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

        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🎬 IMDb", url=f"https://www.imdb.com/title/tt{imdb_id}/" if imdb_id else f"https://google.com/search?q={quote_plus(display_title)}+imdb"),
            InlineKeyboardButton("🔍 Search", url=f"https://t.me/{client.username}?inlinequery={quote_plus(display_title)}")
        ]])

        old = await get_series(key)

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
