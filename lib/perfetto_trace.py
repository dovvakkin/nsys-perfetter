import google.protobuf.text_format as text_format

from lib.protos import perfetto_trace_pb2 as trace


class PerfettoTraceBadArgsError(ValueError):
    pass


def fill_debug_annotation_value(debug_annotation, value):
    if isinstance(value, dict):
        for key in value:
            dict_entry = trace.DebugAnnotation()
            dict_entry.name = key
            fill_debug_annotation_value(dict_entry, value[key])
            debug_annotation.dict_entries.append(dict_entry)
        return

    if isinstance(value, list):
        for item in value:
            array_value = trace.DebugAnnotation()
            fill_debug_annotation_value(array_value, item)
            debug_annotation.array_values.append(array_value)
        return

    if isinstance(value, bool):
        debug_annotation.bool_value = value
        return

    if isinstance(value, int):
        debug_annotation.int_value = value
        return

    if isinstance(value, float):
        debug_annotation.double_value = value
        return

    if isinstance(value, str):
        debug_annotation.string_value = value
        return

    raise PerfettoTraceBadArgsError(f"cannot convert value {value} of type {type(value)} to DebugAnnotation value")


class PerfettoTrace:
    DEFAULT_TRUSTED_PACKET_SEQUENCE_ID = 0

    def __init__(
        self,
    ):
        self._trace = trace.Trace()
        self._name_to_iid = dict()
        self._current_iid = 0

    def _get_next_iid(self):
        self._current_iid += 1
        return self._current_iid

    def add_process(self, uuid, pid, name):
        self._trace.packet.append(
            trace.TracePacket(
                track_descriptor=trace.TrackDescriptor(
                    uuid=uuid, process=trace.ProcessDescriptor(pid=pid, process_name=name)
                ),
                trusted_packet_sequence_id=self.DEFAULT_TRUSTED_PACKET_SEQUENCE_ID,
            )
        )

    def add_thread(self, uuid, parent_uuid, tid, pid, name):
        self._trace.packet.append(
            trace.TracePacket(
                track_descriptor=trace.TrackDescriptor(
                    uuid=uuid,
                    parent_uuid=parent_uuid,
                    thread=trace.ThreadDescriptor(pid=pid, tid=tid, thread_name=name),
                ),
                trusted_packet_sequence_id=self.DEFAULT_TRUSTED_PACKET_SEQUENCE_ID,
            )
        )

    def add_slice(self, uuid, start, end, name, flow_ids=[], args={}):
        # print("slice", uuid, start, end, name)
        if args:
            if not isinstance(args, dict):
                raise PerfettoTraceBadArgsError("slice args is not dict")
            annotations = []

            for key in args:
                debug_annotation = trace.DebugAnnotation()
                debug_annotation.name = key
                fill_debug_annotation_value(debug_annotation, args[key])

                annotations.append(debug_annotation)

            args = annotations

        # interned_data = None
        # if name not in self._name_to_iid:
        #     self._name_to_iid[name] = self._get_next_iid()
        #     interned_data = trace.InternedData(event_names=[trace.EventName(name=name, iid=self._name_to_iid[name])])
        #
        # name_iid = self._name_to_iid[name]
        # name = None
        self._trace.packet.append(
            trace.TracePacket(
                timestamp=start,
                track_event=trace.TrackEvent(
                    type=trace.TrackEvent.Type.TYPE_SLICE_BEGIN,
                    track_uuid=uuid,
                    name=name,
                    # name_iid=name_iid,
                    flow_ids=flow_ids,
                    debug_annotations=args,
                ),
                # interned_data=interned_data,
                trusted_packet_sequence_id=self.DEFAULT_TRUSTED_PACKET_SEQUENCE_ID,
            )
        )
        self._trace.packet.append(
            trace.TracePacket(
                timestamp=end,
                track_event=trace.TrackEvent(
                    type=trace.TrackEvent.Type.TYPE_SLICE_END,
                    track_uuid=uuid,
                ),
                trusted_packet_sequence_id=self.DEFAULT_TRUSTED_PACKET_SEQUENCE_ID,
            )
        )

    def save_proto(self, path, binary_format=True):
        if not binary_format:
            with open(path, "w") as f:
                text_format.PrintMessage(self._trace, f)
            return

        with open(path, "wb") as f:
            f.write(self._trace.SerializeToString())
