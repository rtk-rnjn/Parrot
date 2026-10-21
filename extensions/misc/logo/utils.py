from __future__ import annotations

import math
import os


class LogoError(Exception):
    """Base exception for all Logo parser, interpreter, turtle, and limit errors."""


class LogoRuntimeError(LogoError):
    """Unified runtime and validation error raised across parser, turtle, and evaluator."""


class LogoSyntaxError(LogoRuntimeError):
    """Syntax or tokenization error (subclasses LogoRuntimeError for single-catch handling)."""


def _try_int(value: str | None, default: int, minimum: int = 1) -> int:
    if value is not None:
        try:
            parsed = int(value.strip())
            if parsed >= minimum:
                return parsed
        except ValueError:
            pass
    return default


def _try_float(value: str | None, default: float, minimum: float = 0.05) -> float:
    if value is not None:
        try:
            parsed = float(value.strip())
            if math.isfinite(parsed) and parsed >= minimum:
                return parsed
        except ValueError:
            pass
    return default


def get_max_source_length() -> int:
    return _try_int(os.environ.get("MAX_SOURCE_LENGTH"), 2_000)


def get_max_nesting_depth() -> int:
    return _try_int(os.environ.get("MAX_NESTING_DEPTH"), 50)


def get_max_operations() -> int:
    return _try_int(os.environ.get("MAX_OPERATIONS"), 200_000)


def get_max_repeat() -> int:
    return _try_int(os.environ.get("MAX_REPEAT"), 10_000)


def get_max_call_depth() -> int:
    return _try_int(os.environ.get("MAX_CALL_DEPTH"), 100)


def get_max_pen_width() -> int:
    return _try_int(os.environ.get("MAX_PEN_WIDTH"), 50)


def get_max_segments() -> int:
    return _try_int(os.environ.get("MAX_SEGMENTS"), 20_000)


def get_max_list_length() -> int:
    return _try_int(os.environ.get("MAX_LIST_LENGTH"), 1_000)


def get_max_word_length() -> int:
    return _try_int(os.environ.get("MAX_WORD_LENGTH"), 500)


def get_max_variables() -> int:
    return _try_int(os.environ.get("MAX_VARIABLES"), 500)


def get_max_procedures() -> int:
    return _try_int(os.environ.get("MAX_PROCEDURES"), 200)


def get_max_output_lines() -> int:
    return _try_int(os.environ.get("MAX_OUTPUT_LINES"), 200)


def get_max_fills() -> int:
    return _try_int(os.environ.get("MAX_FILLS"), 50)


def get_max_turtles() -> int:
    return _try_int(os.environ.get("MAX_TURTLES"), 16)


def get_max_gif_frames() -> int:
    return _try_int(os.environ.get("MAX_GIF_FRAMES"), 60)


def get_max_wall_time_seconds() -> float:
    return _try_float(os.environ.get("MAX_WALL_TIME_SECONDS"), 3.0)


def get_max_memory_mb() -> int:
    return _try_int(os.environ.get("MAX_MEMORY_MB"), 256)
