from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import psutil


def _cgroup_memory_limit() -> int | None:
    """Return the container memory limit in bytes."""
    if os.name != "posix":
        return None

    paths = (
        "/sys/fs/cgroup/memory.max",
        "/sys/fs/cgroup/memory/memory.limit_in_bytes",
    )

    for path in paths:
        try:
            raw = Path(path).read_text().strip()

            if raw == "max":
                continue

            limit = int(raw)

            if 0 < limit < (1 << 60):
                return limit

        except OSError, ValueError:
            continue

    return None


def _cgroup_cpu_limit() -> float | None:
    """Return the container CPU quota."""
    if os.name != "posix":
        return None

    try:
        quota, period = Path("/sys/fs/cgroup/cpu.max").read_text().split()

        if quota != "max":
            return int(quota) / int(period)

    except OSError, ValueError, ZeroDivisionError:
        pass

    return None


@lru_cache(maxsize=1)
def get_system_resources() -> dict[str, float]:
    """Get effective RAM and CPU count."""

    total_ram = psutil.virtual_memory().total

    if os.name == "nt":
        # Windows
        cpus = psutil.cpu_count(logical=True) or 1

        try:
            affinity = psutil.Process().cpu_affinity()
            cpus = len(affinity)
        except AttributeError, OSError, psutil.Error:
            pass

    elif os.name == "posix":
        # Linux / macOS
        try:
            cpus = len(os.sched_getaffinity(0))
        except AttributeError, OSError:
            cpus = psutil.cpu_count(logical=True) or 1

    else:
        cpus = psutil.cpu_count(logical=True) or 1

    mem_limit = _cgroup_memory_limit()
    if mem_limit is not None:
        total_ram = min(total_ram, mem_limit)

    cpu_limit = _cgroup_cpu_limit()
    if cpu_limit is not None:
        cpus = min(cpus, cpu_limit)

    return {
        "ram_gb": total_ram / 1024**3,
        "cpus": float(cpus),
    }


def is_limited_memory(
    min_ram_gb: float = 2.0,
    min_cpus: float = 2.0,
) -> bool:
    """Check whether the system has insufficient resources."""

    res = get_system_resources()

    return res["ram_gb"] < min_ram_gb or res["cpus"] < min_cpus
