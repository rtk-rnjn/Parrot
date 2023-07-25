from __future__ import annotations


from discord.ext import commands
from utilities.converters import convert_bool


class AutoWarn(commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"):
    enable: convert_bool | None = True
    count: int | None = None
    punish: str | None = None
    duration: str | None = None
    delete: convert_bool | None = True


class WarnConfig(commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"):
    count: int | None = None
    action: str | None = None
    duration: str | None = None
