"""Background task that sends due reminders (one-shot and recurring)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from aiogram import Bot

from . import config
from .db import db
from .recurrence import next_occurrence

log = logging.getLogger(__name__)


async def reminder_loop(bot: Bot) -> None:
    owner_id = config.OWNER_ID
    while True:
        try:
            now = datetime.now(config.TZ)
            due = await db.get_due()
            for note in due:
                remind_at = note["remind_at"]
                interval = note["repeat_interval_minutes"]
                stale = (now - remind_at).total_seconds() > config.MAX_STALE_HOURS * 3600

                if not stale:
                    await _notify(bot, owner_id, note)

                if interval is not None:
                    # Recurring: re-arm to the next future occurrence from now.
                    # A stale fire is skipped by computing the next tick directly.
                    tod = None
                    if note["repeat_tod"] is not None:
                        t = note["repeat_tod"]
                        tod = (t // 60, t % 60)
                    nxt = next_occurrence(now, interval, tod)
                    await db.reschedule(note["id"], nxt)
                else:
                    # One-shot: mark sent (stale ones are never delivered).
                    await db.mark_sent(note["id"])
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - keep the loop alive
            log.exception("reminder loop iteration failed")
        await asyncio.sleep(config.POLL_INTERVAL)


async def _notify(bot: Bot, owner_id: int | None, note) -> None:
    body = note["text"]
    if not owner_id:
        log.warning("OWNER_ID not set; cannot deliver reminder for note %s", note["id"])
        return
    await bot.send_message(owner_id, f"⏰ Напоминание:\n{body}")