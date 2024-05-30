import sqlite3

import lib.sql_utils.events.cuda as cuda


def select_events(report_cursor: sqlite3.Cursor, device_id: int, stream_id: int):
    for (
        runtime_start,
        runtime_end,
        runtime_global_tid,
        runtime_name,
        gpu_start,
        gpu_end,
        # host_args,
        # device_args
    ) in report_cursor.execute(
        f"""
select
  runtime.start as runtime_start,
  runtime.end as runtime_end,
  runtime.globalTid as runtime_global_tid,
  StringIds.value as runtime_name,
  memset.start as memset_start,
  memset.end as memset_end
from
  CUPTI_ACTIVITY_KIND_RUNTIME as runtime
  inner join (
    select * from CUPTI_ACTIVITY_KIND_MEMSET
    where deviceId={device_id} and streamId={stream_id}
  )as memset on runtime.correlationId = memset.correlationId
  join StringIds on StringIds.id = runtime.nameId
        """
    ):
        yield (
            runtime_start,
            runtime_end,
            runtime_global_tid,
            cuda.trim_cudart_version_tail(runtime_name),
            gpu_start,
            gpu_end,
            {},
            {},
        )
