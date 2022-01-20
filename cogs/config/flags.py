from __future__ import annotations

from discord.ext import commands
from typing import Optional

from utilities.time import ShortTime
from utilities.converters import convert_bool


class AutoWarn(
    commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"
):
    enable: Optional[convert_bool] = True
    count: Optional[int] = None
    punish: Optional[str] = None
    duration: Optional[ShortTime] = None
    delete: Optional[convert_bool] = True


class warnConfig(
    commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"
):
    count: Optional[int] = None
    action: Optional[str] = None
    duration: Optional[ShortTime] = None
