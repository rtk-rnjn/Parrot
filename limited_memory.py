from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import psutil


def _cgroup_memory_limit():
    """Return the container memory limit in bytes, or None if there isn't one."""
    paths = (
        "/sys/fs/cgroup/memory.max",  # cgroup v2
        "/sys/fs/cgroup/memory/memory.limit_in_bytes",  # cgroup v1
    )
    for path in paths:
        try:
            with Path(path).open() as f:
                raw = f.read().strip()
            if raw == "max":
                continue
            limit = int(raw)
            if limit < (1 << 60):  # v1 reports a huge number when unlimited
                return limit
        except OSError, ValueError:
            continue
    return None


def _cgroup_cpu_limit():
    """Return the container CPU quota as a float (e.g. 0.5, 2.0), or None."""
    try:
        with Path("/sys/fs/cgroup/cpu.max").open() as f:  # cgroup v2
            quota, period = f.read().split()
        if quota != "max":
            return int(quota) / int(period)
    except OSError, ValueError:
        pass
    return None


@lru_cache(maxsize=1)
def get_system_resources():
    """Effective RAM (GB) and CPU count, respecting container limits."""
    total_ram = psutil.virtual_memory().total
    mem_limit = _cgroup_memory_limit()
    if mem_limit:
        total_ram = min(total_ram, mem_limit)

    try:
        cpus = len(os.sched_getaffinity(0))  # respects CPU pinning (Linux)
    except AttributeError:
        cpus = psutil.cpu_count(logical=True) or 1
    cpu_limit = _cgroup_cpu_limit()
    if cpu_limit:
        cpus = min(cpus, cpu_limit)

    return {"ram_gb": total_ram / 1024**3, "cpus": cpus}


def is_limited_memory(min_ram_gb: float = 2.0, min_cpus: float = 2) -> bool:
    """True if the host is too small for the heavy features."""
    res = get_system_resources()
    return res["ram_gb"] < min_ram_gb or res["cpus"] < min_cpus
