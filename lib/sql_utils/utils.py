import sqlite3


def is_table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    if cursor.execute(
        f"""
SELECT COUNT(*) AS count FROM pragma_table_info('{table_name}')
    """
    ).fetchall():
        return True

    return False
