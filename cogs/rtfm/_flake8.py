from __future__ import annotations

import re
from typing import Annotated, Literal

from discord.ext import commands

POSSIBLE_FLAKE8_CODE = re.compile(r"([A-Z]\d{2,4})")


def convert_bool(text: str) -> bool:
    """True/False converter."""
    lowered = str(text).lower()
    true = lowered in {"yes", "y", "true", "t", "1", "enable", "on", "o", "ok", "sure", "yeah", "yup", "right"}
    false = lowered in {"no", "n", "false", "f", "0", "disable", "off", "none", "nah", "nope", "wrong"}
    if true:
        return True
    if false:
        return False

    raise commands.BadBoolArgument(lowered)


class Flake8Converter(commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"):
    code: str = commands.flag(description="The code to lint with flake8.")
    ignore: str | None = commands.flag(description="Comma-separated list of error codes to ignore.", default=None)
    select: str | None = commands.flag(description="Comma-separated list of error codes to select.", default=None)
    max_line_length: int | None = commands.flag(description="Maximum allowed line length.", default=None)
    max_doc_length: int | None = commands.flag(description="Maximum allowed docstring length.", default=None)
    max_complexity: int | None = commands.flag(description="Maximum allowed complexity.", default=None)

    statistics: Annotated[bool | None, convert_bool] = commands.flag(description="Enable statistics.", default=None)
    doctests: Annotated[bool | None, convert_bool] = commands.flag(description="Enable doctests.", default=None)
    color: Literal["auto", "always", "never"] | None = commands.flag(description="Set color output.", default=None)
    verbose: Annotated[bool | None, convert_bool] = commands.flag(description="Enable verbose output.", default=None)
    count: Annotated[bool | None, convert_bool] = commands.flag(description="Enable count output.", default=None)


def validate_flake8_code(code: str) -> list[str]:
    return POSSIBLE_FLAKE8_CODE.findall(code)


def validate_flag(flag: Flake8Converter) -> str:
    options = [
        option
        for enabled, option in (
            (flag.count, "--count"),
            (flag.verbose, "-v"),
            (flag.statistics, "--statistics"),
            (flag.doctests, "--doctests"),
        )
        if enabled
    ]
    if flag.color:
        options.append(f"--color={flag.color}")

    if flag.ignore:
        _ig = flag.ignore.replace(",", " ")
        if codes := validate_flake8_code(_ig):
            options.extend(("--ignore", ",".join(codes)))

    if flag.select:
        _sl = flag.select.replace(",", " ")
        if codes := validate_flake8_code(_sl):
            options.extend(("--select", ",".join(codes)))

    if flag.max_line_length:
        options.extend(("--max-line-length", str(flag.max_line_length)))

    if flag.max_doc_length:
        options.extend(("--max-doc-length", str(flag.max_doc_length)))

    if flag.max_complexity:
        options.extend(("--max-complexity", str(flag.max_complexity)))

    return f"{' '.join(('flake8', *options))} "
