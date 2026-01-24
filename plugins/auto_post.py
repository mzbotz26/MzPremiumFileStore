import re, requests, asyncio
import PTN
from difflib import get_close_matches
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes
from imdb import Cinemagoer

ia = Cinemagoer()
locks = {}

# ---------------- TITLE CLEAN ----------------

def clean_title(raw):
    if not raw:
        return ""

    raw = raw.replace(".", " ").replace("_", " ").replace("-", " ")
    raw = re.sub(r"\(.*?\)|\[.*?\]", "", raw)

    raw = re.sub(
        r"\b(onlymovies|mzmoviiez|mzmoviies|telegram|tme|movieshub|filmyzilla|south|uncut|mk)\b",
        "", raw, flags=re.I
    )

    raw = re.sub(r"\b(480p|720p|1080p|2160p|4k|10bit)\b", "", raw, flags=re.I)
    raw = re.sub(
        r"\b(x264|x265|hevc|hdrip|webdl|webrip|bluray|brrip|amzn|nf|dsnp|hdtc|hdts|cam|aac|ddp|dts)\b",
        "", raw, flags=re.I
    )

    raw = re.sub(r"\b(hindi|english|telugu|tamil|malayalam|marathi|dual|audio)\b", "", raw, flags=re.I)
    raw = re.sub(r"\b\d+kbps\b", "", raw, flags=re.I)
    raw = re.sub(r"\b(19|20)\d{2}\b", "", raw)

    raw = re.sub(r"[^a-zA-Z0-9 ]", "", raw)
    raw = re.sub(r"\s+", " ", raw).strip()

    return raw.title()

def merge_key_title(title):
    return re.sub(r"[^a-z0-9]", "", title.lower())

# ---------------- EP RANGE ----------------

def detect_episode_range(name):
    nums = re.findall(r"(?:E|EP|EPI)?\s*(\d{1,2})", name, re.I)
    nums = sorted({int(n) for n in nums})
    if len(nums) >= 2:
        return f"E{nums[0]:02d}–E{nums[-1]:02d}"
    return None

# ---------------- AUDIO ----------------

def detect_audio(name):
    audio_map = {
        "hindi":"Hindi","english":"English","telugu":"Telugu","tamil":"Tamil",
        "malayalam":"Malayalam","marathi":"Marathi","punjabi":"Punjabi","kannada":"Kannada"
    }
    langs = [v for k,v in audio_map.items() if k in name.lower()]
    return " / ".join(sorted(set(langs))) if langs else "Unknown"

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
    for s in ["bluray","brrip","webdl","webrip","hdrip","amzn","nf","dsnp","cam","hdts","hdtc"]:
        if s in name.lower():
            return s.upper()
    return "WEB-DL"

def sort_key(x):
    for i,o in enumerate(["480","720","1080","2160"]):
        if o in x:
            return i
    return 99

# ---------------- IMDb ----------------

def imdb_fetch(title):
    try:
        s = ia.search_movie(title)
        if not s:
            return None,None,None,None,None

        m = ia.get_movie(s[0].movieID)
        return (
            m.get("full-size cover url"),
            str(m.get("rating","N/A")),
            str(m.get("year","")),
            m.get("plot outline","N/A"),
            " / ".join(m.get("genres",[]))
        )
    except:
        return None,None,None,None,None

# ---------------- TMDB ----------------

def tmdb_fetch(title, is_series=False, season=None):
    try:
        url = "tv" if is_series else "movie"

        def search(lang):
            return requests.get(
                f"https://api.themoviedb.org/3/search/{url}?api_key={TMDB_API_KEY}&query={title}&language={lang}",
                timeout=10
            ).json()

        s = search("hi-IN")
        if not s.get("results"):
            s = search("en-US")
            if not s.get("results"):
                return None,None,None,None,None

        mid = s["results"][0]["id"]

        if is_series and season:
            d = requests.get(
                f"https://api.themoviedb.org/3/tv/{mid}/season/{season}?api_key={TMDB_API_KEY}&language=en-US",
                timeout=10
            ).json()
        else:
            d = requests.get(
                f"https://api.themoviedb.org/3/{url}/{mid}?api_key={TMDB_API_KEY}&language=en-US",
                timeout=10
            ).json()

        poster = "https://image.tmdb.org/t/p/w500"+d.get("poster_path","") if d.get("poster_path") else None
        rating = str(d.get("vote_average","N/A"))
        year = (d.get("first_air_date") if is_series else d.get("release_date",""))[:4]
        story = d.get("overview","N/A")
        genres = " / ".join([g["name"] for g in d.get("genres",[])])

        return poster,rating,year,story,genres
    except:
        return None,None,None,None,None

# ---------------- MAIN ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not (message.document or message.video):
        return

    media = message.document or message.video
    fname = media.file_name
    size = media.file_size

    parsed = PTN.parse(fname) or {}

    raw_title = parsed.get("title") or fname
    season = parsed.get("season")
    episode = parsed.get("episode")
    ep_range = detect_episode_range(fname)

    is_series = bool(season or episode or ep_range)

    title = clean_title(raw_title)
    if not title:
        return

    poster,rating,year,story,genres = imdb_fetch(title)

    if not poster or not story:
        tposter,trating,tyear,tstory,tgenres = tmdb_fetch(title, is_series, season)
        poster = poster or tposter
        rating = rating or trating
        year   = year   or tyear
        story  = story  or tstory
        genres = genres or tgenres

    merge_key = merge_key_title(title)
    if year:
        merge_key += f"_{year}"
    if is_series and season:
        merge_key += f"_s{season}"

    if merge_key not in locks:
        locks[merge_key] = asyncio.Lock()

    async with locks[merge_key]:

        try:
            code = await encode(f"get-{message.id*abs(client.db_channel.id)}")
        except:
            code = encode(f"get-{message.id*abs(client.db_channel.id)}")

        link = f"https://t.me/{client.username}?start={code}"

        resolution = detect_quality(parsed.get("resolution",""))
        codec = parsed.get("codec","x264")
        source = detect_source(fname)
        audio = detect_audio(fname)
        size_text = bytes_to_size(size)

        if is_series:
            ep_tag = ep_range or (f"E{episode:02d}" if episode else f"Season {season}")
            title_line = f"{title} (Season {season})"
            tag = "📺 Series"
        else:
            ep_tag = "Movie"
            title_line = title
            tag = "🎬 Movie"

        line = f"""📂 ➤ {ep_tag} {resolution} {codec} {source}
🔗 ➪ <a href='{link}'>Get File</a> ({size_text})"""

        head = f"""🎬 {title_line}

🏷 Type: {tag}
🎞 Genres: {genres or "N/A"}
⭐ Rating: {rating or "N/A"}/10
📆 Year: {year or "N/A"}

📖 Story:
{story or "N/A"}

"""

        footer = f"""

🔊 Audio: {audio}

💪 Powered By : <a href="https://t.me/MzMoviiez">MzMoviiez</a>
"""

        old = await get_series(merge_key)

        if old:
            eps = old["episodes"]
            if line not in eps:
                eps.append(line)
                eps.sort(key=sort_key)
                await update_series_episodes(merge_key, eps)

            await client.edit_message_text(
                POST_CHANNEL,
                old["post_id"],
                head + "\n\n".join(eps) + footer,
                parse_mode=ParseMode.HTML
            )
            return

        text = head + line + footer

        if poster:
            msg = await client.send_photo(POST_CHANNEL, poster, caption=text, parse_mode=ParseMode.HTML)
        else:
            msg = await client.send_message(POST_CHANNEL, text, parse_mode=ParseMode.HTML)

        await save_series(merge_key, msg.id, [line])
