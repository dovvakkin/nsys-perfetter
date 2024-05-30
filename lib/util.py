import humanize

TO_LEFT_ARROW = "←"
TO_RIGHT_ARROW = "→"

NS_IN_MCS = 1000
NS_IN_MS = NS_IN_MCS * 1000
NS_IN_S = NS_IN_MS * 1000
NS_IN_MIN = NS_IN_S * 60
NS_IN_HOUR = NS_IN_MIN * 60
NS_IN_DAY = NS_IN_HOUR * 24


def sql_list(lst: list) -> str:
    return f'({", ".join(map(str, lst))})'


def pretty_format_duration(duration_ns: int) -> str:
    assert duration_ns >= 0, "only positive duration could be pretty printed"

    if duration_ns / NS_IN_DAY > 1:
        return f"{duration_ns / NS_IN_DAY} days"

    if duration_ns / NS_IN_HOUR > 1:
        return f"{duration_ns / NS_IN_HOUR : .3f} hours"

    if duration_ns / NS_IN_MIN > 1:
        return f"{duration_ns / NS_IN_MIN : .3f} min"

    if duration_ns / NS_IN_S > 1:
        return f"{duration_ns / NS_IN_S : .3f} sec"

    if duration_ns / NS_IN_MS > 1:
        return f"{duration_ns / NS_IN_MS : .3f} ms"

    if duration_ns / NS_IN_MCS > 1:
        return f"{duration_ns / NS_IN_MCS : .3f} mcs"

    return f"{duration_ns : .3f} ns"


def pretty_format_throughput(n_bytes: int, copy_time_ns: int) -> str:
    throughput = n_bytes / copy_time_ns * NS_IN_S
    return f"{humanize.naturalsize(throughput, binary=True)}/s"
