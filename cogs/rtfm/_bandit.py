from __future__ import annotations

import re
from typing import Annotated, Literal

from discord.ext import commands

POSSIBLE_BANDIT_CODE = re.compile(r"([A-Z]\d{2,3})")


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


class BanditConverter(commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"):
    code: str = commands.flag(description="The code to lint with bandit.")
    read: Annotated[bool | None, convert_bool] = commands.flag(description="Read files recursively.", default=None)
    verbose: Annotated[bool | None, convert_bool] = commands.flag(description="Enable verbose output.", default=None)
    skip: str | None = commands.flag(description="Comma-separated list of codes to skip.", default=None)
    level: Literal["low", "medium", "high"] | None = commands.flag(description="Set the security level.", default=None)
    confidence: Literal["low", "medium", "high"] | None = commands.flag(description="Set the confidence level.", default=None)


def validate_bandit_code(code: str) -> list[str]:
    return POSSIBLE_BANDIT_CODE.findall(code)


def validate_flag(flag: BanditConverter) -> str:
    options = []
    if flag.read:
        options.append("-r")
    if flag.verbose:
        options.append("-v")

    if flag.skip:
        _sp = flag.skip.replace(" ", "")
        codes = validate_bandit_code(_sp)
        if codes:
            options.extend(("--skip", ",".join(codes)))
    if flag.level:
        options.append({"low": "-l", "medium": "-ll", "high": "-lll"}[flag.level])
    if flag.confidence:
        options.append({"low": "-i", "medium": "-ii", "high": "-iii"}[flag.confidence])
    return f"{' '.join(('bandit', *options))} "
