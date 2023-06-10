from __future__ import annotations

import re
from typing import List, Literal, Optional

from discord.ext import commands

POSSIBLE_PYLINT_CODE = re.compile(r"([A-Z]\d{4})")


class PyLintConverter(
    commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"
):
    code: str
    confidence: Literal[
        "HIGH", "CONTROL_FLOW", "INFERENCE_FAILURE", "INTERENCE", "UNDEFINED"
    ] = "HIGH"
    disable: Optional[str] = None
    enable: Optional[str] = None


def validate_pylint_code(code: str) -> List[str]:
    return POSSIBLE_PYLINT_CODE.findall(code)


def validate_flag(flag: PyLintConverter) -> str:
    cmd_str = "pylint"
    if flag.confidence:
        cmd_str += f" --confidence={flag.confidence}"
    if flag.disable:
        if codes := validate_pylint_code(flag.disable):
            cmd_str += f" --disable={','.join(codes)}"
    if flag.enable:
        if codes := validate_pylint_code(flag.enable):
            cmd_str += f" --enable={','.join(codes)}"
    return f"{cmd_str} "
