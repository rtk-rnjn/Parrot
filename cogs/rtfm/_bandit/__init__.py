from __future__ import annotations

import re
from typing import Annotated, Literal

from discord.ext import commands
from utilities.converters import convert_bool

POSSIBLE_BANDIT_CODE = re.compile(r"([A-Z]\d{2,3})")


class BanditConverter(commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"):
    code: str
    read: Annotated[bool | None, convert_bool] = None
    verbose: Annotated[bool | None, convert_bool] = None
    skip: str | None = None
    level: Literal["low", "medium", "high"] | None = None
    confidence: Literal["low", "medium", "high"] | None = None


def validate_bandit_code(code: str) -> list[str]:
    return POSSIBLE_BANDIT_CODE.findall(code)


def validate_flag(flag: BanditConverter) -> str:
    cmd = "bandit"
    if flag.read:
        cmd += " -r"
    if flag.verbose:
        cmd += " -v"

    if flag.skip:
        _sp = flag.skip.replace(" ", "")
        if codes := validate_bandit_code(_sp):
            cmd += f" --skip {','.join(codes)}"
    if flag.level:
        if flag.level == "low":
            cmd += " -l"
        elif flag.level == "medium":
            cmd += " -ll"
        elif flag.level == "high":
            cmd += " -lll"

    if flag.confidence:
        if flag.confidence == "low":
            cmd += " -i"
        elif flag.confidence == "medium":
            cmd += " -ii"
        elif flag.confidence == "high":
            cmd += " -iii"

    return f"{cmd} "
