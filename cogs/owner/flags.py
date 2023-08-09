from __future__ import annotations

from typing import Annotated

import discord
from discord.ext import commands
from utilities.converters import convert_bool
from utilities.time import ShortTime


class BanFlag(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    reason: str | None = None
    _global: Annotated[bool | None, convert_bool] = commands.flag(name="global", default=False)
    command: Annotated[bool | None, convert_bool] = False


class SubscriptionFlag(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    code: str | None = None
    expiry: ShortTime | None = None
    guild: discord.Guild | None = None
    uses: int | None = 0
    limit: int | None = 1
