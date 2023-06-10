from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Literal, Optional

import aiofiles

from discord.ext import commands

POSSIBLE_BANDIT_CODE = re.compile(r"([A-Z]\d{2,3})")


class BanditConverter(
    commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"
):
    code: str
    read: Optional[bool] = None
    verbose: Optional[bool] = None
    skip: Optional[str] = None
    level: Optional[Literal["low", "medium", "high"]] = None
    confidence: Optional[Literal["low", "medium", "high"]] = None


def validate_bandit_code(code: str) -> List[str]:
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