import asyncio
import logging

from aiogram import Bot, Dispatcher

from . import config, handlers
from .db import db
from .scheduler import reminder_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


async def main() -> None:
    if not config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN is not set — fill in .env")

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()

    # Restrict to the owner if configured (personal bot).
    handlers.router.message.filter(handlers.OwnerOnly(config.OWNER_ID))
    handlers.router.callback_query.filter(handlers.OwnerOnly(config.OWNER_ID))
    dp.include_router(handlers.router)

    await db.connect()
    log.info("connected to database, owner=%s tz=%s", config.OWNER_ID, config.TZ_NAME)

    scheduler = asyncio.create_task(reminder_loop(bot))
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        scheduler.cancel()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())