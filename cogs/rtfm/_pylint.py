from __future__ import annotations

import re
from typing import Literal

from discord.ext import commands

POSSIBLE_PYLINT_CODE = re.compile(r"([A-Z]\d{4})")


class PyLintConverter(commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"):
    code: str = commands.flag(description="The code to lint with pylint.")
    confidence: Literal["high", "control_flow", "inference_failure", "undefined", "inference"] = commands.flag(
        description="Only show messages with the given confidence level.", default="high"
    )
    disable: str | None = commands.flag(description="A comma-separated list of message IDs to disable.", default=None)
    enable: str | None = commands.flag(description="A comma-separated list of message IDs to enable.", default=None)


def validate_pylint_code(code: str) -> list[str]:
    return POSSIBLE_PYLINT_CODE.findall(code)


def validate_flag(flag: PyLintConverter) -> str:
    cmd_str = "pylint"
    if flag.confidence:
        cmd_str += f" --confidence={flag.confidence.upper()}"
    if flag.disable:
        codes = validate_pylint_code(flag.disable)
        if codes:
            cmd_str += f" --disable={','.join(codes)}"
    if flag.enable:
        codes = validate_pylint_code(flag.enable)
        if codes:
            cmd_str += f" --enable={','.join(codes)}"
    return f"{cmd_str} "
