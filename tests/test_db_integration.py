"""Integration tests for the asyncpg data layer against a live PostgreSQL.

These require a reachable database. They read TEST_DATABASE_URL, falling back to
DATABASE_URL, and are skipped entirely when neither is set (e.g. plain `python
-m unittest tests.test_db_integration` with no DB configured).

Each test keeps connect/operate/close inside a single event loop via
`asyncio.run`, because the asyncpg pool is bound to one loop.
"""

import asyncio
import os
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from bot.db import DB
from bot.recurrence import next_occurrence

DB_URL = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
_SKIP = unittest.skipUnless(DB_URL, "TEST_DATABASE_URL/DATABASE_URL not set")

TZ = ZoneInfo("Europe/Moscow")


async def _crud(db: DB):
    """Add two notes, list them, delete one; returns the surviving ids."""
    a = await db.add_note("интеграционная заметка без времени", None)
    future = datetime.now(TZ) + timedelta(hours=2)
    b = await db.add_note("с будущим напоминанием", future)
    notes = await db.list_notes()
    assert any(n["id"] == a for n in notes)
    assert any(n["id"] == b for n in notes)
    assert await db.delete_note(a)
    remaining = await db.list_notes()
    assert all(n["id"] != a for n in remaining)
    assert any(n["id"] == b for n in remaining)
    await db.delete_note(b)
    return [n["id"] for n in remaining]


@_SKIP
class DbIntegrationTest(unittest.TestCase):
    def test_crud_roundtrip(self):
        async def go():
            db = DB(DB_URL)
            await db.connect()
            try:
                await _crud(db)
            finally:
                await db.close()

        asyncio.run(go())

    def test_recurring_reminder_reschedules(self):
        async def go():
            db = DB(DB_URL)
            await db.connect()
            try:
                due = datetime.now(TZ) - timedelta(minutes=5)
                interval = 1440
                tod = (9, 0)
                nid = await db.add_note(
                    "вставать", due, interval, tod[0] * 60 + tod[1]
                )
                # Due and unsent -> shows up in get_due.
                self.assertTrue(any(r["id"] == nid for r in await db.get_due()))

                # Scheduler action: re-arm to the next future occurrence.
                nxt = next_occurrence(datetime.now(TZ), interval, tod)
                await db.reschedule(nid, nxt)

                self.assertFalse(any(r["id"] == nid for r in await db.get_due()))
                got = await db.get_note(nid)
                # asyncpg returns timestamptz in UTC; compare in the bot's tz.
                local = got["remind_at"].astimezone(TZ)
                self.assertGreater(local, datetime.now(TZ))
                self.assertEqual(local.hour, 9)
                self.assertEqual(local.minute, 0)
                await db.delete_note(nid)
            finally:
                await db.close()

        asyncio.run(go())

    def test_tags_roundtrip(self):
        async def go():
            db = DB(DB_URL)
            await db.connect()
            try:
                nid = await db.add_note(
                    "купить хлеб", None, tags=["продукты", "сегодня"]
                )
                got = await db.get_note(nid)
                self.assertEqual(sorted(got["tags"]), ["продукты", "сегодня"])

                by_tag = await db.list_by_tag("ПРОДУКТЫ")
                self.assertTrue(any(r["id"] == nid for r in by_tag))

                await db.add_tag(nid, "продукты")
                await db.add_tag(nid, "важное")
                got = await db.get_note(nid)
                self.assertEqual(sorted(got["tags"]), ["важное", "продукты", "сегодня"])

                await db.remove_tag(nid, "сегодня")
                got = await db.get_note(nid)
                self.assertNotIn("сегодня", got["tags"])

                self.assertEqual(got["remind_at"], None)
                await db.delete_note(nid)
            finally:
                await db.close()

        asyncio.run(go())

    def test_missing_db_returns_no_due(self):
        """With no notes at all, get_due is empty and nothing explodes."""
        async def go():
            db = DB(DB_URL)
            await db.connect()
            try:
                self.assertEqual(await db.get_due(), [])
            finally:
                await db.close()

        asyncio.run(go())


if __name__ == "__main__":
    unittest.main()