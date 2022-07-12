from __future__ import annotations

from typing import Optional

from discord.ext import commands
from utilities.converters import convert_bool
from utilities.time import ShortTime


class AutoWarn(
    commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"  # type: ignore
):
    enable: Optional[convert_bool] = True
    count: Optional[int] = None
    punish: Optional[str] = None
    duration: Optional[str] = None
    delete: Optional[convert_bool] = True


class WarnConfig(
    commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"  # type: ignore
):
    count: Optional[int] = None
    action: Optional[str] = None
    duration: Optional[str] = None
