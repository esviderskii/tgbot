"""Pure helper for computing the next arm time of a recurring reminder.

`interval_minutes` is the repeat cadence; `time_of_day` (HH, MM) optionally
anchors the cadence to a time of day (e.g. "every day at 9:00"). The result is
always strictly in the future relative to `current`.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional


def next_occurrence(
    current: datetime,
    interval_minutes: int,
    time_of_day: Optional[tuple[int, int]] = None,
) -> datetime:
    if time_of_day is not None:
        anchor = current.replace(
            hour=time_of_day[0], minute=time_of_day[1], second=0, microsecond=0
        )
        skipped = (current - anchor).total_seconds() // (interval_minutes * 60)
        steps = int(skipped) + 1 if skipped >= 0 else 0
        return anchor + timedelta(minutes=interval_minutes * steps)

    return current + timedelta(minutes=interval_minutes)