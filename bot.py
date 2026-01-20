# (©)Mzbotz

from aiohttp import web
from plugins.web_server import web_server

from pyrogram import Client
from pyrogram.enums import ParseMode
import sys
from datetime import datetime

from config import (
    API_HASH,
    APP_ID,
    LOGGER,
    TG_BOT_TOKEN,
    TG_BOT_WORKERS,
    FORCESUB_CHANNEL,
    FORCESUB_CHANNEL2,
    FORCESUB_CHANNEL3,
    CHANNEL_ID,
    PORT
)

import pyrogram.utils

# Telegram ID Fix
pyrogram.utils.MIN_CHAT_ID = -999999999999
pyrogram.utils.MIN_CHANNEL_ID = -100999999999999


class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Bot",
            api_hash=API_HASH,
            api_id=APP_ID,
            bot_token=TG_BOT_TOKEN,
            plugins=dict(root="plugins"),
            workers=TG_BOT_WORKERS,
            in_memory=True
        )
        self.LOGGER = LOGGER

    async def start(self):
        await super().start()

        usr_bot_me = await self.get_me()
        self.uptime = datetime.now()

        # -------- FORCE SUB CHANNELS -------- #
        await self._setup_force_sub(FORCESUB_CHANNEL, "invitelink")
        await self._setup_force_sub(FORCESUB_CHANNEL2, "invitelink2")
        await self._setup_force_sub(FORCESUB_CHANNEL3, "invitelink3")

        # -------- DB CHANNEL CHECK -------- #
        try:
            db_channel = await self.get_chat(CHANNEL_ID)
            self.db_channel = db_channel
            test = await self.send_message(db_channel.id, "Test Message")
            await test.delete()
        except Exception as e:
            self.LOGGER(__name__).warning(e)
            self.LOGGER(__name__).warning(
                f"Make Sure bot is Admin in DB Channel, Current CHANNEL_ID: {CHANNEL_ID}"
            )
            sys.exit()

        # Parse mode
        self.parse_mode = ParseMode.HTML

        self.LOGGER(__name__).info("Bot Running..!")
        self.LOGGER(__name__).info("Created by https://t.me/Mzbotz")

        self.LOGGER(__name__).info(
            """
(っ◔◡◔)っ ♥ MZBOTZ ♥
░╚════╝░░╚════╝░╚═════╝░╚══════╝
"""
        )

        self.username = usr_bot_me.username

        # -------- WEB SERVER -------- #
        app = web.AppRunner(await web_server())
        await app.setup()
        await web.TCPSite(app, "0.0.0.0", PORT).start()

    async def _setup_force_sub(self, channel_id, attr_name):
        if not channel_id:
            return

        try:
            chat = await self.get_chat(channel_id)
            link = chat.invite_link

            if not link:
                link = await self.export_chat_invite_link(channel_id)

            setattr(self, attr_name, link)

        except Exception as e:
            self.LOGGER(__name__).warning(e)
            self.LOGGER(__name__).warning(
                f"Bot can't export invite link from ForceSub Channel: {channel_id}"
            )
            self.LOGGER(__name__).info(
                "Make sure bot is admin with invite permission."
            )
            sys.exit()

    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__).info("Bot stopped.")
