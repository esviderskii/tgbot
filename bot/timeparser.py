"""Parse a human-friendly reminder time (and optional recurrence) out of a note.

Understands (Russian):
  * Word/date/time: "завтра в 9:00", "сегодня в 18:30", "послезавтра 7:05",
    "понедельник 14:00", bare "9:00" -> today
  * Relative: "через 30 минут", "через 2 часа", "через 3 дня", "через неделю",
    "через полчаса", "через пару часов"
  * Recurrence: "каждый день в 9:00", "каждую неделю в 18:00",
    "каждые 3 дня", "каждые 2 часа", "каждый час", "каждые 30 минут"

Returns a ParseResult with the first fire time, the repeat interval (minutes)
and time-of-day anchor when recurring (see `next_occurrence` for how the anchor
prevents drift), and the cleaned note body (time/repeat phrase stripped).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from .recurrence import next_occurrence

_WEEKDAYS = {
    "понедельник": 0,
    "вторник": 1,
    "среда": 2,
    "среду": 2,
    "четверг": 3,
    "пятница": 4,
    "пятницу": 4,
    "суббота": 5,
    "субботу": 5,
    "воскресенье": 6,
}

# unit -> minutes
_UNIT_MIN = {
    "секунда": 1 / 60, "секунду": 1 / 60, "секунды": 1 / 60, "секунд": 1 / 60,
    "минута": 1, "минуту": 1, "минуты": 1, "минут": 1, "минуток": 1,
    "час": 60, "часа": 60, "часов": 60, "часок": 60,
    "день": 1440, "дня": 1440, "дней": 1440,
    "неделя": 10080, "неделю": 10080, "недели": 10080, "недель": 10080,
}

_NUM_WORDS = {"полу": 0.5, "пару": 2, "пять": 5, "десять": 10, "пятнадцать": 15}

_TIME = r"([01]?\d|2[0-3])[:.]([0-5]\d)"
_DAYWORD = "|".join(_WEEKDAYS.keys())
_UNIT = "|".join(sorted(_UNIT_MIN.keys(), key=len, reverse=True))

# Recurrence phrases
_RECUR_DAY_TIME = re.compile(rf"каждый\s+день\s+(?:в\s*)?{_TIME}", re.I)
_RECUR_WEEK_TIME = re.compile(rf"кажд\w*\s+недел\w*\s+(?:в\s*)?{_TIME}", re.I)
_RECUR_EVERY_N = re.compile(
    rf"кажд\w*\s+(?P<num>\d*)\s*(?P<unit>недел\w*|дн\w*|час\w*|минут\w*)", re.I
)

# One-shot phrases
_RELATIVE = re.compile(rf"(?:через|спустя)\s+(?P<num>\d+|[А-Яа-я]+)?\s*(?P<unit>{_UNIT})", re.I)
_DAYTIME = re.compile(rf"(?P<day>{_DAYWORD})\s*(?:в\s*)?{_TIME}", re.I)
_BARETIME = re.compile(rf"(?<!\d)(?:в\s*)?{_TIME}(?!\d)")
_FULL_DATE = re.compile(
    r"(?P<day>\d{1,2})[./](?P<month>\d{1,2})\s*(?:в\s*)?"
    r"(?P<h>\d{1,2})[:.](?P<m>[0-5]\d)"
)


@dataclass
class ParseResult:
    remind_at: Optional[datetime]
    interval_minutes: Optional[int]
    repeat_tod: Optional[tuple[int, int]]
    text: str

    @property
    def is_recurring(self) -> bool:
        return self.interval_minutes is not None


def _clean(text: str) -> str:
    text = re.sub(r"\s{2,}", " ", text).strip(" ,.-")
    return text


def _next_weekday(tz: ZoneInfo, target: int) -> datetime:
    now = datetime.now(tz)
    days = (target - now.weekday()) % 7
    if days == 0:
        days = 7
    return (now + timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)


def _parse_relative(m: re.Match, tz: ZoneInfo) -> datetime:
    num_tok = (m.group("num") or "1").lower()
    unit = m.group("unit").lower()
    if num_tok in _NUM_WORDS:
        value = _NUM_WORDS[num_tok]
    elif num_tok.isdigit():
        value = float(num_tok)
    else:
        value = 1.0
    minutes = value * _UNIT_MIN[unit]
    return datetime.now(tz) + timedelta(minutes=minutes)


def parse_reminder(text: str, tz: ZoneInfo) -> ParseResult:
    text = text.strip()
    now = datetime.now(tz)

    # --- Recurrence ---
    m = _RECUR_DAY_TIME.search(text)
    if m:
        interval = 1440
        tod = (int(m.group(1)), int(m.group(2)))
        return ParseResult(
            next_occurrence(now, interval, tod), interval, tod,
            _clean(re.sub(_RECUR_DAY_TIME, " ", text)),
        )

    m = _RECUR_WEEK_TIME.search(text)
    if m:
        interval = 10080
        tod = (int(m.group(1)), int(m.group(2)))
        return ParseResult(
            next_occurrence(now, interval, tod), interval, tod,
            _clean(re.sub(_RECUR_WEEK_TIME, " ", text)),
        )

    m = _RECUR_EVERY_N.search(text)
    if m:
        unit = m.group("unit").lower()
        num = int(m.group("num") or "1")
        if unit.startswith("минут"):
            mult = 1
        elif unit.startswith("час"):
            mult = 60
        elif unit.startswith("дн"):
            mult = 1440
        else:  # недел*
            mult = 10080
        interval = num * mult
        return ParseResult(
            next_occurrence(now, interval), interval, None,
            _clean(re.sub(_RECUR_EVERY_N, " ", text)),
        )

    # --- One-shot ---
    used = None

    m = _RELATIVE.search(text)
    if m:
        used = _parse_relative(m, tz)

    if used is None:
        m = _FULL_DATE.search(text)
        if m:
            used = datetime(
                now.year, int(m.group("month")), int(m.group("day")),
                int(m.group("h")), int(m.group("m")), tzinfo=tz,
            )
            if used < now and used.month < now.month:
                used = used.replace(year=now.year + 1)

    if used is None:
        m = _DAYTIME.search(text)
        if m:
            day = m.group("day").lower()
            hour, minute = int(m.group(2)), int(m.group(3))
            if day in ("сегодня",):
                used = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if used < now:
                    used = used + timedelta(days=1)
            elif day == "завтра":
                used = (now + timedelta(days=1)).replace(
                    hour=hour, minute=minute, second=0, microsecond=0
                )
            elif day == "послезавтра":
                used = (now + timedelta(days=2)).replace(
                    hour=hour, minute=minute, second=0, microsecond=0
                )
            else:
                base = _next_weekday(tz, _WEEKDAYS[day])
                used = base.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if used is None:
        m = _BARETIME.search(text)
        if m:
            hour, minute = int(m.group(1)), int(m.group(2))
            used = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if used < now:
                used = used + timedelta(days=1)

    if used is None:
        return ParseResult(None, None, None, text)

    cleaned = re.sub(_RELATIVE, " ", text) or ""
    cleaned = re.sub(_FULL_DATE, " ", cleaned)
    cleaned = re.sub(_DAYTIME, " ", cleaned)
    cleaned = re.sub(_BARETIME, " ", cleaned)
    return ParseResult(used, None, None, _clean(cleaned))