from __future__ import annotations

from typing import Literal, Optional

from discord.ext import commands
from utilities.converters import convert_bool


class GameCommandFlag(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    me: Optional[convert_bool] = False
    sort_by: Optional[str] = None
    order_by: Literal["asc", "desc"] = "desc"
    limit: int = 100
    _global: Optional[convert_bool] = commands.flag(name="global", default=False, aliases=["g", "all"])
