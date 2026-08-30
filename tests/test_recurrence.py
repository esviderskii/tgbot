import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from bot.recurrence import next_occurrence

TZ = ZoneInfo("Europe/Moscow")
NOW = datetime(2026, 8, 30, 22, 0, tzinfo=TZ)  # Sunday 22:00


class NextOccurrenceTest(unittest.TestCase):
    def test_interval_lands_in_future_from_now(self):
        # "каждые 3 дня" -> 3*1440 minutes
        self.assertEqual(
            next_occurrence(NOW, 3 * 1440),
            datetime(2026, 9, 2, 22, 0, tzinfo=TZ),
        )

    def test_daily_with_time_of_day_anchor(self):
        # "каждый день в 9:00": today's 09:00 already passed -> tomorrow 09:00
        self.assertEqual(
            next_occurrence(NOW, 1440, time_of_day=(9, 0)),
            datetime(2026, 8, 31, 9, 0, tzinfo=TZ),
        )

    def test_anchor_time_still_ahead_today(self):
        at = datetime(2026, 8, 30, 8, 0, tzinfo=TZ)
        self.assertEqual(
            next_occurrence(at, 1440, time_of_day=(9, 0)),
            datetime(2026, 8, 30, 9, 0, tzinfo=TZ),
        )

    def test_interval_keeps_original_wallclock_past_now(self):
        # "каждые 2 часа" from 22:00 -> 00:00 (next, in the future)
        self.assertEqual(
            next_occurrence(NOW, 120),
            datetime(2026, 8, 31, 0, 0, tzinfo=TZ),
        )


if __name__ == "__main__":
    unittest.main()