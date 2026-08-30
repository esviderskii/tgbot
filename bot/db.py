"""Thin asyncpg data layer for the notes table."""

from __future__ import annotations

import asyncpg

from . import config


class DB:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=5)
        await self._init_schema()

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()

    async def _init_schema(self) -> None:
        assert self.pool
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id            SERIAL PRIMARY KEY,
                    text          TEXT NOT NULL,
                    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
                    remind_at     TIMESTAMPTZ,
                    reminder_sent BOOLEAN NOT NULL DEFAULT FALSE
                )
                """
            )
            # Migration for recurring reminders.
            await conn.execute(
                "ALTER TABLE notes ADD COLUMN IF NOT EXISTS "
                "repeat_interval_minutes BIGINT"
            )
            await conn.execute(
                "ALTER TABLE notes ADD COLUMN IF NOT EXISTS repeat_tod SMALLINT"
            )

    async def add_note(
        self,
        text: str,
        remind_at,
        repeat_interval_minutes: int | None = None,
        repeat_tod: int | None = None,
    ) -> int:
        assert self.pool
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "INSERT INTO notes (text, remind_at, repeat_interval_minutes, repeat_tod) "
                "VALUES ($1, $2, $3, $4) RETURNING id",
                text, remind_at, repeat_interval_minutes, repeat_tod,
            )

    async def list_notes(self, limit: int = 50) -> list[asyncpg.Record]:
        assert self.pool
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, text, remind_at, reminder_sent "
                "FROM notes ORDER BY id DESC LIMIT $1",
                limit,
            )
            return rows

    async def get_note(self, note_id: int) -> asyncpg.Record | None:
        assert self.pool
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT id, text, remind_at, reminder_sent FROM notes WHERE id = $1",
                note_id,
            )

    async def delete_note(self, note_id: int) -> bool:
        assert self.pool
        async with self.pool.acquire() as conn:
            res = await conn.execute(
                "DELETE FROM notes WHERE id = $1", note_id
            )
            return "DELETE 1" in res

    async def get_due(self) -> list[asyncpg.Record]:
        """Notes whose reminder is due (or overdue) and not yet sent."""
        assert self.pool
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                "SELECT id, text, remind_at, repeat_interval_minutes, repeat_tod "
                "FROM notes "
                "WHERE remind_at IS NOT NULL AND reminder_sent = FALSE "
                "AND remind_at <= now() ORDER BY remind_at",
            )

    async def mark_sent(self, note_id: int) -> None:
        assert self.pool
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE notes SET reminder_sent = TRUE WHERE id = $1", note_id
            )

    async def reschedule(self, note_id: int, remind_at) -> None:
        """Re-arm a recurring reminder to its next future occurrence."""
        assert self.pool
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE notes SET remind_at = $2, reminder_sent = FALSE WHERE id = $1",
                note_id, remind_at,
            )


# Module-level singleton wired up from config; import this in handlers/main.
db = DB(config.DATABASE_URL)