from __future__ import annotations

from typing import Literal, Annotated

from discord.ext import commands
from utilities.converters import convert_bool


class GameCommandFlag(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    me: Annotated[bool | None, convert_bool] = False
    sort_by: str | None = None
    order_by: Literal["asc", "desc"] = "desc"
    limit: int = 100
    _global: Annotated[bool | None, convert_bool] = commands.flag(name="global", default=False, aliases=["g", "all"])
