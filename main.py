import asyncio
from bot import Bot
from config import LOGGER


async def main():
    bot = Bot()
    await bot.start()
    LOGGER(__name__).info("Bot started successfully!")
    await asyncio.Event().wait()  # bot ko hamesha running rakhe


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        LOGGER(__name__).info("Bot stopped by user")
    except Exception as e:
        LOGGER(__name__).error(f"Fatal error: {e}")
