from __future__ import annotations

from typing import Literal

from discord.ext import commands
from utilities.converters import convert_bool


class GameCommandFlag(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    me: convert_bool | None = False
    sort_by: str | None = None
    order_by: Literal["asc", "desc"] = "desc"
    limit: int = 100
    _global: convert_bool | None = commands.flag(name="global", default=False, aliases=["g", "all"])
