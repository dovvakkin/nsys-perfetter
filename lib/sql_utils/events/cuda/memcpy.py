import sqlite3

import lib.sql_utils.events.cuda as cuda
import lib.sql_utils.names as names
import lib.util as util


def select_events(report_cursor: sqlite3.Cursor, device_id: int, stream_id: int):
    sql_result = report_cursor.execute(
        f"""
select
  runtime.start as runtime_start,
  runtime.end as runtime_end,
  runtime.globalTid as runtime_global_tid,
  StringIds.value as runtime_name,
  memcpy.start as memcpy_start,
  memcpy.end as memcpy_end,
  memcpy.bytes as bytes,
  enum_memcpy.label as memcpy_label,
  src_mem.label as src_kind,
  dst_mem.label as dst_kind,
  memcpy.correlationId as correlation_id
from
  CUPTI_ACTIVITY_KIND_RUNTIME as runtime
  inner join (
    select * from CUPTI_ACTIVITY_KIND_MEMCPY
    where deviceId = {device_id} and streamId = {stream_id}
  ) as memcpy on runtime.correlationId = memcpy.correlationId
  join StringIds on StringIds.id = runtime.nameId
  join ENUM_CUDA_MEMCPY_OPER as enum_memcpy on memcpy.copyKind = enum_memcpy.id
  join ENUM_CUDA_MEM_KIND as src_mem on src_mem.id = memcpy.srcKind
  join ENUM_CUDA_MEM_KIND as dst_mem on dst_mem.id = memcpy.dstKind
        """
    ).fetchall()

    for (
        runtime_start,
        runtime_end,
        runtime_global_tid,
        runtime_name,
        memcpy_start,
        memcpy_end,
        n_bytes,
        memcpy_label,
        src_kind,
        dst_kind,
        correlation_id,
    ) in sql_result:
        device_args = {
            "Info": f"{memcpy_label} {n_bytes} bytes",
            "Source memory kind": src_kind,
            "Destination memory kind": dst_kind,
            "Throughput": util.pretty_format_throughput(n_bytes, memcpy_end - memcpy_start),
            "Launched from thread": names.global_tid_to_pid_tid(runtime_global_tid)[1],
            "Latency": f"{util.TO_LEFT_ARROW}{util.pretty_format_duration(memcpy_start - runtime_start)}",
            "Correlation ID": correlation_id,
            "Stream": f"Stream {stream_id}",
        }

        host_args = {
            "Latency": f"{util.TO_RIGHT_ARROW}{util.pretty_format_duration(memcpy_start - runtime_start)}",
        }

        yield (
            runtime_start,
            runtime_end,
            runtime_global_tid,
            cuda.trim_cudart_version_tail(runtime_name),
            memcpy_start,
            memcpy_end,
            memcpy_label,
            host_args,
            device_args,
        )
