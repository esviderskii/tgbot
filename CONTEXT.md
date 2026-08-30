# Domain Glossary

- **Note** — an entry in the list; the unit the user adds, views and deletes. Has a body of free text.
- **Reminder** — an optional scheduled delivery of a *note* to the owner. A note carries at most one live reminder at a time.
- **One-shot reminder** — a *reminder* that fires once, then is done.
- **Recurring reminder** — a *reminder* that re-arms itself after each fire, repeating on an interval (optionally anchored to a time of day).
- **Next occurrence** — the timestamp a *recurring reminder* is armed for next; recomputed from "now" after a fire, never caught up for missed fires.
- **Tag** — an optional keyword attached to a *note*, stored independently of its *reminder*; used to group and filter notes.