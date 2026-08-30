import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://notes:notes@db:5432/notes")
TZ_NAME: str = os.getenv("TZ", "Europe/Moscow")
# Optional: restrict the bot to a single Telegram user id.
OWNER_ID: int | None = (
    int(os.getenv("OWNER_ID")) if os.getenv("OWNER_ID") else None
)

TZ: ZoneInfo = ZoneInfo(TZ_NAME)

# Reminders older than this threshold on startup are silently dropped (not sent).
MAX_STALE_HOURS: int = 24
# How often the background scheduler polls the DB (seconds).
POLL_INTERVAL: int = 30