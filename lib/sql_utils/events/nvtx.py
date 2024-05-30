import sqlite3


def select_domains(report_cursor: sqlite3.Cursor) -> list[tuple[str, int]]:
    return report_cursor.execute(
        """
select distinct text, domainId
from NVTX_EVENTS
where eventType = 75
union
select 'NVTX' as text, 0 as domainId
    """
    ).fetchall()


def select_events(report_cursor: sqlite3.Cursor, global_tid: int):
    return report_cursor.execute(
        f"""
SELECT
    nvtx.start,
    nvtx.end,
    coalesce(nvtx.text, strings.value) as name,
    nvtx.domainId as domain_id
from
    NVTX_EVENTS as nvtx
    left join StringIds as strings on nvtx.textId = strings.Id
where
    globalTid = {global_tid}
    and nvtx.end is not null
        """
    ).fetchall()
