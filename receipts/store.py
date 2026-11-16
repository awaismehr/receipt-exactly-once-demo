import psycopg


def create_schema(conn: psycopg.Connection) -> None:
    # No unique constraint on stage_id. This is part of the bug.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS receipts (
            id       bigserial PRIMARY KEY,
            stage_id text NOT NULL,
            outcome  text NOT NULL
        )
        """
    )
    conn.commit()


def write_receipt(conn: psycopg.Connection, stage_id: str, outcome: str, *, _before_write=None) -> bool:
    # Check-then-write. This is the bug.
    row = conn.execute(
        "SELECT 1 FROM receipts WHERE stage_id = %s", (stage_id,)
    ).fetchone()
    if _before_write is not None:
        _before_write()  # test seam only; always None in production
    if row is not None:
        conn.rollback()
        return False
    conn.execute(
        "INSERT INTO receipts (stage_id, outcome) VALUES (%s, %s)",
        (stage_id, outcome),
    )
    conn.commit()
    return True
