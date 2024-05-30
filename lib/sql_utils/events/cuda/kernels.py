import sqlite3

from lib import util
from lib.sql_utils import names


def select_events(report_cursor: sqlite3.Cursor, device_id: int, stream_id: int):
    sql_result = report_cursor.execute(
        f"""
select
  runtime.start as runtime_start,
  runtime.end as runtime_end,
  runtime.globalTid as runtime_global_tid,
  stringIdsShort.value as short_name,
  kernel.start as kernel_start,
  kernel.end as kernel_end,
  StringIdsDemangled.value as demangled_name,
  kernel.gridX as gridX,
  kernel.gridY as gridY,
  kernel.gridZ as gridZ,
  kernel.blockX as blockX,
  kernel.blockY as blockY,
  kernel.blockZ as blockZ,
  kernel.staticSharedMemory as staticSharedMemory,
  kernel.dynamicSharedMemory as dynamicSharedMemory,
  kernel.registersPerThread as registersPerThread,
  kernel.localMemoryPerThread as localMemoryPerThread,
  kernel.localMemoryTotal as localMemoryTotal,
  kernel.sharedMemoryExecuted as sharedMemoryExecuted,
  launch_type.label as launchType,
  kernel.correlationId as correlationId
from
  CUPTI_ACTIVITY_KIND_RUNTIME as runtime
  inner join (
    select * from CUPTI_ACTIVITY_KIND_KERNEL
    where deviceId={device_id} and streamId={stream_id}
  ) as kernel on runtime.correlationId = kernel.correlationId
  join ENUM_CUDA_KERNEL_LAUNCH_TYPE as launch_type on kernel.launchType=launch_type.id
  join StringIds as stringIdsShort on stringIdsShort.id = kernel.shortName
  join StringIds as StringIdsDemangled on StringIdsDemangled.id = kernel.demangledName
            """
    ).fetchall()

    for (
        runtime_start,
        runtime_end,
        runtime_global_tid,
        short_name,
        kernel_start,
        kernel_end,
        demangled_name,
        grid_x,
        grid_y,
        grid_z,
        block_x,
        block_y,
        block_z,
        static_shared_memory,
        dynamic_shared_memory,
        registers_per_thread,
        local_memory_per_thread,
        local_memory_total,
        shared_memory_executed,
        launch_type,
        correlation_id,
    ) in sql_result:
        latency = util.pretty_format_duration(kernel_start - runtime_start)
        kernel_args = dict()
        kernel_args["grid"] = f"<<<{grid_x}, {grid_y}, {grid_z}>>>"
        kernel_args["block"] = f"<<<{block_x}, {block_y}, {block_z}>>>"
        kernel_args["Launch Type"] = launch_type
        kernel_args["Static Shared Memory"] = f"{static_shared_memory} bytes"
        kernel_args["Dynamic Shared Memory"] = f"{dynamic_shared_memory} bytes"
        kernel_args["Registers Per Thread"] = registers_per_thread
        kernel_args["Local Memory Per Thread"] = f"{local_memory_per_thread} bytes"
        kernel_args["Shared Memory Executed"] = f"{shared_memory_executed} bytes"
        kernel_args["Launched from thread"] = names.global_tid_to_pid_tid(runtime_global_tid)[1]
        kernel_args["Latency"] = f"{util.TO_LEFT_ARROW}{latency}"
        kernel_args["Correlation ID"] = correlation_id
        kernel_args["Stream"] = f"Stream {stream_id}"

        runtime_args = dict()
        runtime_args["Latency"] = f"{util.TO_RIGHT_ARROW}{latency}"

        yield (
            runtime_start,
            runtime_end,
            runtime_global_tid,
            short_name,
            kernel_start,
            kernel_end,
            demangled_name,
            runtime_args,
            kernel_args,
        )
