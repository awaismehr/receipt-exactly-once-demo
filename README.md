# receipt-exactly-once-demo

A small toy model that reproduces a race condition, shows a failing test for it, and then shows the fix.

## The race

A pipeline stage writes a receipt when it finishes (`done`). A watchdog writes a receipt if the stage overruns (`timeout`). Both call the same function, `write_receipt`.

The unfixed `write_receipt` first runs a `SELECT` to see whether a receipt already exists for the stage, and then runs an `INSERT`. If both writers run the `SELECT` before either runs the `INSERT`, both see "no row" and both insert. The table has no unique constraint on `stage_id`, so both rows commit and the stage ends up with two receipts.

The fix replaces check-then-insert with a single atomic statement, `INSERT ... ON CONFLICT (stage_id) DO NOTHING RETURNING stage_id`, and makes `stage_id` the primary key. Only the caller that gets a row back reports success.

## What the test does

`tests/test_exactly_once.py` makes the race happen deterministically, without sleeps or retries:

1. A watchdog thread starts writing a `timeout` receipt. After its check, it pauses inside the race window using a `threading.Event`.
2. The main thread writes a `done` receipt for the same stage and commits.
3. The watchdog is released and continues with its write.
4. The test asserts that exactly one receipt row exists for the stage and that exactly one writer reported success.

The timeouts on `Event.wait` and `Thread.join` are hang guards only.

## Running locally

You need a PostgreSQL database you can write to (the test drops and recreates the `receipts` table).

```
pip install -r requirements.txt
DATABASE_URL=postgresql://user:password@localhost:5432/dbname pytest -v
```

If `DATABASE_URL` is not set the test fails rather than skips.

## CI

GitHub Actions runs the test against a real PostgreSQL 16 service container.
