from __future__ import annotations

from discord.ext import commands


class PyrightConverter(commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"):
    code: str


def validate_flag(flag: PyrightConverter) -> str:
    return "pyright"
