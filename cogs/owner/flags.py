from __future__ import annotations


import discord
from discord.ext import commands
from utilities.converters import convert_bool
from utilities.time import ShortTime


class AuditFlag(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    guild: discord.Guild | None = None
    limit: int | None = 100
    action: str | None = None
    before: ShortTime | None = None
    after: ShortTime | None = None
    oldest_first: convert_bool | bool = False  # type: ignore
    user: discord.User | discord.Member | None = None


class BanFlag(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    reason: str | None = None
    _global: convert_bool | bool = commands.flag(name="global", default=False)  # type: ignore
    command: convert_bool | bool = False  # type: ignore


class SubscriptionFlag(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    code: str | None = None
    expiry: ShortTime | None = None
    guild: discord.Guild | None = None
    uses: int | None = 0
    limit: int | None = 1
