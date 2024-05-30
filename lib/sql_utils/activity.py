import sqlite3


# n(kernels+memset+memcpu | gpu) / n(kernels+memset+memcpu | all_gpus) > activity_threshold
def select_active_devices(report_cursor: sqlite3.Cursor) -> list[int]:
    sql_result = report_cursor.execute(
        """
WITH ALL_GPU_ACTIVITY AS (
    SELECT deviceId FROM (
        SELECT deviceId FROM CUPTI_ACTIVITY_KIND_KERNEL
        UNION ALL
        SELECT deviceId FROM CUPTI_ACTIVITY_KIND_MEMCPY
        UNION ALL
        SELECT deviceId FROM CUPTI_ACTIVITY_KIND_MEMSET
    )
)
SELECT deviceId
FROM ALL_GPU_ACTIVITY
GROUP BY deviceId
HAVING COUNT(deviceId) > 0
"""
    ).fetchall()

    return [i[0] for i in sql_result]


# n(kernels+memset+memcpu | gpu, stream_id) / n(kernels+memset+memcpu | gpu, all_streams) > activity_threshold
def select_active_streams(
    report_cursor: sqlite3.Cursor, device_id: int, activity_percent_threshold: float = 0
) -> list[tuple[int, float]]:
    assert 0 <= activity_percent_threshold <= 1, "bad activity_threshold"

    return report_cursor.execute(
        f"""
WITH ALL_STREAM_ACTIVITY AS (
SELECT start, end, streamId
FROM (
    SELECT start, end, streamId FROM CUPTI_ACTIVITY_KIND_KERNEL WHERE deviceId = {device_id}
    UNION ALL
    SELECT start, end, streamId FROM CUPTI_ACTIVITY_KIND_MEMCPY WHERE deviceId = {device_id}
    UNION ALL
    SELECT start, end, streamId FROM CUPTI_ACTIVITY_KIND_MEMSET WHERE deviceId = {device_id}
)),
STREAM_RUNNING_TIME AS (
SELECT
    streamId,
    (SUM(end - start) * 100.0) / (SUM(SUM(end - start)) OVER () * 1.0) AS runtime_percent
FROM
    ALL_STREAM_ACTIVITY
GROUP BY
    streamId
)
SELECT streamId, runtime_percent
FROM
  STREAM_RUNNING_TIME
where
  runtime_percent > {activity_percent_threshold}
        """
    ).fetchall()


def select_stream_related_threads(report_cursor: sqlite3.Cursor, device_id: int, stream_id: int):
    sql_result = report_cursor.execute(
        f"""
WITH STREAM_CORRELATIONS AS (
SELECT distinct correlationId
FROM (
    SELECT correlationId FROM CUPTI_ACTIVITY_KIND_KERNEL WHERE deviceId = {device_id} and streamId = {stream_id}
    UNION ALL
    SELECT correlationId FROM CUPTI_ACTIVITY_KIND_MEMCPY WHERE deviceId = {device_id} and streamId = {stream_id}
    UNION ALL
    SELECT correlationId FROM CUPTI_ACTIVITY_KIND_MEMSET WHERE deviceId = {device_id} and streamId = {stream_id}
))
select distinct
    runtime.globalTid
from
    CUPTI_ACTIVITY_KIND_RUNTIME as runtime
    join STREAM_CORRELATIONS as correlations on runtime.correlationId = correlations.correlationId
        """
    ).fetchall()

    return [i[0] for i in sql_result]
