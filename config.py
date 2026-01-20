# By @mzbotz

import os
import logging
from logging.handlers import RotatingFileHandler

# ================= BOT =================

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
APP_ID = int(os.environ.get("APP_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")

# ================= API =================

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")

# ================= CHANNELS =================

POST_CHANNEL = int(os.environ.get("POST_CHANNEL", "-1001678291887"))
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1003487905802"))

FORCESUB_CHANNEL = int(os.environ.get("FORCESUB_CHANNEL", "-1001956378045"))
FORCESUB_CHANNEL2 = int(os.environ.get("FORCESUB_CHANNEL2", "-1002265223561"))
FORCESUB_CHANNEL3 = int(os.environ.get("FORCESUB_CHANNEL3", "-1001931113198"))

# ================= PUBLIC LINKS =================

MOVIE_GROUP = os.environ.get("MOVIE_GROUP", "https://t.me/MzMoviiezGroup")
UPDATE_CHANNEL = os.environ.get("UPDATE_CHANNEL", "https://t.me/MzMoviiez")

# ================= OWNER =================

OWNER_ID = int(os.environ.get("OWNER_ID", "5673859971"))
OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "SamMarathi")

# ================= DATABASE =================

DB_URI = os.environ.get("DATABASE_URL", "")
DB_NAME = os.environ.get("DATABASE_NAME", "mzfiles")

# ================= SERVER =================

PORT = int(os.environ.get("PORT", "8080"))
TG_BOT_WORKERS = int(os.environ.get("TG_BOT_WORKERS", "4"))

# ================= SHORTLINK STEP 1 =================

SHORTLINK_URL = os.environ.get("SHORTLINK_URL", "papajiurl.com")
SHORTLINK_API = os.environ.get("SHORTLINK_API", "41ff6d51799b604c63f6cfe75eb5b7a58794a850")

# ================= SHORTLINK STEP 2 =================

SHORTLINK_URL2 = os.environ.get("SHORTLINK_URL2", "shortxlinks.com")
SHORTLINK_API2 = os.environ.get("SHORTLINK_API2", "3b623c80e2c2534a5eae0bae35777c4c1aedd154")

# ================= VERIFY SYSTEM =================

IS_VERIFY = os.environ.get("IS_VERIFY", "True") == "True"

VERIFY_STEP_TIME = int(os.environ.get("VERIFY_STEP_TIME", "43200"))

VERIFY_TUT_1 = os.environ.get("VERIFY_TUT_1", "https://t.me/howtoopennlinks/19")
VERIFY_TUT_2 = os.environ.get("VERIFY_TUT_2", "https://t.me/howtoopennlinks/21")

# ================= START =================

START_PIC = os.environ.get("START_PIC", "https://graph.org/ℳℛЅᎯℳ-01-14")

START_MSG = os.environ.get(
    "START_MESSAGE",
    "<b>ʜᴇʟʟᴏ {first}\n\n"
    "ɪ ᴀᴍ ᴍᴜʟᴛɪ ғɪʟᴇ sᴛᴏʀᴇ ʙᴏᴛ.\n"
    "ɪ ᴄᴀɴ sᴛᴏʀᴇ ᴘʀɪᴠᴀᴛᴇ ғɪʟᴇs ᴀɴᴅ sʜᴀʀᴇ ᴛʜʀᴏᴜɢʜ sᴘᴇᴄɪᴀʟ ʟɪɴᴋs.</b>"
)

# ================= FORCE SUB =================

FORCE_MSG = os.environ.get(
    "FORCE_SUB_MESSAGE",
    "𝐒𝐨𝐫𝐫𝐲 {first}, 𝐲𝐨𝐮 𝐦𝐮𝐬𝐭 𝐣𝐨𝐢𝐧 𝐨𝐮𝐫 𝐜𝐡𝐚𝐧𝐧𝐞𝐥𝐬 𝐟𝐢𝐫𝐬𝐭."
)

# ================= CUSTOM CAPTION =================

CUSTOM_CAPTION = os.environ.get(
    "CUSTOM_CAPTION",
    "✨ <b>Powered By</b> ✨\n<a href='https://t.me/MzMoviiez'>MzMoviiez</a>"
)

# ================= SECURITY =================

PROTECT_CONTENT = os.environ.get("PROTECT_CONTENT", "False") == "True"
DISABLE_CHANNEL_BUTTON = os.environ.get("DISABLE_CHANNEL_BUTTON", "False") == "True"

# ================= ADMINS =================

try:
    ADMINS = [OWNER_ID]
    for x in os.environ.get("ADMINS", str(OWNER_ID)).split():
        ADMINS.append(int(x))
except:
    ADMINS = [OWNER_ID]

# ================= TEXT =================

BOT_STATS_TEXT = "<b>BOT UPTIME</b>\n{uptime}"
USER_REPLY_TEXT = "ʜᴇʏ! ɪ ᴀᴍ ᴀ ᴘʀᴇᴍɪᴜᴍ ʙᴏᴛ, ʙᴇʜᴀᴠᴇ ʏᴏᴜʀꜱᴇʟꜰ 😌"

# ================= LOG =================

LOG_FILE_NAME = "mzbotz_logs.txt"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        RotatingFileHandler(LOG_FILE_NAME, maxBytes=50000000, backupCount=10),
        logging.StreamHandler()
    ]
)

logging.getLogger("pyrogram").setLevel(logging.WARNING)

def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)
