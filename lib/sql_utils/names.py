import os
import sqlite3

import lib.sql_utils.utils as utils


def global_tid_to_pid_tid(global_tid: int):
    # Serialized Process and Thread Identifiers
    # https://docs.nvidia.com/nsight-systems/UserGuide/index.html
    # SELECT globalTid / 0x1000000 % 0x1000000 AS PID, globalTid % 0x1000000 AS TID FROM TABLE_NAME;
    return (global_tid / 0x1000000) % 0x1000000, global_tid % 0x1000000


def get_device_name(report_cursor: sqlite3.Cursor, device_id: int) -> str:
    name, bus_location = report_cursor.execute(
        f"""
SELECT name, busLocation
FROM TARGET_INFO_GPU
WHERE id = {device_id}
        """
    ).fetchone()
    return f"CUDA HW ({bus_location} - {name})"


def get_stream_name(stream_id: int, activity_percent: float) -> str:
    return f"{activity_percent : .1f}% Stream {stream_id}"


def get_thread_name(report_cursor: sqlite3.Cursor, global_tid: int) -> str:
    if utils.is_table_exists(report_cursor, "ThreadNames"):
        thread_name = report_cursor.execute(
            f"""
    select strings.value
    from
        ThreadNames as threads
        join StringIds as strings on strings.id = threads.nameId
    where
        threads.globalTid={global_tid}
        """
        ).fetchone()

        if thread_name:
            _, tid = global_tid_to_pid_tid(global_tid)
            return f"[{tid}] {thread_name[0]}"

    symbol, module = report_cursor.execute(
        f"""
with THREAD_OSRT_API as (
    select * from OSRT_API where globalTid={global_tid}
),
THREAD_CALLCHAINS as (
    select id, symbol, module, stackDepth
    from
    THREAD_OSRT_API as api join OSRT_CALLCHAINS as callchains on api.callchainId=callchains.id
),
MIN_ID_CALLCHAIN as (
    select * from THREAD_CALLCHAINS
    where id = (select MIN(id) from THREAD_CALLCHAINS)
),
TWO_DEPEST_STACK_EVENTS as (
    select * FROM MIN_ID_CALLCHAIN
    ORDER BY stackDepth DESC
    LIMIT 2
),
-- deepest callchain id seem to be process creation, second thread creation
THREAD_CREATION_STACK_EVENT as (
    select * from TWO_DEPEST_STACK_EVENTS
    where stackDepth = (select min(stackDepth) from TWO_DEPEST_STACK_EVENTS)
)
select symbolStr.value as symbol, moduleStr.value as module
    from THREAD_CREATION_STACK_EVENT as event
    join StringIds as symbolStr
        on symbolStr.id = event.symbol
    join StringIds as moduleStr
        on moduleStr.id = event.module
    """
    ).fetchone()

    _, tid = global_tid_to_pid_tid(global_tid)

    return f"[{tid}] {os.path.basename(module)}!{symbol}"
