from __future__ import annotations

from typing import Annotated

import discord
from discord.ext import commands
from utilities.converters import convert_bool
from utilities.time import ShortTime


class AfkFlags(commands.FlagConverter, prefix="--", delimiter=" "):
    ignore_channel: tuple[discord.TextChannel, ...] = []
    _global: Annotated[bool | None, convert_bool] = commands.flag(name="global", default=False)
    _for: ShortTime | None = commands.flag(name="for", default=None)
    text: str | None = None
    after: ShortTime | None = None
