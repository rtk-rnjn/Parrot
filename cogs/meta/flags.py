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


class AuditFlag(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    guild: discord.Guild | None = None
    limit: int | None = 100
    action: str | None = None
    before: ShortTime | None = None
    after: ShortTime | None = None
    oldest_first: Annotated[bool | None, convert_bool] = False
    user: discord.User | discord.Member | None = None
