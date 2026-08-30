# Recurring reminders as interval + reschedule-on-notes-row

Personal notes bot needs recurring reminders ("every day at 9:00", "every 3 days").
We model recurrence as a `repeat_interval_minutes` column on the existing `notes`
row plus a always-live `next_remind_at`, and the scheduler recomputes
`next_remind_at` forward from "now" after each fire instead of keeping a
separate reminders table or parsing cron strings.

## Why

Keeps one recurring note as one row (list/delete stay trivial), avoids a second
entity, and the interval + optional time-of-day model covers every realistic
personal-bot scenario without cron's complexity. Missing a fire while the bot
was down never causes a catch-up backlog: the next occurrence is just computed
from the current time.

## Consequences

- `notes` gains `repeat_interval_minutes` (nullable) and `next_remind_at`
  replaces the one-shot `remind_at` semantics for recurring rows.
- Schema change is the hard-to-reverse part and why this is recorded: existing
  rows default to no repeat and keep one-shot behaviour.
- Rejected alternative: separate `reminders` table (more entities, harder
  list/delete) and cron strings (unwarranted power for a personal bot).