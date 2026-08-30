# Spec — Recurring Reminders

## Problem Statement

The user can set a one-shot reminder on a note, but not a repeating one. Wants
"remind me every morning at 9:00" and "every 3 days" without recreating the
note each time.

## Solution

From the user's perspective: a note can repeat on an interval. When writing a
note, an optional recurrence produces repeated reminders; deleting the note
stops them. Missed fires (bot was off) are never caught up — the next reminder
is simply the next occurrence after the bot comes back.

## User Stories

1. As a user, I want to add a daily reminder with a time of day, so that I get
   it at the same time each day.
2. As a user, I want to add a reminder every N days / N hours, so that I can
   repeat on a custom cadence.
3. As a user, I want the note text to describe the cadence directly
   ("напоминай каждый день в 9:00", "каждые 3 дня"), so that I don't use a
   separate settings screen.
4. As a user, I want deleting the note to stop its repeats, so that I can cancel
   a recurring reminder without extra commands.
5. As a user, I want a missed fire to be skipped, so that I'm not spammed with
   catch-up reminders after downtime.

## Implementation Decisions

- **Schema**: add `repeat_interval_minutes BIGINT NULL` to `notes`. For a
  recurring note, the reminder is a live `next_remind_at` that the scheduler
  recomputes; one-shot notes keep the existing `remind_at` / `reminder_sent`
  behaviour. An empty `repeat_interval_minutes` means one-shot.
- **Parsing**: extend `timeparser.parse_reminder` to also recognise
  "каждый день в H:M", "каждые N дней", "каждую неделю в H:M" and return the
  recurrence as part of the parse result.
- **Scheduler**: on a due recurring note, send the reminder (subject to the
  existing stale-window rule), then set `next_remind_at` to the next occurrence
  *from now* and keep `reminder_sent = FALSE`. Never queue missed fires.
- **Pure seam**: a `next_occurrence(current, interval_minutes, time_of_day)`
  helper computes the next arm time; this is the primary test seam.

## Testing Decisions

- Tests assert external behaviour only. The main seam is the pure
  `next_occurrence` helper: given a reference "now", an interval and an optional
  time-of-day anchor, the helper returns the correct next arm timestamp,
  including anchoring to the time of day and landing in the future.
- DB-level behaviour (reschedule-after-fire) is covered by one dark test against
  a real Postgres, mirroring how `db.py` was already validated. Live-send itself
  is out of scope for unit tests.

## Out of Scope

- Cron-style expressions.
- A "stop reminding" button on the delivered message (delete-note is the only
  stop mechanism for now).
- Catch-up of missed recurrent fires by design.

## Further Notes

Replaces the one-shot-only restriction in `docs/adr/0001-recurring-reminders-interval-model.md`'s
schema change. Existing rows remain one-shot.