# Spec — GitHub Actions CI

## Problem Statement

There is no automated verification: pushes to `master` are not tested, nothing
runs the unit tests or checks style, and the DB layer is only validated by
manual runs. A mistake can reach the live bot unnoticed.

## Solution

From the contributor's perspective: every push (to `master`) and every pull
request triggers a CI job that runs the lint check, the unit tests, and an
integration test against a real PostgreSQL service, and reports green/red on
the commit/PR.

## User Stories

1. As a maintainer, I want CI to run on every push to `master`, so that regressions are caught the moment they land.
2. As a maintainer, I want CI to run on pull requests, so that I can see failures before merging.
3. As a maintainer, I want the lint check (ruff) to fail the build on style/code errors, so that the codebase stays consistent.
4. As a maintainer, I want the unit tests to run in CI, so that the pure logic stays verified.
5. As a maintainer, I want an integration test against a real PostgreSQL service in CI, so that the asyncpg data layer (including recurring-reminder rescheduling) is exercised end-to-end.
6. As a contributor, I want the integration test to skip gracefully when no database is configured, so that local usage without Postgres does not break.

## Implementation Decisions

- **Workflow file**: `.github/workflows/ci.yml` — a single job `ci`.
- **Runner**: `ubuntu-latest`.
- **Steps**: set up Python 3.12 → install `requirements.txt` + `ruff` → `ruff check .` → `python -m unittest discover -s tests` (runs unit tests) → run integration test with a Postgres service.
- **PostgreSQL service**: `services.postgres` with `postgres:16-alpine`, env `POSTGRES_USER=notes`, `POSTGRES_PASSWORD=notes`, `POSTGRES_DB=notes`, suitable health check so tests run after it is ready.
- **DB URL for CI**: `TEST_DATABASE_URL=postgresql://notes:notes@localhost:5432/notes`.
- **Ruff config**: `pyproject.toml` with `[tool.ruff]` (line-length 100) and `select = ["E", "F"]`. Existing code is cleaned so CI is green on the first run.
- **Integration test**: `tests/test_db_integration.py`, a `unittest` suite guarded by `@unittest.skipUnless(TEST_DATABASE_URL or DATABASE_URL, ...)`. It connects via the app's `DB`, and covers add / list / due-reschedule of a recurring reminder / delete.

## Testing Decisions

- Tests assert external behaviour through public seams only.
- The unit suite (`tests/test_recurrence.py`) stays database-free and always runs.
- The integration suite needs a live Postgres; it reads `TEST_DATABASE_URL`, falling back to `DATABASE_URL`, and is skipped when neither is set. This is the agreed conditional-skip seam.
- Good CI: the same commands that pass locally are what CI runs, so failures reproduce locally.

## Out of Scope

- Deploying the bot (CI does not push images or deploy).
- Covering every code path of the telegram handlers (needs a real Bot token; not e2e-tested here).
- Pre-commit hooks / local lint gates.
- Release automation / versioning.

## Further Notes

The first `master` push after this lands will run CI for the first time against
the existing tests and code — the ruff step intentionally blocks until the
existing code is lint-clean.