from __future__ import annotations

from typing import Literal, Optional

from discord.ext import commands
from utilities.converters import convert_bool


class SokobanStatsFlag(
    commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "
):
    me: Optional[convert_bool] = False
    _global: Optional[convert_bool] = commands.flag(name="global", default=False, aliases=["g", "all"])
    sort_by: Literal["level", "time", "moves"] = "time"
    sort: Literal[1, 0] = 1
    limit: int = 100
