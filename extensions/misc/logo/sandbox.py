from __future__ import annotations

import asyncio
import base64
import json
import os
import resource
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .interpreter import LogoInterpreter
from .parser import LogoParser
from .turtle import Turtle
from .utils import LogoError, LogoRuntimeError, get_max_memory_mb, get_max_wall_time_seconds


@dataclass(frozen=True)
class SandboxResult:
    image_bytes: bytes
    output: tuple[str, ...]
    operations: int
    is_gif: bool = False


def _apply_resource_limits(memory_mb: int, cpu_seconds: int) -> None:
    try:
        mem_bytes = max(64, memory_mb) * 1024 * 1024
        try:
            _, hard_as = resource.getrlimit(resource.RLIMIT_AS)
            if hard_as == resource.RLIM_INFINITY or mem_bytes < hard_as:
                resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, hard_as))
        except ValueError, OSError:
            pass

        try:
            _, hard_cpu = resource.getrlimit(resource.RLIMIT_CPU)
            cpu_limit = max(1, cpu_seconds)
            if hard_cpu == resource.RLIM_INFINITY or cpu_limit < hard_cpu:
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, hard_cpu))
        except ValueError, OSError:
            pass
    except ImportError:
        pass


def _worker_entry() -> int:
    try:
        raw_payload = sys.stdin.buffer.read()
        req = json.loads(raw_payload.decode("utf-8"))
        source = str(req["source"])
        width = int(req.get("width", 1000))
        height = int(req.get("height", 800))
        seed = req.get("seed")
        animate_gif = bool(req.get("animate_gif", False))
        memory_mb = int(req.get("memory_mb", get_max_memory_mb()))
        cpu_seconds = int(req.get("cpu_seconds", 5))

        _apply_resource_limits(memory_mb, cpu_seconds)

        turtle = Turtle(width=width, height=height)
        interpreter = LogoInterpreter(turtle=turtle, seed=seed)
        program = LogoParser().parse(source)
        interpreter.execute(program)

        buf = turtle.render_gif() if animate_gif else turtle.render()

        resp = {
            "ok": True,
            "image_b64": base64.b64encode(buf.getvalue()).decode("ascii"),
            "output": interpreter.output,
            "operations": interpreter.operations,
            "is_gif": animate_gif,
        }
        sys.stdout.write(json.dumps(resp))
        sys.stdout.flush()
        return 0
    except LogoError as exc:
        # Safe user-facing Logo syntax or runtime error
        resp = {
            "ok": False,
            "error": str(exc),
        }
        sys.stdout.write(json.dumps(resp))
        sys.stdout.flush()
        return 0
    except MemoryError:
        resp = {
            "ok": False,
            "error": "Program exceeded memory limit.",
        }
        sys.stdout.write(json.dumps(resp))
        sys.stdout.flush()
        return 0
    except Exception:
        # Never leak raw internal exception details or file paths to Discord replies
        resp = {
            "ok": False,
            "error": "An internal error occurred while executing the Logo program.",
        }
        sys.stdout.write(json.dumps(resp))
        sys.stdout.flush()
        return 0


def run_logo_sandboxed(
    source: str,
    *,
    width: int = 1000,
    height: int = 800,
    seed: int | None = None,
    animate_gif: bool = False,
    timeout: float | None = None,
    memory_mb: int | None = None,
) -> SandboxResult:
    """
    Executes a Logo program inside an isolated subprocess with hard wall-clock
    timeout and OS memory/CPU limits. Safe to call from a thread pool or via
    `run_logo_sandboxed_async` in a Discord bot.
    """
    wall_timeout = timeout if timeout is not None else get_max_wall_time_seconds()
    mem_limit = memory_mb if memory_mb is not None else get_max_memory_mb()
    cpu_seconds = max(1, int(wall_timeout) + 2)

    payload = json.dumps(
        {
            "source": source,
            "width": width,
            "height": height,
            "seed": seed,
            "animate_gif": animate_gif,
            "memory_mb": mem_limit,
            "cpu_seconds": cpu_seconds,
        }
    ).encode("utf-8")

    package_parent = str(Path(__file__).resolve().parent.parent)
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONPATH": package_parent,
        "PYTHONIOENCODING": "utf-8",
    }
    for key in (
        "MAX_SOURCE_LENGTH",
        "MAX_NESTING_DEPTH",
        "MAX_OPERATIONS",
        "MAX_REPEAT",
        "MAX_CALL_DEPTH",
        "MAX_PEN_WIDTH",
        "MAX_SEGMENTS",
        "MAX_LIST_LENGTH",
        "MAX_WORD_LENGTH",
        "MAX_VARIABLES",
        "MAX_PROCEDURES",
        "MAX_OUTPUT_LINES",
        "MAX_FILLS",
        "MAX_TURTLES",
        "MAX_GIF_FRAMES",
        "MAX_WALL_TIME_SECONDS",
        "MAX_MEMORY_MB",
    ):
        if key in os.environ:
            env[key] = os.environ[key]

    try:
        completed = subprocess.run(
            [sys.executable, "-m", "py_logo.sandbox"],
            input=payload,
            capture_output=True,
            timeout=wall_timeout,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        msg = f"Program execution timed out after {wall_timeout:.1f}s."
        raise LogoRuntimeError(msg) from exc

    if not completed.stdout:
        msg = "Program terminated unexpectedly (resource limit or timeout exceeded)."
        raise LogoRuntimeError(msg)

    try:
        data = json.loads(completed.stdout.decode("utf-8"))
    except ValueError as exc:
        msg = "Program output was corrupted or exceeded limits."
        raise LogoRuntimeError(msg) from exc

    if not data.get("ok"):
        err_msg = str(data.get("error") or "Program execution failed.")
        raise LogoRuntimeError(err_msg)

    image_bytes = base64.b64decode(data["image_b64"])
    output_lines = tuple(str(line) for line in data.get("output", ()))
    operations = int(data.get("operations", 0))
    is_gif = bool(data.get("is_gif", False))

    return SandboxResult(
        image_bytes=image_bytes,
        output=output_lines,
        operations=operations,
        is_gif=is_gif,
    )


_DEFAULT_CONCURRENCY_SEMAPHORE = asyncio.Semaphore(4)


async def run_logo_sandboxed_async(
    source: str,
    *,
    width: int = 1000,
    height: int = 800,
    seed: int | None = None,
    animate_gif: bool = False,
    timeout: float | None = None,
    memory_mb: int | None = None,
    semaphore: asyncio.Semaphore | None = None,
) -> SandboxResult:
    """
    Async wrapper for Discord bots (`discord.py`). Bounds global concurrent
    renders via an `asyncio.Semaphore` and runs the subprocess off the event loop.
    """
    sem = semaphore or _DEFAULT_CONCURRENCY_SEMAPHORE
    async with sem:
        return await asyncio.to_thread(
            run_logo_sandboxed,
            source,
            width=width,
            height=height,
            seed=seed,
            animate_gif=animate_gif,
            timeout=timeout,
            memory_mb=memory_mb,
        )


if __name__ == "__main__":
    raise SystemExit(_worker_entry())
