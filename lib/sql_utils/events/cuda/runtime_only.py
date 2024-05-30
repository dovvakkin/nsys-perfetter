import sqlite3

import lib.sql_utils.events.cuda as cuda
import lib.util as util


def select_events(report_cursor: sqlite3.Cursor, stream_related_threads: list[int]):
    for start, end, global_tid, name in report_cursor.execute(
        f"""
select
  runtime.start as runtime_start,
  runtime.end as runtime_end,
  runtime.globalTid as runtime_global_tid,
  StringIds.value as runtime_name
from
  (select * from CUPTI_ACTIVITY_KIND_RUNTIME
    where globalTid in {util.sql_list(stream_related_threads)}
  ) as runtime
  left join CUPTI_ACTIVITY_KIND_MEMSET as memset on runtime.correlationId = memset.correlationId
  left join CUPTI_ACTIVITY_KIND_MEMCPY as memcpy on runtime.correlationId = memcpy.correlationId
  left join CUPTI_ACTIVITY_KIND_KERNEL as kernel on runtime.correlationId = kernel.correlationId
  join StringIds on StringIds.id = runtime.nameId
where
  memset.correlationId is null
  and memcpy.correlationId is null
  and kernel.correlationId is null
        """
    ).fetchall():
        yield start, end, global_tid, cuda.trim_cudart_version_tail(name)
