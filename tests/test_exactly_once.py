import threading

import psycopg

from receipts.store import create_schema, write_receipt


def test_done_and_timeout_receipts_are_exactly_once(database_url):
    with psycopg.connect(database_url) as setup:
        setup.execute("DROP TABLE IF EXISTS receipts")
        create_schema(setup)

    stage = "stage-1"
    watchdog_paused = threading.Event()
    release_watchdog = threading.Event()
    results = {}
    errors = []

    def pause_watchdog():
        # Signal that the watchdog reached the race window, then wait until
        # the main thread has finished its own write and committed.
        watchdog_paused.set()
        if not release_watchdog.wait(timeout=10):
            raise RuntimeError("watchdog was never released")

    def watchdog():
        try:
            with psycopg.connect(database_url) as conn:
                results["timeout"] = write_receipt(
                    conn, stage, "timeout", _before_write=pause_watchdog
                )
        except Exception as exc:  # surfaced by the assertion below
            errors.append(exc)

    thread = threading.Thread(target=watchdog)
    thread.start()
    try:
        assert watchdog_paused.wait(timeout=10), "watchdog never reached the race window"
        with psycopg.connect(database_url) as conn:
            results["done"] = write_receipt(conn, stage, "done")
    finally:
        release_watchdog.set()
        thread.join(timeout=10)

    assert not thread.is_alive(), "watchdog thread hung"
    assert not errors, errors
    with psycopg.connect(database_url) as conn:
        count = conn.execute(
            "SELECT count(*) FROM receipts WHERE stage_id = %s", (stage,)
        ).fetchone()[0]
    assert count == 1, f"expected exactly one receipt for {stage}, found {count}"
    assert sum(results.values()) == 1, f"expected exactly one writer to succeed, got {results}"
