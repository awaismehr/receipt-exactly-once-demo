import psycopg


def create_schema(conn: psycopg.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS receipts (
            stage_id text PRIMARY KEY,
            outcome  text NOT NULL
        )
        """
    )
    conn.commit()


def write_receipt(conn: psycopg.Connection, stage_id: str, outcome: str, *, _before_write=None) -> bool:
    if _before_write is not None:
        _before_write()  # test seam only; always None in production
    row = conn.execute(
        """
        INSERT INTO receipts (stage_id, outcome) VALUES (%s, %s)
        ON CONFLICT (stage_id) DO NOTHING
        RETURNING stage_id
        """,
        (stage_id, outcome),
    ).fetchone()
    conn.commit()
    return row is not None
