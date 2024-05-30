import re

from . import kernels, memcpy, memset, runtime_only

__all__ = ["kernels", "memcpy", "memset", "runtime_only"]

RE_CUDART_VERSION_TAIL = r"_v\d+$"


def trim_cudart_version_tail(name):
    return re.sub(RE_CUDART_VERSION_TAIL, "", name)
