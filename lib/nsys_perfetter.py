import argparse
import collections
import sqlite3

import lib.perfetto_trace as perfetto_trace
import lib.sql_utils.activity as activity
import lib.sql_utils.events.cuda as cuda
import lib.sql_utils.events.nvtx as nvtx
import lib.sql_utils.names as names
import lib.util as util


class NsysReport:

    def __init__(self, nsys_report, min_stream_activity_percent=0.1):
        assert nsys_report.endswith(".sqlite"), f"Nsys Report {nsys_report} expected to be sqlite"
        self._report_connection = sqlite3.connect(nsys_report, timeout=20)
        self._report_cursor = self._report_connection.cursor()
        self.min_stream_activity_percent = min_stream_activity_percent

        self._trace = perfetto_trace.PerfettoTrace()

        self._current_fake_pid = 0
        self._current_uuid = 0
        self._current_arrow_id = 0
        self._current_fake_pid_fake_tid = collections.defaultdict(int)

        self._device_id_to_fake_pid = dict()
        self._device_id_to_uuid = dict()
        self._device_stream_to_fake_tid = dict()
        self._device_stream_to_uuid = dict()
        self._global_tid_to_fake_pid = dict()
        self._global_tid_to_uuid = dict()
        self._global_tid_subtrack_to_uuid = dict()

        self._globad_tid_to_added_events = collections.defaultdict(set)

        self._fill_trace()

    def _get_new_uuid(self):
        self._current_uuid += 1
        return self._current_uuid - 1

    def _get_new_arrow_id(self):
        self._current_arrow_id += 1
        return self._current_arrow_id - 1

    def _get_new_fake_pid(self):
        self._current_fake_pid += 1
        return self._current_fake_pid

    def _get_new_fake_pid_fake_tid(self, fake_pid: int) -> int:
        self._current_fake_pid_fake_tid[fake_pid] += 1
        return self._current_fake_pid_fake_tid[fake_pid] - 1

    def _select_cuda_runtime_only_events(self, stream_related_threads: list[int]):
        return self._report_cursor.execute(
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
        ).fetchall()

    def _fill_nvtx_thread_events(self, global_tid):
        if global_tid in self._globad_tid_to_added_events["nvtx"]:
            return

        for domain_name, domain_id in nvtx.select_domains(self._report_cursor):
            self._global_tid_subtrack_to_uuid[(global_tid, f"nvtx_{domain_id}")] = self._get_new_uuid()
            self._trace.add_thread(
                self._global_tid_subtrack_to_uuid[(global_tid, f"nvtx_{domain_id}")],
                self._global_tid_to_uuid[global_tid],
                self._get_new_fake_pid_fake_tid(self._global_tid_to_fake_pid[global_tid]),
                self._global_tid_to_fake_pid[global_tid],
                domain_name,
            )

        for start, end, name, domain_id in nvtx.select_events(self._report_cursor, global_tid):
            self._trace.add_slice(
                self._global_tid_subtrack_to_uuid[(global_tid, f"nvtx_{domain_id}")], start, end, name
            )

        self._globad_tid_to_added_events["nvtx"].add(global_tid)

    def _fill_nvtx_events(self, stream_related_threads: list[int]):
        for thread in stream_related_threads:
            self._fill_nvtx_thread_events(thread)

    def _fill_cuda_kernels(self, device_id: int, stream_id: int) -> None:
        for (
            runtime_start,
            runtime_end,
            runtime_global_tid,
            short_name,
            kernel_start,
            kernel_end,
            demangled_name,
            runtime_args,
            kernel_args,
        ) in cuda.kernels.select_events(self._report_cursor, device_id, stream_id):
            arrow_id = self._get_new_arrow_id()
            self._trace.add_slice(
                self._global_tid_subtrack_to_uuid[(runtime_global_tid, "cuda")],
                runtime_start,
                runtime_end,
                short_name,
                [arrow_id],
                runtime_args,
            )
            self._trace.add_slice(
                self._device_stream_to_uuid[(device_id, stream_id)],
                kernel_start,
                kernel_end,
                demangled_name,
                [arrow_id],
                kernel_args,
            )

    def _fill_cuda_memcpy(self, device_id: int, stream_id: int) -> None:
        for (
            runtime_start,
            runtime_end,
            runtime_global_tid,
            runtime_name,
            gpu_start,
            gpu_end,
            gpu_label,
            host_args,
            device_args,
        ) in cuda.memcpy.select_events(self._report_cursor, device_id, stream_id):
            arrow_id = self._get_new_arrow_id()
            self._trace.add_slice(
                self._global_tid_subtrack_to_uuid[(runtime_global_tid, "cuda")],
                runtime_start,
                runtime_end,
                runtime_name,
                [arrow_id],
                host_args,
            )
            self._trace.add_slice(
                self._device_stream_to_uuid[(device_id, stream_id)],
                gpu_start,
                gpu_end,
                f"Memcpy {gpu_label}",
                [arrow_id],
                device_args,
            )

    def _fill_cuda_memset(self, device_id: int, stream_id: int):
        for (
            runtime_start,
            runtime_end,
            runtime_global_tid,
            runtime_name,
            gpu_start,
            gpu_end,
            host_args,
            device_args,
        ) in cuda.memset.select_events(self._report_cursor, device_id, stream_id):
            arrow_id = self._get_new_arrow_id()
            self._trace.add_slice(
                self._global_tid_subtrack_to_uuid[(runtime_global_tid, "cuda")],
                runtime_start,
                runtime_end,
                runtime_name,
                [arrow_id],
                host_args,
            )
            self._trace.add_slice(
                self._device_stream_to_uuid[(device_id, stream_id)],
                gpu_start,
                gpu_end,
                "Memset",
                [arrow_id],
                device_args,
            )

    def _fill_cuda_runtime_only_events(self, stream_related_threads: list[int]):
        globad_tid_with_cuda_runtime_only_events = set()

        for start, end, global_tid, name in cuda.runtime_only.select_events(
            self._report_cursor, stream_related_threads
        ):
            if "cuda_runtime_only" in self._globad_tid_to_added_events[global_tid]:
                continue
            globad_tid_with_cuda_runtime_only_events.add(global_tid)
            self._trace.add_slice(
                self._global_tid_subtrack_to_uuid[(global_tid, "cuda")],
                start,
                end,
                name,
            )

        for global_tid in globad_tid_with_cuda_runtime_only_events:
            self._globad_tid_to_added_events[global_tid].add("cuda_runtime_only")

    def _fill_cuda_events(self, device_id: int, stream_id: int, stream_related_threads: list[int]) -> None:
        for global_tid in stream_related_threads:
            if (global_tid, "cuda") in self._global_tid_subtrack_to_uuid:
                continue
            self._global_tid_subtrack_to_uuid[(global_tid, "cuda")] = self._get_new_uuid()
            self._trace.add_thread(
                self._global_tid_subtrack_to_uuid[(global_tid, "cuda")],
                self._global_tid_to_uuid[global_tid],
                self._get_new_fake_pid_fake_tid(self._global_tid_to_fake_pid[global_tid]),
                self._global_tid_to_fake_pid[global_tid],
                "CUDA API",
            )

        self._fill_cuda_kernels(device_id, stream_id)
        self._fill_cuda_memcpy(device_id, stream_id)
        self._fill_cuda_memset(device_id, stream_id)
        self._fill_cuda_runtime_only_events(stream_related_threads)

    def _add_device_track(self, device_id: int) -> None:
        self._device_id_to_fake_pid[device_id] = self._get_new_fake_pid()
        self._device_id_to_uuid[device_id] = self._get_new_uuid()

        self._trace.add_process(
            self._device_id_to_uuid[device_id],
            self._device_id_to_fake_pid[device_id],
            names.get_device_name(self._report_cursor, device_id),
        )

    def _add_stream_track(self, device_id: int, stream_id: int, activity_percent: float) -> None:
        self._device_stream_to_uuid[(device_id, stream_id)] = self._get_new_uuid()
        self._device_stream_to_fake_tid[(device_id, stream_id)] = self._get_new_fake_pid_fake_tid(
            self._device_id_to_fake_pid[device_id]
        )

        self._trace.add_thread(
            self._device_stream_to_uuid[(device_id, stream_id)],
            self._device_id_to_uuid[device_id],
            self._device_stream_to_fake_tid[(device_id, stream_id)],
            self._device_id_to_fake_pid[device_id],
            names.get_stream_name(stream_id, activity_percent),
        )

    def _add_thread_track(self, global_tid: int):
        print(f"add thread {global_tid}")
        if global_tid in self._global_tid_to_uuid:
            return

        self._global_tid_to_fake_pid[global_tid] = self._get_new_fake_pid()
        self._global_tid_to_uuid[global_tid] = self._get_new_uuid()

        self._trace.add_process(
            self._global_tid_to_uuid[global_tid],
            self._global_tid_to_fake_pid[global_tid],
            names.get_thread_name(self._report_cursor, global_tid),
        )

    def _fill_device_events(self, device_id: int) -> None:
        print(f"add device {device_id}")
        self._add_device_track(device_id)
        for stream_id, activity_percent in activity.select_active_streams(
            self._report_cursor, device_id, self.min_stream_activity_percent
        ):
            self._fill_stream_events(device_id, stream_id, activity_percent)

    def _fill_stream_events(self, device_id: int, stream_id: int, activity_percent: float):
        print(f"add stream {stream_id}")
        self._add_stream_track(device_id, stream_id, activity_percent)

        stream_related_global_tids = activity.select_stream_related_threads(self._report_cursor, device_id, stream_id)
        for global_tid in stream_related_global_tids:
            self._add_thread_track(global_tid)

        self._fill_cuda_events(device_id, stream_id, stream_related_global_tids)
        self._fill_nvtx_events(stream_related_global_tids)

    def _fill_trace(self):
        for device_id in activity.select_active_devices(self._report_cursor):
            self._fill_device_events(device_id)

    def save_trace(self, output_fname, binary_format=True):
        self._trace.save_proto(output_fname, binary_format)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nsys-report", help="exported to sqlite nsys report")
    parser.add_argument("--output", help="path to output events in json")

    return parser.parse_args()


def main():
    args = parse_args()
    report = NsysReport(args.nsys_report)
    report.save_trace(args.output)


if __name__ == "__main__":
    main()
